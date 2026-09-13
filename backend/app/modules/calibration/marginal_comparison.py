from __future__ import annotations

from typing import Any

from backend.app.modules.calibration.utils import rounded, to_float


def compare_marginals(
    rows: list[dict[str, Any]],
    targets: list[dict[str, Any]],
    weight_column: str | None = None,
) -> dict[str, Any]:
    target_reports = []
    all_rows = []
    tvds = []
    max_errors = []
    mean_errors = []
    for target in targets:
        report = compare_target(rows, target, weight_column)
        target_reports.append(report)
        all_rows.extend(report["rows"])
        tvds.append(report["total_variation_distance"])
        max_errors.append(report["max_category_error"])
        mean_errors.append(report["mean_absolute_category_error"])
    return {
        "weight_column": weight_column or "unweighted",
        "target_reports": target_reports,
        "rows": all_rows,
        "summary": {
            "target_count": len(target_reports),
            "mean_total_variation_distance": rounded(sum(tvds) / len(tvds) if tvds else 0.0),
            "max_category_error": rounded(max(max_errors) if max_errors else 0.0),
            "mean_absolute_category_error": rounded(sum(mean_errors) / len(mean_errors) if mean_errors else 0.0),
        },
    }


def compare_target(rows: list[dict[str, Any]], target: dict[str, Any], weight_column: str | None = None) -> dict[str, Any]:
    variable = target["variable"]
    total_weight = sum(_row_weight(row, weight_column) for row in rows)
    rows_out = []
    target_props = {}
    synthetic_props = {}
    mapped_values = set()
    for category in target.get("categories", []):
        synthetic_categories = [str(value) for value in category.get("synthetic_categories", [])]
        mapped_values.update(synthetic_categories)
        synthetic_count = sum(_row_weight(row, weight_column) for row in rows if str(row.get(variable, "")) in synthetic_categories)
        synthetic_prop = synthetic_count / total_weight if total_weight else 0.0
        official_prop = float(category["target_proportion"])
        target_props[category["category"]] = official_prop
        synthetic_props[category["category"]] = synthetic_prop
        absolute_diff = abs(synthetic_prop - official_prop)
        rows_out.append({
            "target_id": target["target_id"],
            "variable": variable,
            "category": category["category"],
            "synthetic_categories": "|".join(synthetic_categories),
            "synthetic_count": rounded(synthetic_count),
            "synthetic_proportion": rounded(synthetic_prop),
            "official_count": category.get("official_count"),
            "official_proportion": rounded(official_prop),
            "absolute_proportion_difference": rounded(absolute_diff),
            "relative_difference": rounded(absolute_diff / official_prop) if official_prop else None,
            "status": category.get("status", "USABLE"),
        })
    unmapped_weight = sum(_row_weight(row, weight_column) for row in rows if str(row.get(variable, "")) not in mapped_values)
    unmapped_prop = unmapped_weight / total_weight if total_weight else 0.0
    if unmapped_weight:
        synthetic_props["UNMAPPED_SYNTHETIC"] = unmapped_prop
        target_props["UNMAPPED_SYNTHETIC"] = 0.0
        rows_out.append({
            "target_id": target["target_id"],
            "variable": variable,
            "category": "UNMAPPED_SYNTHETIC",
            "synthetic_categories": "categories not covered by target",
            "synthetic_count": rounded(unmapped_weight),
            "synthetic_proportion": rounded(unmapped_prop),
            "official_count": None,
            "official_proportion": 0.0,
            "absolute_proportion_difference": rounded(unmapped_prop),
            "relative_difference": None,
            "status": "WARNING",
        })
    diffs = [abs(synthetic_props.get(key, 0.0) - target_props.get(key, 0.0)) for key in set(target_props) | set(synthetic_props)]
    tvd = 0.5 * sum(diffs)
    return {
        "target_id": target["target_id"],
        "variable": variable,
        "weight_column": weight_column or "unweighted",
        "total_variation_distance": rounded(tvd),
        "max_category_error": rounded(max(diffs) if diffs else 0.0),
        "mean_absolute_category_error": rounded(sum(diffs) / len(diffs) if diffs else 0.0),
        "unmapped_synthetic_weight": rounded(unmapped_weight),
        "rows": rows_out,
    }


def _row_weight(row: dict[str, Any], weight_column: str | None) -> float:
    if not weight_column:
        return 1.0
    return to_float(row.get(weight_column), 0.0) or 0.0
