from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.modules.synthetic_population.assessment import write_phase3_input_assessment


if __name__ == "__main__":
    print(write_phase3_input_assessment())

