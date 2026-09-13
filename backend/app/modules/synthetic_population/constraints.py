from __future__ import annotations

from pathlib import Path
from typing import Any
import json

from backend.app.modules.data_foundation.io_utils import write_json, write_md
from backend.app.modules.synthetic_population.assessment import ROOT, read_csv


CONSTRAINT_VERSION = "phase3_constraints_v1"
RANGE_CONSTRAINTS = {
    "age": {"min": 0, "max": 120},
    "household_size": {"min": 1},
    "individual_income": {"min": 0},
    "consumption_expenditure": {"min": 0},
}
CATEGORY_CONSTRAINTS = {
    "gender": {"Male", "Female", "Other", "Not stated"},
    "urban_rural": {"Rural", "Urban"},
    "literacy_status": {"Literate", "Illiterate"},
    "employment_status": {"Employed", "Unemployed", "Not in labour force", "Other/Not stated"},
    "labour_force_status": {"Employed", "Unemployed", "Not in labour force", "Other/Not stated"},
    "social_group": {"Scheduled Tribe", "Scheduled Caste", "Other Backward Class", "Others"},
}
NUMERIC_BLANK_ALLOWED = {"individual_income", "consumption_expenditure"}


class SyntheticConstraintError(Exception):
    code = "SYNTHETIC_CONSTRAINT_ERROR"

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": str(self)}


class ConstraintEngine:
    def __init__(self, version: str = CONSTRAINT_VERSION):
        self.version = version

    def validate_row(self, row: dict[str, str], row_number: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        hard = []
        soft = []
        for field, rule in RANGE_CONSTRAINTS.items():
            value = row.get(field, "")
            if value == "" and field in NUMERIC_BLANK_ALLOWED:
                continue
            try:
                number = float(value)
            except ValueError:
                hard.append(self._issue(row_number, field, "RANGE_TYPE", f"{field} must be numeric."))
                continue
            if "min" in rule and number < rule["min"]:
                hard.append(self._issue(row_number, field, "RANGE_MIN", f"{field} is below {rule['min']}."))
            if "max" in rule and number > rule["max"]:
                hard.append(self._issue(row_number, field, "RANGE_MAX", f"{field} is above {rule['max']}."))
        for field, allowed in CATEGORY_CONSTRAINTS.items():
            value = row.get(field, "")
            if value and value not in allowed:
                hard.append(self._issue(row_number, field, "CATEGORY", f"{field} value is not configured."))
        age = self._number(row.get("age", ""))
        employment = row.get("employment_status", "")
        if age is not None and age < 15 and employment in {"Employed", "Unemployed"}:
            soft.append(self._issue(row_number, "employment_status", "CHILD_LABOUR_FORCE_STATUS", "Below-15 labour-force status is a soft anomaly for later review."))
        return hard, soft

    def validate_rows(self, rows: list[dict[str, str]]) -> dict[str, Any]:
        hard: list[dict[str, Any]] = []
        soft: list[dict[str, Any]] = []
        for index, row in enumerate(rows, start=1):
            row_hard, row_soft = self.validate_row(row, index)
            hard.extend(row_hard)
            soft.extend(row_soft)
        return {
            "constraint_version": self.version,
            "total_records": len(rows),
            "hard_violation_count": len(hard),
            "soft_anomaly_count": len(soft),
            "hard_violation_row_count": len({issue["row_number"] for issue in hard}),
            "soft_anomaly_row_count": len({issue["row_number"] for issue in soft}),
            "records_repaired": 0,
            "records_rejected": 0,
            "hard_violation_rate": round(len(hard) / len(rows) * 100, 4) if rows else 0,
            "soft_anomaly_rate": round(len(soft) / len(rows) * 100, 4) if rows else 0,
            "hard_violations_by_type": self._counts(hard),
            "soft_anomalies_by_type": self._counts(soft),
            "sample_hard_violations": hard[:20],
            "sample_soft_anomalies": soft[:20],
        }

    def _issue(self, row_number: int, field: str, issue_type: str, message: str) -> dict[str, Any]:
        return {"row_number": row_number, "field": field, "type": issue_type, "message": message}

    def _number(self, value: str) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _counts(self, issues: list[dict[str, Any]]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for issue in issues:
            key = issue["type"]
            counts[key] = counts.get(key, 0) + 1
        return dict(sorted(counts.items()))


def write_constraint_baseline_report(root: Path = ROOT) -> tuple[Path, Path]:
    training_path = root / "data/synthetic/training/reference_training_v1.csv"
    if not training_path.exists():
        raise SyntheticConstraintError("Prepared training dataset is missing. Run Phase 3 training preparation first.")
    rows = read_csv(training_path)
    summary = ConstraintEngine().validate_rows(rows)
    json_path = root / "data/synthetic/constraints/constraint_baseline_report.json"
    report_path = root / "reports/synthetic_constraint_baseline_report.md"
    write_json(json_path, summary)
    lines = [
        "# Synthetic Constraint Baseline Report", "",
        f"- Constraint version: {summary['constraint_version']}",
        f"- Total records checked: {summary['total_records']}",
        f"- Hard constraint violations: {summary['hard_violation_count']} ({summary['hard_violation_rate']}%)",
        f"- Soft anomalies: {summary['soft_anomaly_count']} ({summary['soft_anomaly_rate']}%)",
        f"- Records repaired: {summary['records_repaired']}",
        f"- Records rejected: {summary['records_rejected']}",
        f"- Hard violation types: {json.dumps(summary['hard_violations_by_type'], sort_keys=True)}",
        f"- Soft anomaly types: {json.dumps(summary['soft_anomalies_by_type'], sort_keys=True)}",
        "- Repair policy: disabled for this module; invalid generation should be visible in reports.",
        "- Note: this report validates the prepared reference-training data. Future generation reports must run the same engine on generated populations.",
    ]
    write_md(report_path, "\n".join(lines))
    return report_path, json_path
