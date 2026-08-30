from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.modules.synthetic_population.neural_training import attempt_neural_generators


if __name__ == "__main__":
    result = attempt_neural_generators()
    for item in result["results"]:
        print(item["model_id"])
        print(item["status"])
        print(item.get("blocking_reason", ""))
    print(result["report_path"])
