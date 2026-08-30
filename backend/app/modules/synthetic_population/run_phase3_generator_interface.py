from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.modules.synthetic_population.generator_training import train_available_generators


if __name__ == "__main__":
    results = train_available_generators()
    for result in results.values():
        print(result["model_id"])
        print(result["artifact_dir"])
        print(result["preview_path"])
    print(ROOT / "reports/synthetic_generator_interface_report.md")
