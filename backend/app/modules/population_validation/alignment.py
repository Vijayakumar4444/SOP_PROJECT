from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


IDENTIFIER_FIELDS = {
    "reference_person_id",
    "reference_household_id",
    "source_record_id",
    "synthetic_person_id",
    "model_id",
    "population_id",
}
METADATA_FIELDS = {
    "primary_source_id",
    "reference_year",
    "record_quality_flag",
    "synthetic_data_label",
    "training_split",
}
WEIGHT_FIELDS = {"survey_weight", "normalized_reference_weight", "calibrated_reference_weight_gender_ur"}
NUMERIC_TYPES = {"integer", "number", "continuous", "float", "int"}
CATEGORICAL_TYPES = {"categorical", "ordinal", "boolean", "string"}


def load_canonical_schema(root: Path) -> dict[str, dict[str, Any]]:
    path = root / "config/canonical_schema.yaml"
    if not path.exists():
        return {}
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {item.get("canonical_variable"): item for item in payload.get("variables", []) if item.get("canonical_variable")}


def normalize_type(value: str | None) -> str:
    value = (value or "").lower()
    if value in {"integer", "int"}:
        return "integer"
    if value in {"number", "continuous", "float"}:
        return "continuous"
    if value in {"ordinal"}:
        return "ordinal"
    if value in {"boolean", "bool"}:
        return "boolean"
    if value in {"string"}:
        return "string"
    return "categorical"


def validation_family(variable_type: str) -> str:
    return "numerical" if normalize_type(variable_type) in {"integer", "continuous"} else "categorical"


def align_variables(
    reference_columns: list[str],
    synthetic_columns: list[str],
    variable_schema: dict[str, str] | None,
    canonical_schema: dict[str, dict[str, Any]] | None,
) -> dict[str, Any]:
    variable_schema = variable_schema or {}
    canonical_schema = canonical_schema or {}
    ref = set(reference_columns)
    syn = set(synthetic_columns)
    all_columns = sorted(ref | syn | set(variable_schema))
    validated = []
    skipped = []
    for column in all_columns:
        reason = None
        if column in IDENTIFIER_FIELDS:
            reason = "SKIPPED_IDENTIFIER"
        elif column in METADATA_FIELDS:
            reason = "SKIPPED_METADATA"
        elif column in WEIGHT_FIELDS:
            reason = "SKIPPED_WEIGHT"
        elif column not in ref:
            reason = "MISSING_IN_REFERENCE"
        elif column not in syn:
            reason = "MISSING_IN_SYNTHETIC"
        if reason:
            skipped.append({"variable": column, "status": reason})
            continue
        declared = variable_schema.get(column) or canonical_schema.get(column, {}).get("data_type") or "categorical"
        normalized = normalize_type(declared)
        if normalized == "string" and column not in variable_schema:
            skipped.append({"variable": column, "status": "INCOMPATIBLE_TYPE", "reason": "free text field without Phase 3 variable schema"})
            continue
        validated.append({
            "variable": column,
            "variable_type": normalized,
            "validation_family": validation_family(normalized),
            "level": canonical_schema.get(column, {}).get("level", "PERSON"),
            "allowed_values": canonical_schema.get(column, {}).get("allowed_values", []),
        })
    return {"validated_variables": validated, "skipped_variables": skipped}
