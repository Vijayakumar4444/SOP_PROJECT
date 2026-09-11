from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.modules.synthetic_population.sampling_service import DynamicSamplingService


if __name__ == "__main__":
    service = DynamicSamplingService(ROOT)
    try:
        service.generate_population(generator="bootstrap", size=999, seed=1)
        raise AssertionError("Unsupported size should fail")
    except Exception as exc:
        assert "Unsupported size" in str(exc)
    try:
        service.generate_population(generator="bootstrap", size=1000, seed=1, mode="CONDITIONAL", conditions={"not_a_field": "x"})
        raise AssertionError("Unsupported condition field should fail")
    except Exception as exc:
        assert "Unsupported condition fields" in str(exc)
    conditional = ROOT / "data/synthetic/sampling/SYNPOP-BOOTSTRAP-CONDITIONAL-1000-43-COND54D3C7AA.csv"
    with conditional.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1000
    assert all(row["urban_rural"] == "Rural" for row in rows)
    print("Module 8 dynamic sampling smoke passed")
