from __future__ import annotations

from typing import Any
import math


def analyze_parameter_sensitivity(
    iteration_results: list[dict[str, Any]],
    target_outcomes: list[str] | None = None,
) -> dict[str, Any]:
    valid_results = [r for r in iteration_results if r.get("iteration_status") == "COMPLETED"]
    n_valid = len(valid_results)

    if n_valid < 5:
        return {
            "n_valid": n_valid,
            "status": "INSUFFICIENT_DATA_FOR_SENSITIVITY",
            "sensitivity_matrix": {},
        }

    target_outcomes = target_outcomes or [
        "total_policy_cost",
        "weighted_beneficiary_population",
        "coverage_rate",
        "budget_utilization",
    ]

    # Find sampled input parameter names
    param_names: set[str] = set()
    for r in valid_results:
        sampled_dict = r.get("sampled_parameters", {})
        if isinstance(sampled_dict, dict):
            for k in sampled_dict.keys():
                param_names.add(k)

    if not param_names:
        return {
            "n_valid": n_valid,
            "status": "NO_VARYING_PARAMETERS_FOUND",
            "sensitivity_matrix": {},
        }

    sensitivity_matrix: dict[str, Any] = {}

    for param_name in sorted(param_names):
        param_sensitivity: dict[str, Any] = {}

        for outcome_name in target_outcomes:
            pairs = []
            for r in valid_results:
                sampled_dict = r.get("sampled_parameters", {})
                if isinstance(sampled_dict, dict) and param_name in sampled_dict and outcome_name in r:
                    val_x = sampled_dict[param_name]
                    val_y = r[outcome_name]
                    if isinstance(val_x, (int, float)) and isinstance(val_y, (int, float)):
                        pairs.append((float(val_x), float(val_y)))

            if len(pairs) < 5:
                continue

            xs = [p[0] for p in pairs]
            ys = [p[1] for p in pairs]

            pearson_r = _pearson_correlation(xs, ys)
            spearman_r = _spearman_correlation(xs, ys)

            param_sensitivity[outcome_name] = {
                "sample_size": len(pairs),
                "pearson_correlation": round(pearson_r, 4),
                "spearman_rank_correlation": round(spearman_r, 4),
                "impact_direction": "POSITIVE" if spearman_r > 0.1 else ("NEGATIVE" if spearman_r < -0.1 else "NEUTRAL"),
                "strength": _correlation_strength(abs(spearman_r)),
            }

        sensitivity_matrix[param_name] = param_sensitivity

    return {
        "n_valid": n_valid,
        "status": "COMPLETED",
        "sensitivity_matrix": sensitivity_matrix,
    }


def _pearson_correlation(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    if n < 2:
        return 0.0
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n

    var_x = sum((x - mean_x) ** 2 for x in xs)
    var_y = sum((y - mean_y) ** 2 for y in ys)

    if var_x <= 1e-12 or var_y <= 1e-12:
        return 0.0

    cov_xy = sum((xs[i] - mean_x) * (ys[i] - mean_y) for i in range(n))
    return cov_xy / math.sqrt(var_x * var_y)


def _spearman_correlation(xs: list[float], ys: list[float]) -> float:
    rank_x = _rank_data(xs)
    rank_y = _rank_data(ys)
    return _pearson_correlation(rank_x, rank_y)


def _rank_data(data: list[float]) -> list[float]:
    indexed = sorted(enumerate(data), key=lambda item: item[1])
    ranks = [0.0] * len(data)
    for rank_idx, (orig_idx, val) in enumerate(indexed):
        ranks[orig_idx] = float(rank_idx + 1)
    return ranks


def _correlation_strength(abs_val: float) -> str:
    if abs_val >= 0.7:
        return "STRONG"
    elif abs_val >= 0.3:
        return "MODERATE"
    elif abs_val >= 0.1:
        return "WEAK"
    return "NEGLIGIBLE"
