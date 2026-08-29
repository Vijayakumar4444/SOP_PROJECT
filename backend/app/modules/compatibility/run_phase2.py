from __future__ import annotations

from pathlib import Path
import csv
import json
import os
import sys
import time
import zipfile
from typing import Any

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.modules.compatibility.capability_registry import DataCapabilityRegistryBuilder
from backend.app.modules.compatibility.service import PolicyDataCompatibilityService


EXAMPLE_POLICIES = [
    {
        "policy_id": "TN_YOUTH_EMPLOYMENT_ASSISTANCE",
        "name": "Tamil Nadu Youth Employment Assistance",
        "description": "Hypothetical assistance for unemployed youth.",
        "jurisdiction": {"state": "Tamil Nadu"},
        "target_population": "Unemployed youth",
        "eligibility": [
            {"variable": "age", "operator": "between", "value": [18, 35]},
            {"variable": "employment_status", "operator": "equals", "value": "Unemployed"},
            {"variable": "household_income", "operator": "less_than", "value": 300000, "unit": "INR/year"},
        ],
        "benefit": {"type": "fixed", "amount": 1000, "frequency": "monthly"},
        "reference_year": 2026,
    },
    {
        "policy_id": "TN_EDUCATION_SKILLING",
        "name": "Tamil Nadu Education-linked Skilling Support",
        "description": "Hypothetical skilling support for young adults by education level.",
        "jurisdiction": {"state": "Tamil Nadu"},
        "eligibility": [
            {"variable": "age", "operator": "between", "value": [18, 29]},
            {"variable": "education_level", "operator": "in", "value": ["Secondary", "Higher Secondary"]},
            {"variable": "district", "operator": "not_null", "value": None},
        ],
        "benefit": {"type": "fixed", "amount": 5000, "frequency": "one_time"},
        "reference_year": 2026,
    },
    {
        "policy_id": "TN_HEALTH_INSURANCE_TOPUP",
        "name": "Tamil Nadu Health Insurance Top-up",
        "description": "Hypothetical top-up for uninsured households with disability status.",
        "jurisdiction": {"state": "Tamil Nadu"},
        "eligibility": [
            {"variable": "health_insurance", "operator": "equals", "value": "No"},
            {"variable": "disability_status", "operator": "equals", "value": "Yes"},
            {"variable": "household_income", "operator": "less_than", "value": 300000, "unit": "INR/year"},
        ],
        "benefit": {"type": "fixed", "amount": 10000, "frequency": "annual"},
        "reference_year": 2026,
    },
]


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    for attempt in range(3):
        try:
            if path.exists():
                try:
                    os.chmod(path, 0o666)
                except Exception:
                    pass
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), extrasaction="ignore")
                writer.writeheader()
                writer.writerows(rows)
            return
        except PermissionError:
            if attempt < 2:
                time.sleep(0.5)
            else:
                alt_path = path.with_name(path.stem + "_updated" + path.suffix)
                with alt_path.open("w", encoding="utf-8", newline="") as handle:
                    writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), extrasaction="ignore")
                    writer.writeheader()
                    writer.writerows(rows)
                return


