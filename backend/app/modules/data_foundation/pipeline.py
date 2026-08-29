from __future__ import annotations

from datetime import date

from .calibration import calibration_diagnostics, gender_marginals, social_marginals, state_marginals, urban_rural_marginals, worker_marginals
from .derived_tables import distribution, generate_macro_state_profile, missingness, variable_dictionary
from .exports import write_simple_xlsx
from .io_utils import write_csv, write_json, write_md
from .plfs_loader import build_reference, load_tn_districts
from .quality import quality_profile
from .settings import DATA_DIRS, REFERENCE_COLUMNS, ROOT, SOURCE_ROWS, TARGET_RECORDS


def ensure_dirs() -> None:
    for folder in DATA_DIRS:
        (ROOT / folder).mkdir(parents=True, exist_ok=True)


def district_geography() -> list[dict]:
    return [{
        "state_code": "33", "state_name": "Tamil Nadu", "district_code": code, "district_name": name,
        "source_id": "SRC_PLFS_2024_OPENCITY_PUBLIC_MIRROR", "reference_year": 2024,
        "boundary_notes": "PLFS 2024 district code table; reconcile known boundary/code issues before exact district calibration.",
    } for code, name in sorted(load_tn_districts().items())]


def template_vs_official(records: list[dict]) -> list[dict]:
    out = []
    for field, official, category_field in [("gender", gender_marginals(), "gender"), ("urban_rural", urban_rural_marginals(), "urban_rural")]:
        counts = {}
        for row in records:
            cat = row.get(field, "")
            counts[cat] = counts.get(cat, 0) + 1
        total = len(records)
        for row in official:
            cat = row.get(category_field, "")
            obs = (counts.get(cat, 0) / total) if total else 0
            exp = float(row.get("proportion") or 0)
            out.append({
                "field": field, "category": cat, "template_count": counts.get(cat, 0),
                "template_proportion": round(obs, 4), "official_proportion": exp,
                "difference": round(obs - exp, 4), "official_source": row.get("source_id", ""),
            })
    return out


def write_reports(records: list[dict], source_rows: int) -> None:
    checks = quality_profile(records)
    quality_checks = [row for row in checks if row["check"].startswith("missing_required_") or row["check"].endswith("_count")]
    failed_checks = [row for row in quality_checks if row["status"] == "FAIL"]
    write_md(ROOT / "reports/phase1_summary.md", f"""# Phase 1 Summary: Data Foundation & Reference Template

- Built {len(records)} Tamil Nadu reference rows from {source_rows} PLFS source rows.
- Preserved survey weights and added normalized/calibrated reference weights.
- Stored DES/Census/data.gov.in sources separately as aggregate/provenance material.
- Generated reference, calibration, metadata, report, and Excel outputs.
- Data quality checks: {len(quality_checks) - len(failed_checks)} passed/warned, {len(failed_checks)} failed.
""")
    write_md(ROOT / "reports/data_quality_report.md", f"""
# Data Quality Report

- Reference rows: {len(records)}
- Tamil Nadu filter: ST == 33
- Missingness report: data/reports/missingness_report.csv
- Quality checks: data/reports/data_quality_checks.csv
- Raw files preserved under data/raw.
""")
    write_md(ROOT / "reports/data_source_collection_report.md", f"# Data Source Collection Report\n\nDocumented {len(SOURCE_ROWS)} trusted/candidate sources. PLFS is the row-level source; DES/Census/data.gov.in are aggregate/provenance sources.")
    write_md(ROOT / "reports/template_validation_report.md", "# Template Validation Report\n\nTemplate-vs-official comparison tables are exported to data/reports/template_vs_official.csv.")


