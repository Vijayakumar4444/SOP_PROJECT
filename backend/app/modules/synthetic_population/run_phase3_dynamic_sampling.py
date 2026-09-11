from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.modules.synthetic_population.sampling_service import run_dynamic_sampling_demo


if __name__ == "__main__":
    manifest = run_dynamic_sampling_demo()
    for item in manifest["demo_populations"]:
        print(item["population_id"])
        print(item["output_path"])
    print(ROOT / "data/synthetic/sampling/dynamic_sampling_manifest.json")
    print(ROOT / "reports/synthetic_dynamic_sampling_report.md")
