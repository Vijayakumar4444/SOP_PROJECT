from __future__ import annotations

from pathlib import Path
from typing import Any
from datetime import datetime, timezone
import json
import uuid

from backend.app.modules.data_foundation.io_utils import read_csv, write_csv, write_json, write_md
from backend.app.modules.monte_carlo.checkpoint_manager import CheckpointManager
from backend.app.modules.monte_carlo.config_loader import load_simulation_config
from backend.app.modules.monte_carlo.config_validator import validate_simulation_config
from backend.app.modules.monte_carlo.convergence_analyzer import check_simulation_convergence
from backend.app.modules.monte_carlo.iteration_runner import run_single_iteration
from backend.app.modules.monte_carlo.population_provider import PopulationProvider
from backend.app.modules.monte_carlo.risk_analyzer import compute_risk_probabilities
from backend.app.modules.monte_carlo.seed_manager import SeedManager
from backend.app.modules.monte_carlo.sensitivity_analyzer import analyze_parameter_sensitivity
from backend.app.modules.monte_carlo.simulation_model import SimulationConfig
from backend.app.modules.monte_carlo.uncertainty_analyzer import compute_uncertainty_summary


class Phase7MonteCarloService:
    """Primary orchestration service for Phase 7 Monte Carlo & Uncertainty Engine."""

    def __init__(self, project_root: Path | str | None = None) -> None:
        if project_root:
            self.root = Path(project_root).resolve()
        else:
            self.root = Path(__file__).resolve().parents[4]

    def run_experiment(
        self,
        config_path: Path | str,
        output_dir: Path | str | None = None,
        iterations_override: int | None = None,
        seed_override: int | None = None,
        resume: bool = True,
    ) -> dict[str, Any]:
        start_time = datetime.now(timezone.utc)
        
        # 1. Load Simulation Config
        full_cfg_path = self.root / config_path if not Path(config_path).is_absolute() else Path(config_path)
        config, raw_cfg_dict = load_simulation_config(full_cfg_path)

        if iterations_override is not None:
            config.experiment.number_of_iterations = iterations_override
        if seed_override is not None:
            config.experiment.base_seed = seed_override

        # 2. Validate Config
        val_result = validate_simulation_config(config)
        if not val_result["valid"]:
            return {
                "success": False,
                "experiment_id": config.experiment.experiment_id,
                "status": "CONFIG_VALIDATION_FAILED",
                "summary": {},
                "artifact_paths": {},
                "warnings": val_result.get("warnings", []),
                "errors": val_result.get("errors", []),
            }

        exp_id = config.experiment.experiment_id
        out_base = Path(output_dir).resolve() if output_dir else self.root / f"artifacts/experiments/{exp_id}"
        out_base.mkdir(parents=True, exist_ok=True)

        config_hash = CheckpointManager.compute_config_hash(raw_cfg_dict)
        cp_mgr = CheckpointManager(out_base)

        # 3. Check for existing checkpoint if resume is enabled
        completed_iterations_data: list[dict[str, Any]] = []
        start_iter = 1

        if resume and config.experiment.resume_enabled:
            cp_data = cp_mgr.load_latest_checkpoint(config_hash)
            if cp_data:
                completed_iterations_data = cp_data.get("completed_iterations_data", [])
                start_iter = cp_data.get("last_iteration_number", 0) + 1
                print(f"--> Resuming experiment '{exp_id}' from iteration {start_iter} ({len(completed_iterations_data)} completed).")

        # 4. Load Base Calibrated Population Records
        base_pop_records = self._load_base_calibrated_population()
        pop_provider = PopulationProvider(base_pop_records)

        # 5. Initialize Seed Manager
        seed_mgr = SeedManager(base_seed=config.experiment.base_seed)

        total_requested = config.experiment.number_of_iterations
        fail_limit = config.failure_handling.maximum_failed_iterations

        # 6. Monte Carlo Iteration Loop
        for i in range(start_iter, total_requested + 1):
            seed_bundle = seed_mgr.get_iteration_seed_bundle(i)

            iter_res = run_single_iteration(
                iteration_number=i,
                config=config,
                seed_bundle=seed_bundle,
                pop_provider=pop_provider,
                base_policy_path=config.policy.policy_path,
                project_root=self.root,
            )

            completed_iterations_data.append(iter_res)

            # Check failure threshold
            failed_count = sum(1 for r in completed_iterations_data if r.get("iteration_status") != "COMPLETED")
            if failed_count >= fail_limit and config.failure_handling.fail_fast:
                print(f"--> Stopping early: Failed iterations count ({failed_count}) reached limit ({fail_limit}).")
                break

            # Save periodic checkpoint
            if i % config.experiment.checkpoint_interval == 0 or i == total_requested:
                cp_mgr.save_checkpoint(
                    experiment_id=exp_id,
                    completed_iterations=completed_iterations_data,
                    current_iteration_number=i,
                    total_requested=total_requested,
                    config_hash=config_hash,
                )

        end_time = datetime.now(timezone.utc)
        duration_sec = round((end_time - start_time).total_seconds(), 4)

        # 7. Post-Simulation Statistical Analysis
        uncertainty_summary = compute_uncertainty_summary(
            iteration_results=completed_iterations_data,
            percentiles_requested=config.outputs.percentiles,
            confidence_level=config.outputs.confidence_level,
        )

        risk_summary = compute_risk_probabilities(
            iteration_results=completed_iterations_data,
            risk_configs=config.risk_metrics,
        )

        convergence_summary = check_simulation_convergence(
            iteration_results=completed_iterations_data,
            config=config.convergence,
        )

        sensitivity_summary = analyze_parameter_sensitivity(
            iteration_results=completed_iterations_data,
        )

        # 8. Write Experiment Output Artifacts
        artifact_paths = self._write_experiment_artifacts(
            out_base=out_base,
            exp_id=exp_id,
            config=config,
            raw_cfg_dict=raw_cfg_dict,
            completed_iterations=completed_iterations_data,
            uncertainty_summary=uncertainty_summary,
            risk_summary=risk_summary,
            convergence_summary=convergence_summary,
            sensitivity_summary=sensitivity_summary,
            start_time=start_time,
            end_time=end_time,
            duration_sec=duration_sec,
        )

        # 9. Write Phase 8 Handoff
        phase8_handoff_path = self.root / "data/synthetic/phase8_recommendation_handoff.json"
        write_json(phase8_handoff_path, {
            "phase": 7,
            "status": "PASS",
            "experiment_id": exp_id,
            "experiment_artifact_dir": str(out_base),
            "uncertainty_summary_path": artifact_paths.get("uncertainty_summary"),
            "risk_probabilities_path": artifact_paths.get("risk_probabilities"),
            "convergence_report_path": artifact_paths.get("convergence_report"),
            "sensitivity_report_path": artifact_paths.get("sensitivity_report"),
        })

        return {
            "success": True,
            "experiment_id": exp_id,
            "status": "COMPLETED",
            "requested_iterations": total_requested,
            "completed_iterations": uncertainty_summary["n_valid"],
            "failed_iterations": uncertainty_summary["n_failed"],
            "converged": convergence_summary.get("converged", False),
            "summary": uncertainty_summary,
            "risk_probabilities": risk_summary.get("risk_metrics", {}),
            "artifact_paths": artifact_paths,
            "warnings": val_result.get("warnings", []),
            "errors": [],
        }

    def _load_base_calibrated_population(self) -> list[dict[str, Any]]:
        handoff_path = self.root / "data/synthetic/phase6_policy_engine_handoff.json"
        if not handoff_path.exists():
            raise FileNotFoundError(f"Phase 6 handoff file not found: {handoff_path}")
        
        handoff_data = json.loads(handoff_path.read_text(encoding="utf-8"))
        calib_rel_path = handoff_data["calibrated_population_path"]
        calib_path = (self.root / calib_rel_path).resolve()
        
        if not calib_path.exists():
            raise FileNotFoundError(f"Calibrated population file not found: {calib_path}")

        return read_csv(calib_path)

    def _write_experiment_artifacts(
        self,
        out_base: Path,
        exp_id: str,
        config: SimulationConfig,
        raw_cfg_dict: dict[str, Any],
        completed_iterations: list[dict[str, Any]],
        uncertainty_summary: dict[str, Any],
        risk_summary: dict[str, Any],
        convergence_summary: dict[str, Any],
        sensitivity_summary: dict[str, Any],
        start_time: datetime,
        end_time: datetime,
        duration_sec: float,
    ) -> dict[str, str]:
        artifact_paths: dict[str, str] = {}

        # 1. Config & Metadata
        cfg_out_path = out_base / "experiment_config.yaml"
        cfg_out_path.write_text(json.dumps(raw_cfg_dict, indent=2) + "\n", encoding="utf-8")
        artifact_paths["experiment_config"] = str(cfg_out_path)

        metadata = {
            "experiment_id": exp_id,
            "name": config.experiment.name,
            "description": config.experiment.description,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "execution_duration_seconds": duration_sec,
            "base_seed": config.experiment.base_seed,
            "total_requested_iterations": config.experiment.number_of_iterations,
            "completed_valid_iterations": uncertainty_summary["n_valid"],
            "failed_iterations": uncertainty_summary["n_failed"],
            "converged": convergence_summary.get("converged", False),
            "population_mode": config.population.mode.value,
            "sampling_strategy": config.population.sampling_strategy.value,
        }
        meta_path = out_base / "experiment_metadata.json"
        write_json(meta_path, metadata)
        artifact_paths["experiment_metadata"] = str(meta_path)

        # 2. Iteration Results Table
        iter_results_path = out_base / "iteration_results.csv"
        write_csv(iter_results_path, completed_iterations)
        artifact_paths["iteration_results"] = str(iter_results_path)

        # 3. Summaries
        unc_path = out_base / "uncertainty_summary.json"
        write_json(unc_path, uncertainty_summary)
        artifact_paths["uncertainty_summary"] = str(unc_path)

        risk_path = out_base / "risk_probabilities.json"
        write_json(risk_path, risk_summary)
        artifact_paths["risk_probabilities"] = str(risk_path)

        conv_path = out_base / "convergence_report.json"
        write_json(conv_path, convergence_summary)
        artifact_paths["convergence_report"] = str(conv_path)

        sens_path = out_base / "sensitivity_report.json"
        write_json(sens_path, sensitivity_summary)
        artifact_paths["sensitivity_report"] = str(sens_path)

        return artifact_paths
