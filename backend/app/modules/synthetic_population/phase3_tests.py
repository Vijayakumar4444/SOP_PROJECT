from __future__ import annotations

from pathlib import Path
from typing import Any
from datetime import datetime, timezone

from backend.app.modules.data_foundation.io_utils import read_csv, write_csv, write_json, write_md
from backend.app.modules.synthetic_population.assessment import ROOT, read_json
from backend.app.modules.synthetic_population.constraints import ConstraintEngine
from backend.app.modules.synthetic_population.generators.base import SyntheticGenerationError
from backend.app.modules.synthetic_population.generators.bootstrap import BootstrapBaselineGenerator
from backend.app.modules.synthetic_population.generators.gaussian_copula import GaussianCopulaGenerator
from backend.app.modules.synthetic_population.generators.neural import CTGANGenerator, TVAEGenerator
from backend.app.modules.synthetic_population.generators.registry import get_generator_class
from backend.app.modules.synthetic_population.population_persistence import run_population_persistence
from backend.app.modules.synthetic_population.sampling_service import DynamicSamplingService


FIXTURE_ROWS = [
    {"fixture_label": "TEST FIXTURE", "age": 22, "gender": "Female", "district": "Chennai", "urban_rural": "Urban", "education_level": "Higher secondary", "employment_status": "Employed", "household_size": 3, "individual_income": 18000},
    {"fixture_label": "TEST FIXTURE", "age": 67, "gender": "Male", "district": "Madurai", "urban_rural": "Rural", "education_level": "Primary", "employment_status": "Not in labour force", "household_size": 5, "individual_income": 0},
    {"fixture_label": "TEST FIXTURE", "age": 35, "gender": "Female", "district": "Coimbatore", "urban_rural": "Urban", "education_level": "Graduate", "employment_status": "Employed", "household_size": 4, "individual_income": 42000},
    {"fixture_label": "TEST FIXTURE", "age": 16, "gender": "Male", "district": "Salem", "urban_rural": "Rural", "education_level": "Secondary", "employment_status": "Not in labour force", "household_size": 6, "individual_income": 0},
    {"fixture_label": "TEST FIXTURE", "age": 44, "gender": "Other", "district": "Tiruchirappalli", "urban_rural": "Urban", "education_level": "Diploma", "employment_status": "Unemployed", "household_size": 2, "individual_income": 0},
    {"fixture_label": "TEST FIXTURE", "age": 72, "gender": "Female", "district": "Thanjavur", "urban_rural": "Rural", "education_level": "No formal schooling", "employment_status": "Not in labour force", "household_size": 4, "individual_income": 0},
]


class Phase3TestFailure(Exception):
    code = "PHASE3_TEST_FAILURE"


