from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import csv
import zipfile

from .harmonizers import age_group, education, employment, employment_type, gender, household_type, num, social_group, urban_rural
from .settings import ROOT, TARGET_RECORDS, TN_STATE_CODE
from .io_utils import read_csv
from .calibration import calibrate_gender_urban_rural, normalize_weights


def household_key(row: dict[str, str]) -> tuple[str, ...]:
    cols = ["PANEL", "QTR", "VISIT", "SEC", "ST", "DC", "NSS_REG", "STRM", "SSTRM", "SS", "SRO", "MFSU", "SEG", "SSS", "SSU"]
    return tuple(row.get(col, "") for col in cols)


def extract_person_csv() -> Path:
    zip_path = ROOT / "data/raw/plfs/plfs_2024_personal_data.zip"
    out_dir = ROOT / "data/staging/plfs_2024_personal"
    csv_path = out_dir / "cperv1.csv"
    if zip_path.exists() and not csv_path.exists():
        out_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path) as archive:
            archive.extractall(out_dir)
    return csv_path


def load_tn_districts() -> dict[str, str]:
    path = ROOT / "data/raw/plfs/plfs_2024_state_district_codes.csv"
    if not path.exists():
        return {}
    return {row["district_code"].zfill(2): row["district_name"] for row in read_csv(path) if row.get("state_code") == TN_STATE_CODE}


def load_tn_households() -> dict[tuple[str, ...], dict[str, str]]:
    path = ROOT / "data/raw/plfs/plfs_2024_household_data.csv"
    households = {}
    if not path.exists():
        return households
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("ST") == TN_STATE_CODE:
                households[household_key(row)] = row
    return households


def stable_hash(text: str) -> int:
    h = 0
    for char in text:
        h = ((h * 31) + ord(char)) & 0xFFFFFFFF
    return h


def stratified_sample(records: list[dict], target: int) -> list[dict]:
    if len(records) <= target:
        return records
    groups = defaultdict(list)
    for record in records:
        groups[(record["district"], record["urban_rural"], record["gender"], record["age_group"])].append(record)
    selected, remaining = [], target
    entries = list(groups.items())
    for idx, (_, group) in enumerate(entries):
        group.sort(key=lambda item: stable_hash(str(item["source_record_id"])))
        groups_left = len(entries) - idx
        take = max(1, min(len(group), round(len(group) / len(records) * target), remaining - groups_left + 1))
        selected.extend(group[:take])
        remaining -= take
    if len(selected) < target:
        ids = {row["source_record_id"] for row in selected}
        extras = sorted((row for row in records if row["source_record_id"] not in ids), key=lambda item: stable_hash(str(item["source_record_id"])))
        selected.extend(extras[: target - len(selected)])
    return selected[:target]


def build_reference() -> tuple[list[dict], int]:
    person_path = extract_person_csv()
    if not person_path.exists():
        return [], 0
    districts = load_tn_districts()
    households = load_tn_households()
    records, source_rows = [], 0
    with person_path.open("r", encoding="utf-8-sig", newline="") as handle:
        for person in csv.DictReader(handle):
            if person.get("ST") != TN_STATE_CODE:
                continue
            source_rows += 1
            household = households.get(household_key(person), {})
            key = household_key(person)
            dc = person.get("DC", "").zfill(2)
            record = {
                "reference_person_id": "",
                "reference_household_id": "PLFS2024_TN_H" + "_".join(key),
                "source_record_id": "|".join(key) + "_" + person.get("SRL", ""),
                "primary_source_id": "SRC_PLFS_2024_OPENCITY_PUBLIC_MIRROR",
                "state": "Tamil Nadu", "state_code": TN_STATE_CODE,
                "district": districts.get(dc, ""), "district_code": dc,
                "urban_rural": urban_rural(person.get("SEC", "")),
                "age": num(person.get("AGE")), "age_group": age_group(person.get("AGE", "")),
                "gender": gender(person.get("SEX", "")), "marital_status": person.get("MARST", ""),
                "relationship_to_head": person.get("REL", ""), "household_size": num(household.get("HH_SIZE")),
                "household_type": household_type(household.get("HHTYPE")),
                "literacy_status": "Illiterate" if person.get("GEDU_LVL") == "01" else "Literate",
                "education_level": education(person.get("GEDU_LVL", "")),
                "labour_force_status": employment(person), "employment_status": employment(person),
                "employment_type": employment_type(person),
                "occupation_group": person.get("OCU_PAS") or person.get("OCU_SAS") or person.get("OCU_CWS") or "",
                "industry_group": person.get("IND_PAS") or person.get("IND_SAS") or person.get("AIND_CWS") or "",
                "individual_income": num(person.get("ERN_REG") or person.get("ERN_SELF")),
                "household_income": "", "consumption_expenditure": num(household.get("HCE_TOT")),
                "income_band": "", "dwelling_type": "", "house_ownership": "", "electricity": "",
                "drinking_water": "", "toilet_facility": "", "cooking_fuel": "", "health_insurance": "",
                "social_group": social_group(household.get("SG")), "survey_weight": num(person.get("MULT")),
                "normalized_reference_weight": "", "calibrated_reference_weight_gender_ur": "",
                "reference_year": 2024, "record_quality_flag": "A",
            }
            records.append(record)
    records = stratified_sample(records, TARGET_RECORDS)
    normalize_weights(records)
    calibrate_gender_urban_rural(records)
    for i, record in enumerate(records, start=1):
        record["reference_person_id"] = f"PLFS2024_TN_P{i:06d}"
    return records, source_rows
