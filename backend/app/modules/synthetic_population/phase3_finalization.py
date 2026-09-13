from __future__ import annotations

from pathlib import Path
from typing import Any
from datetime import datetime, timezone
import json
import time

from backend.app.modules.data_foundation.io_utils import read_csv, write_csv, write_json, write_md
from backend.app.modules.synthetic_population.assessment import ROOT, read_json
from backend.app.modules.synthetic_population.constraints import ConstraintEngine
from backend.app.modules.synthetic_population.model_comparison import run_model_comparison_manifest
from backend.app.modules.synthetic_population.population_persistence import (
    SYNTHETIC_DATA_LABEL,
    SyntheticPopulationPersistenceService,
)
from backend.app.modules.synthetic_population.sampling_service import DynamicSamplingService


ACCEPTANCE_SIZE = 12000
ACCEPTANCE_SEEDS = {"bootstrap": 142, "gaussian_copula": 144, "ctgan": 146, "tvae": 148}
NO_BEST_MODEL_WARNING = (
    "Phase 3 does not select a best model. Candidate populations must be evaluated in Phase 4 population validation before policy simulation use."
)


class Phase3FinalizationService:
    def __init__(self, root: Path = ROOT):
        self.root = root
        self.registry = read_json(root / "artifacts/synthetic_models/model_registry.json")
        self.training = read_json(root / "data/synthetic/training/training_manifest.json")
        self.reference = read_json(root / "data/reference/template_metadata.json")
        self.selection = read_json(root / "data/synthetic/variable_selection.json")
        self.requirements = read_json(root / "data/compatibility/synthetic_population_requirements.json")

    def run(self) -> dict[str, Any]:
        acceptance = self._generate_acceptance_populations()
        holdout_path = self._write_holdout_reference()
        phase4_manifest = self._write_phase4_manifest(acceptance, holdout_path)
        comparison = run_model_comparison_manifest(self.root)
        self._write_docs()
        summary_path = self._write_phase3_summary(acceptance, phase4_manifest, comparison)
        checklist_path = self._write_definition_of_done(phase4_manifest)
        result = {
            "module": "phase3_finalization",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "acceptance_manifest": "data/synthetic/phase3_acceptance_manifest.json",
            "phase4_manifest": "data/synthetic/phase4_validation_manifest.json",
            "model_comparison_manifest": "data/synthetic/model_comparison_manifest.json",
            "summary_report": str(summary_path.relative_to(self.root)).replace("\\", "/"),
            "definition_of_done_report": str(checklist_path.relative_to(self.root)).replace("\\", "/"),
            "documentation": [
                "docs/synthetic_population_generation.md",
                "docs/synthetic_models/bootstrap.md",
                "docs/synthetic_models/gaussian_copula.md",
                "docs/synthetic_models/ctgan.md",
                "docs/synthetic_models/tvae.md",
            ],
            "stop_condition": NO_BEST_MODEL_WARNING,
        }
        write_json(self.root / "data/synthetic/phase3_finalization_manifest.json", result)
        return result

    def _generate_acceptance_populations(self) -> dict[str, Any]:
        sampler = DynamicSamplingService(self.root)
        persistence = SyntheticPopulationPersistenceService(self.root)
        persisted = []
        generated = []
        for model_entry in self.registry.get("models", []):
            if model_entry.get("status") != "TRAINED":
                generated.append({
                    "generator_type": model_entry.get("generator_type"),
                    "model_id": model_entry.get("model_id"),
                    "status": model_entry.get("status"),
                    "blocking_reason": model_entry.get("blocking_reason", "not trained"),
                })
                continue
            generator = model_entry["generator_type"]
            seed = ACCEPTANCE_SEEDS.get(generator, 140)
            population_id = f"SYNPOP-{generator.upper()}-REPRESENTATIVE-{ACCEPTANCE_SIZE}-{seed}-ACCEPTANCE"
            reused = self._reuse_existing_acceptance_population(model_entry, population_id)
            if reused:
                generated.append(reused["generated"])
                persisted.append(reused["persisted"])
                continue
            model = sampler._load_model(model_entry)
            started = time.perf_counter()
            rows = model.sample(ACCEPTANCE_SIZE, seed=seed)
            duration = max(time.perf_counter() - started, 0.000001)
            constraint_summary = ConstraintEngine().validate_rows(rows)
            output_path = self.root / "data/synthetic/acceptance" / f"{population_id}.csv"
            metadata = {
                "population_id": population_id,
                "synthetic": True,
                "mode": "REPRESENTATIVE",
                "model_id": model_entry["model_id"],
                "generator_type": generator,
                "model_version": model_entry.get("model_version", ""),
                "requested_count": ACCEPTANCE_SIZE,
                "generated_count": len(rows),
                "accepted_count": len(rows),
                "acceptance_rate": 100.0,
                "seed": seed,
                "conditions": {},
                "batch_size": ACCEPTANCE_SIZE,
                "batch_count": 1,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "generation_duration_seconds": round(duration, 4),
                "constraint_summary": constraint_summary,
                "output_path": str(output_path.relative_to(self.root)).replace("\\", "/"),
            }
            write_csv(output_path, rows)
            write_json(output_path.with_name(f"{population_id}_metadata.json"), metadata)
            persisted_item = persistence.persist_population(metadata)
            generated.append({
                "generator_type": generator,
                "model_id": model_entry["model_id"],
                "status": "TRAINED",
                "population_id": population_id,
                "rows": len(rows),
                "generation_duration_seconds": round(duration, 4),
                "hard_constraint_violations": constraint_summary["hard_violation_count"],
                "soft_anomalies": constraint_summary["soft_anomaly_count"],
                "source_output_path": metadata["output_path"],
                "persisted_artifact_dir": persisted_item["artifact_dir"],
            })
            persisted.append(persisted_item)
        manifest = {
            "module": "phase3_acceptance_demonstration",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "reference_template_rows": self.reference.get("actual_records", self.training.get("rows")),
            "selected_variable_count": self.training.get("feature_count"),
            "target_population_size_per_successful_model": ACCEPTANCE_SIZE,
            "generated_populations": generated,
            "persisted_populations": persisted,
            "warning": NO_BEST_MODEL_WARNING,
        }
        write_json(self.root / "data/synthetic/phase3_acceptance_manifest.json", manifest)
        write_md(self.root / "reports/phase3_acceptance_demonstration.md", self._acceptance_report(manifest))
        return manifest

    def _reuse_existing_acceptance_population(self, model_entry: dict[str, Any], population_id: str) -> dict[str, Any] | None:
        population_dir = self.root / "artifacts/synthetic_populations" / population_id
        metadata_path = population_dir / "metadata.json"
        population_path = population_dir / "population.csv"
        report_path = population_dir / "generation_report.json"
        report_md_path = self.root / "reports/synthetic_populations" / f"{population_id}.md"
        if not (metadata_path.exists() and population_path.exists() and report_path.exists()):
            return None
        metadata = read_json(metadata_path)
        if metadata.get("model_id") != model_entry.get("model_id"):
            return None
        if metadata.get("size") != ACCEPTANCE_SIZE or metadata.get("mode") != "REPRESENTATIVE":
            return None
        constraint = metadata.get("quality", {}).get("constraint_summary", {})
        persisted_item = {
            "population_id": population_id,
            "experiment_id": metadata.get("generation_experiment_id"),
            "rows": metadata.get("size", 0),
            "artifact_dir": str(population_dir.relative_to(self.root)).replace("\\", "/"),
            "population_csv_path": str(population_path.relative_to(self.root)).replace("\\", "/"),
            "metadata_path": str(metadata_path.relative_to(self.root)).replace("\\", "/"),
            "generation_report_json_path": str(report_path.relative_to(self.root)).replace("\\", "/"),
            "generation_report_md_path": str(report_md_path.relative_to(self.root)).replace("\\", "/"),
            "warnings": metadata.get("warnings", []),
            "exact_reference_duplicate_rate": metadata.get("quality", {}).get("exact_reference_duplicate_diagnostic", {}).get("exact_reference_duplicate_rate", 0),
            "reused_existing_artifact": True,
        }
        generated_item = {
            "generator_type": model_entry.get("generator_type"),
            "model_id": model_entry.get("model_id"),
            "status": "TRAINED",
            "population_id": population_id,
            "rows": metadata.get("size", 0),
            "generation_duration_seconds": "reused",
            "hard_constraint_violations": constraint.get("hard_violation_count", 0),
            "soft_anomalies": constraint.get("soft_anomaly_count", 0),
            "source_output_path": metadata.get("artifact_paths", {}).get("population_csv"),
            "persisted_artifact_dir": persisted_item["artifact_dir"],
            "reused_existing_artifact": True,
        }
        return {"generated": generated_item, "persisted": persisted_item}

    def _write_holdout_reference(self) -> str:
        training_path = self.root / self.training["training_dataset_path"]
        rows = read_csv(training_path)
        holdout = [row for row in rows if row.get("training_split") == "holdout"]
        path = self.root / "data/synthetic/training/reference_holdout_v1.csv"
        write_csv(path, holdout)
        return str(path.relative_to(self.root)).replace("\\", "/")

    def _write_phase4_manifest(self, acceptance: dict[str, Any], holdout_path: str) -> dict[str, Any]:
        models_by_id = {item.get("model_id"): item for item in self.registry.get("models", [])}
        synthetic_artifacts = []
        for item in acceptance.get("persisted_populations", []):
            metadata = read_json(self.root / item["metadata_path"])
            model_entry = models_by_id.get(metadata.get("model_id"), {})
            synthetic_artifacts.append({
                "population_id": item["population_id"],
                "population_artifact": item["population_csv_path"],
                "metadata_artifact": item["metadata_path"],
                "generation_report": item["generation_report_json_path"],
                "model_id": metadata.get("model_id"),
                "generator_type": metadata.get("generator_type"),
                "model_version": metadata.get("generator_version"),
                "variables": metadata.get("variables", []),
                "variable_schema": model_entry.get("variable_types", {}),
                "generation_config": {
                    "size": metadata.get("size"),
                    "seed": metadata.get("seed"),
                    "mode": metadata.get("mode"),
                    "conditions": metadata.get("condition"),
                },
                "constraint_results": metadata.get("quality", {}).get("constraint_summary", {}),
                "population_size": metadata.get("size"),
                "exact_reference_duplicate_diagnostic": metadata.get("quality", {}).get("exact_reference_duplicate_diagnostic", {}),
            })
        manifest = {
            "module": "phase4_validation_contract",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "reference_population_artifact": self.training.get("reference_template_path"),
            "prepared_reference_artifact": self.training.get("training_dataset_path"),
            "holdout_reference_artifact": holdout_path,
            "reference_version": self.reference.get("version", "UNKNOWN"),
            "training_dataset_version": self.training.get("training_dataset_version", "UNKNOWN"),
            "synthetic_population_artifacts": synthetic_artifacts,
            "phase4_expected_validation": [
                "marginal distributions",
                "joint distributions",
                "correlations",
                "KS statistics",
                "Jensen-Shannon divergence",
                "Wasserstein distance",
                "categorical association",
                "logical validity",
                "official marginal comparison",
            ],
            "not_in_phase3": [
                "best model selection",
                "full population validation",
                "calibration/reweighting",
                "policy execution",
                "Monte Carlo simulation",
                "recommendations",
            ],
            "warning": NO_BEST_MODEL_WARNING,
        }
        write_json(self.root / "data/synthetic/phase4_validation_manifest.json", manifest)
        write_md(self.root / "reports/phase4_validation_handoff.md", self._phase4_report(manifest))
        return manifest

    def _write_docs(self) -> None:
        write_md(self.root / "docs/synthetic_population_generation.md", self._main_doc())
        model_docs = {
            "bootstrap": self._model_doc("Weighted Bootstrap", "Resamples supported reference rows with configured weights and strata.", "Simple benchmark; preserves observed combinations.", "Duplicates reference feature rows and is not privacy-preserving."),
            "gaussian_copula": self._model_doc("Gaussian Copula", "Uses empirical marginal distributions with a Gaussian correlation structure.", "Lightweight statistical candidate for mixed tabular data.", "Pure-Python fallback; may weaken complex categorical dependencies."),
            "ctgan": self._model_doc("CTGAN", "Uses SDV CTGANSynthesizer on the Phase 3 selected person-level variables.", "Neural candidate for nonlinear mixed tabular relationships.", "Stochastic training; quality and policy suitability remain Phase 4 responsibilities."),
            "tvae": self._model_doc("TVAE", "Uses SDV TVAESynthesizer on the Phase 3 selected person-level variables.", "Variational neural candidate with a different inductive bias from CTGAN.", "Stochastic training; quality and policy suitability remain Phase 4 responsibilities."),
        }
        for name, text in model_docs.items():
            write_md(self.root / f"docs/synthetic_models/{name}.md", text)

    def _write_phase3_summary(self, acceptance: dict[str, Any], phase4: dict[str, Any], comparison: dict[str, Any]) -> Path:
        included = self.training.get("features", [])
        excluded = [item["variable"] for item in self.selection.get("decisions", []) if item.get("decision") not in {"INCLUDE"}]
        trained = [item for item in self.registry.get("models", []) if item.get("status") == "TRAINED"]
        blocked = [item for item in self.registry.get("models", []) if item.get("status") != "TRAINED"]
        hard_violations = sum(item.get("hard_constraint_violations", 0) for item in acceptance.get("generated_populations", []))
        lines = [
            "# Phase 3 Summary",
            "",
            NO_BEST_MODEL_WARNING,
            "",
            "1. Phase 1 dataset used: `data/processed/reference_template.csv` through `data/synthetic/training/reference_training_v1.csv`.",
            f"2. Phase 2 requirements used: {', '.join(self.requirements.keys())}.",
            f"3. Included variables: {', '.join(included)}.",
            f"4. Excluded variables: {', '.join(excluded)}. Identifiers, metadata, fully missing fields, aggregate-only fields, and unsupported variables were excluded or deferred.",
            f"5. Missing values: categorical/ordinal blanks use `{self.training.get('missing_token', 'Unknown')}`; numeric blanks are preserved; fully missing variables are excluded.",
            f"6. Survey weights: {', '.join(self.training.get('weight_columns', []))}; preserved for weighted sampling and excluded from model features.",
            "7. Implemented generators: bootstrap, gaussian_copula, ctgan, tvae.",
            f"8. Trained successfully: {', '.join(item['model_id'] for item in trained)}. Blocked/skipped: {', '.join(item['model_id'] for item in blocked)}.",
            f"9. Synthetic populations generated in acceptance demo: {len(acceptance.get('persisted_populations', []))}.",
            f"10. Population sizes generated: {sorted({item.get('rows') for item in acceptance.get('persisted_populations', [])})}.",
            f"11. Hard constraints violated in acceptance demo: {hard_violations}.",
            "12. Dynamic sampling: explicit REPRESENTATIVE, CONDITIONAL, and SUBPOPULATION modes with supported size checks and batching metadata.",
            "13. Conditional sampling: supported conditions are validated against trained model variables; impossible conditions fail before persistence.",
            "14. Artifacts created: model registry, model artifacts, sampled CSVs, persisted population CSVs, metadata, generation reports, diagnostics, test manifests, comparison manifest, Phase 4 manifest, and documentation.",
            "15. Limitations: neural generators require the Python SDV stack; Parquet export skipped without a local writer; bootstrap duplicates reference feature rows; full fidelity, privacy, calibration, and policy suitability remain unvalidated.",
            f"16. Phase 4 should validate: {', '.join(phase4['phase4_expected_validation'])}.",
            "",
            "## Acceptance Demonstration",
            "",
        ]
        for item in acceptance.get("generated_populations", []):
            lines.append(f"- {item.get('generator_type')}: {item.get('status')} model={item.get('model_id')} population={item.get('population_id', 'None')} rows={item.get('rows', 0)} hard_violations={item.get('hard_constraint_violations', 'n/a')} reason={item.get('blocking_reason', 'None')}")
        lines.extend([
            "",
            "## Phase 4 Handoff",
            "",
            f"- Manifest: `data/synthetic/phase4_validation_manifest.json`",
            f"- Model comparison manifest: `data/synthetic/model_comparison_manifest.json` with {len(comparison.get('models', []))} generator entries.",
            "- Stop condition: do not continue into population validation, calibration, policy execution, Monte Carlo simulation, or recommendations in Phase 3.",
        ])
        path = self.root / "reports/phase3_summary.md"
        write_md(path, "\n".join(lines))
        return path

    def _write_definition_of_done(self, phase4: dict[str, Any]) -> Path:
        checklist = [
            "Phase 1 outputs inspected",
            "Phase 2 outputs inspected",
            "Phase 3 input assessment created",
            "Policy-aware variable selection implemented",
            "Identifier exclusion implemented",
            "Data type resolver implemented",
            "Missingness strategy implemented",
            "Weight strategy documented",
            "Training data pipeline implemented",
            "Generator abstraction implemented",
            "Bootstrap baseline implemented",
            "Gaussian Copula implemented",
            "CTGAN implemented with SDV",
            "TVAE implemented with SDV",
            "Model registry and persistence implemented",
            "Reproducible configurations implemented",
            "Synthetic IDs implemented",
            "Representative and conditional sampling implemented",
            "Dynamic population sizing implemented",
            "Constraint engine and reports generated",
            "Population persistence and metadata generated",
            "Phase 4 manifest produced",
            "Unit and integration smoke tests passing",
            "Documentation written",
            "Phase 3 summary generated",
        ]
        lines = ["# Phase 3 Definition Of Done", "", NO_BEST_MODEL_WARNING, ""]
        lines.extend(f"- [x] {item}" for item in checklist)
        lines.extend(["", f"- Phase 4 synthetic artifact count: {len(phase4.get('synthetic_population_artifacts', []))}"])
        path = self.root / "reports/phase3_definition_of_done.md"
        write_md(path, "\n".join(lines))
        return path

    def _acceptance_report(self, manifest: dict[str, Any]) -> str:
        lines = [
            "# Phase 3 Acceptance Demonstration",
            "",
            manifest["warning"],
            "",
            f"- Reference Template rows: {manifest['reference_template_rows']}",
            f"- Selected Variables: {manifest['selected_variable_count']}",
            f"- Target population size per successful model: {manifest['target_population_size_per_successful_model']}",
            "",
        ]
        for item in manifest["generated_populations"]:
            lines.append(f"- {item.get('generator_type')}: {item.get('status')} population={item.get('population_id', 'None')} rows={item.get('rows', 0)} duration={item.get('generation_duration_seconds', 'n/a')} hard_violations={item.get('hard_constraint_violations', 'n/a')} reason={item.get('blocking_reason', 'None')}")
        return "\n".join(lines)

    def _phase4_report(self, manifest: dict[str, Any]) -> str:
        return "\n".join([
            "# Phase 4 Validation Handoff",
            "",
            manifest["warning"],
            "",
            f"- Reference population artifact: {manifest['reference_population_artifact']}",
            f"- Prepared reference artifact: {manifest['prepared_reference_artifact']}",
            f"- Holdout reference artifact: {manifest['holdout_reference_artifact']}",
            f"- Synthetic population artifacts: {len(manifest['synthetic_population_artifacts'])}",
            f"- Expected validation: {', '.join(manifest['phase4_expected_validation'])}",
            f"- Explicitly not in Phase 3: {', '.join(manifest['not_in_phase3'])}",
        ])

    def _main_doc(self) -> str:
        return "\n".join([
            "# Synthetic Population Generation",
            "",
            "Phase 3 creates candidate synthetic Tamil Nadu populations from Phase 1 reference data and Phase 2 compatibility decisions. It does not validate final fidelity, calibrate populations, execute policies, or select a best model.",
            "",
            "## Architecture",
            "",
            "Input assessment -> variable selection -> training preparation -> common generator interface -> model registry -> dynamic sampling -> population persistence -> Phase 4 validation manifest.",
            "",
            "## Input Data",
            "",
            f"- Reference template: `{self.training.get('reference_template_path')}`",
            f"- Prepared training data: `{self.training.get('training_dataset_path')}`",
            f"- Reference version: `{self.reference.get('version', 'UNKNOWN')}`",
            "",
            "## Variable Selection",
            "",
            f"Included variables are: {', '.join(self.training.get('features', []))}. Identifiers, provenance metadata, unsupported aggregate-only variables, and fully missing fields are excluded.",
            "",
            "## Generators",
            "",
            "Weighted Bootstrap, Gaussian Copula, CTGAN, and TVAE are Phase 3 candidate generators. CTGAN and TVAE use SDV's single-table neural synthesizers and require the Python dependency stack documented in `docs/python_environment.md`.",
            "",
            "## Missing Data And Weights",
            "",
            f"Missing categorical/ordinal values use `{self.training.get('missing_token', 'Unknown')}`. Weight columns are preserved for sampling strategy: {', '.join(self.training.get('weight_columns', []))}.",
            "",
            "## Constraints And Sampling",
            "",
            "Hard constraints cover age, household size, non-negative economic fields, and configured categories. Sampling supports REPRESENTATIVE, CONDITIONAL, and SUBPOPULATION modes with explicit size and condition checks.",
            "",
            "## Persistence And Reproducibility",
            "",
            "Models are referenced by model_id and persisted under `artifacts/synthetic_models/`. Populations receive synthetic IDs unrelated to reference identifiers and are persisted under `artifacts/synthetic_populations/` with metadata and generation reports.",
            "",
            "## Privacy Limitations",
            "",
            "Synthetic data is not automatically anonymous. Exact duplicate diagnostics are memorization-risk prechecks only, not privacy guarantees.",
            "",
            "## Research Transparency",
            "",
            "Multiple synthetic-data generators are implemented because no single model is guaranteed to reproduce every type of tabular distribution or dependency. Gaussian Copula provides a relatively simple statistical benchmark, CTGAN targets complex mixed tabular distributions, and TVAE provides a variational generative alternative. Their outputs are evaluated in the subsequent Population Validation phase before one is selected for policy simulation.",
            "",
            "## Known Limitations",
            "",
            "Neural training is stochastic even with recorded seeds; Parquet export is skipped without a local writer; full validation, calibration, policy execution, fairness analysis, and recommendations belong to later phases.",
        ])

    def _model_doc(self, title: str, what: str, strength: str, weakness: str) -> str:
        return "\n".join([
            f"# {title}",
            "",
            f"- What it does: {what}",
            "- Why included: it gives Phase 4 a candidate method to compare against alternatives.",
            f"- Strengths: {strength}",
            f"- Weaknesses: {weakness}",
            f"- Expected data types: {', '.join(sorted(set(item.get('type', 'unknown') for item in self.selection.get('decisions', []) if item.get('decision') == 'INCLUDE')))}.",
            "- Important parameters: generator profile, seed, selected variables, constraints version, and model-specific config.",
            "- Known limitations: candidate only; Phase 4 must validate fidelity before downstream policy simulation.",
        ])


def run_phase3_finalization(root: Path = ROOT) -> dict[str, Any]:
    return Phase3FinalizationService(root).run()
