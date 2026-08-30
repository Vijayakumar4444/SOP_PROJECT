from __future__ import annotations

from pathlib import Path
from typing import Any
import csv
import hashlib
import json

from backend.app.modules.data_foundation.io_utils import write_csv, write_json, write_md
from backend.app.modules.synthetic_population.assessment import ROOT, actual_reference_path, read_csv, read_json
from backend.app.modules.synthetic_population.variable_selection import write_variable_selection


TRAINING_VERSION = "phase3_training_v1"
SPLIT_RATIOS = {"train": 0.70, "validation": 0.15, "holdout": 0.15}
WEIGHT_COLUMNS = ["survey_weight", "normalized_reference_weight", "calibrated_reference_weight_gender_ur"]
MISSING_TOKEN = "Unknown"


def stable_bucket(row: dict[str, str], seed: int) -> float:
    key = "|".join([str(seed), row.get("source_record_id", ""), row.get("reference_person_id", "")])
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]
    return int(digest, 16) / float(16 ** 12)


def split_name(bucket: float) -> str:
    if bucket < SPLIT_RATIOS["train"]:
        return "train"
    if bucket < SPLIT_RATIOS["train"] + SPLIT_RATIOS["validation"]:
        return "validation"
    return "holdout"


def normalize_value(value: str, variable_type: str) -> Any:
    if value in (None, ""):
        if variable_type in {"categorical", "ordinal"}:
            return MISSING_TOKEN
        return ""
    if variable_type == "integer":
        try:
            return int(float(value))
        except ValueError:
            return ""
    if variable_type == "continuous":
        try:
            return float(value)
        except ValueError:
            return ""
    return value


def load_selection(root: Path) -> dict[str, Any]:
    path = root / "data/synthetic/variable_selection.json"
    if not path.exists():
        write_variable_selection(root)
    return read_json(path)


def missing_strategy(decision: dict[str, Any]) -> dict[str, Any]:
    name = decision["variable"]
    variable_type = decision["type"]
    missing_pct = float(decision["missing_percentage"])
    if decision["decision"] == "INCLUDE":
        if missing_pct == 0:
            strategy = "NONE_REQUIRED"
            reason = "No missing values in selected reference feature."
        elif variable_type in {"categorical", "ordinal"}:
            strategy = "EXPLICIT_UNKNOWN_CATEGORY"
            reason = "Preserve missingness as an explicit category instead of mode imputation."
        else:
            strategy = "LEAVE_NULL_FOR_MODEL_PREPARATION"
            reason = "Do not mean-impute numeric values during Phase 3 preparation."
    elif decision["decision"] == "EXCLUDE_FROM_FEATURES":
        strategy = "PRESERVE_AS_WEIGHT_METADATA"
        reason = "Available for weighted bootstrap/training strategy, not as a model feature."
    elif decision["decision"] == "DERIVE_AFTER_GENERATION":
        strategy = "DERIVE_AFTER_GENERATION"
        reason = "Avoid learned inconsistency with base variables."
    elif decision["decision"] == "ATTACH_AFTER_GENERATION":
        strategy = "ATTACH_AFTER_GENERATION"
        reason = "Deterministic Tamil Nadu-only metadata/value."
    else:
        strategy = "EXCLUDE_FROM_TRAINING"
        reason = decision["reason"]
    return {"variable": name, "strategy": strategy, "reason": reason, "missing_percentage": missing_pct}


def prepare_training_data(root: Path = ROOT, seed: int = 42) -> dict[str, Any]:
    selection = load_selection(root)
    decisions = selection["decisions"]
    included = selection["included_features"]
    decision_by_name = {item["variable"]: item for item in decisions}
    reference_rows = read_csv(actual_reference_path(root))
    prepared = []
    split_counts = {"train": 0, "validation": 0, "holdout": 0}

    for row in reference_rows:
        split = split_name(stable_bucket(row, seed))
        split_counts[split] += 1
        out = {name: normalize_value(row.get(name, ""), decision_by_name[name]["type"]) for name in included}
        out["training_split"] = split
        for weight in WEIGHT_COLUMNS:
            if weight in row:
                out[weight] = row.get(weight, "")
        prepared.append(out)

    training_dir = root / "data/synthetic/training"
    training_path = training_dir / "reference_training_v1.csv"
    manifest_path = training_dir / "training_manifest.json"
    missing_path = root / "reports/phase3_missing_data_strategy.md"
    report_path = root / "reports/synthetic_training_data_report.md"
    strategies = [missing_strategy(item) for item in decisions]

    write_csv(training_path, prepared)
    manifest = {
        "training_dataset_version": TRAINING_VERSION,
        "reference_template_path": str(actual_reference_path(root).relative_to(root)).replace("\\", "/"),
        "training_dataset_path": str(training_path.relative_to(root)).replace("\\", "/"),
        "rows": len(prepared),
        "features": included,
        "feature_count": len(included),
        "weight_columns": [col for col in WEIGHT_COLUMNS if reference_rows and col in reference_rows[0]],
        "split_ratios": SPLIT_RATIOS,
        "split_counts": split_counts,
        "seed": seed,
        "missing_token": MISSING_TOKEN,
    }
    write_json(manifest_path, manifest)

    missing_lines = ["# Phase 3 Missing Data Strategy", ""]
    for item in strategies:
        missing_lines.append(f"- {item['variable']}: {item['strategy']} ({item['missing_percentage']}%). {item['reason']}")
    write_md(missing_path, "\n".join(missing_lines))

    excluded = [item["variable"] for item in decisions if item["decision"] != "INCLUDE"]
    report_lines = [
        "# Synthetic Training Data Report", "",
        f"- Training rows: {split_counts['train']}",
        f"- Validation rows: {split_counts['validation']}",
        f"- Holdout rows: {split_counts['holdout']}",
        f"- Total prepared rows: {len(prepared)}",
        f"- Variables: {', '.join(included)}",
        f"- Variable types: {json.dumps({name: decision_by_name[name]['type'] for name in included}, sort_keys=True)}",
        f"- Missingness handling: categorical/ordinal blanks become {MISSING_TOKEN}; numeric blanks remain blank; fully missing fields are excluded.",
        f"- Weights: {', '.join(manifest['weight_columns'])}; preserved for weighted sampling, excluded from model features.",
        f"- Excluded variables: {', '.join(excluded)}",
        "- Derived variables: age_group is derived after generation from age.",
        "- Constraints: not implemented in this module; next module should add configurable hard constraints.",
        f"- Reference versions: {TRAINING_VERSION} from {manifest['reference_template_path']}.",
        f"- Output: {manifest['training_dataset_path']}",
    ]
    write_md(report_path, "\n".join(report_lines))
    return {"training_path": training_path, "manifest_path": manifest_path, "missing_report": missing_path, "training_report": report_path, "manifest": manifest}
