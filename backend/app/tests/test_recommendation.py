"""
Unit tests for Phase 8 Recommendation Engine modules.
"""

import os
import unittest
from backend.app.modules.recommendation.recommendation_model import (
    RecommendationConfig,
    CandidateExperimentConfig,
    FeasibilityConstraintConfig,
    MetricConfig,
    StakeholderProfileConfig,
    CandidatePolicyResult,
)
from backend.app.modules.recommendation.config_loader import RecommendationConfigLoader
from backend.app.modules.recommendation.config_validator import (
    RecommendationConfigValidator,
    ConfigValidationError,
)
from backend.app.modules.recommendation.compatibility_validator import (
    CompatibilityValidator,
    CompatibilityValidationError,
)
from backend.app.modules.recommendation.feasibility_filter import FeasibilityFilter
from backend.app.modules.recommendation.metric_normalizer import MetricNormalizer
from backend.app.modules.recommendation.ranking_engine import RankingEngine
from backend.app.modules.recommendation.pareto_analyzer import ParetoAnalyzer
from backend.app.modules.recommendation.tradeoff_analyzer import TradeoffAnalyzer
from backend.app.modules.recommendation.pairwise_comparator import PairwiseComparator
from backend.app.modules.recommendation.weight_sensitivity import WeightSensitivityAnalyzer
from backend.app.modules.recommendation.fairness_analyzer import DemographicFairnessAnalyzer
from backend.app.modules.recommendation.explanation_generator import ExplanationGenerator

