from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.app.modules.calibration.utils import relative_path, write_json


def write_phase6_handoff(
    root: Path,
    calibration_id: str,
    source_handoff: dict[str, Any],
    artifact_paths: dict[str, Path],
    calibration_result: dict[str, Any],
    diagnostics: dict[str, Any],
    target_sets: list[dict[str, Any]],
    config_path: Path,
    config_digest: str,
    final_status: str,
    warnings: list[str],
) -> dict[str, Any]:
    payload = {
        "phase": 5,
        "status": final_status,
        "calibration_id": calibration_id,
        "source_population_id": source_handoff["population_id"],
        "source_model_id": source_handoff["model_id"],
        "source_generator_type": source_handoff.get("generator_type"),
        "phase4_quality_score": source_handoff.get("quality_score"),
        "calibrated_population_path": relative_path(root, artifact_paths["population"]),
        "policy_weight_column": "calibration_weight",
        "expansion_weight_column": "population_weight",
        "method": calibration_result["method"],
        "calibration_status": calibration_result["status"],
        "variables": [target["variable"] for target in target_sets],
        "official_target_metadata": target_sets,
        "effective_sample_size": diagnostics["effective_sample_size"],
        "ess_ratio": diagnostics["ess_ratio"],
        "diagnostics_summary": diagnostics,
        "warnings": warnings,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "reproducibility": {
            "config_path": relative_path(root, config_path),
            "config_digest": config_digest,
            "metadata_path": relative_path(root, artifact_paths["metadata"]),
            "weight_diagnostics_path": relative_path(root, artifact_paths["weight_diagnostics"]),
        },
    }
    write_json(root / "data/synthetic/phase6_policy_engine_handoff.json", payload)
    return payload
