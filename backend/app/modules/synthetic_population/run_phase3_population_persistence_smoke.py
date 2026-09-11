from __future__ import annotations

import sys
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.modules.data_foundation.io_utils import read_csv
from backend.app.modules.synthetic_population.assessment import read_json
from backend.app.modules.synthetic_population.population_persistence import (
    IDENTIFIER_FIELDS,
    SYNTHETIC_DATA_LABEL,
    run_population_persistence,
)


if __name__ == "__main__":
    manifest = run_population_persistence()
    assert manifest["population_count"] >= 1, "expected at least one persisted population"
    for item in manifest["populations"]:
        rows = read_csv(ROOT / item["population_csv_path"])
        assert len(rows) == item["rows"], f"row count mismatch for {item['population_id']}"
        synthetic_ids = [row["synthetic_person_id"] for row in rows]
        assert len(synthetic_ids) == len(set(synthetic_ids)), f"non-unique synthetic IDs for {item['population_id']}"
        assert synthetic_ids[0] == "TN-SYN-P-000000001", "unexpected first synthetic ID"
        assert not (IDENTIFIER_FIELDS & set(rows[0])), f"reference identifier leaked in {item['population_id']}"
        assert "synthetic_data_label" not in rows[0], "synthetic label should live in metadata, not person-level rows"
        metadata = read_json(ROOT / item["metadata_path"])
        assert metadata["synthetic_data_label"] == SYNTHETIC_DATA_LABEL, "mandatory synthetic label missing"
        assert metadata["id_policy"]["linked_to_real_identifiers"] is False, "ID policy must forbid real-ID linkage"
        assert metadata["export_formats"]["parquet"] == "skipped_missing_parquet_writer_dependency", "parquet warning missing"
    workbook_path = ROOT / "data/exports/tamil_nadu_synthetic_population_preview.xlsx"
    assert workbook_path.exists(), "Excel preview workbook missing"
    with zipfile.ZipFile(workbook_path) as archive:
        workbook_xml = archive.read("xl/workbook.xml").decode("utf-8")
    for sheet_name in [
        "00_README",
        "01_POPULATION_METADATA",
        "02_SYNTHETIC_SAMPLE",
        "03_VARIABLE_DICTIONARY",
        "04_GENERATION_CONFIG",
        "05_CONSTRAINT_SUMMARY",
        "06_MODEL_METADATA",
        "07_WARNINGS",
    ]:
        assert sheet_name in workbook_xml, f"missing preview sheet {sheet_name}"
    print("Phase 3 population persistence smoke passed.")
