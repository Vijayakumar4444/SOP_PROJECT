from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.modules.synthetic_population.assessment import read_json
from backend.app.modules.synthetic_population.phase3_finalization import NO_BEST_MODEL_WARNING, run_phase3_finalization


if __name__ == "__main__":
    result = run_phase3_finalization()
    phase4 = read_json(ROOT / result["phase4_manifest"])
    assert phase4["holdout_reference_artifact"], "holdout artifact missing"
    assert len(phase4["synthetic_population_artifacts"]) >= 2, "expected acceptance populations for trained models"
    assert NO_BEST_MODEL_WARNING in phase4["warning"], "no-best-model warning missing"
    for item in phase4["synthetic_population_artifacts"]:
        assert item["population_size"] == 12000, "acceptance population must be 12,000 rows"
        assert item["constraint_results"]["hard_violation_count"] == 0, "hard constraint violation in acceptance population"
    for path in result["documentation"]:
        assert (ROOT / path).exists(), f"missing documentation {path}"
    assert (ROOT / result["summary_report"]).exists(), "phase3 summary missing"
    assert (ROOT / result["definition_of_done_report"]).exists(), "definition-of-done report missing"
    print("Phase 3 finalization smoke passed.")