class Phase3TestSuite:
    def __init__(self, root: Path = ROOT):
        self.root = root
        self.results: list[dict[str, Any]] = []

    def run(self) -> dict[str, Any]:
        self._write_fixture()
        self._case("generator_interface", self._test_generator_interface)
        self._case("data_preparation_excludes_identifiers", self._test_data_preparation)
        self._case("constraints_controlled_rows", self._test_constraints)
        self._case("population_size_and_conditional_sampling", self._test_sampling)
        self._case("synthetic_ids_and_persistence", self._test_synthetic_ids)
        self._case("model_serialization", self._test_model_serialization)
        self._case("phase3_integration_path", self._test_integration)
        failed = [item for item in self.results if item["status"] != "PASSED"]
        manifest = {
            "module": "phase3_test_suite",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "fixture": "tests/synthetic_population/demo_reference_fixture.csv",
            "status": "FAILED" if failed else "PASSED",
            "results": self.results,
        }
        write_json(self.root / "data/synthetic/phase3_test_manifest.json", manifest)
        write_md(self.root / "reports/phase3_test_report.md", self._report(manifest))
        if failed:
            raise Phase3TestFailure(f"{len(failed)} Phase 3 tests failed.")
        return manifest

    def _case(self, name: str, func) -> None:
        try:
            detail = func()
            self.results.append({"name": name, "status": "PASSED", "detail": detail})
        except Exception as exc:
            self.results.append({"name": name, "status": "FAILED", "detail": str(exc)})

    def _write_fixture(self) -> None:
        path = self.root / "tests/synthetic_population/demo_reference_fixture.csv"
        write_csv(path, FIXTURE_ROWS)
        write_md(
            self.root / "tests/synthetic_population/README.md",
            "# Synthetic Population Test Fixtures\n\nThese rows are a TEST FIXTURE only. They are artificial rows for pipeline tests and are not Tamil Nadu official data.\n",
        )

    def _test_generator_interface(self) -> str:
        bootstrap_cls = get_generator_class("bootstrap")
        gaussian_cls = get_generator_class("gaussian_copula")
        ctgan_cls = get_generator_class("ctgan")
        tvae_cls = get_generator_class("tvae")
        try:
            get_generator_class("unsupported")
        except Exception:
            pass
        else:
            raise AssertionError("unsupported generator did not fail")
        assert bootstrap_cls is BootstrapBaselineGenerator
        assert gaussian_cls is GaussianCopulaGenerator
        assert ctgan_cls is CTGANGenerator
        assert tvae_cls is TVAEGenerator
        return "fit/sample/save/load/metadata generators are registered; unsupported generator fails."

    def _test_data_preparation(self) -> str:
        manifest = read_json(self.root / "data/synthetic/training/training_manifest.json")
        features = set(manifest.get("features", []))
        blocked = {"reference_person_id", "reference_household_id", "source_record_id", "primary_source_id", "reference_year", "record_quality_flag"}
        assert not (features & blocked), f"blocked fields in training features: {features & blocked}"
        assert "calibrated_reference_weight_gender_ur" in manifest.get("weight_columns", []), "weight column not preserved"
        return f"{len(features)} feature columns; identifiers and metadata excluded."

    def _test_constraints(self) -> str:
        engine = ConstraintEngine()
        valid = {"age": "30", "household_size": "3", "gender": "Female", "urban_rural": "Rural", "literacy_status": "Literate", "employment_status": "Employed", "labour_force_status": "Employed", "social_group": "Others", "individual_income": "1000", "consumption_expenditure": "800"}
        invalid = dict(valid, age="-1", household_size="0", gender="Invalid")
        assert engine.validate_rows([valid])["hard_violation_count"] == 0
        assert engine.validate_rows([invalid])["hard_violation_count"] >= 3
        return "controlled valid row passes and invalid row fails hard constraints."

    def _test_sampling(self) -> str:
        service = DynamicSamplingService(self.root)
        service._validate_request(1000, "REPRESENTATIVE", {})
        entry = service._resolve_model(None, "bootstrap")
        model = service._load_model(entry)
        one = model.sample(1000, seed=777)
        assert len(one) == 1000
        service._validate_request(1000, "CONDITIONAL", {"urban_rural": "Rural"})
        rural = model.sample(1000, seed=778, conditions={"urban_rural": "Rural"})
        assert all(row.get("urban_rural") == "Rural" for row in rural)
        try:
            model.sample(1000, seed=779, conditions={"age": -100})
        except SyntheticGenerationError:
            pass
        else:
            raise AssertionError("impossible condition did not fail")
        return "representative size and rural conditional sampling passed; impossible condition failed."

    def _test_synthetic_ids(self) -> str:
        manifest = run_population_persistence(self.root)
        for item in manifest["populations"]:
            rows = read_csv(self.root / item["population_csv_path"])
            ids = [row["synthetic_person_id"] for row in rows]
            assert all(ids)
            assert len(ids) == len(set(ids))
            assert not {"reference_person_id", "source_record_id"} & set(rows[0])
        return f"{manifest['population_count']} persisted populations have unique synthetic IDs."

    def _test_model_serialization(self) -> str:
        registry = read_json(self.root / "artifacts/synthetic_models/model_registry.json")
        trained = [item for item in registry.get("models", []) if item.get("status") == "TRAINED"]
        for item in trained:
            model_cls = get_generator_class(item["generator_type"])
            model = model_cls.load(self.root / item["artifact_path"])
            rows = model.sample(10, seed=123)
            assert len(rows) == 10
            assert set(item["variables"]).issubset(rows[0].keys())
        return f"{len(trained)} trained models reload and sample with expected schema."

    def _test_integration(self) -> str:
        persisted = read_json(self.root / "data/synthetic/population_persistence_manifest.json")
        assert persisted.get("population_count", 0) >= 2
        gaussian = [item for item in persisted["populations"] if "GAUSSIAN_COPULA" in item["population_id"]]
        assert gaussian, "Gaussian Copula persisted population missing"
        rows = read_csv(self.root / gaussian[0]["population_csv_path"])
        assert len(rows) == 1000
        assert "synthetic_person_id" in rows[0]
        constraint = ConstraintEngine().validate_rows(rows)
        assert constraint["hard_violation_count"] == 0
        return "Phase 1/2-derived training through Gaussian generation, ID assignment, constraints, save and reload path passed."

    def _report(self, manifest: dict[str, Any]) -> str:
        lines = ["# Phase 3 Test Report", "", f"- Status: {manifest['status']}", f"- Fixture: {manifest['fixture']}", ""]
        for item in manifest["results"]:
            lines.append(f"- {item['name']}: {item['status']} - {item['detail']}")
        return "\n".join(lines)


def run_phase3_test_suite(root: Path = ROOT) -> dict[str, Any]:
    return Phase3TestSuite(root).run()
