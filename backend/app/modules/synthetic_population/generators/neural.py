from __future__ import annotations

from pathlib import Path
from typing import Any
import importlib
import importlib.metadata
import importlib.util
import inspect
import json
import random
import time

from backend.app.modules.synthetic_population.generators.base import (
    SyntheticGenerationError,
    SyntheticModelTrainingError,
    SyntheticPopulationGenerator,
)


MODEL_FILENAME = "sdv_synthesizer.pkl"
SCHEMA_FILENAME = "sdv_metadata.json"
NON_FEATURE_COLUMNS = {"survey_weight", "normalized_reference_weight", "calibrated_reference_weight_gender_ur", "training_split"}
REQUIRED_DEPENDENCIES = ("sdv", "pandas")
SDV_NUMERIC_TYPES = {"integer", "continuous"}


class SDVNeuralGenerator(SyntheticPopulationGenerator):
    generator_type = "neural"
    model_version = "sdv_neural_v1"
    sdv_class_name = ""
    label = "SYNTHETIC_NEURAL_CANDIDATE"
    required_dependencies = REQUIRED_DEPENDENCIES

    def __init__(self) -> None:
        self.metadata: dict[str, Any] = {}
        self.config: dict[str, Any] = {}
        self.columns: list[str] = []
        self.column_types: dict[str, str] = {}
        self.training_summary: dict[str, Any] = {}
        self.sdv_metadata: Any = None
        self.synthesizer: Any = None

    def fit(self, data: list[dict[str, Any]], metadata: dict[str, Any], config: dict[str, Any]) -> None:
        started = time.perf_counter()
        if not data:
            raise SyntheticModelTrainingError(f"{self.generator_type} requires at least one training row.")
        missing = self.missing_dependencies()
        if missing:
            self.training_summary = self._blocked_summary(missing, len(data))
            raise SyntheticModelTrainingError(
                f"{self.generator_type} training is blocked because required dependencies are missing: {', '.join(missing)}."
            )
        self.metadata = dict(metadata)
        self.config = dict(config)
        self.columns = self._feature_columns(data, metadata)
        if not self.columns:
            raise SyntheticModelTrainingError(f"{self.generator_type} requires at least one feature column.")
        self.column_types = self._column_types(data, metadata)
        self._seed(config.get("seed"))
        dataframe = self._dataframe(data)
        self.sdv_metadata = self._build_sdv_metadata(dataframe)
        synthesizer_cls = self._synthesizer_class()
        self.synthesizer = synthesizer_cls(self.sdv_metadata, **self._synthesizer_kwargs(synthesizer_cls))
        try:
            self.synthesizer.fit(dataframe)
        except TypeError:
            self.synthesizer.fit(data=dataframe)
        self.training_summary = {
            "generator": self.generator_type,
            "training_rows": len(dataframe),
            "variables": self.columns,
            "column_types": self.column_types,
            "label": self.label,
            "sdv_synthesizer": self.sdv_class_name,
            "sdv_version": self._dependency_version("sdv"),
            "pandas_version": self._dependency_version("pandas"),
            "seed": self._optional_int(config.get("seed")),
            "epochs": self._optional_int(config.get("epochs")),
            "batch_size": self._optional_int(config.get("batch_size")),
            "enable_gpu": self._optional_bool(config.get("enable_gpu"), False),
            "training_duration_seconds": round(max(time.perf_counter() - started, 0.000001), 4),
            "warning": "Neural SDV training is stochastic; seeds are recorded for reproducibility but exact determinism is not guaranteed.",
        }

    def sample(self, size: int, seed: int | None = None, conditions: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        if size <= 0:
            raise SyntheticGenerationError("Sample size must be positive.")
        if self.synthesizer is None:
            raise SyntheticGenerationError(f"{self.generator_type} cannot sample until a trained SDV model is loaded.")
        conditions = conditions or {}
        self._validate_conditions(conditions)
        self._seed(seed)
        rows: list[dict[str, Any]] = []
        attempts = 0
        batch_size = min(max(size * 2, 100), max(size, 1000))
        limit = max(size * 50, 1000)
        while len(rows) < size and attempts < limit:
            request_size = size - len(rows) if not conditions else min(batch_size, max(size - len(rows), 100))
            frame = self.synthesizer.sample(num_rows=request_size)
            attempts += len(frame)
            for row in self._rows_from_dataframe(frame):
                if all(str(row.get(field, "")) == str(value) for field, value in conditions.items()):
                    row["synthetic_data_label"] = self.label
                    rows.append(row)
                    if len(rows) == size:
                        break
        if len(rows) < size:
            raise SyntheticGenerationError(
                f"Conditional {self.generator_type} sampling accepted {len(rows)} of {size} rows after {attempts} attempts."
            )
        return rows

    def save(self, destination: Path) -> None:
        if self.synthesizer is None:
            raise SyntheticModelTrainingError(f"{self.generator_type} has no trained SDV model to save.")
        destination.mkdir(parents=True, exist_ok=True)
        model_path = destination / MODEL_FILENAME
        self.synthesizer.save(str(model_path))
        (destination / "model_metadata.json").write_text(
            json.dumps(self.get_model_metadata(), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        (destination / "training_summary.json").write_text(
            json.dumps(self.training_summary, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        schema = self.sdv_metadata.to_dict() if hasattr(self.sdv_metadata, "to_dict") else {}
        (destination / SCHEMA_FILENAME).write_text(json.dumps(schema, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, source: Path) -> "SDVNeuralGenerator":
        missing = cls.missing_dependencies()
        if missing:
            raise SyntheticModelTrainingError(
                f"{cls.generator_type} loading is blocked because required dependencies are missing: {', '.join(missing)}."
            )
        model_path = source / MODEL_FILENAME
        if not model_path.exists():
            raise SyntheticModelTrainingError(f"{cls.generator_type} model file is missing: {model_path}")
        metadata_path = source / "model_metadata.json"
        if not metadata_path.exists():
            raise SyntheticModelTrainingError(f"{cls.generator_type} metadata file is missing: {metadata_path}")
        synthesizer_cls = cls._synthesizer_class()
        model = cls()
        model.synthesizer = synthesizer_cls.load(str(model_path))
        model.metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        model.config = model.metadata.get("config", {})
        model.columns = list(model.metadata.get("variables", []))
        model.column_types = dict(model.metadata.get("variable_types", {}))
        model.training_summary = json.loads((source / "training_summary.json").read_text(encoding="utf-8"))
        return model

    def get_model_metadata(self) -> dict[str, Any]:
        data = dict(self.metadata)
        data.update({
            "generator_type": self.generator_type,
            "generator_version": self.model_version,
            "label": self.label,
            "config": self.config,
            "training_summary": self.training_summary,
        })
        return data

    def get_training_summary(self) -> dict[str, Any]:
        return dict(self.training_summary)

    @classmethod
    def missing_dependencies(cls) -> list[str]:
        return [name for name in cls.required_dependencies if importlib.util.find_spec(name) is None]

    def _feature_columns(self, data: list[dict[str, Any]], metadata: dict[str, Any]) -> list[str]:
        variables = [name for name in metadata.get("variables", []) if name not in NON_FEATURE_COLUMNS]
        if variables:
            return variables
        return [name for name in data[0].keys() if name not in NON_FEATURE_COLUMNS]

    def _column_types(self, data: list[dict[str, Any]], metadata: dict[str, Any]) -> dict[str, str]:
        known = {name: kind for name, kind in metadata.get("variable_types", {}).items() if name in self.columns}
        if len(known) == len(self.columns):
            return known
        for column in self.columns:
            if column in known:
                continue
            known[column] = self._infer_type(data, column)
        return known

    def _dataframe(self, data: list[dict[str, Any]]):
        pandas = importlib.import_module("pandas")
        rows = [{column: row.get(column, "") for column in self.columns} for row in data]
        frame = pandas.DataFrame(rows, columns=self.columns)
        for column in self.columns:
            kind = self.column_types.get(column, "categorical")
            if kind in SDV_NUMERIC_TYPES:
                numeric = pandas.to_numeric(frame[column], errors="coerce")
                if kind == "integer":
                    numeric = numeric.round()
                    if numeric.isna().any():
                        numeric = numeric.fillna(numeric.median() if not numeric.dropna().empty else 0)
                    frame[column] = numeric.astype("int64")
                else:
                    if numeric.isna().any():
                        numeric = numeric.fillna(numeric.median() if not numeric.dropna().empty else 0.0)
                    frame[column] = numeric.astype("float64")
            else:
                frame[column] = frame[column].fillna("").astype(str).replace({"": self.config.get("missing_token", "Unknown")})
        return frame

    def _build_sdv_metadata(self, dataframe: Any) -> Any:
        metadata_cls = importlib.import_module("sdv.metadata").SingleTableMetadata
        sdv_metadata = metadata_cls()
        try:
            sdv_metadata.detect_from_dataframe(data=dataframe)
        except TypeError:
            sdv_metadata.detect_from_dataframe(dataframe=dataframe)
        if getattr(sdv_metadata, "primary_key", None):
            sdv_metadata.remove_primary_key()
        for column in self.columns:
            kind = self.column_types.get(column, "categorical")
            sdtype = "numerical" if kind in SDV_NUMERIC_TYPES else "boolean" if kind == "boolean" else "categorical"
            try:
                sdv_metadata.update_column(column_name=column, sdtype=sdtype)
            except TypeError:
                sdv_metadata.update_column(column, sdtype=sdtype)
        return sdv_metadata

    @classmethod
    def _synthesizer_class(cls):
        module = importlib.import_module("sdv.single_table")
        return getattr(module, cls.sdv_class_name)

    def _synthesizer_kwargs(self, synthesizer_cls: Any) -> dict[str, Any]:
        candidates = {
            "epochs": self._optional_int(self.config.get("epochs")),
            "batch_size": self._optional_int(self.config.get("batch_size")),
            "verbose": self._optional_bool(self.config.get("verbose"), False),
            "enable_gpu": self._optional_bool(self.config.get("enable_gpu"), False),
            "enforce_min_max_values": self._optional_bool(self.config.get("enforce_min_max_values"), True),
            "enforce_rounding": self._optional_bool(self.config.get("enforce_rounding"), True),
            "embedding_dim": self._optional_int(self.config.get("embedding_dim")),
            "generator_dim": self._optional_tuple(self.config.get("generator_dim")),
            "discriminator_dim": self._optional_tuple(self.config.get("discriminator_dim")),
            "compress_dims": self._optional_tuple(self.config.get("compress_dims")),
            "decompress_dims": self._optional_tuple(self.config.get("decompress_dims")),
            "l2scale": self._optional_float(self.config.get("l2scale")),
            "loss_factor": self._optional_int(self.config.get("loss_factor")),
        }
        accepted = set(inspect.signature(synthesizer_cls).parameters)
        return {key: value for key, value in candidates.items() if key in accepted and value is not None}

    def _rows_from_dataframe(self, dataframe: Any) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for raw in dataframe.to_dict(orient="records"):
            row: dict[str, Any] = {}
            for column in self.columns:
                value = raw.get(column, "")
                kind = self.column_types.get(column, "categorical")
                if kind == "integer":
                    try:
                        value = int(round(float(value)))
                    except (TypeError, ValueError):
                        value = 0
                elif kind == "continuous":
                    try:
                        value = round(float(value), 6)
                    except (TypeError, ValueError):
                        value = 0.0
                elif value is None:
                    value = self.config.get("missing_token", "Unknown")
                else:
                    value = str(value)
                row[column] = value
            rows.append(row)
        return rows

    def _validate_conditions(self, conditions: dict[str, Any]) -> None:
        unsupported = sorted(set(conditions) - set(self.columns))
        if unsupported:
            raise SyntheticGenerationError(f"Unsupported condition fields: {', '.join(unsupported)}")

    def _infer_type(self, data: list[dict[str, Any]], column: str) -> str:
        numeric = 0
        total = 0
        integer = True
        for row in data:
            value = row.get(column, "")
            if value in ("", None):
                continue
            total += 1
            try:
                parsed = float(value)
                numeric += 1
                integer = integer and parsed.is_integer()
            except (TypeError, ValueError):
                integer = False
        if total and numeric == total:
            return "integer" if integer else "continuous"
        return "categorical"

    def _blocked_summary(self, missing: list[str], training_rows: int) -> dict[str, Any]:
        return {
            "generator": self.generator_type,
            "training_rows": training_rows,
            "status": "BLOCKED",
            "missing_dependencies": missing,
            "reason": "Required neural synthetic-data dependencies are not installed. No dependency was installed silently.",
        }

    def _seed(self, seed: Any) -> None:
        parsed = self._optional_int(seed)
        if parsed is None:
            return
        random.seed(parsed)
        try:
            numpy = importlib.import_module("numpy")
            numpy.random.seed(parsed)
        except Exception:
            pass
        try:
            torch = importlib.import_module("torch")
            torch.manual_seed(parsed)
            if hasattr(torch, "cuda"):
                torch.cuda.manual_seed_all(parsed)
        except Exception:
            pass

    def _dependency_version(self, package: str) -> str:
        try:
            return importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            return "not_installed"

    def _optional_int(self, value: Any) -> int | None:
        if value in (None, ""):
            return None
        return int(float(value))

    def _optional_float(self, value: Any) -> float | None:
        if value in (None, ""):
            return None
        return float(value)

    def _optional_bool(self, value: Any, default: bool) -> bool:
        if value in (None, ""):
            return default
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}

    def _optional_tuple(self, value: Any) -> tuple[int, ...] | None:
        if value in (None, ""):
            return None
        if isinstance(value, (list, tuple)):
            return tuple(int(item) for item in value)
        cleaned = str(value).strip().strip("[]()")
        if not cleaned:
            return None
        return tuple(int(item.strip()) for item in cleaned.split(",") if item.strip())


class CTGANGenerator(SDVNeuralGenerator):
    generator_type = "ctgan"
    model_version = "ctgan_sdv_v1"
    sdv_class_name = "CTGANSynthesizer"
    label = "SYNTHETIC_CTGAN_CANDIDATE"


class TVAEGenerator(SDVNeuralGenerator):
    generator_type = "tvae"
    model_version = "tvae_sdv_v1"
    sdv_class_name = "TVAESynthesizer"
    label = "SYNTHETIC_TVAE_CANDIDATE"
