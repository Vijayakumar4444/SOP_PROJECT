from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import yaml

from backend.app.modules.monte_carlo.simulation_model import (
    CalibrationConfig,
    ConvergenceConfig,
    DistributionType,
    ExperimentConfig,
    FailureHandlingConfig,
    GroupTakeUp,
    OutputConfig,
    ParameterUncertaintyConfig,
    PolicyConfig,
    PopulationConfig,
    PopulationMode,
    RiskMetricConfig,
    SamplingStrategy,
    SimulationConfig,
    TakeUpConfig,
    TakeUpMode,
    UncertaintyConfig,
)


def load_simulation_config(path: Path | str) -> tuple[SimulationConfig, dict[str, Any]]:
    path_obj = Path(path).resolve()
    if not path_obj.exists():
        raise FileNotFoundError(f"Simulation configuration file not found: {path_obj}")

    text = path_obj.read_text(encoding="utf-8")
    if path_obj.suffix in [".yaml", ".yml"]:
        raw_dict = yaml.safe_load(text)
    elif path_obj.suffix == ".json":
        raw_dict = json.loads(text)
    else:
        try:
            raw_dict = yaml.safe_load(text)
        except Exception:
            raw_dict = json.loads(text)

    if not isinstance(raw_dict, dict):
        raise ValueError(f"Invalid simulation config format in {path_obj}")

    config_obj = parse_simulation_dict(raw_dict)
    return config_obj, raw_dict


