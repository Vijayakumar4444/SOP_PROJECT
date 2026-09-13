from __future__ import annotations

from typing import Any
from datetime import datetime

from backend.app.modules.policy_engine.policy_model import (
    AllocationStrategy,
    LogicGroupConfig,
    PolicyDefinition,
    RuleConfig,
)

SUPPORTED_OPERATORS = {
    "equals",
    "not_equals",
    "greater_than",
    "greater_than_or_equal",
    "less_than",
    "less_than_or_equal",
    "in",
    "not_in",
    "between",
    "not_between",
    "is_null",
    "is_not_null",
    "contains",
    "starts_with",
    "ends_with",
}


def validate_policy_schema(policy: PolicyDefinition) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    # Check basic identifiers
    if not policy.policy_id or not policy.policy_id.strip():
        errors.append({"code": "MISSING_POLICY_ID", "path": "policy_id", "message": "Policy ID is required and cannot be empty."})
    if not policy.name or not policy.name.strip():
        errors.append({"code": "MISSING_POLICY_NAME", "path": "name", "message": "Policy name is required."})
    if not policy.version or not policy.version.strip():
        errors.append({"code": "MISSING_POLICY_VERSION", "path": "version", "message": "Policy version is required."})

    # Jurisdiction
    if policy.jurisdiction.state and policy.jurisdiction.state.lower() != "tamil nadu":
        warnings.append({
            "code": "NON_TN_JURISDICTION",
            "path": "jurisdiction.state",
            "message": f"Policy jurisdiction '{policy.jurisdiction.state}' differs from default 'Tamil Nadu'.",
        })

    # Validate rules recursively
    _validate_logic_group(policy.eligibility, "eligibility", errors, warnings)
    _validate_logic_group(policy.exclusions, "exclusions", errors, warnings)

    # Benefit validation
    if policy.benefit.amount < 0:
        errors.append({"code": "NEGATIVE_BENEFIT_AMOUNT", "path": "benefit.amount", "message": "Benefit amount cannot be negative."})
    if policy.benefit.type.value == "percentage_based":
        if policy.benefit.percentage_rate is None or not (0 <= policy.benefit.percentage_rate <= 100):
            errors.append({"code": "INVALID_PERCENTAGE_RATE", "path": "benefit.percentage_rate", "message": "Percentage rate must be between 0 and 100."})

    # Constraints validation
    if policy.constraints.total_budget is not None and policy.constraints.total_budget < 0:
        errors.append({"code": "NEGATIVE_BUDGET", "path": "constraints.total_budget", "message": "Total budget cannot be negative."})
    if policy.constraints.maximum_beneficiaries is not None and policy.constraints.maximum_beneficiaries < 0:
        errors.append({"code": "NEGATIVE_MAX_BENEFICIARIES", "path": "constraints.maximum_beneficiaries", "message": "Maximum beneficiaries cannot be negative."})
    
    if policy.constraints.allocation_strategy == AllocationStrategy.SEEDED_LOTTERY and policy.constraints.lottery_seed is None:
        warnings.append({
            "code": "MISSING_LOTTERY_SEED",
            "path": "constraints.lottery_seed",
            "message": "Seeded lottery selected without explicit seed. Default seed (42) will be used for reproducibility.",
        })

    # Effective Period Date validation
    if policy.effective_period.start_date and policy.effective_period.end_date:
        try:
            start_dt = datetime.strptime(policy.effective_period.start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(policy.effective_period.end_date, "%Y-%m-%d")
            if start_dt > end_dt:
                errors.append({"code": "INVALID_DATE_RANGE", "path": "effective_period", "message": "Start date cannot be after end date."})
        except ValueError:
            warnings.append({"code": "NON_STANDARD_DATE_FORMAT", "path": "effective_period", "message": "Dates should be formatted as YYYY-MM-DD."})

    is_valid = len(errors) == 0
    return {
        "valid": is_valid,
        "errors": errors,
        "warnings": warnings,
    }


def _validate_logic_group(group: LogicGroupConfig, path: str, errors: list[dict[str, str]], warnings: list[dict[str, str]]) -> None:
    if group.logical_operator not in ["AND", "OR", "NOT"]:
        errors.append({"code": "INVALID_LOGICAL_OPERATOR", "path": f"{path}.logical_operator", "message": f"Unsupported logical operator '{group.logical_operator}'."})

    for idx, rule in enumerate(group.rules):
        rule_path = f"{path}.rules[{idx}]"
        _validate_rule(rule, rule_path, errors, warnings)

    for idx, sub_group in enumerate(group.groups):
        sub_path = f"{path}.groups[{idx}]"
        _validate_logic_group(sub_group, sub_path, errors, warnings)


def _validate_rule(rule: RuleConfig, path: str, errors: list[dict[str, str]], warnings: list[dict[str, str]]) -> None:
    if not rule.field or not rule.field.strip():
        errors.append({"code": "MISSING_RULE_FIELD", "path": f"{path}.field", "message": "Rule field cannot be empty."})

    op = rule.operator.lower()
    if op not in SUPPORTED_OPERATORS:
        errors.append({"code": "UNSUPPORTED_OPERATOR", "path": f"{path}.operator", "message": f"Operator '{rule.operator}' is not supported."})

    # Value checks for specific operators
    if op in ["in", "not_in"] and not isinstance(rule.value, (list, tuple, set)):
        errors.append({"code": "INVALID_LIST_VALUE", "path": f"{path}.value", "message": f"Operator '{op}' requires a list value."})
    elif op in ["between", "not_between"]:
        if not isinstance(rule.value, (list, tuple)) or len(rule.value) != 2:
            errors.append({"code": "INVALID_BETWEEN_VALUE", "path": f"{path}.value", "message": f"Operator '{op}' requires a 2-element list [min, max]."})
        elif rule.value[0] is not None and rule.value[1] is not None and rule.value[0] > rule.value[1]:
            errors.append({"code": "INVALID_BETWEEN_RANGE", "path": f"{path}.value", "message": f"Between lower bound {rule.value[0]} is greater than upper bound {rule.value[1]}."})
