from __future__ import annotations

from typing import Any

from .settings import REFERENCE_COLUMNS, TN_STATE_CODE

REQUIRED_COLUMNS = [
    "reference_person_id",
    "reference_household_id",
    "source_record_id",
    "primary_source_id",
    "state",
    "state_code",
    "age",
    "gender",
    "survey_weight",
    "normalized_reference_weight",
    "calibrated_reference_weight_gender_ur",
]


def _number(value: Any) -> float | None:
    try:
        if value in ("", None):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def quality_profile(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    duplicate_person_ids = _duplicate_count(records, "reference_person_id")
    duplicate_source_ids = _duplicate_count(records, "source_record_id")
    invalid_age = 0
    invalid_household_size = 0
    invalid_weight = 0
    non_tn_rows = 0

    invalid_child_occupation = 0
    invalid_unemployed_income = 0
    invalid_govt_sector = 0

    for row in records:
        age = _number(row.get("age"))
        household_size = _number(row.get("household_size"))
        weight = _number(row.get("survey_weight"))
        if age is None or age < 0 or age > 120:
            invalid_age += 1
        if household_size is None or household_size < 1:
            invalid_household_size += 1
        if weight is None or weight <= 0:
            invalid_weight += 1
        if str(row.get("state_code", "")).strip() != TN_STATE_CODE or row.get("state") != "Tamil Nadu":
            non_tn_rows += 1

        # Master Population Schema validation rules
        if age is not None and age < 18 and row.get("occupation_category") in {"DOCTOR", "LAWYER", "TEACHER", "GOVERNMENT_EMPLOYEE", "POLICE", "DEFENCE", "RETIRED"}:
            invalid_child_occupation += 1
        if row.get("employment_status") == "UNEMPLOYED" and _number(row.get("monthly_income") or 0) != 0:
            invalid_unemployed_income += 1
        if row.get("is_government_employee") and row.get("employment_sector") not in {"GOVERNMENT", "PUBLIC_SECTOR"}:
            invalid_govt_sector += 1

    checks = [
        ("row_count", len(records), "PASS" if records else "FAIL", "Reference template must contain rows."),
        ("duplicate_reference_person_id_count", duplicate_person_ids, "PASS" if duplicate_person_ids == 0 else "FAIL", "Reference person IDs must be unique."),
        ("duplicate_source_record_id_count", duplicate_source_ids, "PASS" if duplicate_source_ids == 0 else "WARN", "Duplicate source IDs indicate source reuse or sampling collisions."),
        ("invalid_age_count", invalid_age, "PASS" if invalid_age == 0 else "FAIL", "Age must be numeric from 0 to 120."),
        ("invalid_household_size_count", invalid_household_size, "PASS" if invalid_household_size == 0 else "FAIL", "Household size must be at least 1."),
        ("invalid_survey_weight_count", invalid_weight, "PASS" if invalid_weight == 0 else "FAIL", "Survey weight must be positive."),
        ("non_tamil_nadu_row_count", non_tn_rows, "PASS" if non_tn_rows == 0 else "FAIL", "Rows must be filtered to Tamil Nadu."),
        ("invalid_child_occupation_count", invalid_child_occupation, "PASS" if invalid_child_occupation == 0 else "FAIL", "Children under 18 must not hold professional adult occupations."),
        ("invalid_unemployed_income_count", invalid_unemployed_income, "PASS" if invalid_unemployed_income == 0 else "FAIL", "Unemployed individuals must have 0 current monthly income."),
        ("invalid_govt_sector_count", invalid_govt_sector, "PASS" if invalid_govt_sector == 0 else "FAIL", "Government employees must belong to GOVERNMENT or PUBLIC_SECTOR employment sector."),
    ]

    required_missing = 0
    for column in REQUIRED_COLUMNS:
        missing = sum(1 for row in records if row.get(column, "") in ("", None))
        required_missing += missing
        checks.append((f"missing_required_{column}_count", missing, "PASS" if missing == 0 else "FAIL", f"{column} is required for downstream compatibility."))

    unknown_columns = sorted(set().union(*(row.keys() for row in records)) - set(REFERENCE_COLUMNS)) if records else []
    checks.append(("unknown_column_count", len(unknown_columns), "PASS" if not unknown_columns else "WARN", "; ".join(unknown_columns)))
    checks.append(("missing_required_total_count", required_missing, "PASS" if required_missing == 0 else "FAIL", "Total missing cells across required columns."))

    return [
        {"check": name, "value": value, "status": status, "notes": notes}
        for name, value, status, notes in checks
    ]


def _duplicate_count(records: list[dict[str, Any]], field: str) -> int:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for row in records:
        value = str(row.get(field, "")).strip()
        if not value:
            continue
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return len(duplicates)
