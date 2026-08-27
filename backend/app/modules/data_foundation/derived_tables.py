from __future__ import annotations

from collections import Counter
from typing import Any

from .settings import REFERENCE_COLUMNS


def distribution(records: list[dict[str, Any]], field: str) -> list[dict[str, Any]]:
    counts = Counter(row.get(field, "") or "Missing" for row in records)
    return [{"dimension": field, "category": key, "template_count": value, "template_proportion": value / len(records) if records else ""} for key, value in sorted(counts.items())]


def missingness(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{
        "dataset": "reference_template", "variable": col, "row_count": len(records),
        "missing_count": sum(1 for row in records if row.get(col, "") in ("", None)),
        "missing_percentage": (sum(1 for row in records if row.get(col, "") in ("", None)) / len(records)) if records else "",
    } for col in REFERENCE_COLUMNS]


def variable_dictionary() -> list[dict[str, Any]]:
    rows = []
    for col in REFERENCE_COLUMNS:
        rows.append({
            "canonical_variable": col, "display_name": col.replace("_", " "),
            "description": f"Canonical {col.replace('_', ' ')} field for the Tamil Nadu reference template.",
            "data_type": "number" if any(token in col for token in ["income", "expenditure", "weight"]) else "string",
            "level": "HOUSEHOLD" if "household" in col or col == "relationship_to_head" else "PERSON",
            "unit": "INR or survey weight" if any(token in col for token in ["income", "expenditure", "weight"]) else "",
            "allowed_values": "", "minimum": 0 if any(token in col for token in ["age", "income", "expenditure", "weight", "size"]) else "",
            "maximum": 120 if col == "age" else "", "missing_allowed": "YES",
            "source_ids": "SRC_PLFS_2024_OPENCITY_PUBLIC_MIRROR", "source_variables": "See PLFS layout workbook in data/raw/plfs.",
            "harmonization_method": "Mapped by data_foundation harmonizer modules.",
            "derivation_method": "Derived from PLFS source fields or left null if unsupported.", "reference_year": "2024",
            "quality_flag": "A", "sensitivity_class": "MODERATE_OR_SENSITIVE" if col in {"social_group", "individual_income", "household_income", "consumption_expenditure"} else "LOW",
            "notes": "Do not impute unsupported variables during Phase 1.",
        })
    return rows
