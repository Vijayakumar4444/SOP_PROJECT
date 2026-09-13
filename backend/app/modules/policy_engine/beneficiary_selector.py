from __future__ import annotations

from typing import Any
import random

from backend.app.modules.policy_engine.policy_model import (
    AllocationStrategy,
    PolicyDefinition,
    TargetUnit,
)


def select_beneficiaries(
    policy: PolicyDefinition,
    eligibility_records: list[dict[str, Any]] | Any,
    person_id_col: str = "person_id",
    household_id_col: str = "household_id",
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    if hasattr(eligibility_records, "to_dict"):
        rows = [dict(r) for r in eligibility_records.to_dict(orient="records")]
    else:
        rows = [dict(r) for r in eligibility_records]

    if not rows:
        return [], [], {"total_eligible": 0, "total_selected": 0, "capped_by": None}

    # Filter eligible pool
    if policy.target_unit == TargetUnit.HOUSEHOLD:
        eligible_pool = [r for r in rows if r.get("is_eligible", False) and r.get("is_household_primary_beneficiary", False)]
    else:
        eligible_pool = [r for r in rows if r.get("is_eligible", False)]

    if not eligible_pool:
        for r in rows:
            r["is_selected_beneficiary"] = False
            r["selection_status"] = "INELIGIBLE"
        return rows, [], {"total_eligible": 0, "total_selected": 0, "capped_by": None}

    # Sort according to allocation strategy
    strat = policy.constraints.allocation_strategy
    sorted_eligible = _sort_eligible_pool(eligible_pool, strat, policy, person_id_col)

    # Determine capacity caps
    max_ben = policy.constraints.maximum_beneficiaries
    unit_cost = _estimate_per_unit_annual_cost(policy)
    budget_cap: int | None = None

    if policy.constraints.total_budget is not None and unit_cost > 0:
        budget_cap = int(policy.constraints.total_budget // unit_cost)

    limits = [len(sorted_eligible)]
    capped_by = None

    if max_ben is not None and max_ben >= 0:
        limits.append(max_ben)
    if budget_cap is not None and budget_cap >= 0:
        limits.append(budget_cap)

    effective_limit = min(limits)

    if effective_limit < len(sorted_eligible):
        if max_ben is not None and effective_limit == max_ben:
            capped_by = "MAXIMUM_BENEFICIARIES_CAP"
        elif budget_cap is not None and effective_limit == budget_cap:
            capped_by = "TOTAL_BUDGET_CAP"

    selected_ids = set(r[person_id_col] for r in sorted_eligible[:effective_limit])

    selected_records: list[dict[str, Any]] = []

    for r in rows:
        p_id = r[person_id_col]
        if p_id in selected_ids:
            r["is_selected_beneficiary"] = True
            r["selection_status"] = "SELECTED"
            selected_records.append(r)
        elif r.get("is_eligible", False):
            r["is_selected_beneficiary"] = False
            r["selection_status"] = capped_by or "CAPACITY_LIMIT_REACHED"
        else:
            r["is_selected_beneficiary"] = False
            r["selection_status"] = str(r.get("eligibility_status", "INELIGIBLE"))

    stats = {
        "total_evaluated": len(rows),
        "total_eligible": len(eligible_pool),
        "total_selected": len(selected_records),
        "capped_by": capped_by,
        "effective_capacity_limit": effective_limit,
        "allocation_strategy": strat.value,
    }

    return rows, selected_records, stats


def _sort_eligible_pool(
    pool: list[dict[str, Any]],
    strat: AllocationStrategy,
    policy: PolicyDefinition,
    person_id_col: str,
) -> list[dict[str, Any]]:
    copied = [dict(r) for r in pool]

    def _safe_float(val: Any, default: float = 0.0) -> float:
        try:
            return float(val) if val is not None else default
        except (ValueError, TypeError):
            return default

    if strat == AllocationStrategy.LOWEST_INCOME_FIRST:
        inc_col = "individual_income" if "individual_income" in copied[0] else "consumption_expenditure"
        copied.sort(key=lambda r: (_safe_float(r.get(inc_col)), str(r.get(person_id_col, ""))))

    elif strat == AllocationStrategy.OLDEST_FIRST:
        copied.sort(key=lambda r: (-_safe_float(r.get("age")), str(r.get(person_id_col, ""))))

    elif strat == AllocationStrategy.YOUNGEST_FIRST:
        copied.sort(key=lambda r: (_safe_float(r.get("age")), str(r.get(person_id_col, ""))))

    elif strat == AllocationStrategy.HIGHEST_VULNERABILITY_FIRST:
        copied.sort(key=lambda r: (_safe_float(r.get("consumption_expenditure")), str(r.get(person_id_col, ""))))

    elif strat == AllocationStrategy.GEOGRAPHIC_PRIORITY:
        order_map = {d.lower(): i for i, d in enumerate(policy.constraints.geographic_priority_order)}
        copied.sort(key=lambda r: (order_map.get(str(r.get("district", "")).lower(), 999), str(r.get(person_id_col, ""))))

    elif strat == AllocationStrategy.SEEDED_LOTTERY:
        seed = policy.constraints.lottery_seed if policy.constraints.lottery_seed is not None else 42
        rng = random.Random(seed)
        # Deterministic sort first, then shuffle with seed
        copied.sort(key=lambda r: str(r.get(person_id_col, "")))
        rng.shuffle(copied)

    else:
        # Default ALL / PROPORTIONAL: sort by person_id
        copied.sort(key=lambda r: str(r.get(person_id_col, "")))

    return copied


def _estimate_per_unit_annual_cost(policy: PolicyDefinition) -> float:
    base_amount = policy.benefit.amount
    freq = policy.benefit.frequency.value

    if freq == "monthly":
        annual_cost = base_amount * 12.0
    elif freq in ["one_time", "annual"]:
        annual_cost = base_amount
    else:
        annual_cost = base_amount * 12.0

    return annual_cost
