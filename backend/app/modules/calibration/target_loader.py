from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from backend.app.modules.calibration.utils import read_csv, rounded, to_float


@dataclass
class CalibrationTargetCategory:
    category: str
    synthetic_categories: list[str]
    target_proportion: float
    official_count: float | None
    geography: str
    reference_year: str
    source: str
    source_quality: str
    denominator: float | None
    category_mapping: str
    status: str = "USABLE"
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "synthetic_categories": self.synthetic_categories,
            "target_proportion": rounded(self.target_proportion),
            "official_count": rounded(self.official_count),
            "geography": self.geography,
            "reference_year": self.reference_year,
            "source": self.source,
            "source_quality": self.source_quality,
            "denominator": rounded(self.denominator),
            "category_mapping": self.category_mapping,
            "status": self.status,
            "warnings": self.warnings,
        }


@dataclass
class CalibrationTargetSet:
    target_id: str
    variable: str
    categories: list[CalibrationTargetCategory]
    status: str
    source_file: str
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_id": self.target_id,
            "variable": self.variable,
            "status": self.status,
            "source_file": self.source_file,
            "warnings": self.warnings,
            "categories": [category.to_dict() for category in self.categories],
        }


def load_official_targets(root: Path, population_rows: list[dict[str, Any]], config: dict[str, Any]) -> list[dict[str, Any]]:
    requested = set(config.get("calibration_variables", []))
    target_sets = [
        _direct_target(root, population_rows, "gender", "data/calibration/gender_marginals.csv", requested),
        _direct_target(root, population_rows, "urban_rural", "data/calibration/urban_rural_marginals.csv", requested),
        _social_group_target(root, population_rows, requested),
        _worker_target(root, population_rows, requested),
    ]
    return [target.to_dict() for target in target_sets if target is not None]


