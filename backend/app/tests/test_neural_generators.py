from __future__ import annotations

from pathlib import Path
import importlib.util
import unittest

from backend.app.modules.data_foundation.io_utils import write_json
from backend.app.modules.synthetic_population.constraints import ConstraintEngine
from backend.app.modules.synthetic_population.generator_training import upsert_registry
from backend.app.modules.synthetic_population.generators.neural import CTGANGenerator, TVAEGenerator
from backend.app.modules.synthetic_population.sampling_service import DynamicSamplingService


NEURAL_DEPS_AVAILABLE = all(importlib.util.find_spec(name) is not None for name in ("sdv", "pandas"))
FEATURES = [
    "district",
    "district_code",
    "urban_rural",
    "age",
    "gender",
    "marital_status",
    "relationship_to_head",
    "household_size",
    "household_type",
    "literacy_status",
    "education_level",
    "labour_force_status",
    "employment_status",
    "individual_income",
    "consumption_expenditure",
    "social_group",
]
VARIABLE_TYPES = {
    "district": "categorical",
    "district_code": "categorical",
    "urban_rural": "categorical",
    "age": "integer",
    "gender": "categorical",
    "marital_status": "categorical",
    "relationship_to_head": "categorical",
    "household_size": "integer",
    "household_type": "categorical",
    "literacy_status": "categorical",
    "education_level": "ordinal",
    "labour_force_status": "categorical",
    "employment_status": "categorical",
    "individual_income": "continuous",
    "consumption_expenditure": "continuous",
    "social_group": "categorical",
}


def fixture_rows() -> list[dict[str, object]]:
    seeds = [
        ("Chennai", "603", "Urban", "Female", "Employed", 24000, 16000),
        ("Madurai", "625", "Rural", "Male", "Not in labour force", 0, 4200),
        ("Coimbatore", "632", "Urban", "Female", "Employed", 42000, 22000),
        ("Salem", "608", "Rural", "Male", "Not in labour force", 0, 3800),
        ("Thanjavur", "620", "Rural", "Female", "Unemployed", 0, 5200),
        ("Tiruchirappalli", "614", "Urban", "Other", "Employed", 18000, 12000),
    ]
    rows = []
    for index in range(30):
        district, code, ur, gender, employment, income, spend = seeds[index % len(seeds)]
        rows.append({
            "district": district,
            "district_code": code,
            "urban_rural": ur,
            "age": 18 + (index % 55),
            "gender": gender,
            "marital_status": "Currently married" if index % 3 else "Never married",
            "relationship_to_head": "Head" if index % 4 == 0 else "Member",
            "household_size": 1 + (index % 7),
            "household_type": "Rural household" if ur == "Rural" else "Urban household",
            "literacy_status": "Literate",
            "education_level": "Graduate" if index % 2 else "Secondary",
            "labour_force_status": employment,
            "employment_status": employment,
            "individual_income": income,
            "consumption_expenditure": spend,
            "social_group": "Others" if index % 2 else "Other Backward Class",
            "survey_weight": 1.0,
            "normalized_reference_weight": 1.0,
            "calibrated_reference_weight_gender_ur": 1.0,
            "training_split": "train",
        })
    return rows


@unittest.skipUnless(NEURAL_DEPS_AVAILABLE, "SDV/pandas are required for neural generator integration tests.")
class NeuralGeneratorIntegrationTests(unittest.TestCase):
    def _metadata(self, model_id: str, generator: str) -> dict[str, object]:
        return {
            "model_id": model_id,
            "generator_type": generator,
            "model_version": f"{generator}_sdv_v1",
            "training_dataset_version": "test_training_v1",
            "training_dataset_path": "data/synthetic/training/test.csv",
            "variables": FEATURES,
            "variable_types": VARIABLE_TYPES,
            "training_rows": 30,
            "status": "TRAINING",
            "artifact_path": f"artifacts/synthetic_models/{generator}/{model_id}",
            "config": self._config(generator),
        }

    def _config(self, generator: str) -> dict[str, object]:
        return {
            "generator": generator,
            "version": f"{generator}_sdv_v1",
            "seed": 7,
            "epochs": 1,
            "batch_size": 10,
            "enable_gpu": False,
            "enforce_min_max_values": True,
            "enforce_rounding": True,
        }

    def _assert_lifecycle(self, generator_cls, generator_name: str) -> None:
        root = Path.cwd() / "tests/synthetic_population/neural_test_runtime" / generator_name
        root.mkdir(parents=True, exist_ok=True)
        artifact = root / "artifacts/synthetic_models" / generator_name / f"TN_{generator_name.upper()}_TEST"
        model = generator_cls()
        metadata = self._metadata(f"TN_{generator_name.upper()}_TEST", generator_name)
        model.fit(fixture_rows(), metadata, self._config(generator_name))
        self.assertEqual(model.sdv_metadata.to_dict()["columns"]["age"]["sdtype"], "numerical")
        self.assertEqual(model.sdv_metadata.to_dict()["columns"]["district"]["sdtype"], "categorical")
        model.save(artifact)
        self.assertTrue((artifact / "sdv_synthesizer.pkl").exists())
        reloaded = generator_cls.load(artifact)
        rows = reloaded.sample(12, seed=8)
        self.assertEqual(len(rows), 12)
        self.assertTrue(set(FEATURES).issubset(rows[0]))
        self.assertEqual(ConstraintEngine().validate_rows(rows)["hard_violation_count"], 0)
        registry_path = root / "artifacts/synthetic_models/model_registry.json"
        entry = dict(metadata, status="TRAINED", artifact_path=str(artifact.relative_to(root)).replace("\\", "/"))
        upsert_registry(registry_path, entry)
        write_json(root / "artifacts/synthetic_models/model_registry.json", {"models": [entry]})
        service = DynamicSamplingService(root)
        loaded = service._load_model(entry)
        self.assertEqual(len(loaded.sample(10, seed=9)), 10)

    def test_ctgan_fit_save_load_sample_and_sampling_service(self) -> None:
        self._assert_lifecycle(CTGANGenerator, "ctgan")

    def test_tvae_fit_save_load_sample_and_sampling_service(self) -> None:
        self._assert_lifecycle(TVAEGenerator, "tvae")


if __name__ == "__main__":
    unittest.main()
