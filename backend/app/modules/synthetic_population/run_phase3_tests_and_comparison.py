from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.modules.synthetic_population.model_comparison import run_model_comparison_manifest
from backend.app.modules.synthetic_population.phase3_tests import run_phase3_test_suite


if __name__ == "__main__":
    tests = run_phase3_test_suite()
    comparison = run_model_comparison_manifest()
    print(tests["status"])
    print(ROOT / "data/synthetic/phase3_test_manifest.json")
    print(ROOT / "reports/phase3_test_report.md")
    print(len(comparison["models"]))
    print(ROOT / "data/synthetic/model_comparison_manifest.json")
    print(ROOT / "reports/synthetic_model_comparison_manifest_report.md")
