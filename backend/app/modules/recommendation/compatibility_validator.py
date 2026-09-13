"""
Compatibility validator for multi-experiment recommendation comparison.
"""

from typing import List, Dict, Any
from .recommendation_model import CandidatePolicyResult

class CompatibilityValidationError(Exception):
    pass

class CompatibilityValidator:
    """Validates that candidate Phase 7 experiments are structurally and demographically comparable."""

    @staticmethod
    def validate_compatibility(candidates: List[CandidatePolicyResult]) -> Dict[str, Any]:
        if not candidates:
            raise ValueError("Candidates list for compatibility validation cannot be empty.")

        warnings = []
        errors = []

        base_region = candidates[0].metadata.get("region", "TN")
        base_population_size = candidates[0].metadata.get("base_population_size")
        base_currency = candidates[0].metadata.get("currency", "INR")

        for cand in candidates[1:]:
            region = cand.metadata.get("region", "TN")
            if region != base_region:
                errors.append(f"Region mismatch: '{cand.experiment_id}' uses '{region}' while base is '{base_region}'.")

            pop_size = cand.metadata.get("base_population_size")
            if base_population_size and pop_size and pop_size != base_population_size:
                warnings.append(
                    f"Population size difference: '{cand.experiment_id}' has size {pop_size} vs base size {base_population_size}."
                )

            currency = cand.metadata.get("currency", "INR")
            if currency != base_currency:
                errors.append(f"Currency mismatch: '{cand.experiment_id}' uses '{currency}' while base is '{base_currency}'.")

        is_compatible = len(errors) == 0

        if not is_compatible:
            raise CompatibilityValidationError("Candidate experiments compatibility check failed:\n - " + "\n - ".join(errors))

        return {
            "is_compatible": is_compatible,
            "candidate_count": len(candidates),
            "base_region": base_region,
            "warnings": warnings,
            "errors": errors,
        }
