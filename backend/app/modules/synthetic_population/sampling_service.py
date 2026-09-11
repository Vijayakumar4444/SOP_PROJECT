from __future__ import annotations

from pathlib import Path
from typing import Any
from datetime import datetime, timezone
import csv
import hashlib
import json

from backend.app.modules.data_foundation.io_utils import write_csv, write_json, write_md
from backend.app.modules.synthetic_population.assessment import ROOT, read_json
from backend.app.modules.synthetic_population.constraints import ConstraintEngine
from backend.app.modules.synthetic_population.generators.base import SyntheticGenerationError
from backend.app.modules.synthetic_population.generators.bootstrap import BootstrapBaselineGenerator
from backend.app.modules.synthetic_population.generators.gaussian_copula import GaussianCopulaGenerator


SUPPORTED_SIZES = {1000, 5000, 10000, 12000, 50000, 100000}
SUPPORTED_MODES = {"REPRESENTATIVE", "CONDITIONAL", "SUBPOPULATION"}
DEFAULT_BATCH_SIZE = 50000
GENERATOR_LOADERS = {
    "bootstrap": BootstrapBaselineGenerator,
    "gaussian_copula": GaussianCopulaGenerator,
}


class ConditionalSamplingError(Exception):
    code = "CONDITIONAL_SAMPLING_ERROR"


class ModelArtifactNotFoundError(Exception):
    code = "MODEL_ARTIFACT_NOT_FOUND"


