from __future__ import annotations

from typing import Any
import math

from backend.app.modules.monte_carlo.simulation_model import RiskMetricConfig


def compute_risk_probabilities(
    iteration_results: list[dict[str, Any]],
    risk_configs: list[RiskMetricConfig],
) -> dict[str, Any]:
    valid_results = [r for r in iteration_results if r.get("iteration_status") == "COMPLETED"]
    n_valid = len(valid_results)

    if n_valid == 0:
        return {"n_valid": 0, "risk_metrics": {}}

    risk_outputs: dict[str, Any] = {}

    for rm in risk_configs:
        metric_name = rm.metric
        op = rm.operator.lower()
        thresh = rm.threshold
        out_name = rm.output_name or f"prob_{metric_name}"

        match_count = 0
        applicable_count = 0

        for r in valid_results:
            if metric_name not in r or r[metric_name] is None:
                continue
            val = float(r[metric_name])
            applicable_count += 1

            passed = False
            if op == "greater_than":
                passed = val > thresh
            elif op in ["greater_than_or_equal", "gte"]:
                passed = val >= thresh
            elif op == "less_than":
                passed = val < thresh
            elif op in ["less_than_or_equal", "lte"]:
                passed = val <= thresh
            elif op in ["equals", "eq"]:
                passed = math.isclose(val, thresh)

            if passed:
                match_count += 1

        prob = round(match_count / applicable_count, 4) if applicable_count > 0 else 0.0
        
        # Wilson score interval for binomial proportion
        ci_low, ci_high = _wilson_score_interval(match_count, applicable_count, 0.95)

        risk_outputs[out_name] = {
            "metric": metric_name,
            "operator": op,
            "threshold": thresh,
            "match_count": match_count,
            "applicable_iterations": applicable_count,
            "estimated_probability": prob,
            "confidence_interval_95": {
                "lower": round(ci_low, 4),
                "upper": round(ci_high, 4),
            },
        }

    return {
        "n_valid": n_valid,
        "risk_metrics": risk_outputs,
    }


def _wilson_score_interval(k: int, n: int, confidence: float = 0.95) -> tuple[float, float]:
    if n == 0:
        return 0.0, 0.0
    z = 1.96 if math.isclose(confidence, 0.95) else 2.576
    p_hat = k / n
    denom = 1 + (z**2) / n
    center = (p_hat + (z**2) / (2 * n)) / denom
    term = z * math.sqrt((p_hat * (1 - p_hat) + (z**2) / (4 * n)) / n) / denom
    return max(0.0, center - term), min(1.0, center + term)
