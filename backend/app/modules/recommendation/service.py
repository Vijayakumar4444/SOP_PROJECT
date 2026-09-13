"""
Phase 8 Recommendation Engine Service Orchestrator.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from .recommendation_model import (
    RecommendationConfig,
    RecommendationSummary,
    CandidatePolicyResult,
)
from .config_loader import RecommendationConfigLoader
from .config_validator import RecommendationConfigValidator
from .result_loader import ExperimentResultLoader
from .compatibility_validator import CompatibilityValidator
from .feasibility_filter import FeasibilityFilter
from .metric_normalizer import MetricNormalizer
from .ranking_engine import RankingEngine
from .pareto_analyzer import ParetoAnalyzer
from .tradeoff_analyzer import TradeoffAnalyzer
from .pairwise_comparator import PairwiseComparator
from .weight_sensitivity import WeightSensitivityAnalyzer
from .fairness_analyzer import DemographicFairnessAnalyzer
from .explanation_generator import ExplanationGenerator
from .report_builder import ReportBuilder

class Phase8RecommendationService:
    """Orchestrates Phase 8 Recommendation Engine workflow."""

    def __init__(self, base_dir: str = "."):
        self.base_dir = base_dir

    def run_recommendation(self, config_path: str) -> Dict[str, Any]:
        # 1. Load config
        config = RecommendationConfigLoader.load_from_file(config_path)

        # 2. Validate config
        RecommendationConfigValidator.validate(config)

        # 3. Load experiment candidates
        candidates = ExperimentResultLoader.load_all(config.candidate_experiments, base_dir=self.base_dir)

        # 4. Check compatibility
        compatibility = CompatibilityValidator.validate_compatibility(candidates)

        # 5. Feasibility filtering
        feasibility_checks = FeasibilityFilter.evaluate_all(candidates, config.feasibility_constraints)
        feasible_count = sum(1 for fc in feasibility_checks if fc.is_feasible)

        # 6. Metric Normalization
        normalized_results = MetricNormalizer.normalize_candidates(
            candidates, config.metrics, method=config.normalization_method
        )

        # 7. Multi-Criteria Ranking (WSM & TOPSIS)
        rankings = RankingEngine.rank_candidates(
            candidates=candidates,
            feasibility_checks=feasibility_checks,
            normalized_results=normalized_results,
            metrics=config.metrics,
        )

        # Determine top recommended candidate
        top_recommended = rankings[0].experiment_id if rankings else None

        # 8. Pareto Analysis
        pareto_candidates = ParetoAnalyzer.analyze_pareto(candidates, config.metrics)

        # 9. Tradeoff & Pairwise Analysis
        tradeoffs = TradeoffAnalyzer.analyze_tradeoffs(candidates, config.metrics)
        pairwise = PairwiseComparator.compare_pairs(candidates, config.metrics)

        # 10. Weight Sensitivity Analysis
        sensitivity = WeightSensitivityAnalyzer.analyze_sensitivity(
            candidates=candidates,
            feasibility_checks=feasibility_checks,
            normalized_results=normalized_results,
            metrics=config.metrics,
            stakeholder_profiles=config.stakeholder_profiles,
        )

        # 11. Demographic Fairness Analysis
        fairness = DemographicFairnessAnalyzer.analyze_all(candidates)

        # 12. Explanation Generation
        explanations = ExplanationGenerator.generate_explanations(
            rankings=rankings,
            feasibility_checks=feasibility_checks,
            pareto_candidates=pareto_candidates,
            tradeoffs=tradeoffs,
            sensitivity_results=sensitivity,
            fairness_results=fairness,
        )

        # Construct Summary
        generated_at = datetime.now(timezone.utc).isoformat()
        summary = RecommendationSummary(
            recommendation_id=config.recommendation_id,
            generated_at=generated_at,
            top_recommended_candidate=top_recommended,
            total_candidates=len(candidates),
            feasible_candidates_count=feasible_count,
            rankings=rankings,
            feasibility_checks=feasibility_checks,
            pareto_candidates=pareto_candidates,
            tradeoffs=tradeoffs,
            weight_sensitivity=sensitivity,
            fairness_results=fairness,
            explanations=explanations,
        )

        # 13. Build & Write Reports
        exported_artifacts = ReportBuilder.build_all_reports(
            config=config,
            summary=summary,
            pairwise_comparisons=pairwise,
            base_dir=self.base_dir,
        )

        return {
            "status": "PASS",
            "recommendation_id": config.recommendation_id,
            "top_recommended_candidate": top_recommended,
            "total_candidates": len(candidates),
            "feasible_candidates": feasible_count,
            "exported_artifacts": exported_artifacts,
            "compatibility": compatibility,
            "explanations": explanations,
        }
