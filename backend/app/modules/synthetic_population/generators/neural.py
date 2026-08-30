from __future__ import annotations

from pathlib import Path
from typing import Any
import importlib.util

from backend.app.modules.synthetic_population.generators.base import SyntheticModelTrainingError, SyntheticPopulationGenerator


class DependencyGatedNeuralGenerator(SyntheticPopulationGenerator):
    generator_type = "neural"
    model_version = "dependency_gated_v1"
    required_dependencies = ("sdv", "pandas")

    def __init__(self) -> None:
        self.metadata: dict[str, Any] = {}
        self.config: dict[str, Any] = {}
        self.training_summary: dict[str, Any] = {}

    def fit(self, data: list[dict[str, Any]], metadata: dict[str, Any], config: dict[str, Any]) -> None:
        self.metadata = dict(metadata)
        self.config = dict(config)
        missing = self.missing_dependencies()
        if missing:
            self.training_summary = self._blocked_summary(missing, len(data))
            raise SyntheticModelTrainingError(
                f"{self.generator_type} training is blocked because optional dependencies are missing: {', '.join(missing)}."
            )
        raise SyntheticModelTrainingError(
            f"{self.generator_type} wrapper is dependency-ready but model-specific SDV wiring is scheduled for a later environment."
        )

    def sample(self, size: int, seed: int | None = None, conditions: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        raise SyntheticModelTrainingError(f"{self.generator_type} cannot sample until a model is successfully trained.")

    def save(self, destination: Path) -> None:
        destination.mkdir(parents=True, exist_ok=True)

    @classmethod
    def load(cls, source: Path) -> "DependencyGatedNeuralGenerator":
        raise SyntheticModelTrainingError(f"{cls.generator_type} model artifact is not available.")

    def get_model_metadata(self) -> dict[str, Any]:
        data = dict(self.metadata)
        data.update({
            "generator_type": self.generator_type,
            "generator_version": self.model_version,
            "config": self.config,
            "training_summary": self.training_summary,
        })
        return data

    def get_training_summary(self) -> dict[str, Any]:
        return dict(self.training_summary)

    def missing_dependencies(self) -> list[str]:
        return [name for name in self.required_dependencies if importlib.util.find_spec(name) is None]

    def _blocked_summary(self, missing: list[str], training_rows: int) -> dict[str, Any]:
        return {
            "generator": self.generator_type,
            "training_rows": training_rows,
            "status": "BLOCKED",
            "missing_dependencies": missing,
            "reason": "Optional neural synthetic-data dependencies are not installed. No dependency was installed silently.",
        }


class CTGANGenerator(DependencyGatedNeuralGenerator):
    generator_type = "ctgan"
    model_version = "ctgan_sdv_optional_v1"


class TVAEGenerator(DependencyGatedNeuralGenerator):
    generator_type = "tvae"
    model_version = "tvae_sdv_optional_v1"
