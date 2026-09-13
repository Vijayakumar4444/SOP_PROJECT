from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import platform
import sys

from backend.app.modules.calibration.diagnostics import weight_diagnostics
from backend.app.modules.calibration.handoff import write_phase6_handoff
from backend.app.modules.calibration.marginal_comparison import compare_marginals
from backend.app.modules.calibration.poststratification import poststratify
from backend.app.modules.calibration.raking import rake_weights
from backend.app.modules.calibration.target_loader import load_official_targets, usable_targets
from backend.app.modules.calibration.utils import (
    file_sha256,
    load_yaml_config,
    read_csv,
    read_json,
    relative_path,
    rounded,
    stable_hash,
    to_float,
    write_csv,
    write_json,
    write_md,
)
from backend.app.modules.calibration.validation import evaluate_quality_gates
from backend.app.modules.synthetic_population.assessment import ROOT


PHASE5_VERSION = "phase5_calibration_reweighting_v1"


class Phase5CalibrationService:
    def __init__(self, root: Path = ROOT, config_path: Path | None = None):
        self.root = root
        self.config_path = config_path or root / "config/calibration/calibration.yaml"
        self.config = load_yaml_config(self.config_path)

    def run(self) -> dict[str, Any]:
        handoff_path = self.root / "data/synthetic/phase5_calibration_handoff.json"
        phase4_manifest_path = self.root / "data/synthetic/phase4_validation_manifest.json"
        handoff = self._load_handoff(handoff_path)
        manifest_entry = self._resolve_phase4_manifest_entry(phase4_manifest_path, handoff["population_id"])
        population_path = self.root / manifest_entry["population_artifact"]
        metadata_path = self.root / manifest_entry.get("metadata_artifact", "")
        if not population_path.exists():
            raise FileNotFoundError(f"Selected Phase 4 population file is missing: {population_path}")
        population_rows = read_csv(population_path)
        if not population_rows:
            raise ValueError(f"Selected Phase 4 population is empty: {population_path}")
        original_rows = deepcopy(population_rows)
        target_sets_all = load_official_targets(self.root, population_rows, self.config)
        selected_targets = usable_targets(target_sets_all)
        if not selected_targets:
            raise ValueError("No usable official calibration targets were found.")
        warnings = self._collect_warnings(handoff, target_sets_all)
        pre_comparison = compare_marginals(population_rows, selected_targets)
        method = str(self.config.get("method", "raking")).lower()
        if method in {"post_stratification", "post-stratification", "poststratification"}:
            calibration_result = poststratify(population_rows, selected_targets[0], self.config)
        elif method in {"raking", "ipf"}:
            calibration_result = rake_weights(population_rows, selected_targets, self.config)
        else:
            raise ValueError(f"Unsupported Phase 5 calibration method: {method}")
        official_total = self._official_population_total()
        if official_total:
            for row in population_rows:
                weight = to_float(row.get("calibration_weight"), 0.0) or 0.0
                row["population_weight"] = f"{weight * official_total / len(population_rows):.12g}"
        else:
            warnings.append("No semantically valid official population total found for expansion weights.")
            for row in population_rows:
                row["population_weight"] = ""
        post_comparison = compare_marginals(population_rows, selected_targets, "calibration_weight")
        diagnostics = weight_diagnostics(population_rows, "calibration_weight")
        quality = evaluate_quality_gates(population_rows, calibration_result, post_comparison, diagnostics, self.config, warnings)
        self._assert_demographics_unchanged(original_rows, population_rows)
        calibration_id = self._calibration_id(handoff, selected_targets)
        artifact_dir = self.root / "artifacts/calibrated_populations" / calibration_id
        artifact_paths = self._write_artifacts(
            artifact_dir,
            population_rows,
            handoff,
            manifest_entry,
            target_sets_all,
            selected_targets,
            pre_comparison,
            post_comparison,
            calibration_result,
            diagnostics,
            quality,
            population_path,
            metadata_path,
        )
        handoff6 = write_phase6_handoff(
            self.root,
            calibration_id,
            handoff,
            artifact_paths,
            calibration_result,
            diagnostics,
            selected_targets,
            self.config_path,
            stable_hash(self.config),
            quality["status"],
            warnings,
        )
        reports = self._write_reports(
            calibration_id,
            handoff,
            selected_targets,
            target_sets_all,
            pre_comparison,
            post_comparison,
            calibration_result,
            diagnostics,
            quality,
            artifact_paths,
            handoff6,
            warnings,
        )
        return {
            "phase5_version": PHASE5_VERSION,
            "status": quality["status"],
            "calibration_id": calibration_id,
            "source_population_id": handoff["population_id"],
            "source_model_id": handoff["model_id"],
            "source_population_path": relative_path(self.root, population_path),
            "calibrated_population_path": relative_path(self.root, artifact_paths["population"]),
            "phase6_handoff_path": "data/synthetic/phase6_policy_engine_handoff.json",
            "calibration_targets": [target["variable"] for target in selected_targets],
            "method": calibration_result["method"],
            "convergence_status": calibration_result["status"],
            "iterations": calibration_result["iterations"],
            "weight_diagnostics": diagnostics,
            "pre_calibration_error": pre_comparison["summary"],
            "post_calibration_error": post_comparison["summary"],
            "unresolved_targets": calibration_result.get("unresolved_targets", []),
            "warnings": warnings,
            "reports": reports,
            "quality_gates": quality["gates"],
        }

    def _load_handoff(self, path: Path) -> dict[str, Any]:
        payload = read_json(path)
        if not payload:
            raise FileNotFoundError(f"Phase 5 handoff not found: {path}")
        required = ["population_id", "model_id", "validation_status", "quality_score"]
        missing = [key for key in required if payload.get(key) in {None, ""}]
        if missing:
            raise ValueError(f"Phase 5 handoff is missing required fields: {', '.join(missing)}")
        if payload.get("validation_status") not in {"PASS", "PASS_WITH_WARNINGS"}:
            raise ValueError(f"Phase 4 selected population is not acceptable for calibration: {payload.get('validation_status')}")
        if payload.get("selected_for_calibration") is False:
            raise ValueError("Phase 5 handoff explicitly marks the selected population as not selected for calibration.")
        return payload

    def _resolve_phase4_manifest_entry(self, path: Path, population_id: str) -> dict[str, Any]:
        manifest = read_json(path)
        for entry in manifest.get("synthetic_population_artifacts", []):
            if entry.get("population_id") == population_id:
                return entry
        raise ValueError(f"Selected population {population_id} is not present in {path}.")

    def _collect_warnings(self, handoff: dict[str, Any], target_sets: list[dict[str, Any]]) -> list[str]:
        warnings = list(handoff.get("warnings", []))
        for target in target_sets:
            for warning in target.get("warnings", []):
                warnings.append(f"{target.get('variable')}: {warning}")
            if target.get("status") == "NOT_USABLE":
                warnings.append(f"{target.get('variable')}: target not usable ({target.get('source_file')}).")
        return sorted(set(warnings))

    def _official_population_total(self) -> float | None:
        rows = read_csv(self.root / "data/calibration/state_population_marginals.csv")
        if not rows:
            return None
        row = rows[0]
        if row.get("state") != "Tamil Nadu":
            return None
        return to_float(row.get("population_total"))

    def _calibration_id(self, handoff: dict[str, Any], targets: list[dict[str, Any]]) -> str:
        digest = stable_hash({
            "phase5_version": PHASE5_VERSION,
            "population_id": handoff["population_id"],
            "model_id": handoff["model_id"],
            "config": self.config,
            "targets": targets,
        })
        return f"CAL-{str(self.config.get('method', 'raking')).upper().replace('_', '-')}-{digest}"

    def _write_artifacts(
        self,
        artifact_dir: Path,
        rows: list[dict[str, Any]],
        handoff: dict[str, Any],
        manifest_entry: dict[str, Any],
        target_sets_all: list[dict[str, Any]],
        selected_targets: list[dict[str, Any]],
        pre_comparison: dict[str, Any],
        post_comparison: dict[str, Any],
        calibration_result: dict[str, Any],
        diagnostics: dict[str, Any],
        quality: dict[str, Any],
        population_path: Path,
        metadata_path: Path,
    ) -> dict[str, Path]:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        population_out = artifact_dir / "population_calibrated.csv"
        metadata_out = artifact_dir / "calibration_metadata.json"
        diagnostics_out = artifact_dir / "weight_diagnostics.json"
        history_out = artifact_dir / "convergence_history.csv"
        before_out = artifact_dir / "marginal_comparison_before.csv"
        after_out = artifact_dir / "marginal_comparison_after.csv"
        fieldnames = list(rows[0].keys()) if rows else []
        write_csv(population_out, rows, fieldnames=fieldnames)
        write_json(diagnostics_out, diagnostics)
        write_csv(history_out, calibration_result.get("history", []), fieldnames=["iteration", "maximum_marginal_error", "mean_marginal_error", "weight_min", "weight_max", "converged"])
        write_csv(before_out, pre_comparison["rows"])
        write_csv(after_out, post_comparison["rows"])
        metadata = {
            "phase5_version": PHASE5_VERSION,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "calibration_id": artifact_dir.name,
            "status": quality["status"],
            "source_handoff": handoff,
            "source_manifest_entry": manifest_entry,
            "calibration_method": calibration_result["method"],
            "calibration_result": calibration_result,
            "selected_targets": selected_targets,
            "all_target_sets": target_sets_all,
            "quality_gates": quality["gates"],
            "input_hashes": {
                "source_population_sha256": file_sha256(population_path),
                "source_metadata_sha256": file_sha256(metadata_path),
                "config_sha256": file_sha256(self.config_path),
            },
            "software": {
                "python": sys.version.split()[0],
                "platform": platform.platform(),
            },
            "outputs": {
                "population_calibrated": relative_path(self.root, population_out),
                "weight_diagnostics": relative_path(self.root, diagnostics_out),
                "convergence_history": relative_path(self.root, history_out),
                "marginal_comparison_before": relative_path(self.root, before_out),
                "marginal_comparison_after": relative_path(self.root, after_out),
            },
        }
        write_json(metadata_out, metadata)
        return {
            "population": population_out,
            "metadata": metadata_out,
            "weight_diagnostics": diagnostics_out,
            "convergence_history": history_out,
            "marginal_before": before_out,
            "marginal_after": after_out,
        }

    def _write_reports(
        self,
        calibration_id: str,
        handoff: dict[str, Any],
        selected_targets: list[dict[str, Any]],
        all_targets: list[dict[str, Any]],
        pre_comparison: dict[str, Any],
        post_comparison: dict[str, Any],
        calibration_result: dict[str, Any],
        diagnostics: dict[str, Any],
        quality: dict[str, Any],
        artifact_paths: dict[str, Path],
        handoff6: dict[str, Any],
        warnings: list[str],
    ) -> dict[str, str]:
        reports_dir = self.root / "reports/calibration"
        reports_dir.mkdir(parents=True, exist_ok=True)
        target_report = reports_dir / "calibration_target_report.md"
        diagnostics_report = reports_dir / "weight_diagnostics.md"
        comparison_report = reports_dir / "marginal_comparison_before_after.md"
        convergence_report = reports_dir / "convergence_report.md"
        summary_report = reports_dir / "phase5_summary.md"
        top_summary = self.root / "reports/phase5_summary.md"
        write_md(target_report, self._target_report(all_targets))
        write_md(diagnostics_report, self._diagnostics_report(diagnostics))
        write_md(comparison_report, self._comparison_report(pre_comparison, post_comparison))
        write_md(convergence_report, self._convergence_report(calibration_result))
        summary_text = self._summary_report(calibration_id, handoff, selected_targets, pre_comparison, post_comparison, calibration_result, diagnostics, quality, artifact_paths, handoff6, warnings)
        write_md(summary_report, summary_text)
        write_md(top_summary, summary_text)
        return {
            "phase5_summary": relative_path(self.root, summary_report),
            "top_level_phase5_summary": relative_path(self.root, top_summary),
            "target_report": relative_path(self.root, target_report),
            "weight_diagnostics": relative_path(self.root, diagnostics_report),
            "comparison_report": relative_path(self.root, comparison_report),
            "convergence_report": relative_path(self.root, convergence_report),
        }

    def _target_report(self, targets: list[dict[str, Any]]) -> str:
        lines = ["# Phase 5 Calibration Target Report", ""]
        for target in targets:
            lines.extend([f"## {target['variable']}", "", f"- Target ID: {target['target_id']}", f"- Status: {target['status']}", f"- Source file: {target['source_file']}"])
            for warning in target.get("warnings", []):
                lines.append(f"- Warning: {warning}")
            lines.append("")
            lines.append("| Category | Synthetic categories | Target proportion | Official count | Source |")
            lines.append("| --- | --- | ---: | ---: | --- |")
            for category in target.get("categories", []):
                lines.append(f"| {category['category']} | {', '.join(category['synthetic_categories'])} | {category['target_proportion']} | {category['official_count']} | {category['source']} |")
            lines.append("")
        return "\n".join(lines)

    def _diagnostics_report(self, diagnostics: dict[str, Any]) -> str:
        return "\n".join([
            "# Phase 5 Weight Diagnostics",
            "",
            f"- Weight column: {diagnostics['weight_column']}",
            f"- Nominal sample size: {diagnostics['nominal_sample_size']}",
            f"- Weight sum: {diagnostics['weight_sum']}",
            f"- Minimum weight: {diagnostics['min_weight']}",
            f"- Maximum weight: {diagnostics['max_weight']}",
            f"- Mean weight: {diagnostics['mean_weight']}",
            f"- Median weight: {diagnostics['median_weight']}",
            f"- Standard deviation: {diagnostics['std_weight']}",
            f"- Coefficient of variation: {diagnostics['coefficient_of_variation']}",
            f"- Effective sample size: {diagnostics['effective_sample_size']}",
            f"- ESS ratio: {diagnostics['ess_ratio']}",
            f"- Invalid weights: {diagnostics['invalid_weight_count']}",
            f"- Negative weights: {diagnostics['negative_weight_count']}",
        ])

    def _comparison_report(self, before: dict[str, Any], after: dict[str, Any]) -> str:
        rows_by_key = {(row["target_id"], row["category"]): row for row in after["rows"]}
        lines = ["# Phase 5 Marginal Comparison Before/After", "", "| Target | Category | Before diff | After diff | Improvement | Official proportion | After proportion |", "| --- | --- | ---: | ---: | ---: | ---: | ---: |"]
        for row in before["rows"]:
            after_row = rows_by_key.get((row["target_id"], row["category"]), {})
            before_diff = float(row.get("absolute_proportion_difference") or 0)
            after_diff = float(after_row.get("absolute_proportion_difference") or 0)
            lines.append(f"| {row['variable']} | {row['category']} | {before_diff:.6f} | {after_diff:.6f} | {before_diff - after_diff:.6f} | {row.get('official_proportion')} | {after_row.get('synthetic_proportion')} |")
        lines.extend([
            "",
            f"- Pre-calibration mean TVD: {before['summary']['mean_total_variation_distance']}",
            f"- Post-calibration mean TVD: {after['summary']['mean_total_variation_distance']}",
            f"- Pre-calibration max category error: {before['summary']['max_category_error']}",
            f"- Post-calibration max category error: {after['summary']['max_category_error']}",
        ])
        return "\n".join(lines)

    def _convergence_report(self, result: dict[str, Any]) -> str:
        lines = ["# Phase 5 Convergence Report", "", f"- Method: {result['method']}", f"- Status: {result['status']}", f"- Iterations: {result['iterations']}", ""]
        lines.append("| Iteration | Max marginal error | Mean marginal error | Min weight | Max weight | Converged |")
        lines.append("| ---: | ---: | ---: | ---: | ---: | --- |")
        for row in result.get("history", []):
            lines.append(f"| {row['iteration']} | {row['maximum_marginal_error']} | {row['mean_marginal_error']} | {row['weight_min']} | {row['weight_max']} | {row['converged']} |")
        for item in result.get("unresolved_targets", []):
            lines.append(f"- Unresolved: {item['variable']} {item['category']} - {item['reason']}")
        return "\n".join(lines)

    def _summary_report(
        self,
        calibration_id: str,
        handoff: dict[str, Any],
        targets: list[dict[str, Any]],
        before: dict[str, Any],
        after: dict[str, Any],
        result: dict[str, Any],
        diagnostics: dict[str, Any],
        quality: dict[str, Any],
        artifact_paths: dict[str, Path],
        handoff6: dict[str, Any],
        warnings: list[str],
    ) -> str:
        lines = [
            "# Phase 5 Calibration & Reweighting Summary",
            "",
            f"- Calibration ID: {calibration_id}",
            f"- Input population ID: {handoff['population_id']}",
            f"- Input model ID: {handoff['model_id']}",
            f"- Phase 4 quality score: {handoff.get('quality_score')}",
            f"- Calibration method: {result['method']}",
            f"- Calibration variables: {', '.join(target['variable'] for target in targets)}",
            f"- Official data sources: {', '.join(sorted({category['source'] for target in targets for category in target.get('categories', []) if category.get('source')}))}",
            f"- Iteration count: {result['iterations']}",
            f"- Convergence status: {result['status']}",
            f"- Weight min/max/mean: {diagnostics['min_weight']} / {diagnostics['max_weight']} / {diagnostics['mean_weight']}",
            f"- Effective sample size: {diagnostics['effective_sample_size']}",
            f"- ESS ratio: {diagnostics['ess_ratio']}",
            f"- Pre-calibration mean TVD: {before['summary']['mean_total_variation_distance']}",
            f"- Post-calibration mean TVD: {after['summary']['mean_total_variation_distance']}",
            f"- Pre-calibration max marginal error: {before['summary']['max_category_error']}",
            f"- Post-calibration max marginal error: {after['summary']['max_category_error']}",
            f"- Unresolved targets: {len(result.get('unresolved_targets', []))}",
            f"- Final Phase 5 status: {quality['status']}",
            f"- Calibrated population: {relative_path(self.root, artifact_paths['population'])}",
            f"- Phase 6 handoff: data/synthetic/phase6_policy_engine_handoff.json",
            "",
            "## Quality Gates",
            "",
        ]
        for gate in quality["gates"]:
            lines.append(f"- {gate['name']}: {'PASS' if gate['passed'] else 'FAIL'}")
        lines.extend(["", "## Warnings", ""])
        if warnings:
            lines.extend(f"- {warning}" for warning in warnings)
        else:
            lines.append("- None")
        lines.extend(["", "## Phase 6 Handoff", "", f"- Policy weight column: {handoff6['policy_weight_column']}", f"- Expansion weight column: {handoff6['expansion_weight_column']}"])
        return "\n".join(lines)

    def _assert_demographics_unchanged(self, before: list[dict[str, Any]], after: list[dict[str, Any]]) -> None:
        new_columns = {"base_weight", "raw_calibration_weight", "calibration_weight", "normalized_weight", "population_weight"}
        for index, (left, right) in enumerate(zip(before, after)):
            for key, value in left.items():
                if key not in new_columns and right.get(key) != value:
                    raise AssertionError(f"Calibration changed source attribute {key} at row {index}.")


def run_phase5_calibration(root: Path = ROOT) -> dict[str, Any]:
    return Phase5CalibrationService(root).run()
