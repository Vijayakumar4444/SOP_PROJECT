from __future__ import annotations

import unittest
from pathlib import Path
import sys
import json

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.modules.policy_engine.service import Phase6PolicyService


class PolicyEngineIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = Phase6PolicyService(project_root=ROOT)
        self.output_dir = ROOT / "backend/app/tests/policy_engine_test_runtime"
        self.example_dir = ROOT / "config/policy_engine/examples"

    def test_end_to_end_elderly_pension_execution(self) -> None:
        policy_file = self.example_dir / "tn_elderly_pension.yaml"
        res = self.service.execute_policy(
            policy_path=policy_file,
            output_dir=self.output_dir / "elderly_pension_run",
        )

        self.assertTrue(res["success"], f"Execution failed: {res.get('errors')}")
        self.assertEqual(res["policy_id"], "tn_elderly_pension_001")
        
        summary = res["summary"]
        self.assertGreater(summary["total_evaluated_records"], 0)
        self.assertGreater(summary["unweighted_eligible_records"], 0)
        self.assertGreater(summary["weighted_eligible_population"], 0.0)
        self.assertGreater(summary["total_estimated_program_cost_inr"], 0.0)

        # Check artifact paths exist
        paths = res["artifact_paths"]
        self.assertTrue(Path(paths["run_metadata"]).exists())
        self.assertTrue(Path(paths["policy_summary"]).exists())
        self.assertTrue(Path(paths["eligibility_results"]).exists())
        self.assertTrue(Path(paths["beneficiaries"]).exists())
        self.assertTrue(Path(paths["demographic_breakdown"]).exists())

    def test_end_to_end_household_cooking_subsidy_execution(self) -> None:
        policy_file = self.example_dir / "tn_clean_cooking_subsidy.yaml"
        res = self.service.execute_policy(
            policy_path=policy_file,
            output_dir=self.output_dir / "cooking_subsidy_run",
        )

        self.assertTrue(res["success"], f"Execution failed: {res.get('errors')}")
        self.assertEqual(res["policy_id"], "tn_clean_cooking_subsidy_002")
        self.assertEqual(res["summary"]["target_unit"], "household")

    def test_end_to_end_budget_constrained_skilling_execution(self) -> None:
        policy_file = self.example_dir / "tn_youth_skilling_stipend.yaml"
        res = self.service.execute_policy(
            policy_path=policy_file,
            output_dir=self.output_dir / "skilling_stipend_run",
        )

        self.assertTrue(res["success"], f"Execution failed: {res.get('errors')}")
        self.assertEqual(res["policy_id"], "tn_youth_skilling_stipend_003")
        
        summary = res["summary"]
        self.assertLessEqual(summary["unweighted_selected_beneficiaries"], 1000)


if __name__ == "__main__":
    unittest.main()
