from __future__ import annotations

from pathlib import Path
from typing import Any
from datetime import datetime, timezone

from backend.app.modules.data_foundation.io_utils import write_json, write_md
from backend.app.modules.synthetic_population.assessment import ROOT, read_json
from backend.app.modules.synthetic_population.population_persistence import run_population_persistence


def build_model_comparison_manifest(root: Path = ROOT) -> dict[str, Any]:
    population_manifest_path = root / "data/synthetic/population_persistence_manifest.json"
    if not population_manifest_path.exists():
        run_population_persistence(root)
    populations = read_json(population_manifest_path).get("populations", [])
    acceptance_path = root / "data/synthetic/phase3_acceptance_manifest.json"
    if acceptance_path.exists():
        populations.extend(read_json(acceptance_path).get("persisted_populations", []))
    registry = read_json(root / "artifacts/synthetic_models/model_registry.json")
    reference = read_json(root / "data/reference/template_metadata.json")
    training = read_json(root / "data/synthetic/training/training_manifest.json")
    population_size = max((item.get("rows", 0) for item in populations), default=0)
    models = []
    for model in registry.get("models", []):
        matches = [item for item in populations if item.get("population_id", "").find(model.get("generator_type", "").upper()) >= 0]
        models.append({
            "generator": model.get("generator_type"),
            "model_id": model.get("model_id"),
            "model_version": model.get("model_version"),
            "status": model.get("status"),
            "population_ids": [item["population_id"] for item in matches],
            "population_artifacts": [item["population_csv_path"] for item in matches],
            "blocking_reason": model.get("blocking_reason", ""),
            "validation_phase_note": "Candidate only; Phase 4 must compare fidelity and choose suitability.",
        })
    manifest = {
        "module": "phase3_model_comparison_manifest",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "reference_version": reference.get("version", "UNKNOWN"),
        "training_dataset_version": training.get("training_dataset_version", "UNKNOWN"),
        "population_size": population_size,
        "models": models,
        "phase4_consumption_note": "Do not select a best model from this manifest. It exists so Phase 4 can compare REFERENCE vs BOOTSTRAP vs GAUSSIAN COPULA vs CTGAN vs TVAE.",
    }
    write_json(root / "data/synthetic/model_comparison_manifest.json", manifest)
    write_md(root / "reports/synthetic_model_comparison_manifest_report.md", _report(manifest))
    return manifest


def _report(manifest: dict[str, Any]) -> str:
    lines = [
        "# Synthetic Model Comparison Manifest Report",
        "",
        manifest["phase4_consumption_note"],
        "",
        f"- Reference version: {manifest['reference_version']}",
        f"- Training dataset version: {manifest['training_dataset_version']}",
        f"- Population size: {manifest['population_size']}",
        "",
        "## Candidates",
        "",
    ]
    for item in manifest["models"]:
        lines.extend([
            f"### {item['generator']}",
            "",
            f"- Model ID: {item['model_id']}",
            f"- Status: {item['status']}",
            f"- Population IDs: {item['population_ids'] if item['population_ids'] else 'None'}",
            f"- Blocking reason: {item['blocking_reason'] or 'None'}",
            "",
        ])
    return "\n".join(lines)


def run_model_comparison_manifest(root: Path = ROOT) -> dict[str, Any]:
    return build_model_comparison_manifest(root)
