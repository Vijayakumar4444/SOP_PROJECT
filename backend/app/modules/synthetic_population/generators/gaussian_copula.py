from __future__ import annotations

from pathlib import Path
from typing import Any
from statistics import NormalDist
import json
import math
import random

from backend.app.modules.synthetic_population.assessment import read_csv
from backend.app.modules.synthetic_population.generators.base import SyntheticGenerationError, SyntheticPopulationGenerator


ROOT = Path(__file__).resolve().parents[5]
NON_FEATURE_COLUMNS = {"survey_weight", "normalized_reference_weight", "calibrated_reference_weight_gender_ur", "training_split"}
NORMAL = NormalDist()


class GaussianCopulaGenerator(SyntheticPopulationGenerator):
    generator_type = "gaussian_copula"

    def __init__(self) -> None:
        self.metadata: dict[str, Any] = {}
        self.config: dict[str, Any] = {}
        self.columns: list[str] = []
        self.column_types: dict[str, str] = {}
        self.empirical: dict[str, list[Any]] = {}
        self.correlation: list[list[float]] = []
        self.cholesky: list[list[float]] = []
        self.training_summary: dict[str, Any] = {}

    def fit(self, data: list[dict[str, Any]], metadata: dict[str, Any], config: dict[str, Any]) -> None:
        if len(data) < 2:
            raise SyntheticGenerationError("Gaussian Copula requires at least two training rows.")
        self.metadata = dict(metadata)
        self.config = dict(config)
        self.columns = [name for name in data[0].keys() if name not in NON_FEATURE_COLUMNS]
        if not self.columns:
            raise SyntheticGenerationError("Gaussian Copula requires at least one feature column.")
        self.column_types = dict(metadata.get("variable_types", {})) or self._infer_types(data)
        self.empirical = {col: self._sorted_values(data, col) for col in self.columns}
        normal_rows = self._normal_score_rows(data)
        self.correlation = self._correlation_matrix(normal_rows)
        self.cholesky = self._cholesky(self.correlation, float(config.get("jitter", 0.000001)))
        self.training_summary = {
            "generator": self.generator_type,
            "training_rows": len(data),
            "variables": self.columns,
            "column_types": self.column_types,
            "correlation_dimensions": len(self.correlation),
            "label": "SYNTHETIC_GAUSSIAN_COPULA_CANDIDATE",
            "warning": "Pure-Python fallback generator; full statistical validation belongs to Phase 4.",
        }

    def sample(self, size: int, seed: int | None = None, conditions: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        if size <= 0:
            raise SyntheticGenerationError("Sample size must be positive.")
        rng = random.Random(seed)
        conditions = conditions or {}
        self._validate_conditions(conditions)
        rows: list[dict[str, Any]] = []
        attempts = 0
        limit = max(size * 50, 1000)
        while len(rows) < size and attempts < limit:
            attempts += 1
            row = self._sample_one(rng)
            if all(str(row.get(field, "")) == str(value) for field, value in conditions.items()):
                row["synthetic_data_label"] = "SYNTHETIC_GAUSSIAN_COPULA_CANDIDATE"
                rows.append(row)
        if len(rows) < size:
            raise SyntheticGenerationError(f"Conditional Gaussian Copula sampling accepted {len(rows)} of {size} rows after {attempts} attempts.")
        return rows

    def save(self, destination: Path) -> None:
        destination.mkdir(parents=True, exist_ok=True)
        payload = {
            "metadata": self.get_model_metadata(),
            "columns": self.columns,
            "column_types": self.column_types,
            "empirical": self.empirical,
            "correlation": self.correlation,
            "cholesky": self.cholesky,
            "training_summary": self.training_summary,
        }
        (destination / "model.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        (destination / "model_metadata.json").write_text(json.dumps(self.get_model_metadata(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        (destination / "training_summary.json").write_text(json.dumps(self.training_summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, source: Path) -> "GaussianCopulaGenerator":
        payload = json.loads((source / "model.json").read_text(encoding="utf-8"))
        model = cls()
        model.metadata = payload["metadata"]
        model.config = model.metadata.get("config", {})
        model.columns = payload["columns"]
        model.column_types = payload["column_types"]
        model.empirical = payload["empirical"]
        model.correlation = payload["correlation"]
        model.cholesky = payload["cholesky"]
        model.training_summary = payload["training_summary"]
        return model

    def get_model_metadata(self) -> dict[str, Any]:
        data = dict(self.metadata)
        data.update({
            "generator_type": self.generator_type,
            "generator_version": "gaussian_copula_pure_python_v1",
            "label": "SYNTHETIC_GAUSSIAN_COPULA_CANDIDATE",
            "config": self.config,
            "training_summary": self.training_summary,
        })
        return data

    def get_training_summary(self) -> dict[str, Any]:
        return dict(self.training_summary)

    def _infer_types(self, data: list[dict[str, Any]]) -> dict[str, str]:
        types = {}
        for col in self.columns:
            numeric = 0
            total = 0
            integer = True
            for row in data:
                value = row.get(col, "")
                if value == "":
                    continue
                total += 1
                try:
                    parsed = float(value)
                    numeric += 1
                    integer = integer and parsed.is_integer()
                except (TypeError, ValueError):
                    integer = False
            if total and numeric == total:
                types[col] = "integer" if integer else "continuous"
            else:
                types[col] = "categorical"
        return types

    def _sorted_values(self, data: list[dict[str, Any]], col: str) -> list[Any]:
        values = [row.get(col, "") for row in data]
        if self.column_types[col] in {"integer", "continuous"}:
            numeric = []
            for value in values:
                try:
                    numeric.append(float(value))
                except (TypeError, ValueError):
                    numeric.append(0.0)
            return sorted(numeric)
        return sorted(values, key=lambda item: str(item))

    def _normal_score_rows(self, data: list[dict[str, Any]]) -> list[list[float]]:
        encoded_columns = []
        for col in self.columns:
            values = [row.get(col, "") for row in data]
            ranks = self._ranks(values, self.column_types[col])
            n = len(ranks)
            encoded_columns.append([NORMAL.inv_cdf(min(max((rank + 0.5) / n, 0.000001), 0.999999)) for rank in ranks])
        return [[encoded_columns[col_idx][row_idx] for col_idx in range(len(self.columns))] for row_idx in range(len(data))]

    def _ranks(self, values: list[Any], variable_type: str) -> list[int]:
        if variable_type in {"integer", "continuous"}:
            sortable = [(float(value or 0), idx) for idx, value in enumerate(values)]
        else:
            sortable = [(str(value), idx) for idx, value in enumerate(values)]
        ranks = [0] * len(values)
        for rank, (_, idx) in enumerate(sorted(sortable)):
            ranks[idx] = rank
        return ranks

    def _correlation_matrix(self, rows: list[list[float]]) -> list[list[float]]:
        dims = len(self.columns)
        means = [sum(row[i] for row in rows) / len(rows) for i in range(dims)]
        matrix = []
        for i in range(dims):
            line = []
            for j in range(dims):
                cov = sum((row[i] - means[i]) * (row[j] - means[j]) for row in rows) / max(len(rows) - 1, 1)
                var_i = sum((row[i] - means[i]) ** 2 for row in rows) / max(len(rows) - 1, 1)
                var_j = sum((row[j] - means[j]) ** 2 for row in rows) / max(len(rows) - 1, 1)
                denom = math.sqrt(var_i * var_j)
                line.append(1.0 if i == j else max(min(cov / denom, 0.999), -0.999) if denom else 0.0)
            matrix.append(line)
        return matrix

    def _cholesky(self, matrix: list[list[float]], jitter: float) -> list[list[float]]:
        n = len(matrix)
        lower = [[0.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(i + 1):
                value = matrix[i][j] + (jitter if i == j else 0.0) - sum(lower[i][k] * lower[j][k] for k in range(j))
                if i == j:
                    lower[i][j] = math.sqrt(max(value, jitter))
                else:
                    lower[i][j] = value / lower[j][j] if lower[j][j] else 0.0
        return lower

    def _sample_one(self, rng: random.Random) -> dict[str, Any]:
        z = [rng.gauss(0, 1) for _ in self.columns]
        correlated = []
        for i in range(len(self.columns)):
            correlated.append(sum(self.cholesky[i][j] * z[j] for j in range(i + 1)))
        out = {}
        for col, normal_value in zip(self.columns, correlated):
            u = min(max(NORMAL.cdf(normal_value), 0.0), 0.999999)
            values = self.empirical[col]
            idx = min(int(u * len(values)), len(values) - 1)
            value = values[idx]
            if self.column_types[col] == "integer":
                value = int(round(float(value)))
            elif self.column_types[col] == "continuous":
                value = float(value)
            out[col] = value
        return out

    def _validate_conditions(self, conditions: dict[str, Any]) -> None:
        unsupported = sorted(set(conditions) - set(self.columns))
        if unsupported:
            raise SyntheticGenerationError(f"Unsupported condition fields: {', '.join(unsupported)}")

