from __future__ import annotations

from typing import Any


def num(value: str | None) -> Any:
    if value in (None, ""):
        return ""
    try:
        parsed = float(value)
    except ValueError:
        return ""
    return int(parsed) if parsed.is_integer() else parsed


def age_group(value: str) -> str:
    age = num(value)
    if age == "":
        return ""
    if age <= 14:
        return "0-14"
    if age <= 24:
        return "15-24"
    if age <= 44:
        return "25-44"
    if age <= 59:
        return "45-59"
    return "60+"


def gender(code: str) -> str:
    return {"1": "Male", "2": "Female", "3": "Other"}.get(code, "Not stated")


def urban_rural(sec: str) -> str:
    return {"1": "Rural", "2": "Urban"}.get(sec, "")


def education(code: str) -> str:
    try:
        value = int(code)
    except ValueError:
        return ""
    if value == 1:
        return "Not literate"
    if value in {2, 3, 4, 5}:
        return "Below Primary"
    if value == 6:
        return "Primary"
    if value == 7:
        return "Middle"
    if value == 8:
        return "Secondary"
    if value == 10:
        return "Higher Secondary"
    if value in {11, 12, 13}:
        return "Diploma/Certificate"
    if value == 14:
        return "Graduate"
    if value >= 15:
        return "Postgraduate and above"
    return "Other/Not stated"


def employment(row: dict[str, str]) -> str:
    try:
        pas = int(row.get("PAS", ""))
    except ValueError:
        return ""
    if 11 <= pas <= 51:
        return "Employed"
    if pas == 81:
        return "Unemployed"
    if 91 <= pas <= 99:
        return "Not in labour force"
    return "Other/Not stated"


def employment_type(row: dict[str, str]) -> str:
    return {"1": "Self-employed", "2": "Regular wage/salaried", "3": "Casual labour"}.get(row.get("ETYP_PAS") or row.get("ETYP_SAS"), "")


def social_group(code: str | None) -> str:
    return {"1": "Scheduled Tribe", "2": "Scheduled Caste", "3": "Other Backward Class", "9": "Others"}.get(code or "", "")


def household_type(code: str | None) -> str:
    return {
        "1": "Self-employed in agriculture",
        "2": "Self-employed in non-agriculture",
        "3": "Regular wage/salary earning",
        "4": "Casual labour in agriculture",
        "5": "Casual labour in non-agriculture",
        "9": "Others",
    }.get(code or "", "")