class TestRecommendationEngine(unittest.TestCase):

    def setUp(self):
        self.metrics = [
            MetricConfig(name="mean_total_cost", direction="minimize", weight=0.35),
            MetricConfig(name="mean_beneficiaries", direction="maximize", weight=0.30),
            MetricConfig(name="p95_total_cost", direction="minimize", weight=0.15),
            MetricConfig(name="budget_exceedance_risk", direction="minimize", weight=0.20),
        ]

        self.candidates = [
            CandidatePolicyResult(
                experiment_id="exp_a",
                display_name="Option A",
                policy_type="pension",
                raw_metrics={
                    "mean_total_cost": 40000000.0,
                    "p95_total_cost": 48000000.0,
                    "mean_beneficiaries": 2000.0,
                    "budget_exceedance_risk": 0.10,
                    "relative_mc_error": 0.02,
                },
                metadata={"region": "TN", "currency": "INR", "base_population_size": 1000},
                uncertainty_summary={},
                risk_probabilities={},
                convergence_report={},
                sensitivity_report={},
            ),
            CandidatePolicyResult(
                experiment_id="exp_b",
                display_name="Option B",
                policy_type="subsidy",
                raw_metrics={
                    "mean_total_cost": 30000000.0,
                    "p95_total_cost": 36000000.0,
                    "mean_beneficiaries": 1200.0,
                    "budget_exceedance_risk": 0.05,
                    "relative_mc_error": 0.01,
                },
                metadata={"region": "TN", "currency": "INR", "base_population_size": 1000},
                uncertainty_summary={},
                risk_probabilities={},
                convergence_report={},
                sensitivity_report={},
            ),
            CandidatePolicyResult(
                experiment_id="exp_c",
                display_name="Option C",
                policy_type="stipend",
                raw_metrics={
                    "mean_total_cost": 70000000.0,  # Exceeds 60M budget cap
                    "p95_total_cost": 85000000.0,
                    "mean_beneficiaries": 3500.0,
                    "budget_exceedance_risk": 0.35,  # Exceeds 25% risk limit
                    "relative_mc_error": 0.03,
                },
                metadata={"region": "TN", "currency": "INR", "base_population_size": 1000},
                uncertainty_summary={},
                risk_probabilities={},
                convergence_report={},
                sensitivity_report={},
            ),
        ]

    def test_config_validation(self):
        config = RecommendationConfig(
            version="1.0",
            recommendation_id="test_rec",
            title="Test Recommendation",
            description="Unit test config",
            created_at="2026-09-14T00:00:00Z",
            candidate_experiments=[
                CandidateExperimentConfig(experiment_id="exp_a", path="p1", display_name="A"),
                CandidateExperimentConfig(experiment_id="exp_b", path="p2", display_name="B"),
            ],
            feasibility_constraints=FeasibilityConstraintConfig(max_budget=60000000.0),
            normalization_method="min_max",
            metrics=self.metrics,
            stakeholder_profiles=[
                StakeholderProfileConfig(
                    name="Fiscal",
                    description="Fiscal conservative",
                    weights={
                        "mean_total_cost": 0.5,
                        "mean_beneficiaries": 0.2,
                        "p95_total_cost": 0.15,
                        "budget_exceedance_risk": 0.15,
                    },
                )
            ],
            ranking_method="weighted_sum",
        )
        errors = RecommendationConfigValidator.validate(config)
        self.assertEqual(len(errors), 0)

    def test_compatibility_validation(self):
        res = CompatibilityValidator.validate_compatibility(self.candidates)
        self.assertTrue(res["is_compatible"])
        self.assertEqual(res["candidate_count"], 3)

    def test_feasibility_filtering(self):
        constraints = FeasibilityConstraintConfig(
            max_budget=60000000.0,
            max_risk_probability=0.25,
            min_coverage=1500,
        )
        checks = FeasibilityFilter.evaluate_all(self.candidates, constraints)
        self.assertEqual(len(checks), 3)

        # Candidate A: 40M cost <= 60M, 10% risk <= 25%, 2000 coverage >= 1500 -> FEASIBLE
        self.assertTrue(checks[0].is_feasible)

        # Candidate B: 30M cost <= 60M, 5% risk <= 25%, 1200 coverage < 1500 -> INFEASIBLE (Coverage)
        self.assertFalse(checks[1].is_feasible)
        self.assertIn("Beneficiary count", checks[1].violations[0])

        # Candidate C: 70M cost > 60M, 35% risk > 25% -> INFEASIBLE (Budget & Risk)
        self.assertFalse(checks[2].is_feasible)
        self.assertEqual(len(checks[2].violations), 2)

    def test_metric_normalization(self):
        norm_res = MetricNormalizer.normalize_candidates(self.candidates, self.metrics, method="min_max")
        self.assertEqual(len(norm_res), 3)

        # For mean_total_cost (minimize): Candidate B (30M) should have score 1.0, C (70M) score 0.0
        norm_b = norm_res[1].normalized_metrics["mean_total_cost"]
        norm_c = norm_res[2].normalized_metrics["mean_total_cost"]
        self.assertAlmostEqual(norm_b, 1.0, places=4)
        self.assertAlmostEqual(norm_c, 0.0, places=4)

        # For mean_beneficiaries (maximize): Candidate C (3500) score 1.0, B (1200) score 0.0
        norm_c_ben = norm_res[2].normalized_metrics["mean_beneficiaries"]
        norm_b_ben = norm_res[1].normalized_metrics["mean_beneficiaries"]
        self.assertAlmostEqual(norm_c_ben, 1.0, places=4)
        self.assertAlmostEqual(norm_b_ben, 0.0, places=4)

    def test_ranking_engine_wsm_and_topsis(self):
        constraints = FeasibilityConstraintConfig(max_budget=60000000.0, min_coverage=1000)
        feas_checks = FeasibilityFilter.evaluate_all(self.candidates, constraints)
        norm_res = MetricNormalizer.normalize_candidates(self.candidates, self.metrics, method="min_max")

        rankings = RankingEngine.rank_candidates(
            candidates=self.candidates,
            feasibility_checks=feas_checks,
            normalized_results=norm_res,
            metrics=self.metrics,
        )

        self.assertEqual(len(rankings), 3)
        # Check that feasible options are ranked first
        self.assertTrue(rankings[0].is_feasible)
        self.assertEqual(rankings[0].rank, 1)
        self.assertGreaterEqual(rankings[0].wsm_score, rankings[1].wsm_score)

    def test_pareto_analysis(self):
        pareto_res = ParetoAnalyzer.analyze_pareto(self.candidates, self.metrics)
        self.assertEqual(len(pareto_res), 3)
        pareto_optimal = [p for p in pareto_res if p.is_pareto_optimal]
        self.assertGreaterEqual(len(pareto_optimal), 1)

    def test_tradeoff_and_pairwise(self):
        tradeoffs = TradeoffAnalyzer.analyze_tradeoffs(self.candidates, self.metrics)
        self.assertGreaterEqual(len(tradeoffs), 1)

        pairwise = PairwiseComparator.compare_pairs(self.candidates, self.metrics)
        self.assertEqual(len(pairwise), 3)

    def test_fairness_analyzer(self):
        fairness_res = DemographicFairnessAnalyzer.analyze_all(self.candidates)
        self.assertEqual(len(fairness_res), 3)
        for f in fairness_res:
            self.assertGreaterEqual(f.overall_fairness_score, 0.0)
            self.assertLessEqual(f.overall_fairness_score, 1.0)

    def test_explanation_generator(self):
        constraints = FeasibilityConstraintConfig(max_budget=60000000.0, min_coverage=1000)
        feas_checks = FeasibilityFilter.evaluate_all(self.candidates, constraints)
        norm_res = MetricNormalizer.normalize_candidates(self.candidates, self.metrics, method="min_max")
        rankings = RankingEngine.rank_candidates(
            candidates=self.candidates,
            feasibility_checks=feas_checks,
            normalized_results=norm_res,
            metrics=self.metrics,
        )
        pareto_res = ParetoAnalyzer.analyze_pareto(self.candidates, self.metrics)
        tradeoffs = TradeoffAnalyzer.analyze_tradeoffs(self.candidates, self.metrics)
        fairness_res = DemographicFairnessAnalyzer.analyze_all(self.candidates)

        explanations = ExplanationGenerator.generate_explanations(
            rankings=rankings,
            feasibility_checks=feas_checks,
            pareto_candidates=pareto_res,
            tradeoffs=tradeoffs,
            sensitivity_results=[],
            fairness_results=fairness_res,
        )

        self.assertGreaterEqual(len(explanations), 3)
        self.assertIn("RECOMMENDATION JUSTIFICATION", explanations[0])

if __name__ == "__main__":
    unittest.main()
