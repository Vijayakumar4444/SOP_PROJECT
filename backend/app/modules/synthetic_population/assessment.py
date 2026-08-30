from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any
import csv
import json

from backend.app.modules.data_foundation.io_utils import write_md


ROOT = Path(__file__).resolve().parents[4]
REFERENCE_PATHS = [
    "data/processed/reference_template.parquet",
    "data/processed/reference_template.csv",
]
IDENTIFIER_FIELDS = {"reference_person_id", "reference_household_id", "source_record_id"}
METADATA_FIELDS = {"primary_source_id", "reference_year", "record_quality_flag"}
WEIGHT_FIELDS = {"survey_weight", "normalized_reference_weight", "calibrated_reference_weight_gender_ur"}
ORDINAL_HINTS = {"age_group", "education_level", "income_band"}
BOOLEAN_HINTS = {"is_youth", "is_elderly", "is_unemployed"}
DERIVED_FIELDS = {"age_group"}


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def actual_reference_path(root: Path) -> Path:
    for relative in REFERENCE_PATHS:
        path = root / relative
        if path.exists():
            return path
    return root / REFERENCE_PATHS[-1]


def schema_variables(root: Path) -> dict[str, dict[str, str]]:
    rows = read_csv(root / "data/reference/variable_dictionary.csv")
    return {row.get("canonical_variable", ""): row for row in rows if row.get("canonical_variable")}


def policy_requirements(root: Path) -> dict[str, set[str]]:
    payload = read_json(root / "data/compatibility/synthetic_population_requirements.json")
    required: set[str] = set()
    critical: set[str] = set()
    optional: set[str] = set()
    proxies: set[str] = set()
    derivations: set[str] = set()
    calibration: set[str] = set()
    for item in payload.values():
        req = item.get("synthetic_population_requirements", {})
        required.update(req.get("required_variables", []))
        critical.update(req.get("critical_variables", []))
        optional.update(req.get("optional_variables", []))
        proxies.update(req.get("approved_proxies", []))
        derivations.update(req.get("approved_derivations", []))
        calibration.update(req.get("calibration_variables", []))
    return {
        "required": required,
        "critical": critical,
        "optional": optional,
        "proxies": proxies,
        "derivations": derivations,
        "calibration": calibration,
    }


def classify_variable(name: str, spec: dict[str, str]) -> str:
    dtype = (spec.get("data_type") or "").lower()
    if name in IDENTIFIER_FIELDS:
        return "identifier"
    if name in METADATA_FIELDS:
        return "metadata"
    if name in WEIGHT_FIELDS:
        return "weight"
    if name in BOOLEAN_HINTS:
        return "boolean"
    if name in ORDINAL_HINTS:
        return "ordinal"
    if dtype in {"integer", "int"}:
        return "integer"
    if dtype in {"number", "float", "continuous"}:
        return "continuous"
    return "categorical"


def missingness(rows: list[dict[str, str]], columns: list[str]) -> dict[str, dict[str, Any]]:
    total = len(rows)
    result = {}
    for column in columns:
        count = sum(1 for row in rows if row.get(column, "") in {"", None})
        result[column] = {
            "missing_count": count,
            "missing_percentage": round((count / total) * 100, 4) if total else 0,
        }
    return result


def category_profile(rows: list[dict[str, str]], columns: list[str]) -> tuple[dict[str, int], dict[str, list[str]]]:
    high_cardinality = {}
    rare_categories = {}
    total = len(rows)
    for column in columns:
        counts = Counter(row.get(column, "") or "Missing" for row in rows)
        unique = len(counts)
        if unique > 50 or (total and unique / total > 0.05):
            high_cardinality[column] = unique
        rare = [f"{value} ({count}, {round((count / total) * 100, 3)}%)" for value, count in counts.items() if total and count / total < 0.01]
        if rare:
            rare_categories[column] = sorted(rare)[:12]
    return high_cardinality, rare_categories


def official_marginals(root: Path) -> list[str]:
    folder = root / "data/calibration"
    if not folder.exists():
        return []
    return sorted(str(path.relative_to(root)).replace("\\", "/") for path in folder.glob("*.csv"))


def format_list(values: list[str] | set[str]) -> str:
    values = sorted(value for value in values if value)
    return ", ".join(values) if values else "None"


