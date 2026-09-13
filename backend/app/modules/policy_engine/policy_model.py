from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal


class TargetUnit(str, Enum):
    PERSON = "person"
    HOUSEHOLD = "household"


class MissingValueBehavior(str, Enum):
    INELIGIBLE = "ineligible"
    ELIGIBLE = "eligible"
    IGNORE = "ignore"


class AllocationStrategy(str, Enum):
    ALL = "all"
    LOWEST_INCOME_FIRST = "lowest_income_first"
    HIGHEST_VULNERABILITY_FIRST = "highest_vulnerability_first"
    OLDEST_FIRST = "oldest_first"
    YOUNGEST_FIRST = "youngest_first"
    GEOGRAPHIC_PRIORITY = "geographic_priority"
    PROPORTIONAL = "proportional"
    SEEDED_LOTTERY = "seeded_lottery"


class BenefitType(str, Enum):
    FIXED_AMOUNT = "fixed_amount"
    PERCENTAGE_BASED = "percentage_based"
    ATTRIBUTE_BASED = "attribute_based"
    TIERED = "tiered"
    PER_HOUSEHOLD = "per_household"
    PER_PERSON = "per_person"


class Frequency(str, Enum):
    ONE_TIME = "one_time"
    MONTHLY = "monthly"
    ANNUAL = "annual"


@dataclass
class RuleConfig:
    field: str
    operator: str
    value: Any
    rule_id: str = ""
    description: str = ""

    def __post_init__(self) -> None:
        if not self.rule_id:
            self.rule_id = f"RULE_{self.field}_{self.operator}".upper()


@dataclass
class LogicGroupConfig:
    logical_operator: Literal["AND", "OR", "NOT"] = "AND"
    rules: list[RuleConfig] = field(default_factory=list)
    groups: list[LogicGroupConfig] = field(default_factory=list)


@dataclass
class BenefitConfig:
    type: BenefitType = BenefitType.FIXED_AMOUNT
    amount: float = 0.0
    frequency: Frequency = Frequency.MONTHLY
    currency: str = "INR"
    percentage_field: str | None = None
    percentage_rate: float | None = None
    attribute_field: str | None = None
    tiers: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ConstraintConfig:
    total_budget: float | None = None
    maximum_beneficiaries: int | None = None
    allocation_strategy: AllocationStrategy = AllocationStrategy.ALL
    missing_value_behavior: MissingValueBehavior = MissingValueBehavior.INELIGIBLE
    lottery_seed: int | None = None
    priority_field: str | None = None
    geographic_priority_order: list[str] = field(default_factory=list)


@dataclass
class JurisdictionConfig:
    state: str = "Tamil Nadu"
    geographic_level: str = "state"
    districts: list[str] = field(default_factory=list)


@dataclass
class EffectivePeriodConfig:
    start_date: str = "2026-04-01"
    end_date: str = "2027-03-31"


@dataclass
class PolicyDefinition:
    policy_id: str
    name: str
    version: str = "1.0"
    description: str = ""
    status: str = "active"
    target_unit: TargetUnit = TargetUnit.PERSON
    jurisdiction: JurisdictionConfig = field(default_factory=JurisdictionConfig)
    eligibility: LogicGroupConfig = field(default_factory=LogicGroupConfig)
    exclusions: LogicGroupConfig = field(default_factory=LogicGroupConfig)
    benefit: BenefitConfig = field(default_factory=BenefitConfig)
    constraints: ConstraintConfig = field(default_factory=ConstraintConfig)
    effective_period: EffectivePeriodConfig = field(default_factory=EffectivePeriodConfig)
    required_variables: list[str] = field(default_factory=list)
