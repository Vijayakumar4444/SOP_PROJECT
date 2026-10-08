from __future__ import annotations

import json
from pathlib import Path
from typing import Any


CONTEXT_PATH = Path("data/synthetic/current_submitted_policy_context.json")


def context_path(root: Path) -> Path:
    return root / CONTEXT_PATH


def write_submitted_policy_context(root: Path, run_id: str, policy: Any, configuration: Any) -> dict[str, Any]:
    plain_policy = _to_plain(policy)
    plain_configuration = _to_plain(configuration)
    benefit_amount = _number_or_none(plain_policy.get("benefitAmount"))
    benefit_frequency = str(plain_policy.get("benefitFrequency") or "").lower()
    monthly_benefit = None
    annual_benefit = None
    if benefit_amount and benefit_amount > 0:
        monthly_benefit = benefit_amount if benefit_frequency == "monthly" else None
        annual_benefit = benefit_amount * 12 if benefit_frequency == "monthly" else benefit_amount

    payload = {
        "runId": run_id,
        "policyName": plain_policy.get("name"),
        "department": plain_policy.get("department"),
        "policy": plain_policy,
        "configuration": plain_configuration,
        "parameterOverrides": {
            key: value
            for key, value in {
                "benefit_amount": monthly_benefit if monthly_benefit is not None else benefit_amount,
                "total_budget": _number_or_none(plain_policy.get("budgetAllocation")),
            }.items()
            if value is not None
        },
        "benefit": {
            "amount": benefit_amount,
            "frequency": plain_policy.get("benefitFrequency"),
            "monthlyAmount": monthly_benefit,
            "annualAmount": annual_benefit,
        },
        "budget": {
            "plannedStatewideBudget": _number_or_none(plain_policy.get("budgetAllocation")),
        },
    }
    path = context_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def load_submitted_policy_context(root: Path) -> dict[str, Any]:
    path = context_path(root)
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def submitted_parameter_overrides(root: Path) -> dict[str, Any]:
    context = load_submitted_policy_context(root)
    overrides = context.get("parameterOverrides")
    return overrides if isinstance(overrides, dict) else {}


def apply_submitted_context_to_monte_carlo_config(raw_config: dict[str, Any], root: Path) -> dict[str, Any]:
    overrides = submitted_parameter_overrides(root)
    if not overrides:
        return raw_config

    policy = raw_config.setdefault("policy", {})
    policy_path = str(policy.get("policy_path") or "")
    if "tn_elderly_pension" not in policy_path:
        return raw_config

    parameter_overrides = policy.setdefault("parameter_overrides", {})
    parameter_overrides.update(overrides)
    uncertainty = raw_config.get("uncertainty", {}).get("policy_parameter_uncertainty", {})
    parameters = uncertainty.get("parameters", {})
    benefit = parameters.get("benefit_amount")
    if isinstance(benefit, dict) and "benefit_amount" in overrides:
        amount = float(overrides["benefit_amount"])
        benefit.update({"minimum": amount, "maximum": amount, "mode": amount, "mean": amount})
    return raw_config


def _to_plain(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {key: _to_plain(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_plain(item) for item in value]
    return value


def _number_or_none(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None
