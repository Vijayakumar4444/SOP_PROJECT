import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from backend.app.main import Policy, PolicyRule, SimulationConfiguration, StoredSimulation, _pipeline_progress


class PipelineProgressTests(unittest.TestCase):
    def _stored(self) -> StoredSimulation:
        policy = Policy(
            name="Progress Test Policy",
            department="Social Welfare",
            description="Monthly assistance of Rs 1000 for women.",
            geographicScope="Tamil Nadu",
            selectedDistricts=[],
            rules=[PolicyRule(id="r1", attribute="Gender", operator="=", value="Female", joiner="AND")],
        )
        configuration = SimulationConfiguration(
            monteCarloRuns=1000,
            confidenceLevel=95,
            populationSampleSize=12000,
            budgetConstraint=True,
            sensitivityAnalysis=True,
        )
        return StoredSimulation(policy, configuration, 0.0, "hash")

    def test_pipeline_progress_uses_phase_logs(self):
        memory = Mock()
        memory.get_run_status.return_value = {
            "status": "running",
            "created_at": datetime.now(timezone.utc),
        }
        memory.get_phase_logs.return_value = [
            {"phase_name": "phase1_data_foundation", "status": "completed"},
            {"phase_name": "phase2_compatibility", "status": "running"},
        ]

        with patch("backend.app.main.PolicyMemoryStore", return_value=memory):
            result = _pipeline_progress("SIM-1", self._stored())

        self.assertIsNotNone(result)
        self.assertEqual(result["completedIterations"], 1)
        self.assertEqual(result["totalIterations"], 8)
        self.assertEqual(result["currentStage"], "POLICY-DATA COMPATIBILITY ENGINE")
        self.assertEqual(result["stages"][0]["status"], "complete")
        self.assertEqual(result["stages"][1]["status"], "active")

    def test_pipeline_progress_returns_none_without_logs(self):
        memory = Mock()
        memory.get_run_status.return_value = {"status": "queued", "created_at": datetime.now(timezone.utc)}
        memory.get_phase_logs.return_value = []

        with patch("backend.app.main.PolicyMemoryStore", return_value=memory):
            result = _pipeline_progress("SIM-1", self._stored())

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
