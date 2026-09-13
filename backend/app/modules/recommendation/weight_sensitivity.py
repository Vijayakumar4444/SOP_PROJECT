"""
Weight sensitivity analyzer evaluating policy ranking shifts across stakeholder profiles.
"""

from typing import List, Dict, Any
from .recommendation_model import (
    CandidatePolicyResult,
    FeasibilityCheckResult,
    NormalizedMetricResult,
    MetricConfig,
    StakeholderProfileConfig,
    WeightSensitivityResult,
)
from .ranking_engine import RankingEngine

class WeightSensitivityAnalyzer:
    """Evaluates how candidate policy rankings shift across pre-defined stakeholder weight profiles."""

    @staticmethod
    def analyze_sensitivity(
        candidates: List[CandidatePolicyResult],
        feasibility_checks: List[FeasibilityCheckResult],
        normalized_results: List[NormalizedMetricResult],
        metrics: List[MetricConfig],
        stakeholder_profiles: List[StakeholderProfileConfig],
    ) -> List[WeightSensitivityResult]:
        if not stakeholder_profiles:
            return []

        sensitivity_results = []
        for profile in stakeholder_profiles:
            # Re-rank under profile weights
            scores = RankingEngine.rank_candidates(
                candidates=candidates,
                feasibility_checks=feasibility_checks,
                normalized_results=normalized_results,
                metrics=metrics,
                custom_weights=profile.weights,
            )

            rankings = [
                {
                    "experiment_id": s.experiment_id,
                    "display_name": s.display_name,
                    "rank": s.rank,
                    "wsm_score": s.wsm_score,
                    "is_feasible": s.is_feasible,
                }
                for s in scores
            ]

            sensitivity_results.append(
                WeightSensitivityResult(
                    profile_name=profile.name,
                    weights=profile.weights,
                    rankings=rankings,
                )
            )

        return sensitivity_results
