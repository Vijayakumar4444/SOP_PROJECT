"""
Unit and integration tests for Phase 9 Real-World Policy Validation Engine.
"""

import os
import unittest
from backend.app.modules.real_world_validation.benchmark_loader import BenchmarkLoader
from backend.app.modules.real_world_validation.source_reconciler import SourceReconciler
from backend.app.modules.real_world_validation.rule_encoder import RuleEncoder
from backend.app.modules.real_world_validation.compatibility_checker import PolicyDataCompatibilityChecker
from backend.app.modules.real_world_validation.error_calculator import ErrorCalculator
from backend.app.modules.real_world_validation.uncertainty_calibrator import UncertaintyCalibrator
from backend.app.modules.real_world_validation.error_decomposer import ErrorDecomposer
from backend.app.modules.real_world_validation.validation_scorecard import ValidationScorecardEvaluator
from backend.app.modules.real_world_validation.service import Phase9RealWorldValidationService

class TestRealWorldValidation(unittest.TestCase):

    def setUp(self):
        self.policy_dir = "real_world_validation/kmut_policy"

    def test_benchmark_loader(self):
        obs_csv = os.path.join(self.policy_dir, "observed_results.csv")
        benchmarks = BenchmarkLoader.load_observed_results(obs_csv)
        self.assertGreaterEqual(len(benchmarks), 5)
        approved = [b for b in benchmarks if b.metric_name == "approved_beneficiaries" and b.geographic_level == "Statewide"]
        self.assertEqual(len(approved), 1)
        self.assertEqual(approved[0].metric_value, 11600000.0)

    def test_source_reconciler(self):
        json_path = os.path.join(self.policy_dir, "source_reconciliation.json")
        res = SourceReconciler.load_reconciliation(json_path)
        self.assertIn("approved_beneficiaries", res["reconciled_metrics"])
        self.assertEqual(res["reconciled_metrics"]["approved_beneficiaries"], 11600000)

    def test_rule_encoder(self):
        yaml_path = os.path.join(self.policy_dir, "official_policy_rules.yaml")
        rules = RuleEncoder.parse_official_rules(yaml_path)
        self.assertEqual(rules["policy_id"], "tn_kmut_2023")
        self.assertEqual(rules["benefit_amount_monthly"], 1000.0)

    def test_compatibility_checker(self):
        yaml_path = os.path.join(self.policy_dir, "official_policy_rules.yaml")
        rules = RuleEncoder.parse_official_rules(yaml_path)
        features = ["district", "urban_rural", "age", "gender", "relationship_to_head", "consumption_expenditure", "employment_status"]
        comp = PolicyDataCompatibilityChecker.check_compatibility(rules, features)
        self.assertTrue(comp["is_compatible"])
        self.assertGreaterEqual(comp["compatibility_score"], 0.80)

    def test_error_calculator(self):
        comp = ErrorCalculator.compare_single("approved_beneficiaries", "Tamil Nadu", 11600000.0, 11840400.0)
        self.assertEqual(comp.actual_value, 11600000.0)
        self.assertAlmostEqual(comp.percentage_error, 2.07, places=1)
        self.assertTrue(comp.inside_95_ci)

    def test_uncertainty_calibrator(self):
        comp1 = ErrorCalculator.compare_single("approved_beneficiaries", "Chennai", 620000.0, 630000.0)
        comp2 = ErrorCalculator.compare_single("approved_beneficiaries", "Coimbatore", 480000.0, 490000.0)
        res = UncertaintyCalibrator.evaluate_calibration([comp1, comp2])
        self.assertEqual(res.total_compared_metrics, 2)
        self.assertEqual(res.metrics_inside_interval, 2)
        self.assertEqual(res.empirical_coverage_rate, 1.0)

    def test_error_decomposer(self):
        res = ErrorDecomposer.decompose_error(15840000.0, 11840400.0, 11600000.0)
        self.assertGreater(res.takeup_gap_pct, 0.0)
        self.assertIn("Take-Up", res.primary_error_driver)

    def test_validation_scorecard(self):
        state_comp = [ErrorCalculator.compare_single("approved_beneficiaries", "Tamil Nadu", 11600000.0, 11840400.0)]
        dist_comp = [ErrorCalculator.compare_single("approved_beneficiaries", "Chennai", 620000.0, 630000.0)]
        errors = ErrorCalculator.calculate_summary_metrics(state_comp, dist_comp)
        scorecard = ValidationScorecardEvaluator.evaluate_scorecard("tn_kmut_2023", errors)
        self.assertTrue(scorecard.overall_pass)
        self.assertIn(scorecard.validation_status, ["VALIDATED", "VALIDATED_WITH_LIMITATIONS"])

    def test_full_real_world_validation_service(self):
        service = Phase9RealWorldValidationService(base_dir=".")
        res = service.run_validation(self.policy_dir)
        self.assertEqual(res["status"], "PASS")
        self.assertTrue(res["overall_pass"])
        self.assertLessEqual(res["statewide_beneficiary_mape"], 5.0)

if __name__ == "__main__":
    unittest.main()
