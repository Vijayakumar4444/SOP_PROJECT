from __future__ import annotations

from typing import Any
from backend.app.modules.monte_carlo.simulation_model import DistributionType, SimulationConfig


def validate_simulation_config(config: SimulationConfig) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    # 1. Experiment checks
    if not config.experiment.experiment_id:
        errors.append({"code": "MISSING_EXPERIMENT_ID", "path": "experiment.experiment_id", "message": "Experiment ID is required."})
    if config.experiment.number_of_iterations <= 0:
        errors.append({"code": "INVALID_ITERATIONS", "path": "experiment.number_of_iterations", "message": "Number of iterations must be positive."})

    # 2. Policy path check
    if not config.policy.policy_path:
        errors.append({"code": "MISSING_POLICY_PATH", "path": "policy.policy_path", "message": "Policy path is required."})

    # 3. Parameter uncertainty distribution validation
    if config.uncertainty.policy_parameter_uncertainty_enabled:
        for p_name, p_cfg in config.uncertainty.parameters.items():
            path_prefix = f"uncertainty.parameters['{p_name}']"
            dist = p_cfg.distribution

            if dist in [DistributionType.UNIFORM, DistributionType.DISCRETE_UNIFORM, DistributionType.TRUNCATED_NORMAL]:
                if p_cfg.minimum is None or p_cfg.maximum is None:
                    errors.append({"code": "MISSING_BOUNDS", "path": path_prefix, "message": f"Distribution '{dist.value}' requires minimum and maximum."})
                elif p_cfg.minimum > p_cfg.maximum:
                    errors.append({"code": "INVALID_BOUNDS", "path": path_prefix, "message": f"Minimum ({p_cfg.minimum}) cannot exceed maximum ({p_cfg.maximum})."})

            if dist == DistributionType.TRIANGULAR:
                if p_cfg.minimum is None or p_cfg.maximum is None:
                    errors.append({"code": "MISSING_TRIANGULAR_BOUNDS", "path": path_prefix, "message": "Triangular distribution requires minimum and maximum."})
                elif p_cfg.minimum > p_cfg.maximum:
                    errors.append({"code": "INVALID_TRIANGULAR_BOUNDS", "path": path_prefix, "message": "Minimum cannot exceed maximum."})
                elif p_cfg.mode is not None and not (p_cfg.minimum <= p_cfg.mode <= p_cfg.maximum):
                    errors.append({"code": "INVALID_TRIANGULAR_MODE", "path": path_prefix, "message": f"Mode ({p_cfg.mode}) must be between min ({p_cfg.minimum}) and max ({p_cfg.maximum})."})

            if dist in [DistributionType.NORMAL, DistributionType.TRUNCATED_NORMAL, DistributionType.LOGNORMAL]:
                if p_cfg.std_dev is not None and p_cfg.std_dev < 0:
                    errors.append({"code": "NEGATIVE_STD_DEV", "path": path_prefix, "message": "Standard deviation cannot be negative."})

            if dist == DistributionType.BERNOULLI:
                if p_cfg.probability is None or not (0.0 <= p_cfg.probability <= 1.0):
                    errors.append({"code": "INVALID_PROBABILITY", "path": path_prefix, "message": "Bernoulli probability must be between 0 and 1."})

            if dist == DistributionType.CATEGORICAL:
                if not p_cfg.categories:
                    errors.append({"code": "MISSING_CATEGORIES", "path": path_prefix, "message": "Categorical distribution requires categories list."})
                if p_cfg.weights:
                    if len(p_cfg.weights) != len(p_cfg.categories):
                        errors.append({"code": "WEIGHT_MISMATCH", "path": path_prefix, "message": "Weights count must match categories count."})
                    if any(w < 0 for w in p_cfg.weights):
                        errors.append({"code": "NEGATIVE_WEIGHT", "path": path_prefix, "message": "Weights must be non-negative."})

    # 4. Output percentiles check
    for p in config.outputs.percentiles:
        if not (0.0 <= p <= 1.0):
            errors.append({"code": "INVALID_PERCENTILE", "path": "outputs.percentiles", "message": f"Percentile {p} must be between 0 and 1."})

    # 5. Risk metrics check
    for rm in config.risk_metrics:
        if not rm.metric:
            errors.append({"code": "MISSING_RISK_METRIC_NAME", "path": "risk_metrics", "message": "Risk metric name cannot be empty."})

    is_valid = len(errors) == 0
    return {
        "valid": is_valid,
        "errors": errors,
        "warnings": warnings,
    }