class DynamicSamplingService:
    def __init__(self, root: Path = ROOT):
        self.root = root
        self.registry_path = root / "artifacts/synthetic_models/model_registry.json"
        self.registry = read_json(self.registry_path)

    def generate_population(
        self,
        model_id: str | None = None,
        generator: str | None = None,
        size: int = 1000,
        seed: int = 42,
        mode: str = "REPRESENTATIVE",
        conditions: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        mode = mode.upper()
        conditions = conditions or {}
        self._validate_request(size, mode, conditions)
        model_entry = self._resolve_model(model_id, generator)
        model = self._load_model(model_entry)
        if mode == "REPRESENTATIVE" and conditions:
            raise ConditionalSamplingError("REPRESENTATIVE mode must not include conditions; use CONDITIONAL or SUBPOPULATION.")
        if mode in {"CONDITIONAL", "SUBPOPULATION"} and not conditions:
            raise ConditionalSamplingError(f"{mode} mode requires at least one condition.")
        self._validate_condition_fields(model_entry, conditions)
        batches = self._batches(size)
        rows: list[dict[str, Any]] = []
        started = datetime.now(timezone.utc)
        for batch_index, batch_size in enumerate(batches):
            batch_seed = seed + batch_index
            rows.extend(model.sample(batch_size, seed=batch_seed, conditions=conditions if mode != "REPRESENTATIVE" else None))
        constraint_summary = ConstraintEngine().validate_rows(rows)
        finished = datetime.now(timezone.utc)
        population_id = self._population_id(model_entry, mode, size, seed, conditions)
        output_dir = self.root / "data/synthetic/sampling"
        output_path = output_dir / f"{population_id}.csv"
        report_path = self.root / "reports/synthetic_dynamic_sampling_report.md"
        metadata = {
            "population_id": population_id,
            "synthetic": True,
            "mode": mode,
            "model_id": model_entry["model_id"],
            "generator_type": model_entry["generator_type"],
            "model_version": model_entry.get("model_version", ""),
            "requested_count": size,
            "generated_count": len(rows),
            "accepted_count": len(rows),
            "acceptance_rate": 100.0 if size else 0,
            "seed": seed,
            "conditions": conditions,
            "batch_size": DEFAULT_BATCH_SIZE,
            "batch_count": len(batches),
            "generated_at": finished.isoformat(),
            "generation_duration_seconds": round((finished - started).total_seconds(), 4),
            "constraint_summary": constraint_summary,
            "output_path": str(output_path.relative_to(self.root)).replace("\\", "/"),
        }
        write_csv(output_path, rows)
        write_json(output_dir / f"{population_id}_metadata.json", metadata)
        self._write_report(report_path, metadata)
        return {"rows": rows, "metadata": metadata, "output_path": output_path, "report_path": report_path}

    def _validate_request(self, size: int, mode: str, conditions: dict[str, Any]) -> None:
        if size not in SUPPORTED_SIZES:
            raise SyntheticGenerationError(f"Unsupported size {size}. Supported sizes: {sorted(SUPPORTED_SIZES)}")
        if mode not in SUPPORTED_MODES:
            raise SyntheticGenerationError(f"Unsupported generation mode {mode}. Supported modes: {sorted(SUPPORTED_MODES)}")
        for field, value in conditions.items():
            if value in (None, ""):
                raise ConditionalSamplingError(f"Condition {field} has an empty value.")

    def _resolve_model(self, model_id: str | None, generator: str | None) -> dict[str, Any]:
        models = self.registry.get("models", [])
        if model_id:
            matches = [item for item in models if item.get("model_id") == model_id]
        else:
            matches = [item for item in models if item.get("generator_type") == generator and item.get("status") == "TRAINED"]
        if not matches:
            raise ModelArtifactNotFoundError(f"No trained model found for model_id={model_id!r}, generator={generator!r}.")
        matches = sorted(matches, key=lambda item: item.get("created_at", ""), reverse=True)
        entry = matches[0]
        if entry.get("status") != "TRAINED":
            raise ModelArtifactNotFoundError(f"Model {entry.get('model_id')} is not trained; status={entry.get('status')}.")
        return entry

    def _load_model(self, entry: dict[str, Any]):
        generator_type = entry.get("generator_type")
        loader = GENERATOR_LOADERS.get(generator_type)
        if not loader:
            raise ModelArtifactNotFoundError(f"No loader available for generator {generator_type}.")
        artifact_path = entry.get("artifact_path")
        if not artifact_path:
            raise ModelArtifactNotFoundError(f"Model {entry.get('model_id')} has no artifact path.")
        full_path = self.root / artifact_path
        if not full_path.exists():
            raise ModelArtifactNotFoundError(f"Model artifact path does not exist: {artifact_path}")
        return loader.load(full_path)

    def _validate_condition_fields(self, entry: dict[str, Any], conditions: dict[str, Any]) -> None:
        variables = set(entry.get("variables", []))
        unsupported = sorted(set(conditions) - variables)
        if unsupported:
            raise ConditionalSamplingError(f"Unsupported condition fields for model {entry.get('model_id')}: {', '.join(unsupported)}")

    def _batches(self, size: int) -> list[int]:
        batches = []
        remaining = size
        while remaining > 0:
            batch = min(DEFAULT_BATCH_SIZE, remaining)
            batches.append(batch)
            remaining -= batch
        return batches

    def _population_id(self, entry: dict[str, Any], mode: str, size: int, seed: int, conditions: dict[str, Any]) -> str:
        if not conditions:
            condition_token = "NONE"
        else:
            digest = hashlib.sha256(json.dumps(conditions, sort_keys=True).encode("utf-8")).hexdigest()[:8].upper()
            condition_token = f"COND{digest}"
        return f"SYNPOP-{entry['generator_type'].upper()}-{mode}-{size}-{seed}-{condition_token}"

    def _write_report(self, path: Path, metadata: dict[str, Any]) -> None:
        constraint = metadata["constraint_summary"]
        lines = [
            "# Synthetic Dynamic Sampling Report", "",
            f"- Population ID: {metadata['population_id']}",
            f"- Model ID: {metadata['model_id']}",
            f"- Generator: {metadata['generator_type']}",
            f"- Mode: {metadata['mode']}",
            f"- Requested count: {metadata['requested_count']}",
            f"- Generated count: {metadata['generated_count']}",
            f"- Accepted count: {metadata['accepted_count']}",
            f"- Acceptance rate: {metadata['acceptance_rate']}%",
            f"- Seed: {metadata['seed']}",
            f"- Conditions: {json.dumps(metadata['conditions'], sort_keys=True)}",
            f"- Batch count: {metadata['batch_count']}",
            f"- Batch size: {metadata['batch_size']}",
            f"- Hard constraint violations: {constraint['hard_violation_count']}",
            f"- Soft anomalies: {constraint['soft_anomaly_count']}",
            f"- Output path: {metadata['output_path']}",
            "- Note: generated outputs are candidate synthetic populations only; Phase 4 must validate fidelity before policy use.",
        ]
        write_md(path, "\n".join(lines))



def run_dynamic_sampling_demo(root: Path = ROOT) -> dict[str, Any]:
    service = DynamicSamplingService(root)
    representative = service.generate_population(generator="bootstrap", size=1000, seed=42, mode="REPRESENTATIVE")
    conditional = service.generate_population(generator="bootstrap", size=1000, seed=43, mode="CONDITIONAL", conditions={"urban_rural": "Rural"})
    gaussian = service.generate_population(generator="gaussian_copula", size=1000, seed=44, mode="REPRESENTATIVE")
    manifest = {
        "module": "phase3_dynamic_sampling",
        "supported_population_sizes": sorted(SUPPORTED_SIZES),
        "supported_modes": sorted(SUPPORTED_MODES),
        "demo_populations": [representative["metadata"], conditional["metadata"], gaussian["metadata"]],
    }
    write_json(root / "data/synthetic/sampling/dynamic_sampling_manifest.json", manifest)
    write_dynamic_sampling_summary(root / "reports/synthetic_dynamic_sampling_report.md", manifest)
    return manifest


def write_dynamic_sampling_summary(path: Path, manifest: dict[str, Any]) -> None:
    lines = [
        "# Synthetic Dynamic Sampling Report", "",
        f"- Supported population sizes: {manifest['supported_population_sizes']}",
        f"- Supported modes: {manifest['supported_modes']}",
        "- Note: generated outputs are candidate synthetic populations only; Phase 4 must validate fidelity before policy use.",
        "", "## Demo Populations", "",
    ]
    for item in manifest["demo_populations"]:
        constraint = item["constraint_summary"]
        lines.extend([
            f"### {item['population_id']}", "",
            f"- Model ID: {item['model_id']}",
            f"- Generator: {item['generator_type']}",
            f"- Mode: {item['mode']}",
            f"- Requested / generated / accepted: {item['requested_count']} / {item['generated_count']} / {item['accepted_count']}",
            f"- Acceptance rate: {item['acceptance_rate']}%",
            f"- Seed: {item['seed']}",
            f"- Conditions: {json.dumps(item['conditions'], sort_keys=True)}",
            f"- Batch count: {item['batch_count']} with max batch size {item['batch_size']}",
            f"- Hard constraint violations: {constraint['hard_violation_count']}",
            f"- Soft anomalies: {constraint['soft_anomaly_count']}",
            f"- Output path: {item['output_path']}",
            "",
        ])
    write_md(path, "\n".join(lines))
