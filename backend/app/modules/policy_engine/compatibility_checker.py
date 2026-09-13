from __future__ import annotations

from typing import Any
from backend.app.modules.policy_engine.policy_model import LogicGroupConfig, PolicyDefinition


def extract_referenced_fields(policy: PolicyDefinition) -> set[str]:
    fields: set[str] = set(policy.required_variables)

    def _collect_from_group(group: LogicGroupConfig) -> None:
        for rule in group.rules:
            if rule.field:
                fields.add(rule.field)
        for sub in group.groups:
            _collect_from_group(sub)

    _collect_from_group(policy.eligibility)
    _collect_from_group(policy.exclusions)

    if policy.benefit.percentage_field:
        fields.add(policy.benefit.percentage_field)
    if policy.benefit.attribute_field:
        fields.add(policy.benefit.attribute_field)
    if policy.constraints.priority_field:
        fields.add(policy.constraints.priority_field)

    return fields


def check_policy_population_compatibility(policy: PolicyDefinition, records: list[dict[str, Any]] | Any) -> dict[str, Any]:
    if hasattr(records, "to_dict"):
        rows = records.to_dict(orient="records")
    else:
        rows = list(records)

    referenced = extract_referenced_fields(policy)
    pop_columns: set[str] = set(rows[0].keys()) if rows else set()

    available_vars: list[str] = []
    missing_vars: list[str] = []
    high_missingness_vars: list[dict[str, Any]] = []

    total_rows = len(rows)

    for var in sorted(referenced):
        if var in pop_columns:
            available_vars.append(var)
            null_count = sum(1 for r in rows if r.get(var) is None or str(r.get(var)).strip() == "")
            missing_rate = float(null_count / total_rows) if total_rows > 0 else 0.0
            if missing_rate > 0.20:
                high_missingness_vars.append({
                    "variable": var,
                    "missing_count": null_count,
                    "missing_rate": round(missing_rate, 4),
                })
        else:
            missing_vars.append(var)

    is_compatible = len(missing_vars) == 0

    return {
        "compatible": is_compatible,
        "policy_id": policy.policy_id,
        "total_referenced_variables": len(referenced),
        "available_variables": available_vars,
        "missing_variables": missing_vars,
        "high_missingness_variables": high_missingness_vars,
        "population_record_count": total_rows,
        "population_columns_count": len(pop_columns),
    }
