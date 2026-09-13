"""
Integration tests for Phase 8 Recommendation Engine and end-to-end Simulation Engine phase verification.
"""

import os
import unittest
import json
from backend.app.modules.data_foundation.io_utils import read_json
from backend.app.modules.recommendation.service import Phase8RecommendationService
from backend.app.modules.recommendation.verification import SimulationEngineVerifier

class TestRecommendationIntegration(unittest.TestCase):

    def test_end_to_end_recommendation_run(self):
        config_path = os.path.join("config", "recommendation", "examples", "tn_policy_recommendation.yaml")
        self.assertTrue(os.path.exists(config_path), f"Configuration file missing at '{config_path}'")

        service = Phase8RecommendationService(base_dir=".")
        result = service.run_recommendation(config_path)

        self.assertEqual(result["status"], "PASS")
        self.assertIsNotNone(result["top_recommended_candidate"])
        self.assertEqual(result["total_candidates"], 3)
        self.assertGreaterEqual(result["feasible_candidates"], 1)

        # Verify exported artifacts exist
        artifacts = result["exported_artifacts"]
        for artifact_key, artifact_path in artifacts.items():
            self.assertTrue(os.path.exists(artifact_path), f"Exported artifact '{artifact_key}' missing at '{artifact_path}'")

        # Inspect summary JSON content
        summary_data = read_json(artifacts["summary_json"])
        self.assertEqual(summary_data["recommendation_id"], "tn_rec_001_policy_comparison")
        self.assertEqual(len(summary_data["rankings"]), 3)
        self.assertEqual(summary_data["rankings"][0]["rank"], 1)

        # Inspect handoff manifest
        handoff_data = read_json(artifacts["handoff_manifest"])
        self.assertEqual(handoff_data["phase"], 8)
        self.assertEqual(handoff_data["status"], "PASS")

    def test_full_simulation_engine_phase_verification(self):
        res = SimulationEngineVerifier.verify_all_phases(base_dir=".")
        self.assertEqual(res["overall_status"], "PASS")
        self.assertEqual(res["phases_verified"], 8)
        for phase_name, detail in res["phase_details"].items():
            self.assertEqual(detail["status"], "PASS", f"Phase '{phase_name}' failed verification check.")

if __name__ == "__main__":
    unittest.main()
