"""
Unit and integration tests for Phase 9 Real-World Policy Validation Engine across KMUT and OAP policies.
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
        self.kmut_dir = "real_world_validation/kmut_policy"
        self.oap_dir = "real_world_validation/oap_policy"

    def test_kmut_benchmark_loader(self):
        obs_csv = os.path.join(self.kmut_dir, "observed_results.csv")
        benchmarks = BenchmarkLoader.load_observed_results(obs_csv)
        self.assertGreaterEqual(len(benchmarks), 5)
        approved = [b for b in benchmarks if b.metric_name == "approved_beneficiaries" and b.geographic_level == "Statewide"]
        self.assertEqual(len(approved), 1)
        self.assertEqual(approved[0].metric_value, 11600000.0)

    def test_oap_benchmark_loader(self):
        obs_csv = os.path.join(self.oap_dir, "observed_results.csv")
        benchmarks = BenchmarkLoader.load_observed_results(obs_csv)
        self.assertGreaterEqual(len(benchmarks), 5)
        approved = [b for b in benchmarks if b.metric_name == "approved_beneficiaries" and b.geographic_level == "Statewide"]
        self.assertEqual(len(approved), 1)
        self.assertEqual(approved[0].metric_value, 3580000.0)

    def test_kmut_full_validation_service(self):
        service = Phase9RealWorldValidationService(base_dir=".")
        res = service.run_validation(self.kmut_dir)
        self.assertEqual(res["status"], "PASS")
        self.assertTrue(res["overall_pass"])
        self.assertLessEqual(res["statewide_beneficiary_mape"], 5.0)

    def test_oap_full_validation_service(self):
        service = Phase9RealWorldValidationService(base_dir=".")
        res = service.run_validation(self.oap_dir)
        self.assertEqual(res["status"], "PASS")
        self.assertTrue(res["overall_pass"])
        self.assertLessEqual(res["statewide_beneficiary_mape"], 5.0)

if __name__ == "__main__":
    unittest.main()
