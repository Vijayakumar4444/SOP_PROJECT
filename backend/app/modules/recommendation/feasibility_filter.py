"""
Feasibility constraint filtering engine for policy recommendation candidates.
"""

from typing import List, Dict, Any
from .recommendation_model import (
    CandidatePolicyResult,
    FeasibilityConstraintConfig,
    FeasibilityCheckResult,
)

class FeasibilityFilter:
    """Evaluates candidate policies against hard policy feasibility constraints."""

    @staticmethod
    def evaluate_candidate(
        candidate: CandidatePolicyResult,
        constraints: FeasibilityConstraintConfig,
    ) -> FeasibilityCheckResult:
        violations = []
        evaluated = {}

        raw = candidate.raw_metrics
        mean_cost = raw.get("mean_total_cost", 0.0)
        p95_cost = raw.get("p95_total_cost", mean_cost)
        mean_beneficiaries = raw.get("mean_beneficiaries", 0.0)
        risk_prob = raw.get("budget_exceedance_risk", 0.0)
        mc_error = raw.get("relative_mc_error", 0.0)

        # 1. Max budget constraint
        if constraints.max_budget is not None:
            evaluated["max_budget"] = {
                "threshold": constraints.max_budget,
                "actual": mean_cost,
                "passed": mean_cost <= constraints.max_budget,
            }
            if mean_cost > constraints.max_budget:
                violations.append(
                    f"Mean total cost (₹{mean_cost:,.2f}) exceeds budget cap (₹{constraints.max_budget:,.2f})."
                )

        # 2. Max risk probability constraint
        if constraints.max_risk_probability is not None:
            evaluated["max_risk_probability"] = {
                "threshold": constraints.max_risk_probability,
                "actual": risk_prob,
                "passed": risk_prob <= constraints.max_risk_probability,
            }
            if risk_prob > constraints.max_risk_probability:
                violations.append(
                    f"Budget exceedance risk ({risk_prob:.1%}) exceeds maximum threshold ({constraints.max_risk_probability:.1%})."
                )

        # 3. Min coverage constraint
        if constraints.min_coverage is not None:
            evaluated["min_coverage"] = {
                "threshold": constraints.min_coverage,
                "actual": mean_beneficiaries,
                "passed": mean_beneficiaries >= constraints.min_coverage,
            }
            if mean_beneficiaries < constraints.min_coverage:
                violations.append(
                    f"Beneficiary count ({mean_beneficiaries:,.0f}) is below minimum target coverage ({constraints.min_coverage:,.0f})."
                )

        # 4. Max relative Monte Carlo error constraint
        if constraints.max_relative_mc_error is not None:
            evaluated["max_relative_mc_error"] = {
                "threshold": constraints.max_relative_mc_error,
                "actual": mc_error,
                "passed": mc_error <= constraints.max_relative_mc_error,
            }
            if mc_error > constraints.max_relative_mc_error:
                violations.append(
                    f"Monte Carlo standard error ({mc_error:.2%}) exceeds convergence threshold ({constraints.max_relative_mc_error:.2%})."
                )

        is_feasible = len(violations) == 0

        return FeasibilityCheckResult(
            experiment_id=candidate.experiment_id,
            display_name=candidate.display_name,
            is_feasible=is_feasible,
            violations=violations,
            evaluated_constraints=evaluated,
        )

    @staticmethod
    def evaluate_all(
        candidates: List[CandidatePolicyResult],
        constraints: FeasibilityConstraintConfig,
    ) -> List[FeasibilityCheckResult]:
        return [FeasibilityFilter.evaluate_candidate(c, constraints) for c in candidates]