def main() -> None:
    ensure_dirs()
    records, source_rows = build_reference()
    variables = variable_dictionary()
    macro_profile = generate_macro_state_profile(records)
    run_date = date.today().isoformat()
    source_rows_with_dates = [{**row, "download_date": row.get("download_date") or run_date} for row in SOURCE_ROWS]
    checks = quality_profile(records)
    write_csv(ROOT / "data/source_registry.csv", source_rows_with_dates)
    write_csv(ROOT / "data/reference/variable_dictionary.csv", variables)
    write_csv(ROOT / "data/processed/reference_template.csv", records, list(records[0].keys()) if records else REFERENCE_COLUMNS)
    write_csv(ROOT / "data/calibration/state_population_marginals.csv", state_marginals())
    write_csv(ROOT / "data/calibration/gender_marginals.csv", gender_marginals())
    write_csv(ROOT / "data/calibration/urban_rural_marginals.csv", urban_rural_marginals())
    write_csv(ROOT / "data/calibration/social_group_marginals.csv", social_marginals())
    write_csv(ROOT / "data/calibration/worker_marginals.csv", worker_marginals())
    write_csv(ROOT / "data/calibration/current_district_geography.csv", district_geography())
    write_csv(ROOT / "data/calibration/calibration_diagnostics.csv", calibration_diagnostics(records))
    write_csv(ROOT / "data/reports/missingness_report.csv", missingness(records))
    write_csv(ROOT / "data/reports/data_quality_checks.csv", checks)
    write_csv(ROOT / "data/reports/template_vs_official.csv", template_vs_official(records))
    write_csv(ROOT / "data/reports/tamil_nadu_state_macro_profile.csv", macro_profile)
    write_json(ROOT / "data/reference/template_metadata.json", {
        "name": "Tamil Nadu Population Reference Template", "version": "0.3.0-modular",
        "state": "Tamil Nadu", "target_records": TARGET_RECORDS, "actual_records": len(records),
        "available_plfs_tamil_nadu_source_rows": source_rows,
        "sources": [row["source_id"] for row in source_rows_with_dates],
        "raw_source_files": [str(item.relative_to(ROOT)) for item in (ROOT / "data/raw").rglob("*") if item.is_file()],
        "weight_columns": ["survey_weight", "normalized_reference_weight", "calibrated_reference_weight_gender_ur"],
        "quality_checks": {"total": len(checks), "failed": sum(1 for row in checks if row["status"] == "FAIL")},
        "limitations": ["PLFS-only row template; DES/Census/data.gov.in are aggregate/provenance sources; NFHS/NSS manual access pending."],
    })
    write_simple_xlsx(ROOT / "data/exports/tamil_nadu_population_reference_template.xlsx", {
        "00_README": [{"item": "Reference records", "value": len(records)}, {"item": "Warning", "value": "Reference rows are PLFS survey records, not the complete Tamil Nadu population."}],
        "01_SOURCE_REGISTRY": source_rows_with_dates, "02_VARIABLE_DICTIONARY": variables,
        "03_REFERENCE_TEMPLATE": records, "04_STATE_MARGINALS": state_marginals(),
        "05_TEMPLATE_DISTRICT_DIST": distribution(records, "district"), "06_TEMPLATE_AGE_DIST": distribution(records, "age_group"),
        "07_GENDER_MARGINALS": gender_marginals(), "08_URBAN_RURAL_MARGINALS": urban_rural_marginals(),
        "09_TEMPLATE_EDUCATION_DIST": distribution(records, "education_level"),
        "10_TEMPLATE_EMPLOYMENT_DIST": distribution(records, "employment_status"),
        "11_SOCIAL_MARGINALS": social_marginals(), "12_WORKER_MARGINALS": worker_marginals(),
        "13_CURRENT_GEOGRAPHY": district_geography(), "14_CALIBRATION_DIAGNOSTICS": calibration_diagnostics(records),
        "15_MISSINGNESS_REPORT": missingness(records), "16_QUALITY_CHECKS": checks,
        "17_TEMPLATE_VS_OFFICIAL": template_vs_official(records),
        "18_TN_STATE_MACRO_PROFILE": macro_profile,
    })
    write_reports(records, source_rows)
