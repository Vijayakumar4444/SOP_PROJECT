from __future__ import annotations

import json
import unittest
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.modules.calibration.diagnostics import effective_sample_size, weight_diagnostics
from backend.app.modules.calibration.marginal_comparison import compare_marginals
from backend.app.modules.calibration.poststratification import poststratify
from backend.app.modules.calibration.raking import initialize_weights, rake_weights
from backend.app.modules.calibration.service import Phase5CalibrationService
from backend.app.modules.calibration.target_loader import load_official_targets, usable_targets
from backend.app.modules.data_foundation.io_utils import write_csv, write_json


class Phase5CalibrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = ROOT / "backend/app/tests/calibration_test_runtime"
        self._write_fixture_project()

    def tearDown(self) -> None:
        pass

    def test_phase4_handoff_loading_and_population_resolution(self) -> None:
        service = Phase5CalibrationService(self.root)
        handoff = service._load_handoff(self.root / "data/synthetic/phase5_calibration_handoff.json")
        entry = service._resolve_phase4_manifest_entry(self.root / "data/synthetic/phase4_validation_manifest.json", handoff["population_id"])
        self.assertEqual(handoff["model_id"], "MODEL1")
        self.assertTrue((self.root / entry["population_artifact"]).exists())

    def test_target_loading_and_validation(self) -> None:
        rows = self._population_rows()
        targets = load_official_targets(self.root, rows, self._config())
        usable = usable_targets(targets)
        self.assertEqual([target["variable"] for target in usable], ["gender", "urban_rural", "social_group"])
        social = next(target for target in usable if target["variable"] == "social_group")
        self.assertEqual(social["status"], "USABLE_WITH_WARNINGS")
        self.assertTrue(any(category["category"] == "Non-SC/ST" for category in social["categories"]))

    def test_base_weights_are_initialized_without_changing_attributes(self) -> None:
        rows = self._population_rows()
        before = [dict(row) for row in rows]
        initialize_weights(rows)
        self.assertEqual(rows[0]["gender"], before[0]["gender"])
        self.assertEqual(rows[0]["base_weight"], "1.0")
        self.assertEqual(rows[0]["calibration_weight"], "1.0")

    def test_post_stratification_handles_zero_cells(self) -> None:
        rows = [{"gender": "Male"}, {"gender": "Male"}]
        target = {
            "target_id": "gender",
            "variable": "gender",
            "categories": [
                {"category": "Male", "synthetic_categories": ["Male"], "target_proportion": 0.5},
                {"category": "Female", "synthetic_categories": ["Female"], "target_proportion": 0.5},
            ],
        }
        result = poststratify(rows, target, self._config())
        self.assertEqual(len(result["unresolved_targets"]), 1)

    def test_raking_converges_and_normalizes_weights(self) -> None:
        rows = self._population_rows()
        targets = usable_targets(load_official_targets(self.root, rows, self._config()))
        result = rake_weights(rows, targets, self._config())
        diagnostics = weight_diagnostics(rows, "calibration_weight")
        self.assertTrue(result["converged"])
        self.assertAlmostEqual(diagnostics["weight_sum"], len(rows), places=5)
        self.assertGreater(diagnostics["ess_ratio"], 0.8)

    def test_extreme_weight_trimming_and_no_invalid_weights(self) -> None:
        rows = [{"gender": "Male"}, {"gender": "Female"}]
        targets = [{
            "target_id": "gender",
            "variable": "gender",
            "categories": [
                {"category": "Male", "synthetic_categories": ["Male"], "target_proportion": 0.99},
                {"category": "Female", "synthetic_categories": ["Female"], "target_proportion": 0.01},
            ],
        }]
        config = self._config()
        config["weight_bounds"] = {"min": 0.2, "max": 1.5}
        result = rake_weights(rows, targets, config)
        diagnostics = weight_diagnostics(rows, "calibration_weight")
        self.assertGreater(result["trimming"]["trimmed_row_count"], 0)
        self.assertEqual(diagnostics["negative_weight_count"], 0)
        self.assertEqual(diagnostics["invalid_weight_count"], 0)

    def test_effective_sample_size_formula(self) -> None:
        self.assertEqual(effective_sample_size([1.0, 1.0, 1.0, 1.0]), 4.0)
        self.assertLess(effective_sample_size([4.0, 0.1, 0.1, 0.1]), 4.0)

    def test_pre_post_marginal_comparison_improves(self) -> None:
        rows = self._population_rows()
        targets = usable_targets(load_official_targets(self.root, rows, self._config()))
        before = compare_marginals(rows, targets)
        rake_weights(rows, targets, self._config())
        after = compare_marginals(rows, targets, "calibration_weight")
        self.assertLess(after["summary"]["mean_total_variation_distance"], before["summary"]["mean_total_variation_distance"])

    def test_full_service_writes_artifacts_and_phase6_handoff(self) -> None:
        result = Phase5CalibrationService(self.root).run()
        self.assertIn(result["status"], {"PASS", "PASS_WITH_WARNINGS"})
        self.assertTrue((self.root / result["calibrated_population_path"]).exists())
        self.assertTrue((self.root / result["phase6_handoff_path"]).exists())
        handoff = json.loads((self.root / result["phase6_handoff_path"]).read_text(encoding="utf-8"))
        self.assertEqual(handoff["policy_weight_column"], "calibration_weight")

    def test_original_population_attributes_remain_unchanged(self) -> None:
        original = self._population_rows()
        Phase5CalibrationService(self.root).run()
        calibrated = self._read_csv(self.root / "artifacts/calibrated_populations" / self._calibration_dir_name() / "population_calibrated.csv")
        for before, after in zip(original, calibrated):
            for key, value in before.items():
                self.assertEqual(after[key], value)

    def _write_fixture_project(self) -> None:
        population_dir = self.root / "artifacts/synthetic_populations/POP1"
        population_dir.mkdir(parents=True, exist_ok=True)
        rows = self._population_rows()
        write_csv(population_dir / "population.csv", rows)
        write_json(population_dir / "metadata.json", {"population_id": "POP1"})
        write_json(self.root / "data/synthetic/phase5_calibration_handoff.json", {
            "population_id": "POP1",
            "model_id": "MODEL1",
            "generator_type": "bootstrap",
            "validation_status": "PASS",
            "quality_score": 0.9,
            "selected_for_calibration": True,
            "warnings": [],
        })
        write_json(self.root / "data/synthetic/phase4_validation_manifest.json", {
            "synthetic_population_artifacts": [{
                "population_id": "POP1",
                "population_artifact": "artifacts/synthetic_populations/POP1/population.csv",
                "metadata_artifact": "artifacts/synthetic_populations/POP1/metadata.json",
            }]
        })
        (self.root / "config/calibration").mkdir(parents=True, exist_ok=True)
        (self.root / "config/calibration/calibration.yaml").write_text(
            "method: raking\nmax_iterations: 30\ntolerance: 0.001\ncalibration_variables:\n  - gender\n  - urban_rural\n  - social_group\nweight_bounds:\n  min: 0.2\n  max: 8.0\ntrimming:\n  enabled: true\nquality_gates:\n  max_marginal_error: 0.03\n  min_ess_ratio: 0.5\n  max_weight: 8.0\n  min_weight: 0.2\n  require_convergence: true\n  max_unresolved_targets: 0\n",
            encoding="utf-8",
        )
        write_csv(self.root / "data/calibration/gender_marginals.csv", [
            {"reference_year": "2011", "state": "Tamil Nadu", "gender": "Male", "population": 50, "proportion": 0.5, "source_id": "SRC", "quality_flag": "B"},
            {"reference_year": "2011", "state": "Tamil Nadu", "gender": "Female", "population": 50, "proportion": 0.5, "source_id": "SRC", "quality_flag": "B"},
        ])
        write_csv(self.root / "data/calibration/urban_rural_marginals.csv", [
            {"reference_year": "2011", "state": "Tamil Nadu", "urban_rural": "Urban", "population": 40, "proportion": 0.4, "source_id": "SRC", "quality_flag": "B"},
            {"reference_year": "2011", "state": "Tamil Nadu", "urban_rural": "Rural", "population": 60, "proportion": 0.6, "source_id": "SRC", "quality_flag": "B"},
        ])
        write_csv(self.root / "data/calibration/social_group_marginals.csv", [
            {"reference_year": "2011", "state": "Tamil Nadu", "social_group": "Scheduled Caste", "population": 20, "proportion": 0.2, "source_id": "SRC", "quality_flag": "B"},
            {"reference_year": "2011", "state": "Tamil Nadu", "social_group": "Scheduled Tribe", "population": 1, "proportion": 0.01, "source_id": "SRC", "quality_flag": "B"},
        ])
        write_csv(self.root / "data/calibration/state_population_marginals.csv", [{
            "reference_year": "2011",
            "state_code": "33",
            "state": "Tamil Nadu",
            "population_total": 100,
            "scheduled_caste_population": 20,
            "scheduled_tribe_population": 1,
            "source_id": "SRC",
            "quality_flag": "B",
        }])

    def _population_rows(self) -> list[dict[str, str]]:
        return [
            {"synthetic_person_id": "1", "gender": "Male", "urban_rural": "Urban", "social_group": "Scheduled Caste", "age": "20"},
            {"synthetic_person_id": "2", "gender": "Male", "urban_rural": "Urban", "social_group": "Other Backward Class", "age": "30"},
            {"synthetic_person_id": "3", "gender": "Male", "urban_rural": "Rural", "social_group": "Other Backward Class", "age": "40"},
            {"synthetic_person_id": "4", "gender": "Female", "urban_rural": "Rural", "social_group": "Others", "age": "50"},
            {"synthetic_person_id": "5", "gender": "Female", "urban_rural": "Rural", "social_group": "Scheduled Tribe", "age": "60"},
            {"synthetic_person_id": "6", "gender": "Female", "urban_rural": "Rural", "social_group": "Other Backward Class", "age": "70"},
        ]

    def _config(self) -> dict:
        return {
            "method": "raking",
            "max_iterations": 30,
            "tolerance": 0.001,
            "calibration_variables": ["gender", "urban_rural", "social_group"],
            "weight_bounds": {"min": 0.2, "max": 8.0},
            "trimming": {"enabled": True, "method": "absolute"},
            "quality_gates": {"max_marginal_error": 0.03, "min_ess_ratio": 0.5, "max_weight": 8.0, "min_weight": 0.2, "require_convergence": True, "max_unresolved_targets": 0},
        }

    def _read_csv(self, path: Path) -> list[dict[str, str]]:
        import csv
        with path.open("r", encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))

    def _calibration_dir_name(self) -> str:
        handoff = json.loads((self.root / "data/synthetic/phase6_policy_engine_handoff.json").read_text(encoding="utf-8"))
        return handoff["calibration_id"]


if __name__ == "__main__":
    unittest.main()
