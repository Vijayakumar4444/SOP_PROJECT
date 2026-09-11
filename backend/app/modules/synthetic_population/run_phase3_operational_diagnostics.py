from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.modules.synthetic_population.operational_diagnostics import run_operational_diagnostics


if __name__ == "__main__":
    result = run_operational_diagnostics()
    for item in result["models"]:
        print(item["model_id"])
        print(item["reproducibility"]["same_model_size_seed_reproducible"])
        print(item["performance"]["rows_per_second"])
    print(ROOT / "data/synthetic/diagnostics/phase3_operational_diagnostics.json")
    print(ROOT / "reports/synthetic_operational_diagnostics_report.md")
