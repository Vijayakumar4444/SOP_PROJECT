from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import random

from backend.app.modules.synthetic_population.generators.base import SyntheticGenerationError, SyntheticPopulationGenerator
from backend.app.modules.synthetic_population.assessment import read_csv


ROOT = Path(__file__).resolve().parents[5]
WEIGHT_COLUMNS = {"survey_weight", "normalized_reference_weight", "calibrated_reference_weight_gender_ur"}
NON_FEATURE_COLUMNS = WEIGHT_COLUMNS | {"training_split"}


class BootstrapBaselineGenerator(SyntheticPopulationGenerator):
    generator_type = "bootstrap"

    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []
        self.metadata: dict[str, Any] = {}
        self.config: dict[str, Any] = {}
        self.training_summary: dict[str, Any] = {}

    def fit(self, data: list[dict[str, Any]], metadata: dict[str, Any], config: dict[str, Any]) -> None:
        if not data:
            raise SyntheticGenerationError("Bootstrap baseline requires at least one training row.")
        self.rows = [dict(row) for row in data]
        self.metadata = dict(metadata)
        self.config = dict(config)
        weight_column = self.config.get("weight_column", "calibrated_reference_weight_gender_ur")
        strata = [col for col in self.config.get("stratification_columns", []) if col in self.rows[0]]
        weights = [self._weight(row, weight_column) for row in self.rows]
        self.training_summary = {
            "generator": self.generator_type,
            "training_rows": len(self.rows),
            "variables": [name for name in self.rows[0].keys() if name not in NON_FEATURE_COLUMNS],
            "weight_column": weight_column if any(value > 0 for value in weights) else "NONE",
            "weighted_sampling": any(value > 0 for value in weights),
            "stratification_columns": strata,
            "stratified_sampling": bool(strata),
            "label": "RESAMPLED_BASELINE",
            "warning": "Bootstrap records are resampled from reference rows and may duplicate source observations; do not call this privacy-preserving synthesis.",
        }

    def sample(self, size: int, seed: int | None = None, conditions: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        if size <= 0:
            raise SyntheticGenerationError("Sample size must be positive.")
        candidates = self._conditioned_rows(conditions or {})
        if not candidates:
            raise SyntheticGenerationError("No bootstrap rows satisfy the requested conditions.")
        rng = random.Random(seed)
        sampled = self._stratified_sample(candidates, size, rng)
        rng.shuffle(sampled)
        return [self._output_row(row) for row in sampled[:size]]

    def save(self, destination: Path) -> None:
        destination.mkdir(parents=True, exist_ok=True)
        (destination / "model_metadata.json").write_text(json.dumps(self.get_model_metadata(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        (destination / "training_summary.json").write_text(json.dumps(self.training_summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, source: Path) -> "BootstrapBaselineGenerator":
        metadata = json.loads((source / "model_metadata.json").read_text(encoding="utf-8"))
        training_rows = read_csv(ROOT / metadata["training_dataset_path"])
        model = cls()
        model.fit(training_rows, metadata, metadata.get("config", {}))
        model.metadata = metadata
        return model

    def get_model_metadata(self) -> dict[str, Any]:
        data = dict(self.metadata)
        data.update({
            "generator_type": self.generator_type,
            "generator_version": "bootstrap_baseline_v1",
            "label": "RESAMPLED_BASELINE",
            "config": self.config,
            "training_summary": self.training_summary,
        })
        return data

    def get_training_summary(self) -> dict[str, Any]:
        return dict(self.training_summary)

    def _stratified_sample(self, rows: list[dict[str, Any]], size: int, rng: random.Random) -> list[dict[str, Any]]:
        strata = [col for col in self.config.get("stratification_columns", []) if rows and col in rows[0]]
        if not strata:
            return self._weighted_choices(rows, size, rng)
        groups: dict[tuple[str, ...], list[dict[str, Any]]] = {}
        for row in rows:
            key = tuple(str(row.get(col, "")) for col in strata)
            groups.setdefault(key, []).append(row)
        weights = {key: sum(self._weight(row, self.config.get("weight_column", "")) for row in group) or len(group) for key, group in groups.items()}
        total_weight = sum(weights.values()) or len(rows)
        allocations = {key: int(size * weight / total_weight) for key, weight in weights.items()}
        remaining = size - sum(allocations.values())
        ranked = sorted(groups, key=lambda key: (size * weights[key] / total_weight) - allocations[key], reverse=True)
        for key in ranked[:remaining]:
            allocations[key] += 1
        sampled: list[dict[str, Any]] = []
        for key, count in allocations.items():
            if count > 0:
                sampled.extend(self._weighted_choices(groups[key], count, rng))
        return sampled

    def _weighted_choices(self, rows: list[dict[str, Any]], size: int, rng: random.Random) -> list[dict[str, Any]]:
        weight_column = self.config.get("weight_column", "calibrated_reference_weight_gender_ur")
        weights = [self._weight(row, weight_column) for row in rows]
        return rng.choices(rows, weights=weights if any(value > 0 for value in weights) else None, k=size)

    def _conditioned_rows(self, conditions: dict[str, Any]) -> list[dict[str, Any]]:
        rows = self.rows
        for field, expected in conditions.items():
            rows = [row for row in rows if str(row.get(field, "")) == str(expected)]
        return rows

    def _output_row(self, row: dict[str, Any]) -> dict[str, Any]:
        out = {key: value for key, value in row.items() if key not in NON_FEATURE_COLUMNS}
        out["synthetic_data_label"] = "RESAMPLED_BASELINE"
        return out

    def _weight(self, row: dict[str, Any], weight_column: str) -> float:
        try:
            value = float(row.get(weight_column, 0) or 0)
        except (TypeError, ValueError):
            return 0.0
        return max(value, 0.0)
