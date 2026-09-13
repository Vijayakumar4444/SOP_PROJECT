"""
Dataclasses and data structures for Real-World Policy Validation Engine.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional

@dataclass
class BenchmarkMetric:
    policy_id: str
    reporting_period: str
    geographic_level: str
    geographic_code: str
    geographic_name: str
    metric_name: str
    metric_value: float
    metric_unit: str
    source_id: str

@dataclass
class ExperimentComparisonResult:
    metric_name: str
    geographic_name: str
    actual_value: float
    simulated_value: float
    signed_error: float
    absolute_error: float
    percentage_error: float
    ci_lower_95: float
    ci_upper_95: float
    inside_95_ci: bool

@dataclass
class StatisticalErrorMetrics:
    statewide_beneficiary_mape: float
    statewide_expenditure_mape: float
    district_mape: float
    district_rmse: float
    district_pearson_r: float
    district_spearman_rho: float
    prediction_interval_coverage_rate: float
    accuracy_within_10_percent: float

@dataclass
class UncertaintyCalibrationResult:
    total_compared_metrics: int
    metrics_inside_interval: int
    empirical_coverage_rate: float
    average_interval_width: float
    calibration_status: str

@dataclass
class ErrorDecompositionResult:
    input_data_sampling_error_pct: float
    synthetic_calibration_error_pct: float
    eligibility_proxy_error_pct: float
    takeup_gap_pct: float
    administrative_filter_pct: float
    primary_error_driver: str

@dataclass
class ValidationScorecardResult:
    policy_id: str
    validation_status: str  # VALIDATED, VALIDATED_WITH_LIMITATIONS, PARTIALLY_VALIDATED, NOT_VALIDATED
    criteria_checks: Dict[str, Dict[str, Any]]
    overall_pass: bool
    summary_notes: List[str]
