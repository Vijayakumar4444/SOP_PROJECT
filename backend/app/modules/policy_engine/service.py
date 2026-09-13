from __future__ import annotations

from pathlib import Path
from typing import Any
from datetime import datetime, timezone
import hashlib
import json
import uuid

from backend.app.modules.data_foundation.io_utils import read_csv, write_csv, write_json, write_md
from backend.app.modules.policy_engine.aggregation import compute_policy_aggregates
from backend.app.modules.policy_engine.beneficiary_selector import select_beneficiaries
from backend.app.modules.policy_engine.benefit_calculator import calculate_policy_benefits
from backend.app.modules.policy_engine.compatibility_checker import check_policy_population_compatibility
from backend.app.modules.policy_engine.constraint_validator import validate_execution_constraints
from backend.app.modules.policy_engine.eligibility_evaluator import evaluate_population_eligibility
from backend.app.modules.policy_engine.policy_loader import load_policy_from_file
from backend.app.modules.policy_engine.policy_model import PolicyDefinition
from backend.app.modules.policy_engine.policy_validator import validate_policy_schema


class Phase6PolicyService:
    """Primary orchestration service for Phase 6 Policy Engine."""

    def __init__(self, project_root: Path | str | None = None) -> None:
        if project_root:
            self.root = Path(project_root).resolve()
        else:
            self.root = Path(__file__).resolve().parents[4]

    def execute_policy(
        self,
        policy_path: Path | str,
        population_path: Path | str | None = None,
        output_dir: Path | str | None = None,
        weight_column: str | None = None,
        run_id: str | None = None,
        seed_override: int | None = None,
        summary_only: bool = False,
    ) -> dict[str, Any]:
        start_time = datetime.now(timezone.utc)
        run_id = run_id or f"POLICY-RUN-{uuid.uuid4().hex[:10].upper()}"

        # 1. Load Policy Definition
        policy_file_path = self.root / policy_path if not Path(policy_path).is_absolute() else Path(policy_path)
        policy_def, raw_policy_dict = load_policy_from_file(policy_file_path)

        if seed_override is not None:
            policy_def.constraints.lottery_seed = seed_override

        # 2. Validate Policy Schema
        val_result = validate_policy_schema(policy_def)
        if not val_result["valid"]:
            return {
                "success": False,
                "run_id": run_id,
                "policy_id": policy_def.policy_id,
                "summary": {},
                "artifact_paths": {},
                "warnings": val_result.get("warnings", []),
                "errors": val_result.get("errors", []),
            }

        # 3. Load Population Data
        pop_records, pop_path_resolved, default_weight_col = self._load_population_records(population_path)
        weight_col = weight_column or default_weight_col or "calibration_weight"

        # 4. Check Data Compatibility
        compat_result = check_policy_population_compatibility(policy_def, pop_records)
        if not compat_result["compatible"]:
            return {
                "success": False,
                "run_id": run_id,
                "policy_id": policy_def.policy_id,
                "summary": {},
                "artifact_paths": {},
                "warnings": compat_result.get("high_missingness_variables", []),
                "errors": [{"code": "MISSING_REQUIRED_VARIABLES", "message": f"Population missing required fields: {compat_result['missing_variables']}"}],
            }

        # 5. Evaluate Eligibility Rules
        eligibility_records = evaluate_population_eligibility(
            policy=policy_def,
            records=pop_records,
            run_id=run_id,
            weight_col=weight_col,
        )

        # 6. Beneficiary Selection & Capacity Capping
        results_records, selected_records, selection_stats = select_beneficiaries(
            policy=policy_def,
            eligibility_records=eligibility_records,
        )

        # 7. Benefit & Cost Calculation
        results_records, cost_summary = calculate_policy_benefits(
            policy=policy_def,
            records=results_records,
            weight_col=weight_col,
        )

        # 8. Constraint Validation
        constraints_passed, constraint_items = validate_execution_constraints(
            policy=policy_def,
            results_records=results_records,
            weighted_total_cost=cost_summary["weighted_total_cost"],
        )

        # 9. Compute Aggregates & Breakdowns
        overall_summary, breakdown_rows = compute_policy_aggregates(
            policy=policy_def,
            results_records=results_records,
            cost_summary=cost_summary,
            weight_col=weight_col,
        )

        end_time = datetime.now(timezone.utc)
        duration_sec = round((end_time - start_time).total_seconds(), 4)

        # 10. Write Run Artifacts
        out_base = Path(output_dir).resolve() if output_dir else self.root / f"artifacts/policy_runs/{run_id}"
        out_base.mkdir(parents=True, exist_ok=True)

        artifact_paths: dict[str, str] = {}

        run_metadata = {
            "run_id": run_id,
            "policy_id": policy_def.policy_id,
            "policy_version": policy_def.version,
            "execution_timestamp": start_time.isoformat(),
            "execution_duration_seconds": duration_sec,
            "input_population_path": str(pop_path_resolved),
            "input_population_checksum": self._compute_checksum(pop_path_resolved),
            "policy_file_checksum": self._compute_checksum(policy_file_path),
            "weight_column": weight_col,
            "target_unit": policy_def.target_unit.value,
            "allocation_strategy": policy_def.constraints.allocation_strategy.value,
            "lottery_seed": policy_def.constraints.lottery_seed,
            "total_input_records": len(pop_records),
            "constraints_passed": constraints_passed,
            "final_status": "SUCCESS" if constraints_passed else "SUCCESS_WITH_CONSTRAINT_WARNINGS",
        }

        # Write metadata & summaries
        meta_path = out_base / "run_metadata.json"
        write_json(meta_path, run_metadata)
        artifact_paths["run_metadata"] = str(meta_path)

        policy_spec_path = out_base / "validated_policy.json"
        write_json(policy_spec_path, raw_policy_dict)
        artifact_paths["validated_policy"] = str(policy_spec_path)

        summary_path = out_base / "policy_summary.json"
        write_json(summary_path, overall_summary)
        artifact_paths["policy_summary"] = str(summary_path)

        constraint_path = out_base / "constraint_report.json"
        write_json(constraint_path, {"run_id": run_id, "constraints_passed": constraints_passed, "constraints": constraint_items})
        artifact_paths["constraint_report"] = str(constraint_path)

        compat_path = out_base / "compatibility_report.json"
        write_json(compat_path, compat_result)
        artifact_paths["compatibility_report"] = str(compat_path)

        if breakdown_rows:
            breakdown_csv = out_base / "demographic_breakdown.csv"
            write_csv(breakdown_csv, breakdown_rows)
            artifact_paths["demographic_breakdown"] = str(breakdown_csv)

        # Write tabular record results unless summary_only mode is set
        if not summary_only:
            elig_path = out_base / "eligibility_results.csv"
            write_csv(elig_path, results_records)
            artifact_paths["eligibility_results"] = str(elig_path)

            ben_path = out_base / "beneficiaries.csv"
            only_selected = [r for r in results_records if r.get("is_selected_beneficiary", False)]
            write_csv(ben_path, only_selected)
            artifact_paths["beneficiaries"] = str(ben_path)

        # Audit Log
        audit_entry = {
            "timestamp": end_time.isoformat(),
            "run_id": run_id,
            "policy_id": policy_def.policy_id,
            "status": "COMPLETED",
            "evaluated_records": len(pop_records),
            "eligible_records": overall_summary["unweighted_eligible_records"],
            "selected_beneficiaries": overall_summary["unweighted_selected_beneficiaries"],
            "weighted_beneficiaries": overall_summary["weighted_beneficiary_population"],
            "total_cost_inr": overall_summary["total_estimated_program_cost_inr"],
        }
        audit_log_path = out_base / "audit_log.jsonl"
        audit_log_path.write_text(json.dumps(audit_entry) + "\n", encoding="utf-8")
        artifact_paths["audit_log"] = str(audit_log_path)

        return {
            "success": True,
            "run_id": run_id,
            "policy_id": policy_def.policy_id,
            "summary": overall_summary,
            "artifact_paths": artifact_paths,
            "warnings": val_result.get("warnings", []),
            "errors": [],
        }

    def evaluate_simulation(
        self,
        policy_path: Path | str,
        population_records: list[dict[str, Any]] | Any,
        weight_column: str = "calibration_weight",
        seed: int | None = None,
        parameter_overrides: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Phase 7 integration interface method for fast repeated Monte Carlo calls."""
        policy_def, _ = load_policy_from_file(self.root / policy_path if not Path(policy_path).is_absolute() else Path(policy_path))
        
        if seed is not None:
            policy_def.constraints.lottery_seed = seed
        
        if parameter_overrides:
            if "total_budget" in parameter_overrides:
                policy_def.constraints.total_budget = float(parameter_overrides["total_budget"])
            if "maximum_beneficiaries" in parameter_overrides:
                policy_def.constraints.maximum_beneficiaries = int(parameter_overrides["maximum_beneficiaries"])
            if "benefit_amount" in parameter_overrides:
                policy_def.benefit.amount = float(parameter_overrides["benefit_amount"])

        run_id = f"SIM-RUN-{uuid.uuid4().hex[:8]}"
        
        eligibility_records = evaluate_population_eligibility(policy_def, population_records, run_id=run_id, weight_col=weight_column)
        results_records, _, selection_stats = select_beneficiaries(policy_def, eligibility_records)
        results_records, cost_summary = calculate_policy_benefits(policy_def, results_records, weight_col=weight_column)
        overall_summary, _ = compute_policy_aggregates(policy_def, results_records, cost_summary, weight_col=weight_column)

        return overall_summary

    def _load_population_records(self, population_path: Path | str | None) -> tuple[list[dict[str, Any]], Path, str]:
        if population_path:
            p_path = Path(population_path).resolve()
            if not p_path.exists():
                p_path = (self.root / population_path).resolve()
            if not p_path.exists():
                raise FileNotFoundError(f"Specified population file not found: {population_path}")
            records = read_csv(p_path)
            return records, p_path, "calibration_weight"

        # Fallback to Phase 5 handoff
        handoff_path = self.root / "data/synthetic/phase6_policy_engine_handoff.json"
        if not handoff_path.exists():
            raise FileNotFoundError(f"Phase 5 handoff file not found: {handoff_path}")

        handoff_data = json.loads(handoff_path.read_text(encoding="utf-8"))
        calib_rel_path = handoff_data["calibrated_population_path"]
        calib_path = (self.root / calib_rel_path).resolve()

        if not calib_path.exists():
            raise FileNotFoundError(f"Calibrated population file not found: {calib_path}")

        records = read_csv(calib_path)
        weight_col = handoff_data.get("policy_weight_column", "calibration_weight")
        return records, calib_path, weight_col

    def _compute_checksum(self, path: Path) -> str:
        if not path.exists() or not path.is_file():
            return "N/A"
        return hashlib.sha256(path.read_bytes()).hexdigest()[:12].upper()
