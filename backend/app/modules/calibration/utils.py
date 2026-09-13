from __future__ import annotations

from hashlib import sha256
from math import isfinite
from pathlib import Path
from typing import Any
import json

import yaml

from backend.app.modules.data_foundation.io_utils import read_csv, write_csv, write_json, write_md


DEFAULT_CONFIG: dict[str, Any] = {
    "method": "raking",
    "max_iterations": 50,
    "tolerance": 0.0005,
    "weight_bounds": {"min": 0.2, "max": 8.0},
    "trimming": {"enabled": True, "method": "absolute"},
    "normalization": {"mode": "sample_size"},
    "quality_gates": {
        "max_marginal_error": 0.02,
        "min_ess_ratio": 0.80,
        "max_weight": 8.0,
        "min_weight": 0.2,
        "require_convergence": True,
        "max_unresolved_targets": 0,
    },
    "calibration_variables": ["gender", "urban_rural", "social_group"],
    "target_sum_tolerance": 0.005,
    "minimum_cell_count": 1,
}


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_yaml_config(path: Path) -> dict[str, Any]:
    config = dict(DEFAULT_CONFIG)
    if not path.exists():
        return config
    loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return deep_merge(config, loaded)


def deep_merge(base: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def rounded(value: float | None, digits: int = 6) -> float | None:
    return round(value, digits) if value is not None else None


def to_float(value: Any, default: float | None = None) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result if isfinite(result) else default


def stable_hash(payload: Any, length: int = 10) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return sha256(raw.encode("utf-8")).hexdigest()[:length].upper()


def file_sha256(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative_path(root: Path, path: Path) -> str:
    return str(path.relative_to(root)).replace("\\", "/")


__all__ = [
    "DEFAULT_CONFIG",
    "file_sha256",
    "load_yaml_config",
    "read_csv",
    "read_json",
    "relative_path",
    "rounded",
    "stable_hash",
    "to_float",
    "write_csv",
    "write_json",
    "write_md",
]
