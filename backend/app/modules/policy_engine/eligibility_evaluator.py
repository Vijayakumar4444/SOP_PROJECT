from __future__ import annotations

from typing import Any
from collections import defaultdict

from backend.app.modules.policy_engine.policy_model import (
    MissingValueBehavior,
    PolicyDefinition,
    TargetUnit,
)
from backend.app.modules.policy_engine.rule_engine import evaluate_logic_group


def evaluate_population_eligibility(
    policy: PolicyDefinition,
    records: list[dict[str, Any]] | Any,
    run_id: str,
    weight_col: str = "calibration_weight",
    person_id_col: str = "synthetic_person_id",
    household_id_col: str = "synthetic_household_id",
) -> list[dict[str, Any]]:
    if hasattr(records, "to_dict"):
        rows = [dict(r) for r in records.to_dict(orient="records")]
    else:
        rows = [dict(r) for r in records]

    if not rows:
        return []

    sample_row = rows[0]

    # Resolve person_id_col
    if person_id_col not in sample_row:
        for candidate in ["person_id", "reference_person_id", "id"]:
            if candidate in sample_row:
                person_id_col = candidate
                break

    # Resolve household_id_col
    if household_id_col not in sample_row:
        for candidate in ["household_id", "reference_household_id"]:
            if candidate in sample_row:
                household_id_col = candidate
                break

    # Resolve weight_col
    if weight_col not in sample_row:
        for candidate in ["population_weight", "calibrated_weight", "survey_weight", "base_weight"]:
            if candidate in sample_row:
                weight_col = candidate
                break

    # Fill default IDs / weights if needed
    for i, row in enumerate(rows):
        if person_id_col not in row or not row[person_id_col]:
            row[person_id_col] = f"TN-P-{i+1:08d}"
        if household_id_col not in row or not row[household_id_col]:
            row[household_id_col] = f"TN-HH-{i+1:08d}"
        if weight_col not in row or row[weight_col] is None or row[weight_col] == "":
            row[weight_col] = 1.0
        else:
            row[weight_col] = float(row[weight_col])

    missing_behavior = policy.constraints.missing_value_behavior

    if policy.target_unit == TargetUnit.HOUSEHOLD:
        return _evaluate_household_level(
            policy, rows, run_id, missing_behavior, person_id_col, household_id_col, weight_col
        )
    else:
        return _evaluate_person_level(
            policy, rows, run_id, missing_behavior, person_id_col, household_id_col, weight_col
        )


def _evaluate_person_level(
    policy: PolicyDefinition,
    rows: list[dict[str, Any]],
    run_id: str,
    missing_behavior: MissingValueBehavior,
    person_id_col: str,
    household_id_col: str,
    weight_col: str,
) -> list[dict[str, Any]]:
    evaluated_rows: list[dict[str, Any]] = []

    for row in rows:
        r = dict(row)
        person_id = str(r.get(person_id_col, ""))
        household_id = str(r.get(household_id_col, ""))
        weight_val = float(r.get(weight_col, 1.0))

        elig_passed, p_ids, f_ids = evaluate_logic_group(r, policy.eligibility, missing_behavior)
        excl_triggered, ex_p_ids, _ = evaluate_logic_group(r, policy.exclusions, missing_behavior)

        is_excluded = False
        if len(policy.exclusions.rules) > 0 or len(policy.exclusions.groups) > 0:
            is_excluded = excl_triggered

        is_eligible = elig_passed and (not is_excluded)

        if is_excluded:
            status = "EXCLUDED_BY_POLICY"
            reason_codes = ["EXCLUDED_BY_POLICY"] + ex_p_ids
        elif elig_passed:
            status = "ELIGIBLE_ALL_RULES_PASSED"
            reason_codes = ["ELIGIBLE_ALL_RULES_PASSED"]
        else:
            status = "INELIGIBLE_RULES_FAILED"
            reason_codes = [f"FAILED_{rid}" for rid in f_ids] if f_ids else ["INELIGIBLE"]

        r["policy_id"] = policy.policy_id
        r["policy_version"] = policy.version
        r["run_id"] = run_id
        r["person_id"] = person_id
        r["household_id"] = household_id
        r["is_eligible"] = is_eligible
        r["is_excluded"] = is_excluded
        r["eligibility_status"] = status
        r["eligibility_reason_codes"] = ";".join(reason_codes)
        r["passed_rule_ids"] = ";".join(p_ids)
        r["failed_rule_ids"] = ";".join(f_ids)
        r["population_weight"] = weight_val

        evaluated_rows.append(r)

    return evaluated_rows


def _evaluate_household_level(
    policy: PolicyDefinition,
    rows: list[dict[str, Any]],
    run_id: str,
    missing_behavior: MissingValueBehavior,
    person_id_col: str,
    household_id_col: str,
    weight_col: str,
) -> list[dict[str, Any]]:
    # Evaluate representative head of household once per household
    hh_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        hh_groups[str(r.get(household_id_col, ""))].append(r)

    hh_eval_map: dict[str, tuple[bool, bool, str, list[str], list[str], list[str]]] = {}

    for hh_id, group in hh_groups.items():
        head_row = group[0]
        elig_passed, p_ids, f_ids = evaluate_logic_group(head_row, policy.eligibility, missing_behavior)
        excl_triggered, ex_p_ids, _ = evaluate_logic_group(head_row, policy.exclusions, missing_behavior)

        is_excluded = False
        if len(policy.exclusions.rules) > 0 or len(policy.exclusions.groups) > 0:
            is_excluded = excl_triggered

        is_eligible = elig_passed and (not is_excluded)

        if is_excluded:
            status = "EXCLUDED_BY_POLICY"
            reason_codes = ["EXCLUDED_BY_POLICY"] + ex_p_ids
        elif elig_passed:
            status = "ELIGIBLE_ALL_RULES_PASSED"
            reason_codes = ["ELIGIBLE_ALL_RULES_PASSED"]
        else:
            status = "INELIGIBLE_RULES_FAILED"
            reason_codes = [f"FAILED_{rid}" for rid in f_ids] if f_ids else ["INELIGIBLE"]

        hh_eval_map[hh_id] = (is_eligible, is_excluded, status, reason_codes, p_ids, f_ids)

    evaluated_rows = _evaluate_person_level(policy, rows, run_id, missing_behavior, person_id_col, household_id_col, weight_col)

    seen_hh: set[str] = set()
    for r in evaluated_rows:
        hh_id = str(r["household_id"])
        hh_res = hh_eval_map.get(hh_id, (False, False, "INELIGIBLE", [], [], []))
        is_elig, is_excl, status, _, _, _ = hh_res

        r["is_eligible"] = is_elig
        r["is_excluded"] = is_excl
        r["eligibility_status"] = status

        if is_elig and hh_id not in seen_hh:
            seen_hh.add(hh_id)
            r["is_household_primary_beneficiary"] = True
        else:
            r["is_household_primary_beneficiary"] = False

    return evaluated_rows
