from __future__ import annotations

from typing import Any
from backend.app.modules.policy_engine.policy_model import PolicyDefinition


def validate_execution_constraints(
    policy: PolicyDefinition,
    results_records: list[dict[str, Any]] | Any,
    weighted_total_cost: float,
) -> tuple[bool, list[dict[str, Any]]]:
    if hasattr(results_records, "to_dict"):
        rows = list(results_records.to_dict(orient="records"))
    else:
        rows = list(results_records)

    report_items: list[dict[str, Any]] = []
    all_passed = True

    selected_records = [r for r in rows if r.get("is_selected_beneficiary", False)]
    sel_count = len(selected_records)

    # 1. Budget Constraint
    budget = policy.constraints.total_budget
    if budget is not None and budget > 0:
        passed = weighted_total_cost <= budget
        if not passed:
            all_passed = False
        report_items.append({
            "constraint_id": "C_BUDGET_LIMIT",
            "description": "Total estimated program cost must not exceed policy budget.",
            "status": "PASS" if passed else "FAIL",
            "observed_value": round(weighted_total_cost, 2),
            "allowed_value": budget,
            "severity": "WARNING" if not passed else "INFO",
            "affected_record_count": sel_count,
            "explanation": "Cost within budget." if passed else f"Weighted cost ({weighted_total_cost:.2f}) exceeded budget ({budget}).",
        })

    # 2. Maximum Beneficiaries Constraint
    max_ben = policy.constraints.maximum_beneficiaries
    if max_ben is not None and max_ben > 0:
        passed = sel_count <= max_ben
        if not passed:
            all_passed = False
        report_items.append({
            "constraint_id": "C_MAX_BENEFICIARIES",
            "description": "Selected beneficiary count must not exceed maximum beneficiaries cap.",
            "status": "PASS" if passed else "FAIL",
            "observed_value": sel_count,
            "allowed_value": max_ben,
            "severity": "WARNING" if not passed else "INFO",
            "affected_record_count": sel_count,
            "explanation": "Beneficiaries within capacity." if passed else f"Selected count ({sel_count}) exceeded cap ({max_ben}).",
        })

    # 3. Duplicate Household Benefit Constraint
    if rows and "is_household_primary_beneficiary" in rows[0]:
        hh_dupes = [r for r in selected_records if not r.get("is_household_primary_beneficiary", False)]
        has_dupes = len(hh_dupes) > 0
        if has_dupes:
            all_passed = False
        report_items.append({
            "constraint_id": "C_NO_DUPLICATE_HOUSEHOLD_BENEFIT",
            "description": "A single household must not receive duplicate household-level benefits.",
            "status": "PASS" if not has_dupes else "FAIL",
            "observed_value": len(hh_dupes),
            "allowed_value": 0,
            "severity": "CRITICAL" if has_dupes else "INFO",
            "affected_record_count": len(hh_dupes),
            "explanation": "Zero duplicate household allocations." if not has_dupes else f"Found {len(hh_dupes)} duplicate household allocations.",
        })

    # 4. Non-negative Benefit Values
    neg_benefits = [r for r in rows if r.get("benefit_amount", 0.0) < 0]
    has_neg = len(neg_benefits) > 0
    if has_neg:
        all_passed = False
    report_items.append({
        "constraint_id": "C_NON_NEGATIVE_BENEFITS",
        "description": "All benefit amounts must be non-negative.",
        "status": "PASS" if not has_neg else "FAIL",
        "observed_value": len(neg_benefits),
        "allowed_value": 0,
        "severity": "CRITICAL" if has_neg else "INFO",
        "affected_record_count": len(neg_benefits),
        "explanation": "All benefits are non-negative." if not has_neg else f"Found {len(neg_benefits)} negative benefits.",
    })

    return all_passed, report_items
