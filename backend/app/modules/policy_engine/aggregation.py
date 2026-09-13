from __future__ import annotations

from typing import Any
from collections import defaultdict
from backend.app.modules.policy_engine.policy_model import PolicyDefinition


def compute_policy_aggregates(
    policy: PolicyDefinition,
    results_records: list[dict[str, Any]] | Any,
    cost_summary: dict[str, Any],
    weight_col: str = "population_weight",
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if hasattr(results_records, "to_dict"):
        rows = list(results_records.to_dict(orient="records"))
    else:
        rows = list(results_records)

    total_evaluated = len(rows)
    total_eligible = sum(1 for r in rows if r.get("is_eligible", False))
    total_excluded = sum(1 for r in rows if r.get("is_excluded", False))
    total_beneficiaries = sum(1 for r in rows if r.get("is_selected_beneficiary", False))
    total_ineligible = total_evaluated - total_eligible

    weighted_total_pop = sum(float(r.get(weight_col, 1.0)) for r in rows)
    weighted_eligible_pop = sum(float(r.get(weight_col, 1.0)) for r in rows if r.get("is_eligible", False))
    weighted_beneficiary_pop = sum(float(r.get(weight_col, 1.0)) for r in rows if r.get("is_selected_beneficiary", False))

    unweighted_eligibility_rate = round(total_eligible / total_evaluated, 4) if total_evaluated > 0 else 0.0
    weighted_eligibility_rate = round(weighted_eligible_pop / weighted_total_pop, 4) if weighted_total_pop > 0 else 0.0

    unweighted_coverage_rate = round(total_beneficiaries / total_eligible, 4) if total_eligible > 0 else 0.0
    weighted_coverage_rate = round(weighted_beneficiary_pop / weighted_eligible_pop, 4) if weighted_eligible_pop > 0 else 0.0

    budget = policy.constraints.total_budget
    total_cost = cost_summary.get("weighted_total_cost", 0.0)
    budget_used = min(total_cost, budget) if budget is not None else total_cost
    budget_remaining = max(0.0, budget - total_cost) if budget is not None else None

    overall_summary = {
        "policy_id": policy.policy_id,
        "policy_name": policy.name,
        "policy_version": policy.version,
        "target_unit": policy.target_unit.value,
        "total_evaluated_records": total_evaluated,
        "unweighted_eligible_records": total_eligible,
        "unweighted_ineligible_records": total_ineligible,
        "unweighted_excluded_records": total_excluded,
        "unweighted_selected_beneficiaries": total_beneficiaries,
        "weighted_total_population": round(weighted_total_pop, 2),
        "weighted_eligible_population": round(weighted_eligible_pop, 2),
        "weighted_beneficiary_population": round(weighted_beneficiary_pop, 2),
        "unweighted_eligibility_rate": unweighted_eligibility_rate,
        "weighted_eligibility_rate": weighted_eligibility_rate,
        "unweighted_coverage_rate": unweighted_coverage_rate,
        "weighted_coverage_rate": weighted_coverage_rate,
        "total_estimated_program_cost_inr": total_cost,
        "average_annual_benefit_inr": cost_summary.get("average_annual_benefit", 0.0),
        "total_budget_inr": budget,
        "budget_used_inr": budget_used,
        "budget_remaining_inr": budget_remaining,
        "weight_column_used": weight_col,
    }

    # Demographic Breakdowns
    breakdown_rows: list[dict[str, Any]] = []
    demographic_fields = ["district", "urban_rural", "gender", "social_group", "education_level", "employment_status"]

    if rows:
        sample = rows[0]
        for dim in demographic_fields:
            if dim not in sample:
                continue

            grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for r in rows:
                grouped[str(r.get(dim, "Unknown"))].append(r)

            for cat_val, grp in grouped.items():
                eval_cnt = len(grp)
                elig_cnt = sum(1 for r in grp if r.get("is_eligible", False))
                ben_cnt = sum(1 for r in grp if r.get("is_selected_beneficiary", False))

                w_tot = sum(float(r.get(weight_col, 1.0)) for r in grp)
                w_elig = sum(float(r.get(weight_col, 1.0)) for r in grp if r.get("is_eligible", False))
                w_ben = sum(float(r.get(weight_col, 1.0)) for r in grp if r.get("is_selected_beneficiary", False))
                w_cost = sum(float(r.get("estimated_policy_cost", 0.0)) for r in grp if r.get("is_selected_beneficiary", False))

                breakdown_rows.append({
                    "dimension": dim,
                    "category": cat_val,
                    "unweighted_evaluated": eval_cnt,
                    "unweighted_eligible": elig_cnt,
                    "unweighted_beneficiaries": ben_cnt,
                    "weighted_total_population": round(w_tot, 2),
                    "weighted_eligible_population": round(w_elig, 2),
                    "weighted_beneficiary_population": round(w_ben, 2),
                    "weighted_eligibility_rate": round(w_elig / w_tot, 4) if w_tot > 0 else 0.0,
                    "weighted_coverage_rate": round(w_ben / w_elig, 4) if w_elig > 0 else 0.0,
                    "estimated_cost_inr": round(w_cost, 2),
                })

    return overall_summary, breakdown_rows