def build_assessment(root: Path = ROOT) -> str:
    reference_path = actual_reference_path(root)
    rows = read_csv(reference_path)
    columns = list(rows[0].keys()) if rows else []
    schema = schema_variables(root)
    registry = read_json(root / "data/metadata/data_capability_registry.json")
    metadata = read_json(root / "data/reference/template_metadata.json")
    requirements = policy_requirements(root)
    miss = missingness(rows, columns)

    classified = {name: classify_variable(name, schema.get(name, {})) for name in columns}
    categorical = [name for name, kind in classified.items() if kind == "categorical"]
    high_cardinality, rare_categories = category_profile(rows, categorical)
    household_ids = {row.get("reference_household_id", "") for row in rows if row.get("reference_household_id")}
    reference_years = sorted({str(row.get("reference_year", "")) for row in rows if row.get("reference_year")})
    person_level = [name for name in columns if schema.get(name, {}).get("level", "PERSON") == "PERSON"]
    household_level = [name for name in columns if schema.get(name, {}).get("level") == "HOUSEHOLD"]
    derived = sorted(requirements["derivations"] | (DERIVED_FIELDS & set(columns)))
    mode = "PERSON-LEVEL SYNTHESIS"
    mode_reason = (
        "Phase 1 contains household IDs and household-size attributes, but there is no separate validated household table "
        "and several household-level variables are empty or proxy-limited. Phase 3 should therefore start with a person-level MVP."
    )

    lines = [
        "# Phase 3 Input Assessment",
        "",
        "## Decision",
        "",
        f"- Implementation mode: {mode}",
        f"- Rationale: {mode_reason}",
        "",
        "## Phase 1 Reference Data",
        "",
        f"- Reference template path: {reference_path.relative_to(root).as_posix()}",
        f"- Reference row count: {len(rows)}",
        f"- Reference household count: {len(household_ids)}",
        f"- Template metadata version: {metadata.get('version', 'UNKNOWN')}",
        f"- Data foundation version: {registry.get('data_foundation_version', 'UNKNOWN')}",
        f"- Geographic coverage: {registry.get('state', 'Tamil Nadu')}; {registry.get('district_count', 0)} district labels; urban/rural values: {format_list(registry.get('urban_rural_values', []))}",
        f"- Reference years: {format_list(reference_years)}",
        "",
        "## Canonical Variables",
        "",
        f"- Canonical variables in reference template: {len(columns)}",
        f"- Person-level variables: {format_list(person_level)}",
        f"- Household-level variables: {format_list(household_level)}",
        f"- Identifier variables: {format_list(name for name, kind in classified.items() if kind == 'identifier')}",
        f"- Metadata variables: {format_list(name for name, kind in classified.items() if kind == 'metadata')}",
        f"- Continuous variables: {format_list(name for name, kind in classified.items() if kind == 'continuous')}",
        f"- Integer variables: {format_list(name for name, kind in classified.items() if kind == 'integer')}",
        f"- Categorical variables: {format_list(name for name, kind in classified.items() if kind == 'categorical')}",
        f"- Ordinal variables: {format_list(name for name, kind in classified.items() if kind == 'ordinal')}",
        f"- Boolean variables: {format_list(name for name, kind in classified.items() if kind == 'boolean')}",
        f"- Derived variables: {format_list(derived)}",
        "",
        "## Phase 2 Policy Requirements",
        "",
        f"- Policy-required variables: {format_list(requirements['required'])}",
        f"- Critical variables: {format_list(requirements['critical'])}",
        f"- Optional analysis variables: {format_list(requirements['optional'])}",
        f"- Approved derivations: {format_list(requirements['derivations'])}",
        f"- Approved proxies requiring explicit acknowledgement: {format_list(requirements['proxies'])}",
        f"- Calibration variables requested for later phases: {format_list(requirements['calibration'])}",
        "",
        "## Weights And Missingness",
        "",
        f"- Survey-weight fields: {format_list(name for name, kind in classified.items() if kind == 'weight')}",
        "- Missingness summary:",
    ]
    for name in columns:
        item = miss[name]
        if item["missing_count"]:
            lines.append(f"  - {name}: {item['missing_count']} missing ({item['missing_percentage']}%)")
    if all(not item["missing_count"] for item in miss.values()):
        lines.append("  - No missing values detected.")

    lines.extend([
        "",
        "## Category Diagnostics",
        "",
        f"- High-cardinality variables: {', '.join(f'{k} ({v} values)' for k, v in sorted(high_cardinality.items())) if high_cardinality else 'None'}",
        "- Rare categories below 1%:",
    ])
    if rare_categories:
        for name, values in sorted(rare_categories.items()):
            lines.append(f"  - {name}: {'; '.join(values)}")
    else:
        lines.append("  - None")

    lines.extend([
        "",
        "## Official Marginals",
        "",
        f"- Available calibration/marginal files: {format_list(official_marginals(root))}",
        "",
        "## Known Limitations",
        "",
        f"- {metadata.get('limitations', ['No metadata limitations found.'])[0] if metadata.get('limitations') else 'No metadata limitations found.'}",
        "- Synthetic records must be explicitly labelled artificial and must not be treated as real residents or survey respondents.",
        "- Aggregate-only variables must not be expanded into person-level values in Phase 3 without an explicit approved method.",
        "- Full population validation, model selection, calibration/reweighting, policy execution, and Monte Carlo simulation belong to later phases.",
    ])
    return "\n".join(lines) + "\n"


def write_phase3_input_assessment(root: Path = ROOT) -> Path:
    path = root / "reports/phase3_input_assessment.md"
    write_md(path, build_assessment(root))
    return path



