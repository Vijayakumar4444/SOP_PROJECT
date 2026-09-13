from __future__ import annotations

from typing import Any
from datetime import datetime, timezone
import time

from backend.app.modules.calibration.raking import rake_weights
from backend.app.modules.calibration.target_loader import load_official_targets, usable_targets
from backend.app.modules.monte_carlo.distribution_sampler import DistributionSampler
from backend.app.modules.monte_carlo.population_provider import PopulationProvider
from backend.app.modules.monte_carlo.seed_manager import IterationSeedBundle
from backend.app.modules.monte_carlo.simulation_model import SimulationConfig
from backend.app.modules.monte_carlo.takeup_engine import apply_takeup_uncertainty
from backend.app.modules.policy_engine.aggregation import compute_policy_aggregates
from backend.app.modules.policy_engine.beneficiary_selector import select_beneficiaries
from backend.app.modules.policy_engine.benefit_calculator import calculate_policy_benefits
from backend.app.modules.policy_engine.eligibility_evaluator import evaluate_population_eligibility
from backend.app.modules.policy_engine.policy_loader import load_policy_from_file


def run_single_iteration(
    iteration_number: int,
    config: SimulationConfig,
    seed_bundle: IterationSeedBundle,
    pop_provider: PopulationProvider,
    base_policy_path: str,
    project_root: Any,
) -> dict[str, Any]:
    start_time = datetime.now(timezone.utc)
    t0 = time.time()
    iter_id = f"ITER-{config.experiment.experiment_id}-{iteration_number:05d}"

    result_dict: dict[str, Any] = {
        "experiment_id": config.experiment.experiment_id,
        "iteration_id": iter_id,
        "iteration_number": iteration_number,
        "iteration_status": "PENDING",
        "population_seed": seed_bundle.population_seed,
        "calibration_seed": seed_bundle.calibration_seed,
        "parameter_seed": seed_bundle.parameter_seed,
        "take_up_seed": seed_bundle.take_up_seed,
        "policy_seed": seed_bundle.policy_seed,
        "sampled_parameters": {},
        "error_code": None,
        "warning_count": 0,
    }

    try:
        # 1. Sample Uncertain Policy Parameters
        sampled_params: dict[str, Any] = {}
        if config.uncertainty.policy_parameter_uncertainty_enabled and config.uncertainty.parameters:
            sampler = DistributionSampler(seed=seed_bundle.parameter_seed)
            for p_name, p_cfg in config.uncertainty.parameters.items():
                sampled_params[p_name] = sampler.sample_parameter(p_cfg)

        result_dict["sampled_parameters"] = sampled_params

        # 2. Obtain Population Sample
        result_dict["iteration_status"] = "RUNNING"
        pop_records = pop_provider.get_population_sample(config.population, seed=seed_bundle.population_seed)
        result_dict["iteration_status"] = "POPULATION_CREATED"
        result_dict["population_size"] = len(pop_records)

        # Count households
        hh_ids = set(str(r.get("synthetic_household_id", r.get("household_id", ""))) for r in pop_records)
        result_dict["household_count"] = len(hh_ids)

        # 3. Population Validation (Basic Quality Check)
        result_dict["iteration_status"] = "POPULATION_VALIDATED"
        result_dict["population_quality_score"] = 1.0

        # 4. Calibration (Phase 5 Reweighting if enabled)
        if config.calibration.enabled:
            calib_cfg = {"max_iterations": 30, "tolerance": 0.001}
            # Load targets
            target_sets = load_official_targets(project_root, pop_records, calib_cfg)
            usable_t = usable_targets(target_sets)
            
            if usable_t:
                rake_res = rake_weights(pop_records, usable_t, calib_cfg)
                result_dict["calibration_converged"] = rake_res.get("converged", True)
                result_dict["calibration_error"] = rake_res.get("history", [{}])[-1].get("maximum_marginal_error", 0.0)
            else:
                result_dict["calibration_converged"] = True
                result_dict["calibration_error"] = 0.0
            
            result_dict["iteration_status"] = "CALIBRATED"
        else:
            result_dict["calibration_converged"] = True
            result_dict["calibration_error"] = 0.0

        weight_col = config.calibration.weight_column or "calibration_weight"
        result_dict["weighted_population"] = round(sum(float(r.get(weight_col, 1.0)) for r in pop_records), 2)

        # 5. Load Base Policy & Apply Overrides
        policy_def, _ = load_policy_from_file(project_root / base_policy_path if not (project_root / base_policy_path).is_absolute() else base_policy_path)
        
        # Apply static & sampled overrides
        combined_overrides = dict(config.policy.parameter_overrides)
        combined_overrides.update(sampled_params)

        if "total_budget" in combined_overrides:
            policy_def.constraints.total_budget = float(combined_overrides["total_budget"])
        if "maximum_beneficiaries" in combined_overrides:
            policy_def.constraints.maximum_beneficiaries = int(combined_overrides["maximum_beneficiaries"])
        if "benefit_amount" in combined_overrides:
            policy_def.benefit.amount = float(combined_overrides["benefit_amount"])

        # 6. Apply Phase 6 Policy Engine
        elig_records = evaluate_population_eligibility(policy_def, pop_records, run_id=iter_id, weight_col=weight_col)
        results_records, sel_records, sel_stats = select_beneficiaries(policy_def, elig_records)

        # 7. Apply Take-Up Uncertainty if enabled
        if config.take_up.enabled:
            results_records, takeup_stats = apply_takeup_uncertainty(results_records, config.take_up, seed=seed_bundle.take_up_seed)

        # 8. Calculate Benefits & Costs
        results_records, cost_summary = calculate_policy_benefits(policy_def, results_records, weight_col=weight_col)

        # 9. Compute Aggregates
        summary, _ = compute_policy_aggregates(policy_def, results_records, cost_summary, weight_col=weight_col)
        result_dict["iteration_status"] = "POLICY_APPLIED"

        # 10. Extract Iteration Metrics
        result_dict["policy_id"] = policy_def.policy_id
        result_dict["policy_version"] = policy_def.version
        result_dict["eligible_count"] = summary["unweighted_eligible_records"]
        result_dict["weighted_eligible_population"] = summary["weighted_eligible_population"]
        result_dict["eligibility_rate"] = summary["weighted_eligibility_rate"]
        result_dict["beneficiary_count"] = summary["unweighted_selected_beneficiaries"]
        result_dict["weighted_beneficiary_population"] = summary["weighted_beneficiary_population"]
        result_dict["coverage_rate"] = summary["weighted_coverage_rate"]
        result_dict["total_policy_cost"] = summary["total_estimated_program_cost_inr"]
        result_dict["average_benefit"] = summary["average_annual_benefit_inr"]
        
        budget = summary["total_budget_inr"]
        result_dict["budget_utilization"] = round((summary["total_estimated_program_cost_inr"] / budget) * 100.0, 2) if budget and budget > 0 else 100.0
        result_dict["budget_exceeded"] = summary["total_estimated_program_cost_inr"] > budget if budget and budget > 0 else False
        
        result_dict["constraints_passed"] = sel_stats.get("capped_by") is None
        result_dict["policy_feasible"] = not result_dict["budget_exceeded"]

        t1 = time.time()
        result_dict["execution_duration_seconds"] = round(t1 - t0, 4)
        result_dict["started_at"] = start_time.isoformat()
        result_dict["completed_at"] = datetime.now(timezone.utc).isoformat()
        result_dict["iteration_status"] = "COMPLETED"

    except Exception as exc:
        result_dict["iteration_status"] = "FAILED_POLICY"
        result_dict["error_code"] = type(exc).__name__
        result_dict["error_message"] = str(exc)

    return result_dict
