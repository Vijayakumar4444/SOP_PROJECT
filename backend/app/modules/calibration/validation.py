from __future__ import annotations

from math import isfinite
from typing import Any

from backend.app.modules.calibration.utils import to_float


def evaluate_quality_gates(
    rows: list[dict[str, Any]],
    calibration_result: dict[str, Any],
    post_comparison: dict[str, Any],
    diagnostics: dict[str, Any],
    config: dict[str, Any],
    warnings: list[str],
) -> dict[str, Any]:
    gates_config = config.get("quality_gates", {})
    weights = [to_float(row.get("calibration_weight"), 0.0) or 0.0 for row in rows]
    gates = [
        _gate("calibration_converged", not gates_config.get("require_convergence", True) or calibration_result.get("converged"), "Calibration convergence is required by configuration."),
        _gate("no_negative_weights", all(weight >= 0 for weight in weights), "Calibration weights must not be negative."),
        _gate("no_nan_or_infinite_weights", all(isfinite(weight) for weight in weights), "Calibration weights must be finite numbers."),
        _gate("max_weight_below_threshold", diagnostics["max_weight"] <= gates_config.get("max_weight", 999999.0), f"Maximum weight must be <= {gates_config.get('max_weight', 999999.0)}."),
        _gate("min_weight_above_threshold", diagnostics["min_weight"] >= gates_config.get("min_weight", 0.0), f"Minimum weight must be >= {gates_config.get('min_weight', 0.0)}."),
        _gate("post_marginal_error_below_threshold", post_comparison["summary"]["max_category_error"] <= gates_config.get("max_marginal_error", 1.0), f"Maximum post-calibration marginal error must be <= {gates_config.get('max_marginal_error', 1.0)}."),
        _gate("ess_ratio_above_threshold", diagnostics["ess_ratio"] >= gates_config.get("min_ess_ratio", 0.0), f"ESS ratio must be >= {gates_config.get('min_ess_ratio', 0.0)}."),
        _gate("unresolved_targets_below_tolerance", len(calibration_result.get("unresolved_targets", [])) <= gates_config.get("max_unresolved_targets", 0), f"Unresolved targets must be <= {gates_config.get('max_unresolved_targets', 0)}."),
    ]
    failed = [gate for gate in gates if not gate["passed"]]
    if failed:
        status = "FAIL"
    elif warnings or calibration_result.get("status") == "CONVERGED_WITH_WARNINGS":
        status = "PASS_WITH_WARNINGS"
    else:
        status = "PASS"
    return {"status": status, "gates": gates}


def _gate(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}
