"""
Phase 8: Recommendation Engine for SOP Project (Synthetic Population-Based Policy Simulation for Tamil Nadu).

This module provides multi-criteria decision making, feasibility filtering,
normalization (Min-Max, Z-score), Pareto frontier dominance analysis, trade-off & pairwise analysis,
weight sensitivity across stakeholder profiles, demographic group fairness analysis,
template-based explanation generation, structured artifact reporting, and end-to-end
phase-by-phase verification.
"""

from .recommendation_model import (
    RecommendationConfig,
    CandidatePolicyResult,
    FeasibilityCheckResult,
    NormalizedMetricResult,
    RankingScore,
    ParetoCandidateResult,
    TradeoffComparison,
    PairwiseComparison,
    WeightSensitivityResult,
    DemographicFairnessResult,
    RecommendationSummary,
)
from .service import Phase8RecommendationService

__all__ = [
    "RecommendationConfig",
    "CandidatePolicyResult",
    "FeasibilityCheckResult",
    "NormalizedMetricResult",
    "RankingScore",
    "ParetoCandidateResult",
    "TradeoffComparison",
    "PairwiseComparison",
    "WeightSensitivityResult",
    "DemographicFairnessResult",
    "RecommendationSummary",
    "Phase8RecommendationService",
]
