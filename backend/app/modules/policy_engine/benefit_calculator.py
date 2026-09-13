from __future__ import annotations

from typing import Any

from backend.app.modules.policy_engine.policy_model import (
    BenefitConfig,
    BenefitType,
    Frequency,
    PolicyDefinition,
)


def calculate_policy_benefits(
    policy: PolicyDefinition,
    records: list[dict[str, Any]] | Any,
    weight_col: str = "population_weight",
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if hasattr(records, "to_dict"):
        rows = [dict(r) for r in records.to_dict(orient="records")]
    else:
        rows = [dict(r) for r in records]

    b_config = policy.benefit
    freq_multiplier = _get_frequency_multiplier(b_config.frequency)

    selected_rows: list[dict[str, Any]] = []

    for r in rows:
        if not r.get("is_selected_beneficiary", False):
            r["benefit_amount"] = 0.0
            r["annualized_benefit_amount"] = 0.0
            r["estimated_policy_cost"] = 0.0
            continue

        unit_benefit = _compute_unit_benefit(r, b_config)
        annual_b = round(unit_benefit * freq_multiplier, 2)
        weight_val = float(r.get(weight_col, 1.0))
        est_cost = round(annual_b * weight_val, 2)

        r["benefit_amount"] = unit_benefit
        r["annualized_benefit_amount"] = annual_b
        r["estimated_policy_cost"] = est_cost
        selected_rows.append(r)

    unweighted_cost = round(sum(r["annualized_benefit_amount"] for r in selected_rows), 2)
    weighted_cost = round(sum(r["estimated_policy_cost"] for r in selected_rows), 2)
    
    annual_amounts = [r["annualized_benefit_amount"] for r in selected_rows]
    avg_benefit = round(sum(annual_amounts) / len(annual_amounts), 2) if annual_amounts else 0.0
    min_benefit = round(min(annual_amounts), 2) if annual_amounts else 0.0
    max_benefit = round(max(annual_amounts), 2) if annual_amounts else 0.0

    summary = {
        "unweighted_total_cost": unweighted_cost,
        "weighted_total_cost": weighted_cost,
        "average_annual_benefit": avg_benefit,
        "min_annual_benefit": min_benefit,
        "max_annual_benefit": max_benefit,
        "benefit_type": b_config.type.value,
        "frequency": b_config.frequency.value,
        "currency": b_config.currency,
    }

    return rows, summary


def _compute_unit_benefit(row: dict[str, Any], config: BenefitConfig) -> float:
    b_type = config.type

    if b_type in [BenefitType.FIXED_AMOUNT, BenefitType.PER_HOUSEHOLD, BenefitType.PER_PERSON]:
        return round(float(config.amount), 2)

    elif b_type == BenefitType.PERCENTAGE_BASED:
        field_name = config.percentage_field or "individual_income"
        val = float(row.get(field_name, 0.0))
        rate = (config.percentage_rate or 10.0) / 100.0
        return round(val * rate, 2)

    elif b_type == BenefitType.ATTRIBUTE_BASED:
        field_name = config.attribute_field or "individual_income"
        val = float(row.get(field_name, config.amount))
        return round(val, 2)

    elif b_type == BenefitType.TIERED:
        val = float(row.get("individual_income", 0.0))
        for tier in config.tiers:
            min_val = float(tier.get("min_income", 0.0))
            max_val = float(tier.get("max_income", float("inf")))
            amt = float(tier.get("amount", config.amount))
            if min_val <= val <= max_val:
                return round(amt, 2)
        return round(float(config.amount), 2)

    return round(float(config.amount), 2)


def _get_frequency_multiplier(freq: Frequency) -> float:
    if freq == Frequency.MONTHLY:
        return 12.0
    elif freq in [Frequency.ONE_TIME, Frequency.ANNUAL]:
        return 1.0
    return 12.0
