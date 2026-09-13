from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.modules.calibration.service import run_phase5_calibration


if __name__ == "__main__":
    result = run_phase5_calibration()
    print(result["status"])
    print(result["calibration_id"])
    print(ROOT / result["calibrated_population_path"])
    print(ROOT / result["phase6_handoff_path"])
