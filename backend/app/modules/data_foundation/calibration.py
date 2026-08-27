from __future__ import annotations

from collections import Counter
from typing import Any

OFFICIAL_GENDER_UR = {
    ("Male", "Rural"): 18867932,
    ("Female", "Rural"): 18361658,
    ("Male", "Urban"): 17270043,
    ("Female", "Urban"): 17647397,
}


def normalize_weights(records: list[dict[str, Any]]) -> None:
    weights = [float(row["survey_weight"]) for row in records if row["survey_weight"] != ""]
    total = sum(weights)
    if total <= 0:
        return
    for row in records:
        row["normalized_reference_weight"] = "" if row["survey_weight"] == "" else float(row["survey_weight"]) * len(records) / total


def calibrate_gender_urban_rural(records: list[dict[str, Any]]) -> None:
    sample_weight = Counter()
    for row in records:
        key = (row["gender"], row["urban_rural"])
        if key in OFFICIAL_GENDER_UR and row["normalized_reference_weight"] != "":
            sample_weight[key] += float(row["normalized_reference_weight"])
    total_official = sum(OFFICIAL_GENDER_UR.values())
    total_sample = sum(sample_weight.values())
    factors = {}
    for key, official in OFFICIAL_GENDER_UR.items():
        sample_share = sample_weight[key] / total_sample if total_sample else 0
        official_share = official / total_official
        factors[key] = official_share / sample_share if sample_share else 1.0
    for row in records:
        if row["normalized_reference_weight"] != "":
            row["calibrated_reference_weight_gender_ur"] = float(row["normalized_reference_weight"]) * factors.get((row["gender"], row["urban_rural"]), 1.0)


def state_marginals() -> list[dict[str, Any]]:
    return [{
        "reference_year": 2011, "state_code": "33", "state": "Tamil Nadu",
        "population_total": 72147030, "male_population": 36137975, "female_population": 36009055,
        "urban_population": 34917440, "rural_population": 37229590, "literates_total": 51837507,
        "scheduled_caste_population": 14438445, "scheduled_tribe_population": 794697,
        "total_workers": 32884681, "main_workers": 27942181, "marginal_workers": 4942500,
        "non_workers": 39262349, "source_id": "SRC_TN_DES_GLANCE_2023_24;SRC_CENSUS_PCA_SD_2011",
        "quality_flag": "B", "notes": "Census 2011 values from official TN DES At a Glance / Census PCA provenance.",
    }]


def gender_marginals() -> list[dict[str, Any]]:
    total = 72147030
    return [
        {"reference_year": 2011, "state": "Tamil Nadu", "gender": "Male", "population": 36137975, "proportion": 36137975 / total, "source_id": "SRC_TN_DES_GLANCE_2023_24;SRC_CENSUS_PCA_SD_2011", "quality_flag": "B"},
        {"reference_year": 2011, "state": "Tamil Nadu", "gender": "Female", "population": 36009055, "proportion": 36009055 / total, "source_id": "SRC_TN_DES_GLANCE_2023_24;SRC_CENSUS_PCA_SD_2011", "quality_flag": "B"},
    ]


def urban_rural_marginals() -> list[dict[str, Any]]:
    total = 72147030
    return [
        {"reference_year": 2011, "state": "Tamil Nadu", "urban_rural": "Urban", "population": 34917440, "proportion": 34917440 / total, "source_id": "SRC_TN_DES_GLANCE_2023_24;SRC_CENSUS_PCA_SD_2011", "quality_flag": "B"},
        {"reference_year": 2011, "state": "Tamil Nadu", "urban_rural": "Rural", "population": 37229590, "proportion": 37229590 / total, "source_id": "SRC_TN_DES_GLANCE_2023_24;SRC_CENSUS_PCA_SD_2011", "quality_flag": "B"},
    ]


def social_marginals() -> list[dict[str, Any]]:
    total = 72147030
    return [
        {"reference_year": 2011, "state": "Tamil Nadu", "social_group": "Scheduled Caste", "population": 14438445, "proportion": 14438445 / total, "source_id": "SRC_TN_DES_GLANCE_2023_24;SRC_CENSUS_PCA_SD_2011", "quality_flag": "B"},
        {"reference_year": 2011, "state": "Tamil Nadu", "social_group": "Scheduled Tribe", "population": 794697, "proportion": 794697 / total, "source_id": "SRC_TN_DES_GLANCE_2023_24;SRC_CENSUS_PCA_SD_2011", "quality_flag": "B"},
    ]


def worker_marginals() -> list[dict[str, Any]]:
    total = 72147030
    values = {"Total workers": 32884681, "Main workers": 27942181, "Marginal workers": 4942500, "Non-workers": 39262349}
    return [{"reference_year": 2011, "state": "Tamil Nadu", "worker_category": k, "population": v, "proportion": v / total, "source_id": "SRC_TN_DES_GLANCE_2023_24;SRC_CENSUS_PCA_SD_2011", "quality_flag": "B"} for k, v in values.items()]


def calibration_diagnostics(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sample, calibrated = Counter(), Counter()
    for row in records:
        key = f"{row['gender']}|{row['urban_rural']}"
        if row["normalized_reference_weight"] != "":
            sample[key] += float(row["normalized_reference_weight"])
        if row["calibrated_reference_weight_gender_ur"] != "":
            calibrated[key] += float(row["calibrated_reference_weight_gender_ur"])
    sample_total, cal_total, official_total = sum(sample.values()), sum(calibrated.values()), sum(OFFICIAL_GENDER_UR.values())
    return [{
        "calibration_dimension": "gender_x_urban_rural", "category": f"{g}|{ur}",
        "official_share": official / official_total,
        "sample_weighted_share_before": sample[f"{g}|{ur}"] / sample_total if sample_total else "",
        "sample_weighted_share_after": calibrated[f"{g}|{ur}"] / cal_total if cal_total else "",
        "source_id": "SRC_TN_DES_GLANCE_2023_24;SRC_CENSUS_PCA_SD_2011",
        "method": "post-stratification factor on normalized_reference_weight; original source rows unchanged",
    } for (g, ur), official in OFFICIAL_GENDER_UR.items()]
