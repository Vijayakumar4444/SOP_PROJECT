from __future__ import annotations

from pathlib import Path
from typing import Any
from datetime import UTC, datetime
import json
import re

from .capability_registry import DataCapabilityRegistryBuilder
from .domain_checker import DomainChecker
from .models import CompatibilityReport, PolicyRequirement, RequirementResult
from .readiness import ReadinessEvaluator
from .requirements import PolicyRequirementExtractor
from .rules import DERIVATIONS, ENGINE_VERSION, PROXIES, SCORING_CONFIG_VERSION, STATUS_SCORES, TEMPORAL_SENSITIVITY, TEMPORAL_THRESHOLDS
from .scoring import ReliabilityScorer


ROOT = Path(__file__).resolve().parents[4]


class PolicyDataCompatibilityService:
    def __init__(self, root: Path = ROOT, persist_reports: bool = True):
        self.root = root
        self.persist_reports = persist_reports
        registry_path = root / "data/metadata/data_capability_registry.json"
        self.registry = json.loads(registry_path.read_text(encoding="utf-8")) if registry_path.exists() else DataCapabilityRegistryBuilder(root).build()
        self.requirements = PolicyRequirementExtractor()
        self.domains = DomainChecker()
        self.scorer = ReliabilityScorer(self.registry)
        self.readiness_evaluator = ReadinessEvaluator()

    def evaluate(self, policy_definition: dict[str, Any], dataset_context: dict[str, Any] | None = None) -> CompatibilityReport:
        requirements = self.requirements.extract(policy_definition)
        domains = self.domains.check(requirements)
        requirement_results = [self._evaluate_requirement(req) for req in requirements]
        joint = self._joint_availability(requirements)
        score_breakdown = self.scorer.breakdown(domains, requirement_results, joint)
        reliability = self.scorer.overall(score_breakdown)
        blocking = self.readiness_evaluator.blocking_issues(requirement_results)
        readiness = self.readiness_evaluator.readiness(reliability, blocking, requirement_results)
        warnings = self.readiness_evaluator.warnings(requirement_results, joint)
        report = CompatibilityReport(
            report_id=f"COMPAT-{policy_definition.get('policy_id', 'POLICY')}-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
            policy_id=policy_definition.get("policy_id", ""),
            policy_name=policy_definition.get("name", ""),
            data_foundation_version=self.registry.get("data_foundation_version", "UNKNOWN"),
            compatibility_engine_version=ENGINE_VERSION,
            scoring_config_version=SCORING_CONFIG_VERSION,
            domains=domains,
            requirements=requirement_results,
            joint_availability=joint,
            score_breakdown={key: round(value * 100, 2) for key, value in score_breakdown.items()},
            reliability_score=reliability,
            simulation_readiness=readiness,
            blocking_issues=blocking,
            warnings=warnings,
            recommendations=self.readiness_evaluator.recommendations(requirement_results, readiness),
            synthetic_population_requirements=self._phase3_requirements(requirement_results, policy_definition),
        )
        if self.persist_reports:
            self._persist_report(report)
        return report

    def _evaluate_requirement(self, req: PolicyRequirement) -> RequirementResult:
        variables = self.registry["variables"]
        warnings = []
        canonical = req.canonical_variable
        capability = variables.get(canonical)
        matched_name = canonical
        derivation = None
        if not capability and canonical in DERIVATIONS:
            matched_name, derivation = DERIVATIONS[canonical]
            capability = variables.get(matched_name)
        status = "MISSING"
        if capability:
            if derivation:
                status = "DERIVABLE"
                warnings.append(f"{canonical} is derivable from {matched_name}: {derivation}.")
            elif capability.get("aggregate_only"):
                status = "AGGREGATE_ONLY"
                warnings.append(f"{canonical} is available only as aggregate data and cannot directly evaluate person-level eligibility.")
            elif capability.get("non_null_percentage", 0) >= 95:
                status = "EXACT_AVAILABLE"
            elif capability.get("non_null_percentage", 0) > 0:
                status = "PARTIALLY_AVAILABLE"
                warnings.append(f"{canonical} has missingness: {capability.get('missing_percentage')}%.")
        if canonical in PROXIES and status in {"MISSING", "AGGREGATE_ONLY"}:
            proxy_name = PROXIES[canonical]["proxy"]
            proxy_cap = variables.get(proxy_name)
            if proxy_cap and not proxy_cap.get("aggregate_only") and proxy_cap.get("non_null_percentage", 0) > 0:
                capability = proxy_cap
                matched_name = proxy_name
                status = "PROXY_AVAILABLE"
                warnings.append(PROXIES[canonical]["warning"])
        level_status = self._level_status(req, capability)
        unit_status = self._unit_status(req, canonical, matched_name)
        temporal_status, temporal_score = self._temporal(req, capability)
        geo_status = self._geographic(req, capability)
        if level_status != "COMPATIBLE":
            warnings.append(level_status)
        if unit_status != "COMPATIBLE":
            warnings.append(unit_status)
        if geo_status != "COMPATIBLE":
            warnings.append(geo_status)
        score = STATUS_SCORES[status]
        if level_status != "COMPATIBLE":
            score *= 0.7
        if unit_status != "COMPATIBLE":
            score *= 0.75
        if geo_status != "COMPATIBLE":
            score *= 0.8
        score *= temporal_score
        return RequirementResult(
            requirement=req,
            status=status,
            score=round(score, 4),
            preferred_source=(capability or {}).get("sources", [""])[0] if (capability or {}).get("sources") else "",
            alternative_sources=(capability or {}).get("sources", [])[1:] if capability else [],
            non_null_percentage=(capability or {}).get("non_null_percentage", 0),
            temporal_status=temporal_status,
            temporal_score=round(temporal_score, 4),
            geographic_status=geo_status,
            level_status=level_status,
            unit_status=unit_status,
            warnings=warnings,
            lineage=(capability or {}).get("lineage", []),
        )

    def _level_status(self, req: PolicyRequirement, capability: dict[str, Any] | None) -> str:
        if not capability:
            return "MISSING_LEVEL"
        actual = capability.get("level", "")
        if req.required_level == actual or actual == "PERSON":
            return "COMPATIBLE"
        if capability.get("aggregate_only"):
            return f"AGGREGATE_ONLY_LEVEL: requires {req.required_level}, available {actual}"
        return f"LEVEL_MISMATCH: requires {req.required_level}, available {actual}"

    def _unit_status(self, req: PolicyRequirement, canonical: str, matched: str) -> str:
        if not req.required_unit:
            return "COMPATIBLE"
        if canonical == "household_income" and matched == "consumption_expenditure":
            return "UNIT_SEMANTIC_MISMATCH: consumption expenditure is not INR/year household income"
        if canonical == "household_income":
            return "UNIT_UNCONFIRMED: household income period/definition unavailable"
        return "COMPATIBLE"

    def _temporal(self, req: PolicyRequirement, capability: dict[str, Any] | None) -> tuple[str, float]:
        if not capability or not capability.get("reference_years"):
            return "UNKNOWN", 0.5
        year = max(capability["reference_years"])
        gap = abs(req.policy_reference_year - year)
        sensitivity = TEMPORAL_SENSITIVITY.get(req.canonical_variable, "MODERATE_CHANGE")
        current, recent, aging = TEMPORAL_THRESHOLDS[sensitivity]
        if gap <= current:
            return "CURRENT", 1.0
        if gap <= recent:
            return "RECENT", 0.85
        if gap <= aging:
            return "AGING", 0.65
        if gap <= aging * 2:
            return "STALE", 0.4
        return "VERY_STALE", 0.2

    def _geographic(self, req: PolicyRequirement, capability: dict[str, Any] | None) -> str:
        if not capability:
            return "GEOGRAPHY_UNKNOWN"
        levels = set(capability.get("geographic_resolution", []))
        if req.canonical_variable == "state" and "STATE" in levels:
            return "COMPATIBLE"
        if req.canonical_variable in {"district", "district_code"} and "DISTRICT" in levels:
            return "GEOGRAPHIC_VERSION_WARNING: district codes include known boundary/code conflict"
        if {"STATE", "DISTRICT", "URBAN_RURAL"} & levels:
            return "COMPATIBLE"
        return "GEOGRAPHY_INSUFFICIENT"

    def _joint_availability(self, requirements: list[PolicyRequirement]) -> dict[str, Any]:
        req_vars = [r.canonical_variable for r in requirements if r.importance == "CRITICAL"]
        datasets = {}
        for name, dataset in self.registry.get("joint_datasets", {}).items():
            variables = set(dataset.get("variables", []))
            rows = []
            matched = 0
            for var in req_vars:
                actual = var
                status = "YES" if actual in variables else "NO"
                if status == "NO" and var in PROXIES and PROXIES[var]["proxy"] in variables:
                    status = "PROXY"
                if status in {"YES", "PROXY"}:
                    matched += 1
                rows.append({"variable": var, "available": status})
            datasets[name] = {"source_id": dataset.get("source_id"), "row_count": dataset.get("row_count"), "matrix": rows, "score": matched / max(len(req_vars), 1)}
        best = max((item["score"] for item in datasets.values()), default=0)
        return {"required_critical_variables": req_vars, "datasets": datasets, "score": round(best * 100, 2)}


    def _phase3_requirements(self, results: list[RequirementResult], policy: dict[str, Any]) -> dict[str, Any]:
        required = [r.requirement.canonical_variable for r in results if r.requirement.importance in {"CRITICAL", "IMPORTANT"}]
        return {
            "policy_id": policy.get("policy_id", ""),
            "synthetic_population_requirements": {
                "required_variables": required,
                "critical_variables": [r.requirement.canonical_variable for r in results if r.requirement.importance == "CRITICAL"],
                "optional_variables": [r.requirement.canonical_variable for r in results if r.requirement.importance == "OPTIONAL"],
                "approved_derivations": [r.requirement.canonical_variable for r in results if r.status == "DERIVABLE"],
                "approved_proxies": [r.requirement.canonical_variable for r in results if r.status == "PROXY_AVAILABLE"],
                "calibration_variables": ["gender", "urban_rural", "social_group", "worker_category"],
                "geographic_level": "DISTRICT" if "district" in required else "STATE",
                "temporal_warnings": [f"{r.requirement.canonical_variable}: {r.temporal_status}" for r in results if r.temporal_status not in {"CURRENT", "RECENT"}],
            }
        }

    def _persist_report(self, report: CompatibilityReport) -> None:
        out_dir = self.root / "data/compatibility/reports"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / f"{report.report_id}.json").write_text(json.dumps(report.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")


def parse_policy_text(text: str) -> dict[str, Any]:
    """Small deterministic helper for examples; not an LLM extractor."""
    eligibility = []
    if re.search(r"age|aged", text, re.I):
        match = re.search(r"(\d{1,2})\s*[–-]\s*(\d{1,2})", text)
        eligibility.append({"variable": "age", "operator": "between", "value": [int(match.group(1)), int(match.group(2))] if match else []})
    if re.search(r"unemploy", text, re.I):
        eligibility.append({"variable": "employment_status", "operator": "equals", "value": "Unemployed"})
    if re.search(r"income", text, re.I):
        eligibility.append({"variable": "household_income", "operator": "less_than", "value": 300000, "unit": "INR/year"})
    if re.search(r"Tamil Nadu", text, re.I):
        eligibility.append({"variable": "state", "operator": "equals", "value": "Tamil Nadu"})
    return {
        "policy_id": "TEXT_POLICY",
        "name": text[:80],
        "jurisdiction": {"state": "Tamil Nadu"},
        "eligibility": eligibility,
        "reference_year": 2026,
    }