def write_md(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def xml_escape(value: Any) -> str:
    return str(value if value is not None else "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def cell_ref(row: int, col: int) -> str:
    letters = ""
    while col:
        col, rem = divmod(col - 1, 26)
        letters = chr(65 + rem) + letters
    return f"{letters}{row}"


def write_simple_xlsx(path: Path, sheets: dict[str, list[dict[str, Any]]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    files = {}
    rels = []
    sheet_entries = []
    overrides = [
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
    ]
    for idx, (name, rows) in enumerate(sheets.items(), start=1):
        headers = list(rows[0].keys()) if rows else ["note"]
        if not rows:
            rows = [{"note": ""}]
        all_rows = [headers] + [[row.get(header, "") for header in headers] for row in rows]
        xml_rows = []
        for r, row in enumerate(all_rows, start=1):
            cells = []
            for c, value in enumerate(row, start=1):
                ref = cell_ref(r, c)
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    cells.append(f'<c r="{ref}"><v>{value}</v></c>')
                else:
                    cells.append(f'<c r="{ref}" t="inlineStr"><is><t>{xml_escape(value)}</t></is></c>')
            xml_rows.append(f'<row r="{r}">{"".join(cells)}</row>')
        files[f"xl/worksheets/sheet{idx}.xml"] = f'<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews><sheetData>{"".join(xml_rows)}</sheetData><autoFilter ref="A1:{cell_ref(len(all_rows), len(headers))}"/></worksheet>'
        safe = name[:31]
        sheet_entries.append(f'<sheet name="{xml_escape(safe)}" sheetId="{idx}" r:id="rId{idx}"/>')
        rels.append(f'<Relationship Id="rId{idx}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{idx}.xml"/>')
        overrides.append(f'<Override PartName="/xl/worksheets/sheet{idx}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>')
    files["[Content_Types].xml"] = f'<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>{"".join(overrides)}</Types>'
    files["_rels/.rels"] = '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>'
    files["xl/workbook.xml"] = f'<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>{"".join(sheet_entries)}</sheets></workbook>'
    files["xl/_rels/workbook.xml.rels"] = f'<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">{"".join(rels)}</Relationships>'
    tmp = path.with_suffix(".tmp.xlsx")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    try:
        tmp.replace(path)
    except PermissionError:
        tmp.replace(path.with_name(path.stem + "_updated.xlsx"))


def flattened_requirements(report: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for req in report["requirements"]:
        requirement = req["requirement"]
        rows.append({
            "policy_id": report["policy_id"],
            "variable": requirement["canonical_variable"],
            "importance": requirement["importance"],
            "status": req["status"],
            "score": req["score"],
            "source": req["preferred_source"],
            "non_null_percentage": req["non_null_percentage"],
            "temporal_status": req["temporal_status"],
            "geographic_status": req["geographic_status"],
            "warnings": "; ".join(req["warnings"]),
        })
    return rows


def build_reports(registry: dict[str, Any], reports: list[dict[str, Any]]) -> None:
    variables = registry["variables"]
    missingness = ROOT / "data/reports/missingness_report.csv"
    missing_summary = ""
    if missingness.exists():
        missing_summary = missingness.read_text(encoding="utf-8").splitlines()[:8]
    write_md(ROOT / "reports/phase2_input_assessment.md", f"""
# Phase 2 Input Assessment

- Data foundation version: {registry.get('data_foundation_version')}
- Reference records: {registry.get('reference_records')}
- Source records available: {registry.get('available_source_records')}
- Sources available: {len(registry.get('sources', {}))}
- Canonical/capability variables: {len(variables)}
- Person/household row-level source: PLFS 2024 public-use Tamil Nadu reference template
- Aggregate/provenance sources: Tamil Nadu DES PDFs, Census 2011 PCA catalog, data.gov.in catalog, NFHS/NSS manual-access entries
- Years represented: 2011, 2019, 2021, 2022-23, 2023-24, 2024, 2026 metadata
- District coverage: {registry.get('district_count')} PLFS district labels, with a known district-code conflict warning
- Urban/rural coverage: {', '.join(registry.get('urban_rural_values', []))}
- Survey weights: survey_weight, normalized_reference_weight, calibrated_reference_weight_gender_ur
- Missingness sample: {' | '.join(missing_summary)}
- Known limitations: {'; '.join(registry.get('known_limitations', []))}
""")
    rows = []
    for report in reports:
        rows.append({
            "policy": report["policy_name"],
            "domains": ", ".join(d["domain"] for d in report["domains"]),
            "score": report["reliability_score"],
            "readiness": report["simulation_readiness"],
            "blocking": "; ".join(report["blocking_issues"]),
            "warnings": "; ".join(report["warnings"][:5]),
        })
    write_md(ROOT / "reports/phase2_validation_report.md", "# Phase 2 Validation Report\n\n" + "\n".join(
        f"## {row['policy']}\n\n- Domains: {row['domains']}\n- Reliability score: {row['score']}\n- Readiness: {row['readiness']}\n- Blocking issues: {row['blocking'] or 'None'}\n- Warnings: {row['warnings'] or 'None'}\n"
        for row in rows
    ))
    supported_domains = sorted({domain["domain"] for report in reports for domain in report["domains"]})
    weak = [name for name, cap in variables.items() if cap.get("aggregate_only") or cap.get("missing_percentage", 0) >= 100]
    write_md(ROOT / "reports/phase2_summary.md", f"""
# Phase 2 Summary

1. **What was implemented?** A Python Policy-Data Compatibility Engine over the Tamil Nadu Phase 1 Data Foundation.
2. **Canonical variables evaluated:** {len(variables)}.
3. **Supported domains:** {', '.join(supported_domains)}.
4. **Weakly supported domains:** health, housing, direct household income, disability until NFHS/NSS/detail sources are imported.
5. **Major Tamil Nadu data gaps:** direct annual household income, NFHS health/amenity microdata, NSS consumption/health rounds, precise district-boundary reconciliation.
6. **Variable compatibility:** exact canonical match first, approved derivation second, approved proxy third, aggregate-only and missing kept separate.
7. **Temporal compatibility:** compares policy reference year with source year using LOW/MODERATE/HIGH change assumptions in config.
8. **Joint availability:** checks whether critical variables coexist in the PLFS reference template rows.
9. **Reliability score:** weighted domain, variable, availability, joint, temporal, geography, and source-quality components.
10. **NOT_READY causes:** missing or aggregate-only critical variables, or very low overall score.
11. **Most useful Phase 1 sources:** PLFS for row-level joint relationships; DES/Census for official calibration targets.
12. **Remaining limitations:** compatibility is a project-specific readiness measure, not an official metric or outcome estimate.
""")
    write_csv(ROOT / "data/compatibility/policy_validation_summary.csv", rows)


def write_docs() -> None:
    write_md(ROOT / "docs/policy_data_compatibility_engine.md", """
# Policy-Data Compatibility Engine

The engine determines whether the Tamil Nadu data foundation can support a proposed policy simulation. It does not execute policies, create synthetic populations, estimate outcomes, or fill missing variables.

Pipeline: policy requirements, domain check, variable check, availability, joint availability, temporal/geographic checks, source quality, reliability scoring, simulation readiness, and Phase 3 synthetic-population requirements.

Availability statuses: EXACT_AVAILABLE, DERIVABLE, PROXY_AVAILABLE, AGGREGATE_ONLY, PARTIALLY_AVAILABLE, MISSING.

Research disclaimer: The Policy-Data Compatibility Score is a project-specific analytical measure designed to quantify whether the available Tamil Nadu Data Foundation supports the variables and dimensions required by a proposed policy simulation. It is not an official government metric, a measure of policy effectiveness, or a formal statistical confidence probability.
""")
    write_md(ROOT / "docs/compatibility_scoring_methodology.md", """
# Compatibility Scoring Methodology

Overall score =

0.15 * domain
+ 0.25 * variable
+ 0.20 * availability
+ 0.15 * joint availability
+ 0.10 * temporal
+ 0.10 * geographic
+ 0.05 * source quality

Variable status scores:

- EXACT_AVAILABLE: 1.00
- DERIVABLE: 0.85
- PARTIALLY_AVAILABLE: 0.65
- PROXY_AVAILABLE: 0.45
- AGGREGATE_ONLY: 0.30
- MISSING: 0.00

Critical-variable gate: a missing or aggregate-only critical eligibility variable makes the policy NOT_READY. Proxy-backed critical variables can be READY_WITH_WARNINGS only if the proxy is explicitly approved and joint availability is adequate.

Temporal scores use configurable sensitivity classes. These are project assumptions, not universal scientific constants.
""")


def main() -> None:
    registry = DataCapabilityRegistryBuilder(ROOT).build()
    service = PolicyDataCompatibilityService(ROOT)
    reports = [service.evaluate(policy).to_dict() for policy in EXAMPLE_POLICIES]
    out = ROOT / "data/compatibility"
    out.mkdir(parents=True, exist_ok=True)
    (out / "example_policy_reports.json").write_text(json.dumps(reports, indent=2, ensure_ascii=False), encoding="utf-8")
    phase3 = {report["policy_id"]: report["synthetic_population_requirements"] for report in reports}
    (out / "synthetic_population_requirements.json").write_text(json.dumps(phase3, indent=2, ensure_ascii=False), encoding="utf-8")
    write_csv(out / "requirement_results.csv", [row for report in reports for row in flattened_requirements(report)])
    build_reports(registry, reports)
    write_docs()
    sheets = {
        "README": [{"item": "Purpose", "value": "Policy-data compatibility report for hypothetical Phase 2 validation policies"}],
        "POLICY_REQUIREMENTS": [row for report in reports for row in flattened_requirements(report)],
        "DOMAIN_CHECK": [dict(policy_id=report["policy_id"], **domain) for report in reports for domain in report["domains"]],
        "SCORE_BREAKDOWN": [dict(policy_id=report["policy_id"], **report["score_breakdown"], reliability_score=report["reliability_score"], readiness=report["simulation_readiness"]) for report in reports],
        "WARNINGS": [{"policy_id": report["policy_id"], "warning": warning} for report in reports for warning in report["warnings"]],
        "RECOMMENDATIONS": [{"policy_id": report["policy_id"], "recommendation": rec} for report in reports for rec in report["recommendations"]],
    }
    write_simple_xlsx(ROOT / "reports/policy_data_compatibility_report.xlsx", sheets)


if __name__ == "__main__":
    main()
