from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.modules.synthetic_population.phase3_finalization import run_phase3_finalization


if __name__ == "__main__":
    result = run_phase3_finalization()
    print(result["phase4_manifest"])
    print(result["summary_report"])
    print(result["definition_of_done_report"])
    for doc in result["documentation"]:
        print(doc)
