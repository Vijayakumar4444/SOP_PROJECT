from __future__ import annotations

from typing import Any
from pathlib import Path

from backend.app.modules.data_foundation.io_utils import write_json, write_md
from backend.app.modules.synthetic_population.assessment import ROOT
from backend.app.modules.synthetic_population.generator_training import load_model_registry, train_candidate_model
from backend.app.modules.synthetic_population.generators.base import SyntheticModelTrainingError
from backend.app.modules.synthetic_population.generators.neural import CTGANGenerator, TVAEGenerator


NEURAL_GENERATORS = {
    "ctgan": CTGANGenerator,
    "tvae": TVAEGenerator,
}


def attempt_neural_generators(root: Path = ROOT) -> dict[str, Any]:
    registry_path = root / "artifacts/synthetic_models/model_registry.json"
    results = []
    for name, cls in NEURAL_GENERATORS.items():
        try:
            trained = train_candidate_model(root, name)
            registry = load_model_registry(registry_path)
            metadata = next(item for item in registry.get("models", []) if item.get("model_id") == trained["model_id"])
        except SyntheticModelTrainingError as exc:
            registry = load_model_registry(registry_path)
            candidates = [item for item in registry.get("models", []) if item.get("generator_type") == name]
            metadata = sorted(candidates, key=lambda item: item.get("created_at", ""), reverse=True)[0] if candidates else {
                "generator_type": name,
                "model_id": f"TN_{name.upper()}_FAILED",
                "model_version": cls.model_version,
                "status": "FAILED",
                "blocking_reason": str(exc),
                "missing_dependencies": cls.missing_dependencies(),
                "training_rows": 0,
                "variables": [],
            }
        results.append(metadata)
    report_path = root / "reports/synthetic_neural_generators_report.md"
    write_neural_report(report_path, results, registry_path, root)
    write_json(root / "data/synthetic/neural_generator_status.json", {"generators": results})
    return {"results": results, "report_path": report_path, "registry_path": registry_path}


def write_neural_report(path: Path, results: list[dict[str, Any]], registry_path: Path, root: Path) -> None:
    lines = [
        "# Synthetic Neural Generators Report", "",
        "- Training stack: SDV single-table neural synthesizers with pandas-backed tabular inputs.",
        "- Unit-test policy: production-size CTGAN/TVAE training is kept out of ordinary unit tests.",
        "",
    ]
    for result in results:
        artifact = result.get("artifact_path") or "None"
        lines.extend([
            f"## {result['generator_type'].upper()}", "",
            f"- Model ID: {result['model_id']}",
            f"- Status: {result['status']}",
            f"- Missing dependencies: {', '.join(result.get('missing_dependencies', [])) or 'None'}",
            f"- Blocking reason: {result.get('blocking_reason', '')}",
            f"- Training rows inspected: {result['training_rows']}",
            f"- Variables: {', '.join(result['variables'])}",
            f"- Artifact path: {artifact}",
            "- Result: trained artifacts are only reported when the SDV fit/save path succeeds.",
            "",
        ])
    lines.append(f"- Registry path: {str(registry_path.relative_to(root)).replace('\\', '/')}")
    write_md(path, "\n".join(lines))
