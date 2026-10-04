"""Policy memory priors used to calibrate fresh backend simulations."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.app.policy_memory import PolicyMemoryStore, build_policy_memory_context


def write_policy_memory_priors(
    run_id: str,
    memory: PolicyMemoryStore,
    output_path: Path,
    similar_limit: int = 5,
) -> dict[str, Any]:
    """Write DB-derived priors for the current run.

    These priors are intentionally advisory. They tune uncertainty/risk ranges
    for the fresh simulation, but never replace synthetic population generation
    or policy execution.
    """

    run = memory.get_run_inputs(run_id)
    if not run:
        payload = _empty_payload(run_id, "run_not_found")
    else:
        policy_payload = run.get("policy_payload") or {}
        policy_hash = str(run.get("policy_hash") or "")
        similar = memory.find_similar_completed(policy_payload, policy_hash, limit=similar_limit)
        context = build_policy_memory_context(similar, policy_hash)
        payload = {
            "runId": run_id,
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "available": bool(similar),
            "source": "policy_simulation_runs",
            "policyHash": policy_hash,
            "similarPolicyCount": len(similar),
            "similarPolicies": similar,
            "priors": context.get("priors", {}),
            "monteCarloCalibration": derive_monte_carlo_calibration(context.get("priors", {})),
        }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def derive_monte_carlo_calibration(priors: dict[str, Any]) -> dict[str, Any]:
    calibration: dict[str, Any] = {}
    for metric, bounds in [
        ("coverage", (0.0, 1.0)),
        ("fiscalPressure", (0.0, 5.0)),
        ("riskScore", (0.0, 100.0)),
        ("equityScore", (0.0, 100.0)),
        ("benefitAmount", (0.0, float("inf"))),
    ]:
        stats = priors.get(metric)
        if not isinstance(stats, dict) or stats.get("mean") is None:
            continue
        calibration[metric] = _expanded_range(stats, bounds[0], bounds[1])
    if calibration:
        calibration["source"] = "similar_policy_priors"
        calibration["sampleSize"] = priors.get("sampleSize", 0)
    return calibration


def apply_policy_memory_priors_to_config(raw_config: dict[str, Any], priors_payload: dict[str, Any]) -> dict[str, Any]:
    """Return a config copy tuned with memory priors."""

    if not priors_payload.get("available"):
        return raw_config

    tuned = json.loads(json.dumps(raw_config))
    calibration = priors_payload.get("monteCarloCalibration") or {}
    tuned["policy_memory_priors"] = priors_payload

    coverage = calibration.get("coverage")
    if isinstance(coverage, dict):
        tuned.setdefault("risk_metrics", []).append(
            {
                "metric": "coverage_rate",
                "operator": "less_than",
                "threshold": coverage["lower"],
                "output_name": "probability_coverage_below_memory_prior",
            }
        )

    benefit = calibration.get("benefitAmount")
    params = (
        tuned.setdefault("uncertainty", {})
        .setdefault("policy_parameter_uncertainty", {})
        .setdefault("parameters", {})
    )
    if isinstance(benefit, dict) and isinstance(params.get("benefit_amount"), dict):
        _narrow_parameter_range(params["benefit_amount"], benefit)

    fiscal = calibration.get("fiscalPressure")
    if isinstance(fiscal, dict):
        tuned.setdefault("calibration", {})["memory_prior_context"] = {
            "fiscalPressure": fiscal,
            "sampleSize": calibration.get("sampleSize", 0),
        }

    return tuned


def load_policy_memory_priors(root: Path) -> dict[str, Any]:
    path = root / "data" / "synthetic" / "policy_memory_priors.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _empty_payload(run_id: str, reason: str) -> dict[str, Any]:
    return {
        "runId": run_id,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "available": False,
        "reason": reason,
        "similarPolicyCount": 0,
        "similarPolicies": [],
        "priors": {},
        "monteCarloCalibration": {},
    }


def _expanded_range(stats: dict[str, Any], minimum: float, maximum: float) -> dict[str, float]:
    mean = _number(stats.get("mean"), 0.0)
    lower = _number(stats.get("min"), mean)
    upper = _number(stats.get("max"), mean)
    if lower == upper:
        spread = max(abs(mean) * 0.1, 0.05 if maximum <= 1 else 1.0)
        lower -= spread
        upper += spread
    else:
        spread = (upper - lower) * 0.1
        lower -= spread
        upper += spread
    return {
        "mean": round(_clamp(mean, minimum, maximum), 6),
        "lower": round(_clamp(lower, minimum, maximum), 6),
        "upper": round(_clamp(upper, minimum, maximum), 6),
    }


def _narrow_parameter_range(parameter: dict[str, Any], prior_range: dict[str, float]) -> None:
    existing_min = _number(parameter.get("minimum"), prior_range["lower"])
    existing_max = _number(parameter.get("maximum"), prior_range["upper"])
    next_min = max(existing_min, prior_range["lower"])
    next_max = min(existing_max, prior_range["upper"])
    if next_min >= next_max:
        return
    parameter["minimum"] = next_min
    parameter["maximum"] = next_max
    if "mode" in parameter:
        parameter["mode"] = _clamp(prior_range["mean"], next_min, next_max)
    if "mean" in parameter:
        parameter["mean"] = _clamp(prior_range["mean"], next_min, next_max)


def _number(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return min(maximum, max(minimum, value))
