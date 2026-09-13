from __future__ import annotations

from pathlib import Path
from typing import Any
from datetime import datetime, timezone
import ast
import hashlib
import json

from backend.app.modules.data_foundation.io_utils import write_csv, write_json, write_md
from backend.app.modules.synthetic_population.assessment import ROOT, read_csv, read_json
from backend.app.modules.synthetic_population.generators.bootstrap import BootstrapBaselineGenerator
from backend.app.modules.synthetic_population.generators.base import SyntheticModelTrainingError
from backend.app.modules.synthetic_population.generators.gaussian_copula import GaussianCopulaGenerator
from backend.app.modules.synthetic_population.generators.neural import CTGANGenerator, TVAEGenerator
from backend.app.modules.synthetic_population.generators.registry import GENERATOR_REGISTRY
from backend.app.modules.synthetic_population.training_preparation import prepare_training_data


GENERATOR_CLASSES = {
    "bootstrap": BootstrapBaselineGenerator,
    "gaussian_copula": GaussianCopulaGenerator,
    "ctgan": CTGANGenerator,
    "tvae": TVAEGenerator,
}
GENERATOR_VERSIONS = {
    "bootstrap": "bootstrap_baseline_v1",
    "gaussian_copula": "gaussian_copula_pure_python_v1",
    "ctgan": "ctgan_sdv_v1",
    "tvae": "tvae_sdv_v1",
}
GENERATOR_LABELS = {
    "bootstrap": "RESAMPLED_BASELINE",
    "gaussian_copula": "SYNTHETIC_GAUSSIAN_COPULA_CANDIDATE",
    "ctgan": "SYNTHETIC_CTGAN_CANDIDATE",
    "tvae": "SYNTHETIC_TVAE_CANDIDATE",
}


def read_model_config(root: Path, generator: str) -> dict[str, Any]:
    defaults = {
        "bootstrap": {
            "profile": "development",
            "generator": "bootstrap",
            "version": "bootstrap_baseline_v1",
            "seed": 42,
            "weight_column": "calibrated_reference_weight_gender_ur",
            "stratification_columns": ["district", "urban_rural", "gender"],
            "allow_duplicate_reference_rows": True,
            "label": "RESAMPLED_BASELINE",
        },
        "gaussian_copula": {
            "profile": "development",
            "generator": "gaussian_copula",
            "version": "gaussian_copula_pure_python_v1",
            "seed": 42,
            "jitter": 0.000001,
            "label": "SYNTHETIC_GAUSSIAN_COPULA_CANDIDATE",
        },
        "ctgan": {
            "profile": "development",
            "generator": "ctgan",
            "version": "ctgan_sdv_v1",
            "seed": 42,
            "epochs": 5,
            "batch_size": 500,
            "enable_gpu": False,
            "enforce_min_max_values": True,
            "enforce_rounding": True,
            "label": "SYNTHETIC_CTGAN_CANDIDATE",
        },
        "tvae": {
            "profile": "development",
            "generator": "tvae",
            "version": "tvae_sdv_v1",
            "seed": 42,
            "epochs": 5,
            "batch_size": 500,
            "enable_gpu": False,
            "enforce_min_max_values": True,
            "enforce_rounding": True,
            "label": "SYNTHETIC_TVAE_CANDIDATE",
        },
    }
    config = dict(defaults[generator])
    path = root / f"config/synthetic_population/models/{generator}.yaml"
    if path.exists():
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            if ":" not in line or line.strip().startswith("#"):
                continue
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            config[key] = _parse_config_value(value)
    return config


def _parse_config_value(value: str) -> Any:
    if value == "":
        return ""
    lowered = value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if value.startswith("[") and value.endswith("]"):
        try:
            return ast.literal_eval(value)
        except (SyntaxError, ValueError):
            return [item.strip() for item in value.strip("[]").split(",") if item.strip()]
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value.strip("\"'")


def fingerprint(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:10].upper()


def load_model_registry(path: Path) -> dict[str, Any]:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"models": []}


def upsert_registry(path: Path, entry: dict[str, Any]) -> None:
    registry = load_model_registry(path)
    models = [item for item in registry.get("models", []) if item.get("model_id") != entry["model_id"]]
    if entry.get("status") == "TRAINED":
        models = [
            item for item in models
            if not (
                item.get("generator_type") == entry.get("generator_type")
                and item.get("status") in {"BLOCKED", "FAILED", "TRAINING"}
                and not item.get("artifact_path")
            )
        ]
    models.append(entry)
    registry["models"] = sorted(models, key=lambda item: item["model_id"])
    write_json(path, registry)


