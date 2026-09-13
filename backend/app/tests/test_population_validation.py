from __future__ import annotations

import unittest
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.modules.population_validation.service import PopulationValidationService


class PopulationValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = PopulationValidationService(ROOT)

    def test_numeric_distribution_scores_order_similar_above_different(self) -> None:
        reference = [{"age": value, "employment_status": "Employed", "household_size": 3, "gender": "Female", "urban_rural": "Urban", "education_level": "Graduate", "individual_income": value * 100} for value in range(20, 70)]
        good = [{"age": value, "employment_status": "Employed", "household_size": 3, "gender": "Female", "urban_rural": "Urban", "education_level": "Graduate", "individual_income": value * 100} for value in range(21, 71)]
        bad = [{"age": value, "employment_status": "Employed", "household_size": 3, "gender": "Female", "urban_rural": "Urban", "education_level": "Graduate", "individual_income": value * 100} for value in range(70, 120)]
        metadata = {"variable_schema": {"age": "integer", "employment_status": "categorical", "household_size": "integer", "gender": "categorical", "urban_rural": "categorical", "education_level": "categorical", "individual_income": "continuous"}}
        good_report = self.service.validate(reference, good, metadata)
        bad_report = self.service.validate(reference, bad, metadata)
        good_age = next(item for item in good_report["variable_metrics"] if item["variable"] == "age")
        bad_age = next(item for item in bad_report["variable_metrics"] if item["variable"] == "age")
        self.assertGreater(good_age["fidelity_score"], bad_age["fidelity_score"])

    def test_categorical_distribution_scores_order_similar_above_different(self) -> None:
        reference = [{"gender": "A" if index < 50 else "B", "age": 30, "household_size": 3} for index in range(100)]
        good = [{"gender": "A" if index < 51 else "B", "age": 30, "household_size": 3} for index in range(100)]
        bad = [{"gender": "A" if index < 90 else "B", "age": 30, "household_size": 3} for index in range(100)]
        metadata = {"variable_schema": {"gender": "categorical", "age": "integer", "household_size": "integer"}}
        good_report = self.service.validate(reference, good, metadata)
        bad_report = self.service.validate(reference, bad, metadata)
        good_gender = next(item for item in good_report["variable_metrics"] if item["variable"] == "gender")
        bad_gender = next(item for item in bad_report["variable_metrics"] if item["variable"] == "gender")
        self.assertGreater(good_gender["fidelity_score"], bad_gender["fidelity_score"])

    def test_correlation_preservation_scores_order_correlated_above_independent(self) -> None:
        reference = [{"age": index, "individual_income": index * 10, "household_size": 3} for index in range(1, 101)]
        good = [{"age": index, "individual_income": index * 10 + 1, "household_size": 3} for index in range(1, 101)]
        bad = [{"age": index, "individual_income": (101 - index) * 10, "household_size": 3} for index in range(1, 101)]
        metadata = {"variable_schema": {"age": "integer", "individual_income": "continuous", "household_size": "integer"}}
        good_report = self.service.validate(reference, good, metadata)
        bad_report = self.service.validate(reference, bad, metadata)
        self.assertGreater(good_report["component_scores"]["correlation_preservation"], bad_report["component_scores"]["correlation_preservation"])

    def test_validity_detects_invalid_ranges_and_categories(self) -> None:
        reference = [{"age": 30, "household_size": 3, "gender": "Female", "urban_rural": "Urban", "literacy_status": "Literate", "employment_status": "Employed", "labour_force_status": "Employed", "social_group": "Others", "individual_income": 1000, "consumption_expenditure": 800}]
        synthetic = [{"age": -5, "household_size": 0, "gender": "UnknownValue", "urban_rural": "Urban", "literacy_status": "Literate", "employment_status": "Employed", "labour_force_status": "Employed", "social_group": "Others", "individual_income": 1000, "consumption_expenditure": 800}]
        metadata = {"variable_schema": {key: "categorical" for key in reference[0]}}
        metadata["variable_schema"].update({"age": "integer", "household_size": "integer", "individual_income": "continuous", "consumption_expenditure": "continuous"})
        report = self.service.validate(reference, synthetic, metadata)
        self.assertGreaterEqual(report["validity_metrics"]["hard_violation_count"], 3)
        self.assertEqual(report["validation_status"], "FAIL")

    def test_model_comparison_ranks_good_fixture_higher(self) -> None:
        good = {"population_id": "GOOD", "quality_score": 0.90, "validation_status": "PASS", "component_scores": {"distribution_fidelity": 0.9, "correlation_preservation": 0.9, "data_validity": 1.0, "statistical_similarity": 0.9}, "warnings": [], "variable_metrics": [], "official_marginal_metrics": []}
        poor = {"population_id": "POOR", "quality_score": 0.50, "validation_status": "FAIL", "component_scores": {"distribution_fidelity": 0.5, "correlation_preservation": 0.5, "data_validity": 1.0, "statistical_similarity": 0.5}, "warnings": ["bad"], "variable_metrics": [], "official_marginal_metrics": []}
        comparison = self.service.compare_reports([poor, good])
        self.assertEqual(comparison["comparison"][0]["population_id"], "GOOD")
        self.assertEqual(comparison["selection"]["selected_population_id"], "GOOD")

    def test_quality_gate_blocks_critical_variable_failure(self) -> None:
        reference = [{"employment_status": "Employed", "age": 30, "household_size": 3, "gender": "Female", "urban_rural": "Urban", "education_level": "Graduate", "individual_income": 1000} for _ in range(90)]
        reference.extend({"employment_status": "Unemployed", "age": 30, "household_size": 3, "gender": "Female", "urban_rural": "Urban", "education_level": "Graduate", "individual_income": 1000} for _ in range(10))
        synthetic = [{"employment_status": "Unemployed", "age": 30, "household_size": 3, "gender": "Female", "urban_rural": "Urban", "education_level": "Graduate", "individual_income": 1000} for _ in range(100)]
        metadata = {"critical_variables": ["employment_status"], "variable_schema": {"employment_status": "categorical", "age": "integer", "household_size": "integer", "gender": "categorical", "urban_rural": "categorical", "education_level": "categorical", "individual_income": "continuous"}}
        report = self.service.validate(reference, synthetic, metadata)
        self.assertEqual(report["validation_status"], "FAIL")
        self.assertTrue(any(item["name"] == "variable_fidelity:employment_status" and not item["passed"] for item in report["gate_results"]))


if __name__ == "__main__":
    unittest.main()