def usable_targets(target_sets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [target for target in target_sets if target.get("status") in {"USABLE", "USABLE_WITH_WARNINGS"}]


def _direct_target(
    root: Path,
    population_rows: list[dict[str, Any]],
    variable: str,
    source_file: str,
    requested: set[str],
) -> CalibrationTargetSet | None:
    if requested and variable not in requested:
        return None
    rows = read_csv(root / source_file)
    if not rows:
        return CalibrationTargetSet(f"{variable}_official_marginal", variable, [], "NOT_USABLE", source_file, ["Target file is missing or empty."])
    if population_rows and variable not in population_rows[0]:
        return CalibrationTargetSet(f"{variable}_official_marginal", variable, [], "NOT_USABLE", source_file, [f"Synthetic population does not contain {variable}."])
    categories = []
    for row in rows:
        category = row.get(variable, "")
        proportion = to_float(row.get("proportion"))
        if not category or proportion is None:
            continue
        categories.append(CalibrationTargetCategory(
            category=category,
            synthetic_categories=[category],
            target_proportion=proportion,
            official_count=to_float(row.get("population")),
            geography=row.get("state") or "Tamil Nadu",
            reference_year=row.get("reference_year", ""),
            source=row.get("source_id", ""),
            source_quality=row.get("quality_flag", ""),
            denominator=_denominator(rows),
            category_mapping=f"Exact synthetic {variable} category match.",
        ))
    return _validate_target_set(
        CalibrationTargetSet(f"{variable}_official_marginal", variable, categories, "USABLE", source_file),
        population_rows,
    )


def _social_group_target(root: Path, population_rows: list[dict[str, Any]], requested: set[str]) -> CalibrationTargetSet | None:
    variable = "social_group"
    source_file = "data/calibration/social_group_marginals.csv"
    if requested and variable not in requested:
        return None
    if population_rows and variable not in population_rows[0]:
        return CalibrationTargetSet("social_group_official_marginal", variable, [], "NOT_USABLE", source_file, ["Synthetic population does not contain social_group."])
    social_rows = read_csv(root / source_file)
    state_rows = read_csv(root / "data/calibration/state_population_marginals.csv")
    if not social_rows or not state_rows:
        return CalibrationTargetSet("social_group_official_marginal", variable, [], "NOT_USABLE", source_file, ["Required social_group/state population files are missing."])
    state = state_rows[0]
    denominator = to_float(state.get("population_total"))
    sc_count = to_float(state.get("scheduled_caste_population"))
    st_count = to_float(state.get("scheduled_tribe_population"))
    if not denominator or sc_count is None or st_count is None:
        return CalibrationTargetSet("social_group_official_marginal", variable, [], "NOT_USABLE", source_file, ["State population total or SC/ST counts are missing."])
    social_by_category = {row.get("social_group", ""): row for row in social_rows}
    common = {
        "geography": state.get("state") or "Tamil Nadu",
        "reference_year": state.get("reference_year", ""),
        "source": state.get("source_id", ""),
        "source_quality": state.get("quality_flag", ""),
        "denominator": denominator,
    }
    categories = [
        CalibrationTargetCategory(
            category="Scheduled Caste",
            synthetic_categories=["Scheduled Caste"],
            target_proportion=sc_count / denominator,
            official_count=sc_count,
            category_mapping="Exact social_group match.",
            **_category_meta(social_by_category.get("Scheduled Caste"), common),
        ),
        CalibrationTargetCategory(
            category="Scheduled Tribe",
            synthetic_categories=["Scheduled Tribe"],
            target_proportion=st_count / denominator,
            official_count=st_count,
            category_mapping="Exact social_group match.",
            **_category_meta(social_by_category.get("Scheduled Tribe"), common),
        ),
        CalibrationTargetCategory(
            category="Non-SC/ST",
            synthetic_categories=["Other Backward Class", "Others"],
            target_proportion=(denominator - sc_count - st_count) / denominator,
            official_count=denominator - sc_count - st_count,
            category_mapping="Derived residual non-SC/ST target from official population total minus official SC and ST counts; mapped to synthetic Other Backward Class + Others.",
            **common,
            warnings=["Official data does not split non-SC/ST into OBC and Others, so those synthetic categories are calibrated as one grouped residual."],
        ),
    ]
    target = CalibrationTargetSet("social_group_official_marginal_grouped", variable, categories, "USABLE_WITH_WARNINGS", source_file)
    target.warnings.append("Non-SC/ST target is an official residual grouping, not an official OBC/Others split.")
    return _validate_target_set(target, population_rows)


def _worker_target(root: Path, population_rows: list[dict[str, Any]], requested: set[str]) -> CalibrationTargetSet | None:
    variable = "worker_category"
    if requested and variable not in requested:
        return None
    if population_rows and variable not in population_rows[0]:
        return CalibrationTargetSet(
            "worker_category_official_marginal",
            variable,
            [],
            "NOT_USABLE",
            "data/calibration/worker_marginals.csv",
            ["Official worker_category marginals exist, but the selected synthetic population does not contain worker_category."],
        )
    return None


def _category_meta(row: dict[str, str] | None, common: dict[str, Any]) -> dict[str, Any]:
    if not row:
        return common
    return {
        "geography": row.get("state") or common["geography"],
        "reference_year": row.get("reference_year") or common["reference_year"],
        "source": row.get("source_id") or common["source"],
        "source_quality": row.get("quality_flag") or common["source_quality"],
        "denominator": common["denominator"],
    }


def _denominator(rows: list[dict[str, str]]) -> float | None:
    total = 0.0
    seen = False
    for row in rows:
        value = to_float(row.get("population"))
        if value is not None:
            total += value
            seen = True
    return total if seen else None


def _validate_target_set(target: CalibrationTargetSet, population_rows: list[dict[str, Any]]) -> CalibrationTargetSet:
    warnings = list(target.warnings)
    if not target.categories:
        target.status = "NOT_USABLE"
        target.warnings = warnings or ["No usable categories found."]
        return target
    total_prop = sum(category.target_proportion for category in target.categories)
    if abs(total_prop - 1.0) > 0.005:
        warnings.append(f"Target proportions sum to {total_prop:.6f}, not 1.0.")
    names = [category.category for category in target.categories]
    duplicate_names = sorted(name for name, count in Counter(names).items() if count > 1)
    if duplicate_names:
        warnings.append(f"Duplicate target categories: {', '.join(duplicate_names)}.")
    synthetic_values = set()
    if population_rows and target.variable in population_rows[0]:
        synthetic_values = {str(row.get(target.variable, "")) for row in population_rows}
    mapped_values = {value for category in target.categories for value in category.synthetic_categories}
    missing_from_synthetic = sorted(value for value in mapped_values if value not in synthetic_values)
    extra_synthetic = sorted(value for value in synthetic_values if value not in mapped_values)
    if missing_from_synthetic:
        warnings.append(f"Target categories absent from synthetic data: {', '.join(missing_from_synthetic)}.")
    if extra_synthetic:
        warnings.append(f"Synthetic categories not directly targeted: {', '.join(extra_synthetic)}.")
    for category in target.categories:
        if category.official_count is not None and category.official_count < 0:
            warnings.append(f"Negative official count for {category.category}.")
        if not category.reference_year:
            warnings.append(f"Missing reference year for {category.category}.")
        if not category.source:
            warnings.append(f"Missing source for {category.category}.")
        if category.geography != "Tamil Nadu":
            warnings.append(f"Unexpected geography for {category.category}: {category.geography}.")
    hard_errors = [warning for warning in warnings if warning.startswith("Target proportions") or warning.startswith("Duplicate") or warning.startswith("Negative")]
    if hard_errors:
        target.status = "NOT_USABLE"
    elif warnings or target.status == "USABLE_WITH_WARNINGS":
        target.status = "USABLE_WITH_WARNINGS"
    else:
        target.status = "USABLE"
    target.warnings = sorted(set(warnings))
    return target
