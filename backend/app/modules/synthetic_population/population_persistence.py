from __future__ import annotations

from pathlib import Path
from typing import Any
from datetime import datetime, timezone
import hashlib
import json

from backend.app.modules.data_foundation.exports import write_simple_xlsx
from backend.app.modules.data_foundation.io_utils import read_csv, write_csv, write_json, write_md
from backend.app.modules.synthetic_population.assessment import ROOT, read_json
from backend.app.modules.synthetic_population.sampling_service import run_dynamic_sampling_demo


SYNTHETIC_DATA_LABEL = (
    "This file contains artificially generated synthetic records. These rows are not actual residents or survey respondents. "
    "They were generated from statistical relationships learned from the Tamil Nadu reference data foundation."
)
PERSON_ID_PREFIX = "TN-SYN-P-"
IDENTIFIER_FIELDS = {"reference_person_id", "reference_household_id", "source_record_id"}
PERSON_LEVEL_EXCLUDED_FIELDS = IDENTIFIER_FIELDS | {"synthetic_data_label"}
MODULE_NAME = "phase3_population_persistence"


class PopulationPersistenceError(Exception):
    code = "POPULATION_PERSISTENCE_ERROR"


class SyntheticPopulationPersistenceService:
    def __init__(self, root: Path = ROOT):
        self.root = root
        self.manifest_path = root / "data/synthetic/sampling/dynamic_sampling_manifest.json"
        self.reference_metadata = read_json(root / "data/reference/template_metadata.json")
        self.training_manifest = read_json(root / "data/synthetic/training/training_manifest.json")
        self.model_registry = read_json(root / "artifacts/synthetic_models/model_registry.json")

    def persist_demo_populations(self) -> dict[str, Any]:
        manifest = self._load_sampling_manifest()
        persisted = []
        for item in manifest.get("demo_populations", []):
            persisted.append(self.persist_population(item))
        result = {
            "module": MODULE_NAME,
            "synthetic_data_label": SYNTHETIC_DATA_LABEL,
            "population_count": len(persisted),
            "populations": persisted,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        write_json(self.root / "data/synthetic/population_persistence_manifest.json", result)
        self._write_preview_workbook(result)
        self._write_index_report(result)
        return result

    def persist_population(self, sampling_metadata: dict[str, Any]) -> dict[str, Any]:
        source_path = self.root / sampling_metadata["output_path"]
        if not source_path.exists():
            raise PopulationPersistenceError(f"Sampled population is missing: {sampling_metadata['output_path']}")
        source_rows = read_csv(source_path)
        rows = self._with_synthetic_ids(source_rows)
        population_id = sampling_metadata["population_id"]
        experiment_id = self._experiment_id(population_id)
        population_dir = self.root / "artifacts/synthetic_populations" / population_id
        population_path = population_dir / "population.csv"
        metadata_path = population_dir / "metadata.json"
        experiment_path = population_dir / "generation_experiment.json"
        report_json_path = population_dir / "generation_report.json"
        report_md_path = self.root / "reports/synthetic_populations" / f"{population_id}.md"
        duplicate_diagnostic = self._exact_duplicate_diagnostic(source_rows, sampling_metadata)
        warnings = self._warnings(sampling_metadata, duplicate_diagnostic)
        metadata = self._metadata(population_id, experiment_id, sampling_metadata, rows, warnings, duplicate_diagnostic, population_path)
        experiment = self._experiment(experiment_id, sampling_metadata, metadata)
        report = self._generation_report(metadata, sampling_metadata, duplicate_diagnostic, warnings, population_path)
        fieldnames = ["synthetic_person_id"] + [name for name in (list(source_rows[0].keys()) if source_rows else []) if name not in PERSON_LEVEL_EXCLUDED_FIELDS]
        write_csv(population_path, rows, fieldnames)
        write_json(metadata_path, metadata)
        write_json(experiment_path, experiment)
        write_json(report_json_path, report)
        write_md(report_md_path, self._report_markdown(report))
        return {
            "population_id": population_id,
            "experiment_id": experiment_id,
            "rows": len(rows),
            "artifact_dir": str(population_dir.relative_to(self.root)).replace("\\", "/"),
            "population_csv_path": str(population_path.relative_to(self.root)).replace("\\", "/"),
            "metadata_path": str(metadata_path.relative_to(self.root)).replace("\\", "/"),
            "generation_report_json_path": str(report_json_path.relative_to(self.root)).replace("\\", "/"),
            "generation_report_md_path": str(report_md_path.relative_to(self.root)).replace("\\", "/"),
            "warnings": warnings,
            "exact_reference_duplicate_rate": duplicate_diagnostic["exact_reference_duplicate_rate"],
        }

    def _load_sampling_manifest(self) -> dict[str, Any]:
        if not self.manifest_path.exists():
            return run_dynamic_sampling_demo(self.root)
        return read_json(self.manifest_path)

    def _with_synthetic_ids(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        output = []
        for index, row in enumerate(rows, start=1):
            clean = {key: value for key, value in row.items() if key not in PERSON_LEVEL_EXCLUDED_FIELDS}
            output.append({"synthetic_person_id": f"{PERSON_ID_PREFIX}{index:09d}", **clean})
        ids = [row["synthetic_person_id"] for row in output]
        if len(ids) != len(set(ids)):
            raise PopulationPersistenceError("Synthetic person IDs are not unique.")
        return output

    def _metadata(
        self,
        population_id: str,
        experiment_id: str,
        sampling_metadata: dict[str, Any],
        rows: list[dict[str, Any]],
        warnings: list[str],
        duplicate_diagnostic: dict[str, Any],
        population_path: Path,
    ) -> dict[str, Any]:
        constraint = sampling_metadata.get("constraint_summary", {})
        variables = [name for name in (list(rows[0].keys()) if rows else []) if name != "synthetic_person_id"]
        return {
            "population_id": population_id,
            "generation_experiment_id": experiment_id,
            "synthetic": True,
            "synthetic_data_label": SYNTHETIC_DATA_LABEL,
            "jurisdiction": "Tamil Nadu",
            "generator_type": sampling_metadata.get("generator_type"),
            "generator_version": sampling_metadata.get("model_version", ""),
            "model_id": sampling_metadata.get("model_id"),
            "reference_template_version": self.reference_metadata.get("version", "UNKNOWN"),
            "phase2_requirement_version": "synthetic_population_requirements_current",
            "training_dataset_version": self.training_manifest.get("training_dataset_version", "UNKNOWN"),
            "generated_at": sampling_metadata.get("generated_at"),
            "persisted_at": datetime.now(timezone.utc).isoformat(),
            "size": len(rows),
            "seed": sampling_metadata.get("seed"),
            "mode": sampling_metadata.get("mode"),
            "condition": sampling_metadata.get("conditions", {}),
            "constraint_version": constraint.get("constraint_version", "UNKNOWN"),
            "variables": variables,
            "id_policy": {
                "person_id_column": "synthetic_person_id",
                "person_id_format": f"{PERSON_ID_PREFIX}000000001",
                "unique": True,
                "stable_within_exported_dataset": True,
                "linked_to_real_identifiers": False,
                "household_ids": "not emitted; Phase 3 MVP persists person-level synthetic populations only",
            },
            "artifact_paths": {
                "population_csv": str(population_path.relative_to(self.root)).replace("\\", "/"),
                "population_parquet": None,
            },
            "export_formats": {
                "csv": "available",
                "parquet": "skipped_missing_parquet_writer_dependency",
                "excel_preview": "data/exports/tamil_nadu_synthetic_population_preview.xlsx",
            },
            "quality": {
                "constraint_summary": constraint,
                "exact_reference_duplicate_diagnostic": duplicate_diagnostic,
            },
            "warnings": warnings,
        }

    def _experiment(self, experiment_id: str, sampling_metadata: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
        return {
            "experiment_id": experiment_id,
            "population_id": metadata["population_id"],
            "generator": sampling_metadata.get("generator_type"),
            "model_id": sampling_metadata.get("model_id"),
            "reference_template_version": metadata["reference_template_version"],
            "phase2_requirements_version": metadata["phase2_requirement_version"],
            "training_config": self._model_entry(sampling_metadata.get("model_id")).get("config", {}),
            "generation_config": {
                "size": metadata["size"],
                "seed": metadata["seed"],
                "mode": metadata["mode"],
                "conditions": metadata["condition"],
                "batch_size": sampling_metadata.get("batch_size"),
                "batch_count": sampling_metadata.get("batch_count"),
            },
            "variables": metadata["variables"],
            "constraints_version": metadata["constraint_version"],
            "created_at": metadata["persisted_at"],
            "status": "COMPLETED",
        }

    def _generation_report(
        self,
        metadata: dict[str, Any],
        sampling_metadata: dict[str, Any],
        duplicate_diagnostic: dict[str, Any],
        warnings: list[str],
        population_path: Path,
    ) -> dict[str, Any]:
        constraint = sampling_metadata.get("constraint_summary", {})
        return {
            "population_id": metadata["population_id"],
            "generation_experiment_id": metadata["generation_experiment_id"],
            "model_id": metadata["model_id"],
            "generator": metadata["generator_type"],
            "size": metadata["size"],
            "seed": metadata["seed"],
            "mode": metadata["mode"],
            "conditions": metadata["condition"],
            "variables": metadata["variables"],
            "duration_seconds": sampling_metadata.get("generation_duration_seconds"),
            "constraint_violations": constraint.get("hard_violation_count", 0),
            "soft_anomalies": constraint.get("soft_anomaly_count", 0),
            "repairs": constraint.get("records_repaired", 0),
            "rejected_rows": constraint.get("records_rejected", 0),
            "exact_reference_duplicate_diagnostic": duplicate_diagnostic,
            "output_path": str(population_path.relative_to(self.root)).replace("\\", "/"),
            "warnings": warnings,
            "synthetic_data_label": SYNTHETIC_DATA_LABEL,
        }

    def _exact_duplicate_diagnostic(self, source_rows: list[dict[str, Any]], sampling_metadata: dict[str, Any]) -> dict[str, Any]:
        model_entry = self._model_entry(sampling_metadata.get("model_id"))
        feature_columns = [name for name in model_entry.get("variables", []) if name not in IDENTIFIER_FIELDS]
        training_path = self.root / model_entry.get("training_dataset_path", self.training_manifest.get("training_dataset_path", ""))
        reference_rows = read_csv(training_path) if training_path.exists() else []
        reference_keys = {self._row_key(row, feature_columns) for row in reference_rows}
        duplicate_count = sum(1 for row in source_rows if self._row_key(row, feature_columns) in reference_keys)
        total = len(source_rows)
        return {
            "reference_dataset_path": str(training_path.relative_to(self.root)).replace("\\", "/") if training_path.exists() else None,
            "comparison_columns": feature_columns,
            "generated_rows_checked": total,
            "exact_reference_duplicate_count": duplicate_count,
            "exact_reference_duplicate_rate": round((duplicate_count / total) * 100, 4) if total else 0,
            "interpretation": "Exact row-level feature matches are expected for bootstrap resampling and should be lower for generative candidates.",
        }

    def _row_key(self, row: dict[str, Any], columns: list[str]) -> str:
        return json.dumps([str(row.get(column, "")) for column in columns], separators=(",", ":"), ensure_ascii=False)

    def _warnings(self, sampling_metadata: dict[str, Any], duplicate_diagnostic: dict[str, Any]) -> list[str]:
        warnings = [
            "Parquet export skipped because no parquet writer dependency is available in the local runtime.",
            "Synthetic population has not yet passed Phase 4 population validation.",
        ]
        if sampling_metadata.get("generator_type") == "bootstrap":
            warnings.append("Bootstrap output is a resampled baseline and may have high exact reference duplicate rates.")
        if duplicate_diagnostic["exact_reference_duplicate_rate"] > 0:
            warnings.append(f"Exact reference duplicate diagnostic found {duplicate_diagnostic['exact_reference_duplicate_rate']}% feature-level matches.")
        return warnings

    def _experiment_id(self, population_id: str) -> str:
        digest = hashlib.sha256(population_id.encode("utf-8")).hexdigest()[:10].upper()
        return f"SYNEXP-{digest}"

    def _model_entry(self, model_id: str | None) -> dict[str, Any]:
        for item in self.model_registry.get("models", []):
            if item.get("model_id") == model_id:
                return item
        return {}

    def _write_preview_workbook(self, manifest: dict[str, Any]) -> None:
        first = manifest["populations"][0] if manifest.get("populations") else {}
        population_rows = read_csv(self.root / first["population_csv_path"]) if first else []
        first_metadata = read_json(self.root / first["metadata_path"]) if first else {}
        first_model = self._model_entry(first_metadata.get("model_id"))
        generation_config = {
            "size": first_metadata.get("size", ""),
            "seed": first_metadata.get("seed", ""),
            "mode": first_metadata.get("mode", ""),
            "condition": first_metadata.get("condition", {}),
            "constraint_version": first_metadata.get("constraint_version", ""),
        }
        sheets = {
            "00_README": [{"synthetic_data_label": SYNTHETIC_DATA_LABEL, "scope": "Inspection preview only; use persisted CSV artifacts for machine reads."}],
            "01_POPULATION_METADATA": self._dict_rows(first_metadata),
            "02_SYNTHETIC_SAMPLE": population_rows[:100],
            "03_VARIABLE_DICTIONARY": [{"variable": name, "role": "synthetic identifier" if name == "synthetic_person_id" else "synthesized feature"} for name in (list(population_rows[0].keys()) if population_rows else [])],
            "04_GENERATION_CONFIG": self._dict_rows(generation_config),
            "05_CONSTRAINT_SUMMARY": self._dict_rows(first_metadata.get("quality", {}).get("constraint_summary", {})),
            "06_MODEL_METADATA": self._dict_rows(first_model),
            "07_WARNINGS": [{"warning": warning} for warning in first_metadata.get("warnings", [])] or [{"warning": ""}],
        }
        write_simple_xlsx(self.root / "data/exports/tamil_nadu_synthetic_population_preview.xlsx", sheets)

    def _dict_rows(self, value: dict[str, Any]) -> list[dict[str, str]]:
        rows = []
        for key, item in value.items():
            rows.append({"field": key, "value": json.dumps(item, ensure_ascii=False, sort_keys=True) if isinstance(item, (dict, list)) else item})
        return rows or [{"field": "", "value": ""}]

    def _write_index_report(self, manifest: dict[str, Any]) -> None:
        lines = ["# Synthetic Population Persistence Report", "", SYNTHETIC_DATA_LABEL, "", "## Persisted Populations", ""]
        for item in manifest.get("populations", []):
            lines.extend([
                f"### {item['population_id']}",
                "",
                f"- Experiment ID: {item['experiment_id']}",
                f"- Rows: {item['rows']}",
                f"- Population CSV: {item['population_csv_path']}",
                f"- Metadata: {item['metadata_path']}",
                f"- Generation report: {item['generation_report_md_path']}",
                f"- Exact reference duplicate rate: {item['exact_reference_duplicate_rate']}%",
                f"- Warnings: {'; '.join(item['warnings']) if item['warnings'] else 'None'}",
                "",
            ])
        lines.append("- Excel preview: data/exports/tamil_nadu_synthetic_population_preview.xlsx")
        write_md(self.root / "reports/synthetic_population_persistence_report.md", "\n".join(lines))

    def _report_markdown(self, report: dict[str, Any]) -> str:
        duplicate = report["exact_reference_duplicate_diagnostic"]
        return "\n".join([
            f"# Synthetic Population Generation Report: {report['population_id']}",
            "",
            SYNTHETIC_DATA_LABEL,
            "",
            f"- Population ID: {report['population_id']}",
            f"- Experiment ID: {report['generation_experiment_id']}",
            f"- Model ID: {report['model_id']}",
            f"- Generator: {report['generator']}",
            f"- Size: {report['size']}",
            f"- Seed: {report['seed']}",
            f"- Mode: {report['mode']}",
            f"- Conditions: {json.dumps(report['conditions'], sort_keys=True)}",
            f"- Variables: {', '.join(report['variables'])}",
            f"- Duration seconds: {report['duration_seconds']}",
            f"- Constraint violations: {report['constraint_violations']}",
            f"- Repairs: {report['repairs']}",
            f"- Rejected rows: {report['rejected_rows']}",
            f"- Exact reference duplicate count: {duplicate['exact_reference_duplicate_count']} of {duplicate['generated_rows_checked']} ({duplicate['exact_reference_duplicate_rate']}%)",
            f"- Output path: {report['output_path']}",
            f"- Warnings: {'; '.join(report['warnings']) if report['warnings'] else 'None'}",
        ])


def run_population_persistence(root: Path = ROOT) -> dict[str, Any]:
    return SyntheticPopulationPersistenceService(root).persist_demo_populations()
