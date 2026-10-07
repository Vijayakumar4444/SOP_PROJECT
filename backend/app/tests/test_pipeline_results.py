import unittest
from unittest.mock import Mock, patch

from fastapi import HTTPException

from backend.app.main import (
    Policy,
    PolicyRule,
    SIMULATIONS,
    SimulationConfiguration,
    StoredSimulation,
    _completed_pipeline_result,
    _is_pipeline_artifact_result,
    simulation_results,
)
from backend.app.pipeline_results import build_pipeline_result


class PipelineResultsTests(unittest.TestCase):
    def _base_result(self):
        return {
            "simulation": {
                "id": "SIM-1",
                "policyName": "Test Policy",
                "department": "Social Welfare",
                "date": "2026-10-04T00:00:00+00:00",
                "monteCarloRuns": 1000,
                "confidenceLevel": 95,
                "populationSampleSize": 1000,
                "beneficiaryCoverage": 0.4,
                "estimatedCost": 100,
                "equityScore": 70,
                "budgetRisk": "Low",
                "status": "completed",
            },
            "timestamp": "2026-10-04T00:00:00+00:00",
            "beneficiary": {
                "coverage": 0.4,
                "beneficiaries": 10,
                "targetFit": 60,
                "basePopulation": 1000,
                "targetShare": 1.0,
                "targetUniverse": "Total synthetic population",
                "eligiblePopulation": 10,
                "nonEligiblePopulation": 990,
                "targetPopulation": 1000,
            },
            "budget": {
                "allocatedBudget": 1000,
                "meanCost": 100,
                "unusedBudget": 900,
                "costPerBeneficiary": 10,
                "probabilityOverrun": 0,
                "worstCaseCost": 120,
                "utilization": 0.1,
                "riskScore": 10,
                "riskLevel": "Low",
            },
            "monteCarlo": {
                "mean": 100,
                "median": 100,
                "p5": 90,
                "p95": 120,
                "budget": 1000,
                "overrunProbability": 0,
                "buckets": [],
            },
            "confidenceIntervals": [],
            "demographics": {
                "gender": [],
                "socialGroup": [],
                "ruralUrban": [],
                "ageGroup": [],
                "incomeGroup": [],
            },
            "districts": [
                {
                    "id": "chennai",
                    "district": "Chennai",
                    "population": 1000,
                    "eligiblePopulation": 100,
                    "beneficiaries": 10,
                    "coverage": 0.1,
                    "estimatedCost": 100,
                    "costPerBeneficiary": 10,
                    "equityScore": 70,
                    "budgetPressure": 0.1,
                    "ruralCoverage": 0.1,
                    "urbanCoverage": 0.1,
                    "coordinates": [80, 13],
                }
            ],
            "equity": {
                "overall": 70,
                "gender": 70,
                "socialGroup": 70,
                "ruralUrban": 70,
                "district": 70,
                "income": 70,
                "explanation": "Base result.",
            },
            "interpretation": {"classification": "Moderate", "summary": "Base.", "strengths": [], "concerns": []},
            "sensitivity": [],
        }

    def test_build_pipeline_result_overlays_real_backend_metrics(self):
        recommendation = {
            "recommendation_id": "rec-1",
            "top_recommended_candidate": "exp-1",
            "total_candidates": 1,
            "feasible_candidates_count": 1,
            "rankings": [
                {
                    "experiment_id": "exp-1",
                    "display_name": "Backend Option",
                    "is_feasible": True,
                    "raw_metrics": {"budget_exceedance_risk": 0.12, "relative_mc_error": 0.02},
                }
            ],
            "feasibility_checks": [
                {
                    "experiment_id": "exp-1",
                    "evaluated_constraints": {"max_budget": {"threshold": 5000}},
                }
            ],
            "explanations": ["RECOMMENDATION JUSTIFICATION: Backend option passed."],
        }
        uncertainty = {
            "metrics_summary": {
                "beneficiary_count": {"mean": 200, "mean_confidence_interval": {"lower": 180, "upper": 220}},
                "weighted_eligible_population": {"mean": 240},
                "coverage_rate": {"mean": 0.8},
                "total_policy_cost": {
                    "mean": 3000,
                    "median": 2950,
                    "mean_confidence_interval": {"lower": 2600, "upper": 3400},
                    "percentiles": {"p5": 2500, "p25": 2800, "p50": 2950, "p75": 3200, "p95": 3500},
                },
                "budget_utilization": {"mean": 0.6},
                "eligibility_rate": {"mean": 0.2},
                "average_benefit": {"mean": 15},
            }
        }
        fairness = {
            "fairness_results": [
                {
                    "experiment_id": "exp-1",
                    "overall_fairness_score": 0.86,
                    "gender_disparity": 1.1,
                    "district_disparity": 1.4,
                    "group_breakdowns": {"gender_share": {"female": 0.55, "male": 0.45}, "districts": {"Chennai": 200}},
                }
            ]
        }

        result = build_pipeline_result(self._base_result(), recommendation, uncertainty, fairness, top_experiment="exp-1")

        self.assertEqual(result["simulation"]["estimatedCost"], 3000)
        self.assertEqual(result["beneficiary"]["beneficiaries"], 200)
        self.assertEqual(result["beneficiary"]["eligiblePopulation"], 240)
        self.assertEqual(result["budget"]["allocatedBudget"], 5000)
        self.assertEqual(result["budget"]["riskLevel"], "Moderate")
        self.assertEqual(result["monteCarlo"]["p95"], 3500)
        self.assertEqual(result["equity"]["overall"], 86)
        self.assertEqual(result["interpretation"]["classification"], "Success")
        self.assertEqual(result["backendOutput"]["source"], "pipeline_artifacts")
        self.assertEqual(result["prediction"]["sample"]["population"], 1000)
        self.assertEqual(result["prediction"]["sample"]["beneficiaries"], 200)
        self.assertEqual(result["prediction"]["statewideEstimate"]["beneficiaries"], 200)
        self.assertEqual(result["prediction"]["submittedPolicyBenefit"]["annualAmount"], 10)
        self.assertEqual(result["prediction"]["pipelineArtifactBenefit"]["annualAmount"], 15)

    def test_reference_old_age_policy_includes_official_prediction_error(self):
        base = self._base_result()
        base["simulation"]["policyName"] = "Reference - Tamil Nadu Indira Gandhi National Old Age Pension Scheme"
        base["simulation"]["populationSampleSize"] = 12_000
        base["beneficiary"]["basePopulation"] = 12_048_463
        base["budget"]["costPerBeneficiary"] = 12_000
        recommendation = {
            "recommendation_id": "rec-1",
            "top_recommended_candidate": "exp-1",
            "rankings": [{"experiment_id": "exp-1", "display_name": "Old Age", "is_feasible": True, "raw_metrics": {}}],
            "feasibility_checks": [{"experiment_id": "exp-1", "evaluated_constraints": {"max_budget": {"threshold": 60_000_000}}}],
        }
        uncertainty = {
            "metrics_summary": {
                "beneficiary_count": {"mean": 1835},
                "weighted_eligible_population": {"mean": 1843},
                "eligibility_rate": {"mean": 0.1536},
                "coverage_rate": {"mean": 1},
                "total_policy_cost": {"mean": 33_169_432.91, "median": 33_169_432.91, "percentiles": {"p5": 33_169_432.91, "p95": 33_169_432.91}},
                "average_benefit": {"mean": 18_000},
                "budget_utilization": {"mean": 0.66},
            }
        }

        result = build_pipeline_result(base, recommendation, uncertainty, top_experiment="exp-1")

        self.assertEqual(result["prediction"]["officialBenchmark"]["beneficiaries"], 1_436_569)
        self.assertEqual(result["prediction"]["submittedPolicyBenefit"]["annualAmount"], 12_000)
        self.assertEqual(result["prediction"]["pipelineArtifactBenefit"]["annualAmount"], 18_000)
        self.assertGreater(result["prediction"]["statewideEstimate"]["beneficiaries"], 1_800_000)
        self.assertAlmostEqual(result["prediction"]["actualPredictionError"]["absolutePercentError"], 0.2826, places=2)

    def test_completed_pipeline_result_requires_phase8_completed(self):
        memory = Mock()
        memory.get_run_status.return_value = {"status": "completed"}
        memory.get_phase_logs.return_value = [{"phase_name": "phase7_monte_carlo", "status": "completed"}]

        with patch("backend.app.main.PolicyMemoryStore", return_value=memory):
            result = _completed_pipeline_result("SIM-1", self._base_result())

        self.assertIsNone(result)

    def test_results_endpoint_returns_not_ready_before_phase8(self):
        policy = Policy(
            name="Pipeline Only Policy",
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
        SIMULATIONS["SIM-NOT-READY"] = StoredSimulation(policy, configuration, 0.0, "hash")
        memory = Mock()
        memory.get_run_status.return_value = {"status": "running"}
        memory.get_phase_logs.return_value = [{"phase_name": "phase1_data_foundation", "status": "completed"}]

        try:
            with patch("backend.app.main.PolicyMemoryStore", return_value=memory):
                with self.assertRaises(HTTPException) as raised:
                    simulation_results("SIM-NOT-READY")
            self.assertEqual(raised.exception.status_code, 409)
            self.assertEqual(raised.exception.detail["status"], "not_ready")
        finally:
            SIMULATIONS.pop("SIM-NOT-READY", None)

    def test_only_pipeline_artifact_results_are_cacheable_for_results(self):
        self.assertFalse(_is_pipeline_artifact_result({"simulation": {"id": "SIM-1"}}))
        self.assertTrue(_is_pipeline_artifact_result({"backendOutput": {"source": "pipeline_artifacts"}}))


if __name__ == "__main__":
    unittest.main()