def parse_simulation_dict(raw: dict[str, Any]) -> SimulationConfig:
    # 1. Experiment
    exp_raw = raw.get("experiment", {})
    experiment = ExperimentConfig(
        experiment_id=str(exp_raw.get("experiment_id", "")),
        name=str(exp_raw.get("name", "")),
        description=str(exp_raw.get("description", "")),
        base_seed=int(exp_raw.get("base_seed", 20260913)),
        number_of_iterations=int(exp_raw.get("number_of_iterations", 100)),
        execution_mode=str(exp_raw.get("execution_mode", "local")),
        parallel_workers=int(exp_raw.get("parallel_workers", 1)),
        fail_fast=bool(exp_raw.get("fail_fast", False)),
        resume_enabled=bool(exp_raw.get("resume_enabled", True)),
        checkpoint_interval=int(exp_raw.get("checkpoint_interval", 20)),
    )

    # 2. Population
    pop_raw = raw.get("population", {})
    mode_str = str(pop_raw.get("mode", "resampling")).lower()
    try:
        mode = PopulationMode(mode_str)
    except ValueError:
        mode = PopulationMode.RESAMPLING

    strat_str = str(pop_raw.get("sampling_strategy", "household_bootstrap")).lower()
    try:
        strat = SamplingStrategy(strat_str)
    except ValueError:
        strat = SamplingStrategy.HOUSEHOLD_BOOTSTRAP

    population = PopulationConfig(
        mode=mode,
        sampling_strategy=strat,
        generator_reference=str(pop_raw.get("generator_reference", "bootstrap")),
        base_population_path=pop_raw.get("base_population_path"),
        population_size=int(pop_raw.get("population_size", 12000)),
        preserve_households=bool(pop_raw.get("preserve_households", True)),
    )

    # 3. Calibration
    calib_raw = raw.get("calibration", {})
    calibration = CalibrationConfig(
        enabled=bool(calib_raw.get("enabled", True)),
        target_reference=str(calib_raw.get("target_reference", "official_tamil_nadu_targets")),
        method=str(calib_raw.get("method", "raking")),
        weight_column=str(calib_raw.get("weight_column", "calibration_weight")),
        failure_behavior=str(calib_raw.get("failure_behavior", "reject_iteration")),
    )

    # 4. Policy
    pol_raw = raw.get("policy", {})
    policy = PolicyConfig(
        policy_path=str(pol_raw.get("policy_path", "")),
        parameter_overrides=pol_raw.get("parameter_overrides", {}),
    )

    # 5. Uncertainty
    unc_raw = raw.get("uncertainty", {})
    pop_unc_enabled = bool(unc_raw.get("population_uncertainty", {}).get("enabled", True))
    pol_unc_raw = unc_raw.get("policy_parameter_uncertainty", {})
    pol_unc_enabled = bool(pol_unc_raw.get("enabled", False))

    params_dict: dict[str, ParameterUncertaintyConfig] = {}
    if pol_unc_enabled and "parameters" in pol_unc_raw:
        for p_name, p_cfg in pol_unc_raw["parameters"].items():
            if not isinstance(p_cfg, dict):
                continue
            dist_str = str(p_cfg.get("distribution", "uniform")).lower()
            try:
                dist_enum = DistributionType(dist_str)
            except ValueError:
                dist_enum = DistributionType.UNIFORM

            params_dict[p_name] = ParameterUncertaintyConfig(
                distribution=dist_enum,
                minimum=float(p_cfg["minimum"]) if p_cfg.get("minimum") is not None else None,
                maximum=float(p_cfg["maximum"]) if p_cfg.get("maximum") is not None else None,
                mode=float(p_cfg["mode"]) if p_cfg.get("mode") is not None else None,
                mean=float(p_cfg["mean"]) if p_cfg.get("mean") is not None else None,
                std_dev=float(p_cfg["std_dev"]) if p_cfg.get("std_dev") is not None else None,
                step=float(p_cfg["step"]) if p_cfg.get("step") is not None else None,
                alpha=float(p_cfg["alpha"]) if p_cfg.get("alpha") is not None else None,
                beta=float(p_cfg["beta"]) if p_cfg.get("beta") is not None else None,
                probability=float(p_cfg["probability"]) if p_cfg.get("probability") is not None else None,
                categories=p_cfg.get("categories", []),
                weights=[float(w) for w in p_cfg.get("weights", [])],
            )

    uncertainty = UncertaintyConfig(
        population_uncertainty_enabled=pop_unc_enabled,
        policy_parameter_uncertainty_enabled=pol_unc_enabled,
        parameters=params_dict,
        calibration_uncertainty_enabled=bool(unc_raw.get("calibration_uncertainty", {}).get("enabled", False)),
    )

    # 6. Take-up
    take_raw = raw.get("take_up", {})
    take_mode_str = str(take_raw.get("mode", "constant_probability")).lower()
    try:
        take_mode = TakeUpMode(take_mode_str)
    except ValueError:
        take_mode = TakeUpMode.CONSTANT

    groups_list = []
    for g in take_raw.get("groups", []):
        if isinstance(g, dict):
            groups_list.append(GroupTakeUp(field=str(g.get("field", "")), value=g.get("value"), probability=float(g.get("probability", 1.0))))

    take_up = TakeUpConfig(
        enabled=bool(take_raw.get("enabled", False)),
        mode=take_mode,
        probability=float(take_raw.get("probability", 1.0)),
        default_probability=float(take_raw.get("default_probability", 1.0)),
        groups=groups_list,
    )

    # 7. Convergence
    conv_raw = raw.get("convergence", {})
    convergence = ConvergenceConfig(
        enabled=bool(conv_raw.get("enabled", True)),
        minimum_iterations=int(conv_raw.get("minimum_iterations", 20)),
        check_interval=int(conv_raw.get("check_interval", 10)),
        metrics=[str(m) for m in conv_raw.get("metrics", ["total_policy_cost", "weighted_beneficiary_population", "coverage_rate"])],
        relative_mc_error_threshold=float(conv_raw.get("relative_mc_error_threshold", 0.02)),
        stable_checks_required=int(conv_raw.get("stable_checks_required", 2)),
        early_stopping=bool(conv_raw.get("early_stopping", False)),
    )

    # 8. Risk Metrics
    risk_metrics = []
    for rm in raw.get("risk_metrics", []):
        if isinstance(rm, dict):
            risk_metrics.append(RiskMetricConfig(
                metric=str(rm.get("metric", "")),
                operator=str(rm.get("operator", "greater_than")),
                threshold=float(rm.get("threshold", 0.0)),
                output_name=str(rm.get("output_name", f"prob_{rm.get('metric')}")),
            ))

    # 9. Outputs
    out_raw = raw.get("outputs", {})
    outputs = OutputConfig(
        confidence_level=float(out_raw.get("confidence_level", 0.95)),
        percentiles=[float(p) for p in out_raw.get("percentiles", [0.025, 0.05, 0.25, 0.50, 0.75, 0.95, 0.975])],
        store_record_level_results=bool(out_raw.get("store_record_level_results", False)),
        store_iteration_populations=bool(out_raw.get("store_iteration_populations", False)),
        store_failed_iterations=bool(out_raw.get("store_failed_iterations", True)),
    )

    # 10. Failure Handling
    fail_raw = raw.get("failure_handling", {})
    failure_handling = FailureHandlingConfig(
        fail_fast=bool(fail_raw.get("fail_fast", False)),
        maximum_failed_iterations=int(fail_raw.get("maximum_failed_iterations", 20)),
        maximum_failure_rate=float(fail_raw.get("maximum_failure_rate", 0.20)),
        include_failed_iterations_in_statistics=bool(fail_raw.get("include_failed_iterations_in_statistics", False)),
    )

    return SimulationConfig(
        experiment=experiment,
        population=population,
        calibration=calibration,
        policy=policy,
        uncertainty=uncertainty,
        take_up=take_up,
        convergence=convergence,
        risk_metrics=risk_metrics,
        outputs=outputs,
        failure_handling=failure_handling,
    )
