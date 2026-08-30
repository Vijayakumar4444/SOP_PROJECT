from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.modules.synthetic_population.generators.gaussian_copula import GaussianCopulaGenerator
from backend.app.modules.synthetic_population.constraints import ConstraintEngine


if __name__ == "__main__":
    model_path = ROOT / "artifacts/synthetic_models/gaussian_copula/TN_GAUSSIAN_COPULA_CB9DD0CE87"
    model = GaussianCopulaGenerator.load(model_path)
    first = model.sample(25, seed=123)
    second = model.sample(25, seed=123)
    assert len(first) == 25
    assert first == second
    assert "reference_person_id" not in first[0]
    assert "source_record_id" not in first[0]
    assert first[0]["synthetic_data_label"] == "SYNTHETIC_GAUSSIAN_COPULA_CANDIDATE"
    summary = ConstraintEngine().validate_rows(first)
    assert summary["hard_violation_count"] == 0
    print("Module 6 Gaussian smoke passed")
