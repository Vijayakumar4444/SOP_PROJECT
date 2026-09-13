from __future__ import annotations

from typing import Any
import math


def compute_uncertainty_summary(
    iteration_results: list[dict[str, Any]],
    percentiles_requested: list[float] | None = None,
    confidence_level: float = 0.95,
) -> dict[str, Any]:
    percentiles_requested = percentiles_requested or [0.025, 0.05, 0.25, 0.50, 0.75, 0.95, 0.975]
    valid_results = [r for r in iteration_results if r.get("iteration_status") == "COMPLETED"]
    failed_results = [r for r in iteration_results if r.get("iteration_status") != "COMPLETED"]

    n_valid = len(valid_results)
    n_failed = len(failed_results)

    if n_valid == 0:
        return {
            "n_valid": 0,
            "n_failed": n_failed,
            "metrics_summary": {},
        }

    # Extract numeric metric names
    numeric_metrics = [
        "eligible_count",
        "weighted_eligible_population",
        "eligibility_rate",
        "beneficiary_count",
        "weighted_beneficiary_population",
        "coverage_rate",
        "total_policy_cost",
        "average_benefit",
        "budget_utilization",
    ]

    summary_by_metric: dict[str, Any] = {}

    for metric_name in numeric_metrics:
        vals = [float(r[metric_name]) for r in valid_results if metric_name in r and r[metric_name] is not None]
        if not vals:
            continue

        metric_stats = compute_single_metric_uncertainty(vals, percentiles_requested, confidence_level)
        summary_by_metric[metric_name] = metric_stats

    return {
        "n_valid": n_valid,
        "n_failed": n_failed,
        "metrics_summary": summary_by_metric,
    }


def compute_single_metric_uncertainty(
    values: list[float],
    percentiles_requested: list[float],
    confidence_level: float = 0.95,
) -> dict[str, Any]:
    n = len(values)
    if n == 0:
        return {}

    sorted_vals = sorted(values)
    mean_val = sum(sorted_vals) / n

    if n > 1:
        var_val = sum((x - mean_val) ** 2 for x in sorted_vals) / (n - 1)
        std_val = math.sqrt(var_val)
    else:
        var_val = 0.0
        std_val = 0.0

    min_val = sorted_vals[0]
    max_val = sorted_vals[-1]
    median_val = _quantile(sorted_vals, 0.50)
    q25 = _quantile(sorted_vals, 0.25)
    q75 = _quantile(sorted_vals, 0.75)
    iqr_val = q75 - q25

    # Monte Carlo standard error
    mc_se = std_val / math.sqrt(n) if n > 0 else 0.0
    relative_mc_error = (mc_se / abs(mean_val)) if mean_val != 0 else 0.0

    # Coefficient of variation
    cv_val = (std_val / abs(mean_val)) if mean_val != 0 else 0.0

    # Percentiles dictionary
    pct_dict = {}
    for p in percentiles_requested:
        pct_key = f"p{int(round(p * 1000)) / 10:g}".replace(".", "_")
        pct_dict[pct_key] = round(_quantile(sorted_vals, p), 4)

    # 95% Confidence Interval for the mean
    z_val = 1.96 if math.isclose(confidence_level, 0.95) else 2.576
    ci_lower = mean_val - z_val * mc_se
    ci_upper = mean_val + z_val * mc_se

    return {
        "n_samples": n,
        "mean": round(mean_val, 4),
        "median": round(median_val, 4),
        "std_dev": round(std_val, 4),
        "variance": round(var_val, 4),
        "min": round(min_val, 4),
        "max": round(max_val, 4),
        "iqr": round(iqr_val, 4),
        "coefficient_of_variation": round(cv_val, 4),
        "mc_standard_error": round(mc_se, 4),
        "relative_mc_error": round(relative_mc_error, 4),
        "mean_confidence_interval": {
            "confidence_level": confidence_level,
            "lower": round(ci_lower, 4),
            "upper": round(ci_upper, 4),
        },
        "percentiles": pct_dict,
    }


def _quantile(sorted_list: list[float], q: float) -> float:
    if not sorted_list:
        return 0.0
    if len(sorted_list) == 1:
        return sorted_list[0]
    idx = q * (len(sorted_list) - 1)
    lower = int(idx)
    upper = min(lower + 1, len(sorted_list) - 1)
    frac = idx - lower
    return sorted_list[lower] + (sorted_list[upper] - sorted_list[lower]) * frac
