"""
Uncertainty calibrator evaluating empirical interval coverage of government benchmarks within Monte Carlo prediction bounds.
"""

from typing import List, Dict, Any
from .validation_model import ExperimentComparisonResult, UncertaintyCalibrationResult

class UncertaintyCalibrator:
    """Evaluates whether actual government reported figures fall within simulated 95% Monte Carlo confidence intervals."""

    @staticmethod
    def evaluate_calibration(comparisons: List[ExperimentComparisonResult]) -> UncertaintyCalibrationResult:
        if not comparisons:
            return UncertaintyCalibrationResult(
                total_compared_metrics=0,
                metrics_inside_interval=0,
                empirical_coverage_rate=1.0,
                average_interval_width=0.0,
                calibration_status="NO_METRICS",
            )

        total = len(comparisons)
        inside = sum(1 for c in comparisons if c.inside_95_ci)
        coverage_rate = inside / total if total > 0 else 0.0

        widths = [(c.ci_upper_95 - c.ci_lower_95) for c in comparisons]
        avg_width = sum(widths) / total if total > 0 else 0.0

        status = "WELL_CALIBRATED" if coverage_rate >= 0.80 else "UNDER_CONVERGED"

        return UncertaintyCalibrationResult(
            total_compared_metrics=total,
            metrics_inside_interval=inside,
            empirical_coverage_rate=round(coverage_rate, 4),
            average_interval_width=round(avg_width, 2),
            calibration_status=status,
        )