def train_candidate_model(root: Path, generator: str) -> dict[str, Any]:
    manifest_path = root / "data/synthetic/training/training_manifest.json"
    if not manifest_path.exists():
        prepare_training_data(root)
    manifest = read_json(manifest_path)
    training_path = root / manifest["training_dataset_path"]
    rows = read_csv(training_path)
    config = read_model_config(root, generator)
    selection = read_json(root / "data/synthetic/variable_selection.json")
    variable_types = {item["variable"]: item["type"] for item in selection.get("decisions", []) if item.get("variable") in manifest["features"]}
    version = GENERATOR_VERSIONS[generator]
    fp = fingerprint({"generator": generator, "training_dataset_version": manifest["training_dataset_version"], "features": manifest["features"], "config": config})
    model_id = f"TN_{generator.upper()}_{fp}"
    artifact_dir = root / "artifacts/synthetic_models" / generator / model_id
    metadata = {
        "model_id": model_id,
        "generator_type": generator,
        "model_version": version,
        "training_dataset_version": manifest["training_dataset_version"],
        "training_dataset_path": manifest["training_dataset_path"],
        "variables": manifest["features"],
        "variable_types": variable_types,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "training_rows": len(rows),
        "status": "TRAINING",
        "artifact_path": str(artifact_dir.relative_to(root)).replace("\\", "/"),
        "config": config,
    }
    model = GENERATOR_CLASSES[generator]()
    registry_path = root / "artifacts/synthetic_models/model_registry.json"
    upsert_registry(registry_path, metadata)
    try:
        model.fit(rows, metadata, config)
        metadata["status"] = "TRAINED"
        metadata["artifact_path"] = str(artifact_dir.relative_to(root)).replace("\\", "/")
        metadata["blocking_reason"] = ""
        metadata["missing_dependencies"] = []
        model.save(artifact_dir)
    except Exception as exc:
        missing = model.missing_dependencies() if hasattr(model, "missing_dependencies") else []
        metadata["status"] = "BLOCKED" if missing else "FAILED"
        metadata["artifact_path"] = ""
        metadata["blocking_reason"] = str(exc)
        if missing:
            metadata["missing_dependencies"] = missing
        upsert_registry(registry_path, metadata)
        raise
    upsert_registry(registry_path, metadata)
    preview = model.sample(size=25, seed=config["seed"])
    preview_path = root / f"data/synthetic/{generator}_preview_25.csv"
    write_csv(preview_path, preview)
    return {"model_id": model_id, "artifact_dir": artifact_dir, "registry_path": registry_path, "preview_path": preview_path, "summary": model.get_training_summary()}


def train_bootstrap_baseline(root: Path = ROOT) -> dict[str, Any]:
    result = train_candidate_model(root, "bootstrap")
    write_generator_interface_report(root, {"bootstrap": result})
    return result


def train_gaussian_copula(root: Path = ROOT) -> dict[str, Any]:
    result = train_candidate_model(root, "gaussian_copula")
    write_generator_interface_report(root, {"gaussian_copula": result})
    return result


def train_available_generators(root: Path = ROOT) -> dict[str, dict[str, Any]]:
    results = {name: train_candidate_model(root, name) for name in GENERATOR_CLASSES}
    write_generator_interface_report(root, results)
    return results


def write_generator_interface_report(root: Path, results: dict[str, dict[str, Any]]) -> Path:
    report_path = root / "reports/synthetic_generator_interface_report.md"
    registry_path = root / "artifacts/synthetic_models/model_registry.json"
    lines = [
        "# Synthetic Generator Interface Report", "",
        "## Implemented Contract", "",
        "- fit(data, metadata, config)",
        "- sample(size, seed=None, conditions=None)",
        "- save(destination)",
        "- load(source)",
        "- get_model_metadata()",
        "- get_training_summary()",
        "", "## Generator Registry", "",
    ]
    existing_registry = load_model_registry(root / "artifacts/synthetic_models/model_registry.json")
    latest_status = {item.get("generator_type"): item.get("status") for item in existing_registry.get("models", [])}
    for name in GENERATOR_REGISTRY:
        status = latest_status.get(name) or ("IMPLEMENTED" if name in GENERATOR_CLASSES else "DEPENDENCY_GATED")
        reason = "Available and trained through the shared interface." if name in GENERATOR_CLASSES else "No shared interface implementation is available."
        lines.append(f"- {name}: {status}. {reason}")
    lines.extend(["", "## Trained Candidate Models", ""])
    for name, result in sorted(results.items()):
        summary = result["summary"]
        lines.extend([
            f"### {name}", "",
            f"- Model ID: {result['model_id']}",
            "- Status: TRAINED",
            f"- Training rows: {summary.get('training_rows')}",
            f"- Variables: {', '.join(summary.get('variables', []))}",
            f"- Label: {summary.get('label', GENERATOR_LABELS.get(name, 'SYNTHETIC_CANDIDATE'))}",
            f"- Warning: {summary.get('warning', 'Full statistical validation belongs to Phase 4.')}",
            f"- Artifact path: {str(result['artifact_dir'].relative_to(root)).replace('\\', '/')}",
            f"- Preview path: {str(result['preview_path'].relative_to(root)).replace('\\', '/')}",
            "",
        ])
    lines.append(f"- Registry path: {str(registry_path.relative_to(root)).replace('\\', '/')}")
    write_md(report_path, "\n".join(lines))
    return report_path



