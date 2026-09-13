"""
Configuration validator for Phase 8 Recommendation Engine.
"""

from typing import List
from .recommendation_model import RecommendationConfig

class ConfigValidationError(Exception):
    pass

class RecommendationConfigValidator:
    """Validates RecommendationConfig fields, weights, bounds, and directions."""

    @staticmethod
    def validate(config: RecommendationConfig) -> List[str]:
        errors = []

        if not config.recommendation_id:
            errors.append("recommendation_id must not be empty.")

        if not config.candidate_experiments:
            errors.append("candidate_experiments must contain at least 1 experiment definition.")

        if config.normalization_method not in ["min_max", "z_score"]:
            errors.append(f"Invalid normalization method '{config.normalization_method}'. Allowed: ['min_max', 'z_score'].")

        if config.ranking_method not in ["weighted_sum", "topsis"]:
            errors.append(f"Invalid ranking method '{config.ranking_method}'. Allowed: ['weighted_sum', 'topsis'].")

        if not config.metrics:
            errors.append("metrics list must not be empty.")
        else:
            weight_sum = 0.0
            for m in config.metrics:
                if m.direction not in ["minimize", "maximize"]:
                    errors.append(f"Metric '{m.name}' has invalid direction '{m.direction}'. Allowed: ['minimize', 'maximize'].")
                if m.weight < 0:
                    errors.append(f"Metric '{m.name}' weight cannot be negative: {m.weight}.")
                weight_sum += m.weight

            if abs(weight_sum - 1.0) > 0.05:
                errors.append(f"Metric weights must sum to approximately 1.0 (current sum: {weight_sum:.3f}).")

        for profile in config.stakeholder_profiles:
            profile_weight_sum = sum(profile.weights.values())
            if abs(profile_weight_sum - 1.0) > 0.05:
                errors.append(
                    f"Stakeholder profile '{profile.name}' weights must sum to approximately 1.0 (current sum: {profile_weight_sum:.3f})."
                )

        if errors:
            raise ConfigValidationError("Recommendation configuration validation failed:\n - " + "\n - ".join(errors))

        return errors
