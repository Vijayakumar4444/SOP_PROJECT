from __future__ import annotations

from typing import Any

from backend.app.modules.calibration.diagnostics import weight_diagnostics
from backend.app.modules.calibration.marginal_comparison import compare_marginals
from backend.app.modules.calibration.utils import rounded


def initialize_weights(rows: list[dict[str, Any]]) -> None:
    for row in rows:
        row["base_weight"] = "1.0"
        row["raw_calibration_weight"] = "1.0"
        row["calibration_weight"] = "1.0"
        row["normalized_weight"] = "1.0"


def rake_weights(
    rows: list[dict[str, Any]],
    targets: list[dict[str, Any]],
    config: dict[str, Any],
) -> dict[str, Any]:
    initialize_weights(rows)
    weights = [1.0 for _ in rows]
    max_iterations = int(config.get("max_iterations", 50))
    tolerance = float(config.get("tolerance", 0.0005))
    history = []
    unresolved = []
    converged = False
    for iteration in range(1, max_iterations + 1):
        for target in targets:
            total_weight = sum(weights)
            variable = target["variable"]
            for category in target.get("categories", []):
                matches = [idx for idx, row in enumerate(rows) if str(row.get(variable, "")) in set(map(str, category.get("synthetic_categories", [])))]
                current = sum(weights[idx] for idx in matches)
                desired = float(category["target_proportion"]) * total_weight
                if current <= 0:
                    if desired > 0:
                        unresolved.append({
                            "iteration": iteration,
                            "target_id": target["target_id"],
                            "variable": variable,
                            "category": category["category"],
                            "reason": "Official target has positive mass, but no matching synthetic rows exist.",
                        })
                    continue
                factor = desired / current
                for idx in matches:
                    weights[idx] *= factor
        for idx, row in enumerate(rows):
            row["raw_calibration_weight"] = f"{weights[idx]:.12g}"
            row["calibration_weight"] = f"{weights[idx]:.12g}"
        comparison = compare_marginals(rows, targets, "calibration_weight")
        diagnostics = weight_diagnostics(rows, "calibration_weight")
        max_error = comparison["summary"]["max_category_error"]
        history.append({
            "iteration": iteration,
            "maximum_marginal_error": max_error,
            "mean_marginal_error": comparison["summary"]["mean_absolute_category_error"],
            "weight_min": diagnostics["min_weight"],
            "weight_max": diagnostics["max_weight"],
            "converged": max_error <= tolerance,
        })
        if max_error <= tolerance:
            converged = True
            break
    trim_result = apply_trimming_and_normalization(rows, weights, config)
    status = "CONVERGED" if converged else "NOT_CONVERGED"
    if converged and (unresolved or trim_result["trimmed_row_count"]):
        status = "CONVERGED_WITH_WARNINGS"
    return {
        "method": "raking",
        "status": status,
        "converged": converged,
        "iterations": len(history),
        "history": history,
        "unresolved_targets": _deduplicate_unresolved(unresolved),
        "trimming": trim_result,
    }


def apply_trimming_and_normalization(rows: list[dict[str, Any]], weights: list[float], config: dict[str, Any]) -> dict[str, Any]:
    bounds = config.get("weight_bounds", {})
    lower = float(bounds.get("min", 0.0))
    upper = float(bounds.get("max", 999999.0))
    trimming = config.get("trimming", {})
    trimmed = []
    final = list(weights)
    if trimming.get("enabled", True):
        for idx, weight in enumerate(final):
            capped = min(max(weight, lower), upper)
            if capped != weight:
                trimmed.append(idx)
            final[idx] = capped
    desired_total = float(len(rows))
    final = _normalize_with_bounds(final, desired_total, lower, upper)
    for idx, row in enumerate(rows):
        row["calibration_weight"] = f"{final[idx]:.12g}"
        row["normalized_weight"] = f"{final[idx]:.12g}"
    return {
        "enabled": bool(trimming.get("enabled", True)),
        "method": trimming.get("method", "absolute"),
        "lower_bound": rounded(lower),
        "upper_bound": rounded(upper),
        "trimmed_row_count": len(trimmed),
        "trimmed_row_indices_sample": trimmed[:20],
        "normalized_to": rounded(desired_total),
    }


def _normalize_with_bounds(weights: list[float], desired_total: float, lower: float, upper: float) -> list[float]:
    if not weights or sum(weights) == 0:
        return weights
    if desired_total < lower * len(weights) or desired_total > upper * len(weights):
        return [weight * desired_total / sum(weights) for weight in weights]
    final = [min(max(weight, lower), upper) for weight in weights]
    for _ in range(50):
        total = sum(final)
        delta = desired_total - total
        if abs(delta) <= 1e-9:
            break
        if delta > 0:
            candidates = [idx for idx, weight in enumerate(final) if weight < upper]
            capacity = sum(upper - final[idx] for idx in candidates)
            if not candidates or capacity <= 0:
                break
            for idx in candidates:
                addition = delta * ((upper - final[idx]) / capacity)
                final[idx] = min(upper, final[idx] + addition)
        else:
            candidates = [idx for idx, weight in enumerate(final) if weight > lower]
            capacity = sum(final[idx] - lower for idx in candidates)
            if not candidates or capacity <= 0:
                break
            for idx in candidates:
                reduction = (-delta) * ((final[idx] - lower) / capacity)
                final[idx] = max(lower, final[idx] - reduction)
    return final


def _deduplicate_unresolved(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    out = []
    for item in items:
        key = (item["target_id"], item["category"], item["reason"])
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out
