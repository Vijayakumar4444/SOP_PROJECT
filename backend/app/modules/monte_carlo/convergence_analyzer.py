from __future__ import annotations

from typing import Any
import math

from backend.app.modules.monte_carlo.simulation_model import ConvergenceConfig


def check_simulation_convergence(
    iteration_results: list[dict[str, Any]],
    config: ConvergenceConfig,
) -> dict[str, Any]:
    valid_results = [r for r in iteration_results if r.get("iteration_status") == "COMPLETED"]
    n_valid = len(valid_results)

    if not config.enabled or n_valid < config.minimum_iterations:
        return {
            "converged": False,
            "status": "INSUFFICIENT_ITERATIONS",
            "minimum_iterations_required": config.minimum_iterations,
            "current_valid_iterations": n_valid,
            "checkpoints": [],
        }

    metrics = config.metrics or ["total_policy_cost", "weighted_beneficiary_population", "coverage_rate"]
    check_interval = config.check_interval or 10
    threshold = config.relative_mc_error_threshold or 0.02
    stable_required = config.stable_checks_required or 2

    checkpoint_history: list[dict[str, Any]] = []
    consecutive_stable = 0
    overall_converged = False

    # Compute checkpoints
    for step in range(config.minimum_iterations, n_valid + 1, check_interval):
        sub_slice = valid_results[:step]
        chk_metrics: dict[str, Any] = {}
        step_all_stable = True

        for m_name in metrics:
            vals = [float(r[m_name]) for r in sub_slice if m_name in r and r[m_name] is not None]
            if not vals:
                continue

            n_sub = len(vals)
            m_mean = sum(vals) / n_sub
            m_var = sum((x - m_mean) ** 2 for x in vals) / (n_sub - 1) if n_sub > 1 else 0.0
            m_std = math.sqrt(m_var)
            mc_se = m_std / math.sqrt(n_sub)
            rel_error = (mc_se / abs(m_mean)) if m_mean != 0 else 0.0

            is_stable = rel_error <= threshold
            if not is_stable:
                step_all_stable = False

            chk_metrics[m_name] = {
                "running_mean": round(m_mean, 4),
                "running_std": round(m_std, 4),
                "mc_standard_error": round(mc_se, 4),
                "relative_mc_error": round(rel_error, 4),
                "stable": is_stable,
            }

        if step_all_stable:
            consecutive_stable += 1
        else:
            consecutive_stable = 0

        checkpoint_history.append({
            "iteration": step,
            "consecutive_stable_checks": consecutive_stable,
            "all_metrics_stable": step_all_stable,
            "metric_diagnostics": chk_metrics,
        })

    if consecutive_stable >= stable_required:
        overall_converged = True

    return {
        "converged": overall_converged,
        "status": "CONVERGED" if overall_converged else "NOT_CONVERGED",
        "current_valid_iterations": n_valid,
        "consecutive_stable_checks": consecutive_stable,
        "required_stable_checks": stable_required,
        "error_threshold": threshold,
        "checkpoint_history": checkpoint_history,
    }
