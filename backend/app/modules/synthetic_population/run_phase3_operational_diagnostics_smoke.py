from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.modules.synthetic_population.operational_diagnostics import PRIVACY_WARNING, run_operational_diagnostics


if __name__ == "__main__":
    result = run_operational_diagnostics()
    assert result["models"], "expected diagnostics for trained models"
    assert result["gpu"]["required"] is False, "GPU must not be required"
    assert PRIVACY_WARNING in result["privacy_warning"], "privacy warning missing"
    for item in result["models"]:
        assert item["reproducibility"]["same_model_size_seed_reproducible"] is True, f"not reproducible: {item['model_id']}"
        assert item["performance"]["rows_per_second"] > 0, f"missing rows/sec: {item['model_id']}"
        assert item["artifact_safety"]["client_reference"] == "model_id", "client reference must be model_id"
        assert item["artifact_safety"]["exposes_executable_model_object"] is False, "must not expose executable model objects"
    print("Phase 3 operational diagnostics smoke passed.")
