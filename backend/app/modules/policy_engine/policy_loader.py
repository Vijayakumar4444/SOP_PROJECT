from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import yaml

from backend.app.modules.policy_engine.policy_model import (
    AllocationStrategy,
    BenefitConfig,
    BenefitType,
    ConstraintConfig,
    EffectivePeriodConfig,
    Frequency,
    JurisdictionConfig,
    LogicGroupConfig,
    MissingValueBehavior,
    PolicyDefinition,
    RuleConfig,
    TargetUnit,
)


def load_policy_from_file(path: Path | str) -> tuple[PolicyDefinition, dict[str, Any]]:
    path_obj = Path(path).resolve()
    if not path_obj.exists():
        raise FileNotFoundError(f"Policy file not found: {path_obj}")

    text = path_obj.read_text(encoding="utf-8")
    if path_obj.suffix in [".yaml", ".yml"]:
        raw_dict = yaml.safe_load(text)
    elif path_obj.suffix == ".json":
        raw_dict = json.loads(text)
    else:
        # Try YAML first, fallback to JSON
        try:
            raw_dict = yaml.safe_load(text)
        except Exception:
            raw_dict = json.loads(text)

    if not isinstance(raw_dict, dict):
        raise ValueError(f"Invalid policy specification content in {path_obj}")

    policy_def = parse_policy_dict(raw_dict)
    return policy_def, raw_dict


def parse_logic_group(raw: dict[str, Any] | list[Any] | None) -> LogicGroupConfig:
    if not raw:
        return LogicGroupConfig()
    
    if isinstance(raw, list):
        rules = [parse_rule(r) for r in raw]
        return LogicGroupConfig(logical_operator="AND", rules=rules)

    operator = str(raw.get("logical_operator", "AND")).upper()
    if operator not in ["AND", "OR", "NOT"]:
        operator = "AND"

    raw_rules = raw.get("rules", [])
    rules = [parse_rule(r) for r in raw_rules if isinstance(r, dict)]

    raw_groups = raw.get("groups", [])
    groups = [parse_logic_group(g) for g in raw_groups if isinstance(g, (dict, list))]

    return LogicGroupConfig(logical_operator=operator, rules=rules, groups=groups) # type: ignore


def parse_rule(raw: dict[str, Any]) -> RuleConfig:
    field_name = str(raw.get("field", ""))
    operator = str(raw.get("operator", "equals")).lower()
    value = raw.get("value", None)
    rule_id = str(raw.get("rule_id", f"R_{field_name}_{operator}".upper()))
    description = str(raw.get("description", ""))
    return RuleConfig(field=field_name, operator=operator, value=value, rule_id=rule_id, description=description)


def parse_policy_dict(raw: dict[str, Any]) -> PolicyDefinition:
    policy_id = str(raw.get("policy_id", ""))
    name = str(raw.get("name", ""))
    version = str(raw.get("version", "1.0"))
    description = str(raw.get("description", ""))
    status = str(raw.get("status", "active"))

    target_unit_str = str(raw.get("target_unit", "person")).lower()
    try:
        target_unit = TargetUnit(target_unit_str)
    except ValueError:
        target_unit = TargetUnit.PERSON

    # Jurisdiction
    jur_raw = raw.get("jurisdiction", {})
    jurisdiction = JurisdictionConfig(
        state=str(jur_raw.get("state", "Tamil Nadu")),
        geographic_level=str(jur_raw.get("geographic_level", "state")),
        districts=[str(d) for d in jur_raw.get("districts", [])],
    )

    # Eligibility & Exclusions
    eligibility = parse_logic_group(raw.get("eligibility"))
    exclusions = parse_logic_group(raw.get("exclusions"))

    # Benefit
    ben_raw = raw.get("benefit", {})
    ben_type_str = str(ben_raw.get("type", "fixed_amount")).lower()
    try:
        ben_type = BenefitType(ben_type_str)
    except ValueError:
        ben_type = BenefitType.FIXED_AMOUNT

    freq_str = str(ben_raw.get("frequency", "monthly")).lower()
    try:
        freq = Frequency(freq_str)
    except ValueError:
        freq = Frequency.MONTHLY

    benefit = BenefitConfig(
        type=ben_type,
        amount=float(ben_raw.get("amount", 0.0)),
        frequency=freq,
        currency=str(ben_raw.get("currency", "INR")),
        percentage_field=ben_raw.get("percentage_field"),
        percentage_rate=float(ben_raw.get("percentage_rate")) if ben_raw.get("percentage_rate") is not None else None,
        attribute_field=ben_raw.get("attribute_field"),
        tiers=ben_raw.get("tiers", []),
    )

    # Constraints
    con_raw = raw.get("constraints", {})
    alloc_str = str(con_raw.get("allocation_strategy", "all")).lower()
    try:
        alloc_strat = AllocationStrategy(alloc_str)
    except ValueError:
        alloc_strat = AllocationStrategy.ALL

    missing_str = str(con_raw.get("missing_value_behavior", "ineligible")).lower()
    try:
        missing_beh = MissingValueBehavior(missing_str)
    except ValueError:
        missing_beh = MissingValueBehavior.INELIGIBLE

    constraints = ConstraintConfig(
        total_budget=float(con_raw["total_budget"]) if con_raw.get("total_budget") is not None else None,
        maximum_beneficiaries=int(con_raw["maximum_beneficiaries"]) if con_raw.get("maximum_beneficiaries") is not None else None,
        allocation_strategy=alloc_strat,
        missing_value_behavior=missing_beh,
        lottery_seed=int(con_raw["lottery_seed"]) if con_raw.get("lottery_seed") is not None else None,
        priority_field=con_raw.get("priority_field"),
        geographic_priority_order=[str(g) for g in con_raw.get("geographic_priority_order", [])],
    )

    # Effective Period
    eff_raw = raw.get("effective_period", {})
    effective_period = EffectivePeriodConfig(
        start_date=str(eff_raw.get("start_date", "2026-04-01")),
        end_date=str(eff_raw.get("end_date", "2027-03-31")),
    )

    # Required variables
    req_vars = [str(v) for v in raw.get("required_variables", [])]

    return PolicyDefinition(
        policy_id=policy_id,
        name=name,
        version=version,
        description=description,
        status=status,
        target_unit=target_unit,
        jurisdiction=jurisdiction,
        eligibility=eligibility,
        exclusions=exclusions,
        benefit=benefit,
        constraints=constraints,
        effective_period=effective_period,
        required_variables=req_vars,
    )
