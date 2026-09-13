from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal


class PopulationMode(str, Enum):
    REGENERATION = "regeneration"
    RESAMPLING = "resampling"
    FIXED = "fixed"


class SamplingStrategy(str, Enum):
    HOUSEHOLD_BOOTSTRAP = "household_bootstrap"
    BOOTSTRAP = "bootstrap"
    STRATIFIED = "stratified"


class DistributionType(str, Enum):
    FIXED = "fixed"
    UNIFORM = "uniform"
    DISCRETE_UNIFORM = "discrete_uniform"
    NORMAL = "normal"
    TRUNCATED_NORMAL = "truncated_normal"
    LOGNORMAL = "lognormal"
    TRIANGULAR = "triangular"
    BETA = "beta"
    BERNOULLI = "bernoulli"
    CATEGORICAL = "categorical"


class TakeUpMode(str, Enum):
    CONSTANT = "constant_probability"
    GROUP_SPECIFIC = "group_specific"


@dataclass
class ExperimentConfig:
    experiment_id: str
    name: str
    description: str = ""
    base_seed: int = 20260913
    number_of_iterations: int = 100
    execution_mode: str = "local"
    parallel_workers: int = 1
    fail_fast: bool = False
    resume_enabled: bool = True
    checkpoint_interval: int = 20


@dataclass
class PopulationConfig:
    mode: PopulationMode = PopulationMode.RESAMPLING
    sampling_strategy: SamplingStrategy = SamplingStrategy.HOUSEHOLD_BOOTSTRAP
    generator_reference: str = "bootstrap"
    base_population_path: str | None = None
    population_size: int = 12000
    preserve_households: bool = True


@dataclass
class CalibrationConfig:
    enabled: bool = True
    target_reference: str = "official_tamil_nadu_targets"
    method: str = "raking"
    weight_column: str = "calibration_weight"
    failure_behavior: str = "reject_iteration"


@dataclass
class PolicyConfig:
    policy_path: str
    parameter_overrides: dict[str, Any] = field(default_factory=dict)


@dataclass
class ParameterUncertaintyConfig:
    distribution: DistributionType = DistributionType.UNIFORM
    minimum: float | None = None
    maximum: float | None = None
    mode: float | None = None
    mean: float | None = None
    std_dev: float | None = None
    step: float | None = None
    alpha: float | None = None
    beta: float | None = None
    probability: float | None = None
    categories: list[Any] = field(default_factory=list)
    weights: list[float] = field(default_factory=list)


@dataclass
class UncertaintyConfig:
    population_uncertainty_enabled: bool = True
    policy_parameter_uncertainty_enabled: bool = False
    parameters: dict[str, ParameterUncertaintyConfig] = field(default_factory=dict)
    calibration_uncertainty_enabled: bool = False


@dataclass
class GroupTakeUp:
    field: str
    value: Any
    probability: float


@dataclass
class TakeUpConfig:
    enabled: bool = False
    mode: TakeUpMode = TakeUpMode.CONSTANT
    probability: float = 1.0
    default_probability: float = 1.0
    groups: list[GroupTakeUp] = field(default_factory=list)


@dataclass
class RiskMetricConfig:
    metric: str
    operator: str # greater_than, less_than, etc.
    threshold: float
    output_name: str


@dataclass
class ConvergenceConfig:
    enabled: bool = True
    minimum_iterations: int = 20
    check_interval: int = 10
    metrics: list[str] = field(default_factory=lambda: ["total_policy_cost", "weighted_beneficiary_population", "coverage_rate"])
    relative_mc_error_threshold: float = 0.02
    stable_checks_required: int = 2
    early_stopping: bool = False


@dataclass
class OutputConfig:
    confidence_level: float = 0.95
    percentiles: list[float] = field(default_factory=lambda: [0.025, 0.05, 0.25, 0.50, 0.75, 0.95, 0.975])
    store_record_level_results: bool = False
    store_iteration_populations: bool = False
    store_failed_iterations: bool = True


@dataclass
class FailureHandlingConfig:
    fail_fast: bool = False
    maximum_failed_iterations: int = 20
    maximum_failure_rate: float = 0.20
    include_failed_iterations_in_statistics: bool = False


@dataclass
class SimulationConfig:
    experiment: ExperimentConfig
    population: PopulationConfig = field(default_factory=PopulationConfig)
    calibration: CalibrationConfig = field(default_factory=CalibrationConfig)
    policy: PolicyConfig = field(default_factory=lambda: PolicyConfig(policy_path=""))
    uncertainty: UncertaintyConfig = field(default_factory=UncertaintyConfig)
    take_up: TakeUpConfig = field(default_factory=TakeUpConfig)
    convergence: ConvergenceConfig = field(default_factory=ConvergenceConfig)
    risk_metrics: list[RiskMetricConfig] = field(default_factory=list)
    outputs: OutputConfig = field(default_factory=OutputConfig)
    failure_handling: FailureHandlingConfig = field(default_factory=FailureHandlingConfig)
