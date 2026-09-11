from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.modules.synthetic_population.population_persistence import run_population_persistence


if __name__ == "__main__":
    manifest = run_population_persistence()
    for item in manifest["populations"]:
        print(item["population_id"])
        print(item["population_csv_path"])
        print(item["metadata_path"])
        print(item["generation_report_md_path"])
    print(ROOT / "data/synthetic/population_persistence_manifest.json")
    print(ROOT / "reports/synthetic_population_persistence_report.md")
    print(ROOT / "data/exports/tamil_nadu_synthetic_population_preview.xlsx")
