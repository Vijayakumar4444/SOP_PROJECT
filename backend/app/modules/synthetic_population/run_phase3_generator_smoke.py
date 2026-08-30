from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.modules.synthetic_population.generators.bootstrap import BootstrapBaselineGenerator


if __name__ == "__main__":
    model_path = ROOT / "artifacts/synthetic_models/bootstrap/TN_BOOTSTRAP_BASELINE_1D08E0184C"
    model = BootstrapBaselineGenerator.load(model_path)
    first = model.sample(5, seed=99)
    second = model.sample(5, seed=99)
    assert len(first) == 5
    assert first == second
    assert "reference_person_id" not in first[0]
    assert "source_record_id" not in first[0]
    assert first[0]["synthetic_data_label"] == "RESAMPLED_BASELINE"
    print("Module 5 smoke passed")
