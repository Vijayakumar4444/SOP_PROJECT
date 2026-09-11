from __future__ import annotations

from pathlib import Path
from typing import Any
from datetime import datetime, timezone
import hashlib
import json
import time

from backend.app.modules.data_foundation.io_utils import write_json, write_md
from backend.app.modules.synthetic_population.assessment import ROOT, read_json
from backend.app.modules.synthetic_population.constraints import ConstraintEngine
from backend.app.modules.synthetic_population.randomness import seed_everything
from backend.app.modules.synthetic_population.sampling_service import DynamicSamplingService


DIAGNOSTIC_SIZE = 1000
DIAGNOSTIC_SEED = 314159
PRIVACY_WARNING = (
    "Synthetic data is not automatically anonymous. Phase 3 exact-duplicate checks are memorization-risk prechecks only, "
    "not a formal privacy guarantee or disclosure-risk evaluation."
)


class OperationalDiagnosticsService:
    def __init__(self, root: Path = ROOT):
        self.root = root
        self.sampling_service = DynamicSamplingService(root)

    def run(self) -> dict[str, Any]:
        persistence = read_json(self.root / "data/synthetic/population_persistence_manifest.json")
        registry = read_json(self.root / "artifacts/synthetic_models/model_registry.json")
        trained_models = [item for item in registry.get("models", []) if item.get("status") == "TRAINED"]
        diagnostics = [self._diagnose_model(item, persistence) for item in trained_models]
        result = {
            "module": "phase3_operational_diagnostics",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "diagnostic_size": DIAGNOSTIC_SIZE,
            "diagnostic_seed": DIAGNOSTIC_SEED,
            "randomness": seed_everything(DIAGNOSTIC_SEED),
            "gpu": {
                "required": False,
                "detected": False,
                "policy": "CPU-compatible generation is required; Phase 3 does not assume GPU availability.",
            },
            "privacy_warning": PRIVACY_WARNING,
            "models": diagnostics,
        }
        write_json(self.root / "data/synthetic/diagnostics/phase3_operational_diagnostics.json", result)
        write_md(self.root / "reports/synthetic_operational_diagnostics_report.md", self._report(result))
        return result

    def _diagnose_model(self, model_entry: dict[str, Any], persistence: dict[str, Any]) -> dict[str, Any]:
        model = self.sampling_service._load_model(model_entry)
        started = time.perf_counter()
        first = model.sample(DIAGNOSTIC_SIZE, seed=DIAGNOSTIC_SEED)
        duration = max(time.perf_counter() - started, 0.000001)
        second = model.sample(DIAGNOSTIC_SIZE, seed=DIAGNOSTIC_SEED)
        reproducible = self._fingerprint_rows(first) == self._fingerprint_rows(second)
        constraint_summary = ConstraintEngine().validate_rows(first)
        persisted = [item for item in persistence.get("populations", []) if item.get("model_id") == model_entry.get("model_id")]
        if not persisted:
            persisted = [item for item in persistence.get("populations", []) if model_entry.get("generator_type", "").upper() in item.get("population_id", "")]
        artifact_path = self.root / model_entry.get("artifact_path", "")
        persisted_sizes = [self._path_size(self.root / item["artifact_dir"]) for item in persisted if item.get("artifact_dir")]
        duplicate_rates = [item.get("exact_reference_duplicate_rate", 0) for item in persisted]
        return {
            "model_id": model_entry.get("model_id"),
            "generator_type": model_entry.get("generator_type"),
            "model_version": model_entry.get("model_version"),
            "status": model_entry.get("status"),
            "reproducibility": {
                "same_model_size_seed_reproducible": reproducible,
                "row_fingerprint": self._fingerprint_rows(first),
                "limitations": "Pure Python bootstrap and Gaussian copula paths are deterministic for the same seed in this environment.",
            },
            "performance": {
                "generation_duration_seconds": round(duration, 6),
                "rows_per_second": round(DIAGNOSTIC_SIZE / duration, 2),
                "model_artifact_bytes": self._path_size(artifact_path),
                "persisted_population_artifact_bytes": sum(persisted_sizes),
                "peak_memory": "not_measured_in_portable_phase3_runner",
            },
            "constraint_summary": constraint_summary,
            "memorization_risk_precheck": {
                "exact_reference_duplicate_rates_from_persisted_outputs": duplicate_rates,
                "warning": PRIVACY_WARNING,
            },
            "artifact_safety": {
                "client_reference": "model_id",
                "exposes_executable_model_object": False,
                "backend_artifact_path_recorded_for_internal_use": bool(model_entry.get("artifact_path")),
            },
        }

    def _fingerprint_rows(self, rows: list[dict[str, Any]]) -> str:
        raw = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _path_size(self, path: Path) -> int:
        if not path.exists():
            return 0
        if path.is_file():
            return path.stat().st_size
        return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())

    def _report(self, result: dict[str, Any]) -> str:
        lines = [
            "# Synthetic Operational Diagnostics Report",
            "",
            result["privacy_warning"],
            "",
            f"- Diagnostic size: {result['diagnostic_size']}",
            f"- Diagnostic seed: {result['diagnostic_seed']}",
            f"- Randomness: {json.dumps(result['randomness'], sort_keys=True)}",
            f"- GPU policy: {result['gpu']['policy']}",
            "",
            "## Models",
            "",
        ]
        for item in result["models"]:
            perf = item["performance"]
            repro = item["reproducibility"]
            mem = item["memorization_risk_precheck"]
            lines.extend([
                f"### {item['model_id']}",
                "",
                f"- Generator: {item['generator_type']}",
                f"- Reproducible for same seed: {repro['same_model_size_seed_reproducible']}",
                f"- Rows per second: {perf['rows_per_second']}",
                f"- Generation duration seconds: {perf['generation_duration_seconds']}",
                f"- Model artifact bytes: {perf['model_artifact_bytes']}",
                f"- Persisted population artifact bytes: {perf['persisted_population_artifact_bytes']}",
                f"- Hard constraint violations: {item['constraint_summary']['hard_violation_count']}",
                f"- Soft anomalies: {item['constraint_summary']['soft_anomaly_count']}",
                f"- Exact duplicate rates from persisted outputs: {mem['exact_reference_duplicate_rates_from_persisted_outputs']}",
                "",
            ])
        return "\n".join(lines)


def run_operational_diagnostics(root: Path = ROOT) -> dict[str, Any]:
    return OperationalDiagnosticsService(root).run()
