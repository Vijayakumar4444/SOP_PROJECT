from __future__ import annotations

from typing import Any

from backend.app.modules.calibration.raking import apply_trimming_and_normalization, initialize_weights


def poststratify(
    rows: list[dict[str, Any]],
    target: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    initialize_weights(rows)
    variable = target["variable"]
    unresolved = []
    weights = [1.0 for _ in rows]
    total_records = len(rows)
    for category in target.get("categories", []):
        synthetic_categories = set(map(str, category.get("synthetic_categories", [])))
        matches = [idx for idx, row in enumerate(rows) if str(row.get(variable, "")) in synthetic_categories]
        desired = float(category["target_proportion"]) * total_records
        if not matches:
            unresolved.append({
                "target_id": target["target_id"],
                "variable": variable,
                "category": category["category"],
                "reason": "Official target has positive mass, but no matching synthetic rows exist.",
            })
            continue
        factor = desired / len(matches)
        for idx in matches:
            weights[idx] = factor
    for idx, row in enumerate(rows):
        row["raw_calibration_weight"] = f"{weights[idx]:.12g}"
        row["calibration_weight"] = f"{weights[idx]:.12g}"
    trimming = apply_trimming_and_normalization(rows, weights, config)
    return {
        "method": "post_stratification",
        "status": "CONVERGED_WITH_WARNINGS" if unresolved else "CONVERGED",
        "converged": not unresolved,
        "iterations": 1,
        "history": [{
            "iteration": 1,
            "maximum_marginal_error": None,
            "mean_marginal_error": None,
            "weight_min": None,
            "weight_max": None,
            "converged": not unresolved,
        }],
        "unresolved_targets": unresolved,
        "trimming": trimming,
    }
