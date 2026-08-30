from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.app.modules.data_foundation.io_utils import write_json, write_md
from backend.app.modules.synthetic_population.assessment import (
    ROOT,
    actual_reference_path,
    classify_variable,
    missingness,
    policy_requirements,
    read_csv,
    read_json,
    schema_variables,
)


CORE_STRUCTURAL_VARIABLES = {
    "age", "gender", "district", "urban_rural", "household_size",
    "education_level", "employment_status", "social_group",
}
DETERMINISTIC_FIELDS = {"state", "state_code", "age_group"}
PROXY_MAP = {"household_income": "consumption_expenditure"}
INCLUDE = "INCLUDE"
EXCLUDE = "EXCLUDE"
EXCLUDE_FROM_FEATURES = "EXCLUDE_FROM_FEATURES"
ATTACH_AFTER_GENERATION = "ATTACH_AFTER_GENERATION"
DERIVE_AFTER_GENERATION = "DERIVE_AFTER_GENERATION"


def source_quality(capability: dict[str, Any]) -> str:
    if not capability:
        return "UNKNOWN"
    if capability.get("aggregate_only"):
        return "AGGREGATE_ONLY"
    return capability.get("quality_flag") or "UNKNOWN"


def policy_role(name: str, requirements: dict[str, set[str]]) -> str:
    roles = []
    if name in requirements["critical"]:
        roles.append("CRITICAL")
    elif name in requirements["required"]:
        roles.append("REQUIRED")
    if name in requirements["calibration"]:
        roles.append("CALIBRATION")
    for requested, proxy in PROXY_MAP.items():
        if name == proxy and requested in requirements["proxies"]:
            roles.append(f"PROXY_FOR_{requested}")
    return "; ".join(roles) if roles else "NONE"


def decide_variable(name: str, kind: str, missing_pct: float, capability: dict[str, Any], requirements: dict[str, set[str]]) -> tuple[str, str, str]:
    role = policy_role(name, requirements)
    aggregate_only = bool(capability.get("aggregate_only")) if capability else False
    if kind == "identifier":
        return EXCLUDE, "Identifier must not be learned by a generator.", "NOT_SUITABLE"
    if kind == "metadata":
        return EXCLUDE, "Provenance metadata must not be used as behavioural features.", "NOT_SUITABLE"
    if kind == "weight":
        return EXCLUDE_FROM_FEATURES, "Weight retained for sampling strategy, not model features.", "WEIGHT_ONLY"
    if name in DETERMINISTIC_FIELDS:
        if name == "age_group":
            return DERIVE_AFTER_GENERATION, "Derive deterministically from age after synthesis.", "DERIVED"
        return ATTACH_AFTER_GENERATION, "Tamil Nadu-only deterministic field; attach after synthesis.", "DETERMINISTIC"
    if aggregate_only:
        return EXCLUDE, "Aggregate-only capability cannot become person-level synthetic data in Phase 3.", "NOT_SUITABLE"
    if missing_pct >= 100:
        return EXCLUDE, "Field is fully missing in the reference template.", "NOT_SUITABLE"
    if name in requirements["proxies"]:
        proxy = PROXY_MAP.get(name, "approved proxy")
        return EXCLUDE, f"Requested variable is proxy-backed; preserve semantic truth via {proxy} instead.", "PROXY_REQUEST_EXCLUDED"
    if name in CORE_STRUCTURAL_VARIABLES or role != "NONE":
        return INCLUDE, "Supported core/policy variable with usable reference data.", "SUITABLE"
    if missing_pct > 50:
        return EXCLUDE, "High missingness and no current policy need; defer.", "LOW_SUITABILITY"
    if kind in {"continuous", "integer", "categorical", "ordinal"}:
        return INCLUDE, "Usable optional analysis variable with acceptable missingness.", "SUITABLE_OPTIONAL"
    return EXCLUDE, "No approved Phase 3 training role.", "LOW_SUITABILITY"


def build_variable_selection(root: Path = ROOT) -> list[dict[str, Any]]:
    rows = read_csv(actual_reference_path(root))
    columns = list(rows[0].keys()) if rows else []
    schema = schema_variables(root)
    capabilities = read_json(root / "data/metadata/data_capability_registry.json").get("variables", {})
    requirements = policy_requirements(root)
    miss = missingness(rows, columns)
    decisions = []
    for name in columns:
        kind = classify_variable(name, schema.get(name, {}))
        capability = capabilities.get(name, {})
        missing_pct = miss[name]["missing_percentage"]
        decision, reason, suitability = decide_variable(name, kind, missing_pct, capability, requirements)
        decisions.append({
            "variable": name,
            "decision": decision,
            "reason": reason,
            "type": kind,
            "policy_requirement": policy_role(name, requirements),
            "structural_importance": "CORE" if name in CORE_STRUCTURAL_VARIABLES else "NONE",
            "missing_percentage": missing_pct,
            "source_quality": source_quality(capability),
            "training_suitability": suitability,
        })
    for name in sorted((requirements["required"] | requirements["critical"]) - set(columns)):
        capability = capabilities.get(name, {})
        decisions.append({
            "variable": name,
            "decision": EXCLUDE,
            "reason": "Required by Phase 2 but unavailable as a usable reference-template field.",
            "type": "unavailable",
            "policy_requirement": policy_role(name, requirements),
            "structural_importance": "NONE",
            "missing_percentage": 100.0,
            "source_quality": source_quality(capability),
            "training_suitability": "NOT_SUITABLE",
        })
    return decisions


def write_variable_selection(root: Path = ROOT) -> tuple[Path, Path]:
    decisions = build_variable_selection(root)
    report_path = root / "reports/synthetic_variable_selection.md"
    json_path = root / "data/synthetic/variable_selection.json"
    included = [row["variable"] for row in decisions if row["decision"] == INCLUDE]
    lines = [
        "# Synthetic Variable Selection", "", "## Summary", "",
        f"- Included model features: {len(included)}",
        f"- Included variables: {', '.join(included) if included else 'None'}",
        "- household_income is not synthesized directly; consumption_expenditure is retained as the explicit proxy-backed economic field.",
        "- Reference/source identifiers are excluded; new synthetic IDs will be generated later.",
        "", "## Decisions", "",
        "| Variable | Decision | Type | Policy Requirement | Structural | Missing % | Source Quality | Training Suitability | Reason |",
        "| --- | --- | --- | --- | --- | ---: | --- | --- | --- |",
    ]
    for row in decisions:
        lines.append(
            f"| {row['variable']} | {row['decision']} | {row['type']} | {row['policy_requirement']} | "
            f"{row['structural_importance']} | {row['missing_percentage']} | {row['source_quality']} | "
            f"{row['training_suitability']} | {row['reason']} |"
        )
    write_md(report_path, "\n".join(lines))
    write_json(json_path, {"included_features": included, "decisions": decisions})
    return report_path, json_path
