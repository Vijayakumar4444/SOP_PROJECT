"""
Dataclasses and data models for Phase 8 Recommendation Engine.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional

@dataclass
class CandidateExperimentConfig:
    experiment_id: str
    path: str
    display_name: str
    policy_type: str = "generic"

@dataclass
class FeasibilityConstraintConfig:
    max_budget: Optional[float] = None
    max_risk_probability: Optional[float] = None
    min_coverage: Optional[float] = None
    max_relative_mc_error: Optional[float] = None

@dataclass
class MetricConfig:
    name: str
    direction: str  # "minimize" or "maximize"
    weight: float = 0.25
    display_name: Optional[str] = None

@dataclass
class StakeholderProfileConfig:
    name: str
    description: str
    weights: Dict[str, float]

@dataclass
class RecommendationConfig:
    version: str
    recommendation_id: str
    title: str
    description: str
    created_at: str
    candidate_experiments: List[CandidateExperimentConfig]
    feasibility_constraints: FeasibilityConstraintConfig
    normalization_method: str  # "min_max" or "z_score"
    metrics: List[MetricConfig]
    stakeholder_profiles: List[StakeholderProfileConfig]
    ranking_method: str  # "weighted_sum" or "topsis"
    enable_pareto: bool = True
    enable_fairness_analysis: bool = True
    enable_tradeoff_analysis: bool = True
    enable_weight_sensitivity: bool = True
    output_dir: str = "artifacts/recommendation"
    summary_json: str = "recommendation_summary.json"
    ranking_csv: str = "ranking_results.csv"
    tradeoff_json: str = "tradeoff_report.json"
    fairness_json: str = "fairness_report.json"
    report_md: str = "recommendation_report.md"
    handoff_manifest: str = "data/synthetic/phase8_recommendation_handoff.json"

@dataclass
class CandidatePolicyResult:
    experiment_id: str
    display_name: str
    policy_type: str
    raw_metrics: Dict[str, float]
    metadata: Dict[str, Any]
    uncertainty_summary: Dict[str, Any]
    risk_probabilities: Dict[str, Any]
    convergence_report: Dict[str, Any]
    sensitivity_report: Dict[str, Any]
    iteration_records: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class FeasibilityCheckResult:
    experiment_id: str
    display_name: str
    is_feasible: bool
    violations: List[str]
    evaluated_constraints: Dict[str, Any]

@dataclass
class NormalizedMetricResult:
    experiment_id: str
    normalized_metrics: Dict[str, float]

@dataclass
class RankingScore:
    experiment_id: str
    display_name: str
    is_feasible: bool
    wsm_score: float
    topsis_score: float
    rank: int
    topsis_rank: int
    normalized_metrics: Dict[str, float]
    raw_metrics: Dict[str, float]

@dataclass
class ParetoCandidateResult:
    experiment_id: str
    display_name: str
    is_pareto_optimal: bool
    dominated_by: List[str]
    dominates: List[str]

@dataclass
class TradeoffComparison:
    candidate_a: str
    candidate_b: str
    metric_a: str
    metric_b: str
    value_a_diff: float
    value_b_diff: float
    marginal_tradeoff_ratio: float
    description: str

@dataclass
class PairwiseComparison:
    candidate_a: str
    candidate_b: str
    wins_a: int
    wins_b: int
    ties: int
    detailed_deltas: Dict[str, float]

@dataclass
class WeightSensitivityResult:
    profile_name: str
    weights: Dict[str, float]
    rankings: List[Dict[str, Any]]  # List of {experiment_id, rank, score}

@dataclass
class GroupFairnessMetric:
    group_name: str
    subgroup_values: Dict[str, float]
    disparity_ratio: float  # max / min ratio or Gini coefficient
    is_equitable: bool

@dataclass
class DemographicFairnessResult:
    experiment_id: str
    display_name: str
    district_disparity: float
    gender_disparity: float
    overall_fairness_score: float
    group_breakdowns: Dict[str, Dict[str, float]]

@dataclass
class RecommendationSummary:
    recommendation_id: str
    generated_at: str
    top_recommended_candidate: Optional[str]
    total_candidates: int
    feasible_candidates_count: int
    rankings: List[RankingScore]
    feasibility_checks: List[FeasibilityCheckResult]
    pareto_candidates: List[ParetoCandidateResult]
    tradeoffs: List[TradeoffComparison]
    weight_sensitivity: List[WeightSensitivityResult]
    fairness_results: List[DemographicFairnessResult]
    explanations: List[str]
