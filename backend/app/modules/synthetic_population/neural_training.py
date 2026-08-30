from __future__ import annotations

from pathlib import Path
from typing import Any
from datetime import datetime, timezone
import json

from backend.app.modules.data_foundation.io_utils import write_json, write_md
from backend.app.modules.synthetic_population.assessment import ROOT, read_csv, read_json
from backend.app.modules.synthetic_population.generator_training import load_model_registry, upsert_registry
from backend.app.modules.synthetic_population.generators.base import SyntheticModelTrainingError
from backend.app.modules.synthetic_population.generators.neural import CTGANGenerator, TVAEGenerator
from backend.app.modules.synthetic_population.training_preparation import prepare_training_data


NEURAL_GENERATORS = {
    "ctgan": CTGANGenerator,
    "tvae": TVAEGenerator,
}


def attempt_neural_generators(root: Path = ROOT) -> dict[str, Any]:
    manifest_path = root / "data/synthetic/training/training_manifest.json"
    if not manifest_path.exists():
        prepare_training_data(root)
    manifest = read_json(manifest_path)
    rows = read_csv(root / manifest["training_dataset_path"])
    registry_path = root / "artifacts/synthetic_models/model_registry.json"
    results = []
    for name, cls in NEURAL_GENERATORS.items():
        generator = cls()
        model_id = f"TN_{name.upper()}_BLOCKED_DEPENDENCIES"
        config = read_simple_config(root / f"config/synthetic_population/models/{name}.yaml")
        metadata = {
            "model_id": model_id,
            "generator_type": name,
            "model_version": generator.model_version,
            "training_dataset_version": manifest["training_dataset_version"],
            "training_dataset_path": manifest["training_dataset_path"],
            "variables": manifest["features"],
            "variable_types": manifest.get("variable_types", {}),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "training_rows": len(rows),
            "status": "BLOCKED",
            "artifact_path": "",
            "config": config,
        }
        try:
            generator.fit(rows, metadata, config)
            metadata["status"] = "TRAINED"
            metadata["blocking_reason"] = ""
        except SyntheticModelTrainingError as exc:
            metadata["status"] = "BLOCKED"
            metadata["blocking_reason"] = str(exc)
            metadata["missing_dependencies"] = generator.missing_dependencies()
        upsert_registry(registry_path, metadata)
        results.append(metadata)
    report_path = root / "reports/synthetic_neural_generators_report.md"
    write_neural_report(report_path, results, registry_path, root)
    write_json(root / "data/synthetic/neural_generator_status.json", {"generators": results})
    return {"results": results, "report_path": report_path, "registry_path": registry_path}


def read_simple_config(path: Path) -> dict[str, Any]:
    config: dict[str, Any] = {}
    if not path.exists():
        return config
    for line in path.read_text(encoding="utf-8").splitlines():
        if ":" not in line or line.strip().startswith("#"):
            continue
        key, value = line.split(":", 1)
        config[key.strip()] = value.strip()
    return config


def write_neural_report(path: Path, results: list[dict[str, Any]], registry_path: Path, root: Path) -> None:
    lines = [
        "# Synthetic Neural Generators Report", "",
        "- Dependency action: no packages were installed silently.",
        "- Expected optional stack: SDV/pandas and their model dependencies.",
        "- Unit-test policy: expensive CTGAN/TVAE training must not run in normal tests.",
        "",
    ]
    for result in results:
        lines.extend([
            f"## {result['generator_type'].upper()}", "",
            f"- Model ID: {result['model_id']}",
            f"- Status: {result['status']}",
            f"- Missing dependencies: {', '.join(result.get('missing_dependencies', [])) or 'None'}",
            f"- Blocking reason: {result.get('blocking_reason', '')}",
            f"- Training rows inspected: {result['training_rows']}",
            f"- Variables: {', '.join(result['variables'])}",
            "- Result: no model artifact or synthetic population was fabricated.",
            "",
        ])
    lines.append(f"- Registry path: {str(registry_path.relative_to(root)).replace('\\', '/')}")
    write_md(path, "\n".join(lines))
