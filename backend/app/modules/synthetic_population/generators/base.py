from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class SyntheticPopulationGenerator(ABC):
    generator_type = "base"

    @abstractmethod
    def fit(self, data: list[dict[str, Any]], metadata: dict[str, Any], config: dict[str, Any]) -> None:
        raise NotImplementedError

    @abstractmethod
    def sample(self, size: int, seed: int | None = None, conditions: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def save(self, destination: Path) -> None:
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def load(cls, source: Path) -> "SyntheticPopulationGenerator":
        raise NotImplementedError

    @abstractmethod
    def get_model_metadata(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def get_training_summary(self) -> dict[str, Any]:
        raise NotImplementedError


class UnsupportedGeneratorError(Exception):
    code = "UNSUPPORTED_GENERATOR"


class SyntheticModelTrainingError(Exception):
    code = "SYNTHETIC_MODEL_TRAINING_ERROR"


class SyntheticGenerationError(Exception):
    code = "SYNTHETIC_GENERATION_ERROR"
