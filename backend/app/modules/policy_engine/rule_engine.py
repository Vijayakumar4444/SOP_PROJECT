from __future__ import annotations

from typing import Any
import math

from backend.app.modules.policy_engine.policy_model import (
    LogicGroupConfig,
    MissingValueBehavior,
    RuleConfig,
)


def evaluate_single_rule(
    record: dict[str, Any],
    rule: RuleConfig,
    missing_behavior: MissingValueBehavior = MissingValueBehavior.INELIGIBLE,
) -> tuple[bool, str]:
    field_val = record.get(rule.field)
    op = rule.operator.lower()
    target_val = rule.value

    # Null / Missing checks
    is_missing = False
    if field_val is None:
        is_missing = True
    elif isinstance(field_val, float) and math.isnan(field_val):
        is_missing = True
    elif isinstance(field_val, str) and field_val.strip() == "":
        is_missing = True

    if is_missing:
        if op == "is_null":
            return True, f"{rule.rule_id}_PASSED_IS_NULL"
        elif op == "is_not_null":
            return False, f"{rule.rule_id}_FAILED_IS_NOT_NULL"
        
        if missing_behavior == MissingValueBehavior.ELIGIBLE:
            return True, f"{rule.rule_id}_MISSING_DEFAULT_ELIGIBLE"
        else:
            return False, f"{rule.rule_id}_MISSING_INELIGIBLE"

    if op == "is_null":
        return False, f"{rule.rule_id}_FAILED_IS_NULL"
    elif op == "is_not_null":
        return True, f"{rule.rule_id}_PASSED_IS_NOT_NULL"

    # Normalize values for comparison
    norm_field, norm_target = _normalize_pair(field_val, target_val)

    if op == "equals":
        passed = norm_field == norm_target
    elif op == "not_equals":
        passed = norm_field != norm_target
    elif op == "greater_than":
        passed = norm_field > norm_target
    elif op == "greater_than_or_equal":
        passed = norm_field >= norm_target
    elif op == "less_than":
        passed = norm_field < norm_target
    elif op == "less_than_or_equal":
        passed = norm_field <= norm_target
    elif op == "in":
        target_list = [_normalize_value(x) for x in (norm_target if isinstance(norm_target, (list, tuple, set)) else [norm_target])]
        passed = norm_field in target_list
    elif op == "not_in":
        target_list = [_normalize_value(x) for x in (norm_target if isinstance(norm_target, (list, tuple, set)) else [norm_target])]
        passed = norm_field not in target_list
    elif op == "between":
        if isinstance(norm_target, (list, tuple)) and len(norm_target) == 2:
            low, high = _normalize_value(norm_target[0]), _normalize_value(norm_target[1])
            passed = low <= norm_field <= high
        else:
            passed = False
    elif op == "not_between":
        if isinstance(norm_target, (list, tuple)) and len(norm_target) == 2:
            low, high = _normalize_value(norm_target[0]), _normalize_value(norm_target[1])
            passed = not (low <= norm_field <= high)
        else:
            passed = True
    elif op == "contains":
        passed = str(norm_target) in str(norm_field)
    elif op == "starts_with":
        passed = str(norm_field).startswith(str(norm_target))
    elif op == "ends_with":
        passed = str(norm_field).endswith(str(norm_target))
    else:
        passed = False

    reason_code = f"{rule.rule_id}_PASSED" if passed else f"INELIGIBLE_{rule.field.upper()}"
    return passed, reason_code


def evaluate_logic_group(
    record: dict[str, Any],
    group: LogicGroupConfig,
    missing_behavior: MissingValueBehavior = MissingValueBehavior.INELIGIBLE,
) -> tuple[bool, list[str], list[str]]:
    if not group.rules and not group.groups:
        return True, [], []

    op = group.logical_operator.upper()
    passed_rule_ids: list[str] = []
    failed_rule_ids: list[str] = []

    if op == "AND":
        all_passed = True
        for rule in group.rules:
            res, code = evaluate_single_rule(record, rule, missing_behavior)
            if res:
                passed_rule_ids.append(rule.rule_id)
            else:
                failed_rule_ids.append(rule.rule_id)
                all_passed = False
        
        for sub in group.groups:
            res, p_ids, f_ids = evaluate_logic_group(record, sub, missing_behavior)
            passed_rule_ids.extend(p_ids)
            failed_rule_ids.extend(f_ids)
            if not res:
                all_passed = False

        return all_passed, passed_rule_ids, failed_rule_ids

    elif op == "OR":
        any_passed = False
        for rule in group.rules:
            res, code = evaluate_single_rule(record, rule, missing_behavior)
            if res:
                passed_rule_ids.append(rule.rule_id)
                any_passed = True
            else:
                failed_rule_ids.append(rule.rule_id)

        for sub in group.groups:
            res, p_ids, f_ids = evaluate_logic_group(record, sub, missing_behavior)
            passed_rule_ids.extend(p_ids)
            failed_rule_ids.extend(f_ids)
            if res:
                any_passed = True

        return any_passed, passed_rule_ids, failed_rule_ids

    elif op == "NOT":
        all_passed = True
        for rule in group.rules:
            res, code = evaluate_single_rule(record, rule, missing_behavior)
            if res:
                passed_rule_ids.append(rule.rule_id)
            else:
                failed_rule_ids.append(rule.rule_id)
                all_passed = False
        
        negated = not all_passed
        return negated, passed_rule_ids, failed_rule_ids

    return False, [], []


def _normalize_value(val: Any) -> Any:
    if val is None:
        return None

    if isinstance(val, bool):
        return val

    if isinstance(val, (int, float)):
        return val

    if isinstance(val, str):
        v_str = val.strip()
        try:
            if "." in v_str:
                return float(v_str)
            return int(v_str)
        except ValueError:
            pass

        if v_str.lower() in ["true", "yes", "y", "1"]:
            return True
        elif v_str.lower() in ["false", "no", "n", "0"]:
            return False

        return v_str

    return val


def _normalize_pair(field_val: Any, target_val: Any) -> tuple[Any, Any]:
    norm_field = _normalize_value(field_val)
    
    if isinstance(target_val, (list, tuple)):
        norm_target = [_normalize_value(x) for x in target_val]
    else:
        norm_target = _normalize_value(target_val)

    if isinstance(norm_field, (int, float)) and isinstance(norm_target, (int, float)):
        return float(norm_field), float(norm_target)

    if isinstance(norm_field, str) and isinstance(norm_target, str):
        return norm_field.lower(), norm_target.lower()

    return norm_field, norm_target
