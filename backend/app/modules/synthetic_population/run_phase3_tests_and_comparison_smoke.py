from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.modules.synthetic_population.model_comparison import run_model_comparison_manifest
from backend.app.modules.synthetic_population.phase3_tests import run_phase3_test_suite


if __name__ == "__main__":
    tests = run_phase3_test_suite()
    assert tests["status"] == "PASSED", "Phase 3 test suite failed"
    assert len(tests["results"]) >= 7, "expected Phase 3 coverage cases"
    comparison = run_model_comparison_manifest()
    generators = {item["generator"] for item in comparison["models"]}
    assert {"bootstrap", "gaussian_copula", "ctgan", "tvae"}.issubset(generators), "comparison manifest missing generators"
    assert "Do not select a best model" in comparison["phase4_consumption_note"], "best-model warning missing"
    trained = [item for item in comparison["models"] if item["status"] == "TRAINED"]
    assert all(item["population_ids"] for item in trained), "trained models must have candidate population IDs"
    print("Phase 3 tests and model comparison smoke passed.")
