"""
Validation scorecard evaluating predefined validation thresholds and assigning validation status.
"""

from typing import Dict, Any, List
from .validation_model import StatisticalErrorMetrics, ValidationScorecardResult

class ValidationScorecardEvaluator:
    """Evaluates configurable validation thresholds against statistical error metrics."""

    @staticmethod
    def evaluate_scorecard(
        policy_id: str,
        errors: StatisticalErrorMetrics,
        thresholds: Dict[str, float] = None,
    ) -> ValidationScorecardResult:
        if thresholds is None:
            thresholds = {
                "max_statewide_beneficiary_mape": 15.0,
                "max_statewide_expenditure_mape": 15.0,
                "max_district_mape": 25.0,
                "min_district_pearson_r": 0.70,
                "min_interval_coverage_rate": 0.80,
            }

        checks = {
            "statewide_beneficiary_mape": {
                "threshold": thresholds["max_statewide_beneficiary_mape"],
                "actual": errors.statewide_beneficiary_mape,
                "passed": errors.statewide_beneficiary_mape <= thresholds["max_statewide_beneficiary_mape"],
            },
            "statewide_expenditure_mape": {
                "threshold": thresholds["max_statewide_expenditure_mape"],
                "actual": errors.statewide_expenditure_mape,
                "passed": errors.statewide_expenditure_mape <= thresholds["max_statewide_expenditure_mape"],
            },
            "district_mape": {
                "threshold": thresholds["max_district_mape"],
                "actual": errors.district_mape,
                "passed": errors.district_mape <= thresholds["max_district_mape"],
            },
            "district_pearson_r": {
                "threshold": thresholds["min_district_pearson_r"],
                "actual": errors.district_pearson_r,
                "passed": errors.district_pearson_r >= thresholds["min_district_pearson_r"],
            },
            "prediction_interval_coverage": {
                "threshold": thresholds["min_interval_coverage_rate"],
                "actual": errors.prediction_interval_coverage_rate,
                "passed": errors.prediction_interval_coverage_rate >= thresholds["min_interval_coverage_rate"],
            },
        }

        passed_count = sum(1 for c in checks.values() if c["passed"])
        total_checks = len(checks)

        if passed_count == total_checks:
            status = "VALIDATED"
        elif passed_count >= 3:
            status = "VALIDATED_WITH_LIMITATIONS"
        elif passed_count >= 1:
            status = "PARTIALLY_VALIDATED"
        else:
            status = "NOT_VALIDATED"

        notes = [
            f"Passed {passed_count} of {total_checks} configurable validation criteria.",
            f"Statewide Beneficiary MAPE: {errors.statewide_beneficiary_mape}% (Threshold: <= {thresholds['max_statewide_beneficiary_mape']}%).",
            f"District Pearson Rank Correlation: {errors.district_pearson_r} (Threshold: >= {thresholds['min_district_pearson_r']}).",
        ]

        return ValidationScorecardResult(
            policy_id=policy_id,
            validation_status=status,
            criteria_checks=checks,
            overall_pass=(status in ["VALIDATED", "VALIDATED_WITH_LIMITATIONS", "PARTIALLY_VALIDATED"]),
            summary_notes=notes,
        )
