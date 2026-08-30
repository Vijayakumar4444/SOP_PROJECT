from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.modules.synthetic_population.constraints import write_constraint_baseline_report


if __name__ == "__main__":
    report_path, json_path = write_constraint_baseline_report()
    print(report_path)
    print(json_path)
