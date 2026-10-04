import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from backend.app.policy_priors import (
    apply_policy_memory_priors_to_config,
    derive_monte_carlo_calibration,
    write_policy_memory_priors,
)


class PolicyPriorsTests(unittest.TestCase):
    def test_derives_ranges_from_prior_metrics(self):
        calibration = derive_monte_carlo_calibration(
            {
                "sampleSize": 2,
                "coverage": {"mean": 0.8, "min": 0.75, "max": 0.85},
                "benefitAmount": {"mean": 12000, "min": 10000, "max": 14000},
            }
        )

        self.assertEqual(calibration["source"], "similar_policy_priors")
        self.assertEqual(calibration["sampleSize"], 2)
        self.assertLess(calibration["coverage"]["lower"], 0.75)
        self.assertGreater(calibration["benefitAmount"]["upper"], 14000)

    def test_applies_priors_to_monte_carlo_config_without_replacing_simulation(self):
        raw_config = {
            "calibration": {"enabled": True},
            "uncertainty": {
                "policy_parameter_uncertainty": {
                    "enabled": True,
                    "parameters": {
                        "benefit_amount": {
                            "distribution": "uniform",
                            "minimum": 500,
                            "maximum": 2000,
                        }
                    },
                }
            },
            "risk_metrics": [],
        }
        priors = {
            "available": True,
            "monteCarloCalibration": {
                "sampleSize": 3,
                "coverage": {"mean": 0.7, "lower": 0.62, "upper": 0.78},
                "benefitAmount": {"mean": 1200, "lower": 1000, "upper": 1400},
                "fiscalPressure": {"mean": 0.5, "lower": 0.4, "upper": 0.6},
            },
        }

        tuned = apply_policy_memory_priors_to_config(raw_config, priors)

        benefit = tuned["uncertainty"]["policy_parameter_uncertainty"]["parameters"]["benefit_amount"]
        self.assertEqual(benefit["minimum"], 1000)
        self.assertEqual(benefit["maximum"], 1400)
        self.assertEqual(tuned["risk_metrics"][0]["output_name"], "probability_coverage_below_memory_prior")
        self.assertEqual(tuned["calibration"]["memory_prior_context"]["sampleSize"], 3)
        self.assertIn("policy_memory_priors", tuned)

    def test_write_policy_memory_priors_uses_similar_policy_context(self):
        memory = Mock()
        memory.get_run_inputs.return_value = {
            "policy_hash": "hash-1",
            "policy_payload": {"name": "Women Support", "department": "Social Welfare", "description": "Monthly assistance of Rs 1000."},
        }
        memory.find_similar_completed.return_value = [
            {
                "runId": "SIM-OLD",
                "similarityScore": 0.8,
                "metrics": {"coverage": 0.75, "benefitAmount": 12000, "riskScore": 40},
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "policy_memory_priors.json"
            payload = write_policy_memory_priors("SIM-NEW", memory, output)

        self.assertTrue(payload["available"])
        self.assertEqual(payload["similarPolicyCount"], 1)
        self.assertEqual(payload["monteCarloCalibration"]["coverage"]["mean"], 0.75)

    def test_orchestrator_prepares_priors_before_running_phase(self):
        from backend.app.pipeline_orchestrator import FullPipelineOrchestrator, PipelinePhase

        memory = Mock()
        completed_process = Mock(returncode=0, stdout="out", stderr="")

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "data" / "synthetic").mkdir(parents=True)
            orchestrator = FullPipelineOrchestrator(
                root=root,
                memory_store=memory,
                phases=(PipelinePhase("phase_a", ("cmd", "a"), "a.json"),),
            )
            with patch("backend.app.pipeline_orchestrator.subprocess.run", return_value=completed_process):
                orchestrator.run("SIM-1")

            self.assertTrue((root / "data" / "synthetic" / "policy_memory_priors.json").exists())


if __name__ == "__main__":
    unittest.main()
