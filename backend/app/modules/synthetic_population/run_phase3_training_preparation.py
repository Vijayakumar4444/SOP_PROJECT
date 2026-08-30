from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.modules.synthetic_population.training_preparation import prepare_training_data


if __name__ == "__main__":
    result = prepare_training_data()
    print(result["training_path"])
    print(result["manifest_path"])
    print(result["missing_report"])
    print(result["training_report"])
