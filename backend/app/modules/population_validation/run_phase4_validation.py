from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.modules.population_validation.service import run_phase4_validation


if __name__ == "__main__":
    comparison = run_phase4_validation()
    print(comparison["selection"]["validation_status"])
    print(ROOT / "reports/phase4_model_comparison.md")
    print(ROOT / "reports/phase4_summary.md")
    print(ROOT / "data/synthetic/phase5_calibration_handoff.json")
