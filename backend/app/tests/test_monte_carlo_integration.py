from __future__ import annotations

import unittest
from pathlib import Path
import sys
import json

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.modules.monte_carlo.service import Phase7MonteCarloService


class MonteCarloIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = Phase7MonteCarloService(project_root=ROOT)
        self.output_dir = ROOT / "backend/app/tests/monte_carlo_test_runtime"
        self.example_dir = ROOT / "config/monte_carlo/examples"

    def test_end_to_end_population_uncertainty_experiment(self) -> None:
        cfg_file = self.example_dir / "experiment_1_population_uncertainty.yaml"
        res = self.service.run_experiment(
            config_path=cfg_file,
            output_dir=self.output_dir / "exp1_run",
            iterations_override=5,
            resume=False,
        )

        self.assertTrue(res["success"], f"Experiment failed: {res.get('errors')}")
        self.assertEqual(res["completed_iterations"], 5)
        self.assertEqual(res["failed_iterations"], 0)

        # Check artifact paths exist
        paths = res["artifact_paths"]
        self.assertTrue(Path(paths["experiment_metadata"]).exists())
        self.assertTrue(Path(paths["iteration_results"]).exists())
        self.assertTrue(Path(paths["uncertainty_summary"]).exists())
        self.assertTrue(Path(paths["risk_probabilities"]).exists())
        self.assertTrue(Path(paths["convergence_report"]).exists())

    def test_reproducibility_across_identical_runs(self) -> None:
        cfg_file = self.example_dir / "experiment_2_policy_parameter_uncertainty.yaml"

        run1 = self.service.run_experiment(
            config_path=cfg_file,
            output_dir=self.output_dir / "exp2_run1",
            iterations_override=5,
            seed_override=2026,
            resume=False,
        )

        run2 = self.service.run_experiment(
            config_path=cfg_file,
            output_dir=self.output_dir / "exp2_run2",
            iterations_override=5,
            seed_override=2026,
            resume=False,
        )

        # Confirm identical cost results
        cost1 = run1["summary"]["metrics_summary"]["total_policy_cost"]["mean"]
        cost2 = run2["summary"]["metrics_summary"]["total_policy_cost"]["mean"]
        self.assertEqual(cost1, cost2)

    def test_checkpoint_resume_flow(self) -> None:
        cfg_file = self.example_dir / "experiment_3_combined_uncertainty.yaml"
        run_dir = self.output_dir / "exp3_resume_run"

        # Run 3 iterations first
        res1 = self.service.run_experiment(
            config_path=cfg_file,
            output_dir=run_dir,
            iterations_override=3,
            resume=False,
        )
        self.assertEqual(res1["completed_iterations"], 3)

        # Resume to 5 iterations
        res2 = self.service.run_experiment(
            config_path=cfg_file,
            output_dir=run_dir,
            iterations_override=5,
            resume=True,
        )
        self.assertEqual(res2["completed_iterations"], 5)


if __name__ == "__main__":
    unittest.main()
