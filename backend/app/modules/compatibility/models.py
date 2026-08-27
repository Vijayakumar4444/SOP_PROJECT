from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


class CompatibilityError(Exception):
    code = "COMPATIBILITY_ERROR"

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": str(self)}


class InvalidPolicyDefinitionError(CompatibilityError):
    code = "INVALID_POLICY_DEFINITION"


class MissingPhase1MetadataError(CompatibilityError):
    code = "MISSING_PHASE1_METADATA"


@dataclass
class PolicyRequirement:
    variable: str
    canonical_variable: str
    requirement_type: str
    importance: str
    required_level: str
    required_unit: str = ""
    required_geography: str = "Tamil Nadu"
    policy_reference_year: int = 2026


@dataclass
class VariableCapability:
    canonical_name: str
    level: str
    data_type: str
    unit: str
    sources: list[str]
    reference_years: list[int]
    non_null_percentage: float
    missing_percentage: float
    geographic_resolution: list[str]
    quality_flag: str
    source_variables: str
    lineage: list[dict[str, str]] = field(default_factory=list)
    aggregate_only: bool = False
    notes: str = ""


@dataclass
class RequirementResult:
    requirement: PolicyRequirement
    status: str
    score: float
    preferred_source: str
    alternative_sources: list[str]
    non_null_percentage: float
    temporal_status: str
    temporal_score: float
    geographic_status: str
    level_status: str
    unit_status: str
    warnings: list[str]
    lineage: list[dict[str, str]]


@dataclass
class CompatibilityReport:
    report_id: str
    policy_id: str
    policy_name: str
    data_foundation_version: str
    compatibility_engine_version: str
    scoring_config_version: str
    domains: list[dict[str, Any]]
    requirements: list[RequirementResult]
    joint_availability: dict[str, Any]
    score_breakdown: dict[str, float]
    reliability_score: float
    simulation_readiness: str
    blocking_issues: list[str]
    warnings: list[str]
    recommendations: list[str]
    synthetic_population_requirements: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        return data
