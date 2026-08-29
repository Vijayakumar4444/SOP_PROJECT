from __future__ import annotations

from collections import Counter
from typing import Any

from .settings import REFERENCE_COLUMNS

NUMERIC_COLUMNS = {
    "age",
    "household_size",
    "individual_income",
    "household_income",
    "consumption_expenditure",
    "survey_weight",
    "normalized_reference_weight",
    "calibrated_reference_weight_gender_ur",
    "reference_year",
}


def distribution(records: list[dict[str, Any]], field: str) -> list[dict[str, Any]]:
    counts = Counter(row.get(field, "") or "Missing" for row in records)
    return [{"dimension": field, "category": key, "template_count": value, "template_proportion": value / len(records) if records else ""} for key, value in sorted(counts.items())]


def missingness(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{
        "dataset": "reference_template", "variable": col, "row_count": len(records),
        "missing_count": sum(1 for row in records if row.get(col, "") in ("", None)),
        "missing_percentage": (sum(1 for row in records if row.get(col, "") in ("", None)) / len(records)) if records else "",
    } for col in REFERENCE_COLUMNS]


def is_true(val: Any) -> bool:
    return str(val).strip().lower() in {"true", "1", "yes"}


def generate_macro_state_profile(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Generates comprehensive macro-level general state indicators for Tamil Nadu across demographics, education, employment, occupations, and amenities."""
    if not records:
        return []
    total = len(records)

    def pct(condition_fn) -> float:
        count = sum(1 for r in records if condition_fn(r))
        return round((count / total) * 100, 2)

    students = [r for r in records if is_true(r.get("is_student")) or r.get("employment_status") == "STUDENT"]
    total_students = len(students) if students else 1

    def student_pct(condition_fn) -> float:
        count = sum(1 for r in students if condition_fn(r))
        return round((count / total_students) * 100, 2)

    employed = [r for r in records if r.get("employment_status") in {"EMPLOYED", "SELF_EMPLOYED"}]
    total_employed = len(employed) if employed else 1

    def emp_pct(condition_fn) -> float:
        count = sum(1 for r in employed if condition_fn(r))
        return round((count / total_employed) * 100, 2)

    adult_females = [r for r in records if r.get("gender") == "Female" and int(r.get("age") or 0) >= 18]
    total_females = len(adult_females) if adult_females else 1

    profile = [
        # 1. Demographics
        {"domain": "Demographics", "indicator": "Male Population Share (%)", "value": pct(lambda r: r.get("gender") == "Male"), "benchmark_source": "PLFS 2024 / Census 2011"},
        {"domain": "Demographics", "indicator": "Female Population Share (%)", "value": pct(lambda r: r.get("gender") == "Female"), "benchmark_source": "PLFS 2024 / Census 2011"},
        {"domain": "Demographics", "indicator": "Urban Residence Share (%)", "value": pct(lambda r: r.get("urban_rural") == "Urban"), "benchmark_source": "Census 2011 / DES Handbook"},
        {"domain": "Demographics", "indicator": "Rural Residence Share (%)", "value": pct(lambda r: r.get("urban_rural") == "Rural"), "benchmark_source": "Census 2011 / DES Handbook"},
        {"domain": "Demographics", "indicator": "Senior Citizens (Age 60+) (%)", "value": pct(lambda r: int(r.get("age") or 0) >= 60), "benchmark_source": "Census 2011 / PLFS 2024"},

        # 2. Education & Literacy
        {"domain": "Education", "indicator": "Overall Literacy Rate (%)", "value": pct(lambda r: r.get("literacy_status") == "Literate"), "benchmark_source": "Census 2011 / NFHS-5 TN"},
        {"domain": "Education", "indicator": "Female Literacy Rate (%)", "value": round((sum(1 for r in adult_females if r.get("literacy_status") == "Literate") / total_females) * 100, 2), "benchmark_source": "NFHS-5 Tamil Nadu Report"},
        {"domain": "Education", "indicator": "Students in Government Schools (%)", "value": student_pct(lambda r: r.get("school_type") == "GOVERNMENT"), "benchmark_source": "UDISE+ 2024-25 Tamil Nadu Official Data (36.03%)"},
        {"domain": "Education", "indicator": "Students in Private Schools (%)", "value": student_pct(lambda r: r.get("school_type") == "PRIVATE"), "benchmark_source": "UDISE+ 2024-25 Tamil Nadu Official Data (48.14%)"},
        {"domain": "Education", "indicator": "Students in Govt-Aided Schools (%)", "value": student_pct(lambda r: r.get("school_type") == "GOVERNMENT_AIDED"), "benchmark_source": "UDISE+ 2024-25 Tamil Nadu Official Data (15.65%)"},
        {"domain": "Education", "indicator": "Students in Other Management Schools (%)", "value": student_pct(lambda r: r.get("school_type") == "OTHER"), "benchmark_source": "UDISE+ 2024-25 Tamil Nadu Official Data (0.18%)"},
        {"domain": "Education", "indicator": "Students on State Board (%)", "value": student_pct(lambda r: r.get("education_board") == "STATE_BOARD"), "benchmark_source": "Tamil Nadu School Education Dept"},
        {"domain": "Education", "indicator": "Students on CBSE Board (%)", "value": student_pct(lambda r: r.get("education_board") == "CBSE"), "benchmark_source": "CBSE Tamil Nadu Region Data"},
        {"domain": "Education", "indicator": "Students on ICSE/International Boards (%)", "value": student_pct(lambda r: r.get("education_board") in {"ICSE", "INTERNATIONAL"}), "benchmark_source": "CISCE Tamil Nadu Data"},

        # 3. Employment & Sectors
        {"domain": "Employment", "indicator": "Labour Force Participation Rate (%)", "value": pct(lambda r: r.get("employment_status") in {"EMPLOYED", "SELF_EMPLOYED", "UNEMPLOYED"}), "benchmark_source": "PLFS 2024 Tamil Nadu"},
        {"domain": "Employment", "indicator": "Worker Population Ratio (%)", "value": pct(lambda r: r.get("employment_status") in {"EMPLOYED", "SELF_EMPLOYED"}), "benchmark_source": "PLFS 2024 Tamil Nadu"},
        {"domain": "Employment", "indicator": "Unemployment Rate (%)", "value": pct(lambda r: r.get("employment_status") == "UNEMPLOYED"), "benchmark_source": "PLFS 2024 Tamil Nadu"},
        {"domain": "Employment", "indicator": "Government Employees Share (% of Workforce)", "value": emp_pct(lambda r: is_true(r.get("is_government_employee")) or r.get("employment_sector") in {"GOVERNMENT", "PUBLIC_SECTOR"}), "benchmark_source": "TN DES Employment Chapter"},
        {"domain": "Employment", "indicator": "Private Sector Workforce (% of Workforce)", "value": emp_pct(lambda r: r.get("employment_sector") == "PRIVATE"), "benchmark_source": "PLFS 2024 Tamil Nadu"},
        {"domain": "Employment", "indicator": "Self-Employed / Business Owners (% of Workforce)", "value": emp_pct(lambda r: is_true(r.get("self_employed")) or is_true(r.get("business_owner")) or r.get("employment_sector") == "SELF_EMPLOYED"), "benchmark_source": "PLFS 2024 Tamil Nadu"},
        {"domain": "Employment", "indicator": "Agriculture Sector Workforce (% of Workforce)", "value": emp_pct(lambda r: r.get("employment_sector") == "AGRICULTURE" or r.get("industry_sector") == "Agriculture_Allied"), "benchmark_source": "PLFS 2024 / NSS 77th Round"},
        {"domain": "Employment", "indicator": "Manufacturing & Construction (% of Workforce)", "value": emp_pct(lambda r: r.get("industry_sector") == "Manufacturing_Construction"), "benchmark_source": "PLFS 2024 Tamil Nadu"},
        {"domain": "Employment", "indicator": "Services & Trade Workforce (% of Workforce)", "value": emp_pct(lambda r: r.get("industry_sector") == "Services_Trade"), "benchmark_source": "PLFS 2024 Tamil Nadu"},
        {"domain": "Employment", "indicator": "Informal Work Share (% of Workforce)", "value": emp_pct(lambda r: r.get("formal_informal_status") == "INFORMAL"), "benchmark_source": "PLFS 2024 / MoSPI NSO"},

        # 4. Occupational Categories
        {"domain": "Occupations", "indicator": "Farmers & Agricultural Labourers (% of Population)", "value": pct(lambda r: r.get("occupation_category") in {"FARMER", "AGRICULTURAL_WORKER"}), "benchmark_source": "PLFS 2024 / NSS 77th Round"},
        {"domain": "Occupations", "indicator": "Teachers & Education Workers (% of Population)", "value": pct(lambda r: r.get("occupation_category") in {"TEACHER", "PROFESSOR", "LECTURER"} or is_true(r.get("education_worker")) or r.get("education_occupation") not in {"None", "", None}), "benchmark_source": "UDISE+ / DES Handbook"},
        {"domain": "Occupations", "indicator": "Doctors, Nurses & Healthcare Workers (% of Population)", "value": pct(lambda r: r.get("occupation_category") in {"DOCTOR", "NURSE", "HEALTHCARE_WORKER"} or is_true(r.get("healthcare_worker")) or r.get("healthcare_occupation") not in {"None", "", None}), "benchmark_source": "NFHS-5 / CMCHIS Registry"},
        {"domain": "Occupations", "indicator": "IT & Technology Professionals (% of Population)", "value": pct(lambda r: r.get("occupation_category") in {"IT_SOFTWARE", "DATA_PROFESSIONAL", "IT_SUPPORT"} or is_true(r.get("it_sector_worker")) or r.get("it_occupation") not in {"NONE", "None", "", None}), "benchmark_source": "PLFS 2024 Urban TN"},
        {"domain": "Occupations", "indicator": "Police & Public Safety Personnel (% of Population)", "value": pct(lambda r: r.get("occupation_category") in {"POLICE", "DEFENCE", "SECURITY_WORKER"} or is_true(r.get("public_safety_worker")) or is_true(r.get("police_employee"))), "benchmark_source": "TN Police / DES Handbook"},
        {"domain": "Occupations", "indicator": "Lawyers & Legal Professionals (% of Population)", "value": pct(lambda r: r.get("occupation_category") in {"LAWYER", "LEGAL_SUPPORT"} or r.get("legal_profession") not in {"None", "", None}), "benchmark_source": "Bar Council of TN Benchmark"},
        {"domain": "Occupations", "indicator": "Construction & Factory Workers (% of Population)", "value": pct(lambda r: r.get("occupation_category") in {"CONSTRUCTION_WORKER", "FACTORY_WORKER"}), "benchmark_source": "PLFS 2024 Tamil Nadu"},
        {"domain": "Occupations", "indicator": "Homemakers / Domestic Work (% of Population)", "value": pct(lambda r: r.get("employment_status") == "HOMEMAKER"), "benchmark_source": "PLFS 2024 Tamil Nadu"},
        {"domain": "Occupations", "indicator": "Senior Citizens Retired (% of Population)", "value": pct(lambda r: r.get("employment_status") == "RETIRED"), "benchmark_source": "PLFS 2024 / Census 2011"},

        # 5. Socio-Economic & Amenities
        {"domain": "SocioEconomic", "indicator": "Below Poverty Line (BPL) Share (%)", "value": pct(lambda r: r.get("poverty_status") == "BPL"), "benchmark_source": "NITI Aayog MPI / NFHS-5"},
        {"domain": "SocioEconomic", "indicator": "PDS Rice Ration Card Holders (%)", "value": pct(lambda r: r.get("ration_card_type") in {"PHH_Rice", "NPHH_Rice", "AAY"}), "benchmark_source": "TN Civil Supplies Smart Card Portal"},
        {"domain": "SocioEconomic", "indicator": "Bank Account Ownership Rate (%)", "value": pct(lambda r: r.get("bank_account_ownership") == "Yes"), "benchmark_source": "RBI Financial Inclusion Index"},
        {"domain": "SocioEconomic", "indicator": "Domestic Electricity Access Rate (%)", "value": pct(lambda r: r.get("electricity") == "Yes"), "benchmark_source": "NFHS-5 TN Table 14 / Census 2011"},
        {"domain": "SocioEconomic", "indicator": "Clean LPG Cooking Fuel Coverage (%)", "value": pct(lambda r: r.get("cooking_fuel") == "LPG_Clean"), "benchmark_source": "NFHS-5 TN Table 14"},
        {"domain": "SocioEconomic", "indicator": "Piped Tap Water Coverage (%)", "value": pct(lambda r: r.get("drinking_water") == "Piped_Tap"), "benchmark_source": "NFHS-5 TN Table 14"},
        {"domain": "SocioEconomic", "indicator": "Improved Sanitation / Toilet Coverage (%)", "value": pct(lambda r: r.get("toilet_facility") == "Flush_Improved"), "benchmark_source": "NFHS-5 TN Table 14"},
        {"domain": "SocioEconomic", "indicator": "Internet Access Coverage (%)", "value": pct(lambda r: r.get("internet_access") in {"Mobile_Broadband", "Fiber_Wifi"}), "benchmark_source": "TRAI TN Circle / NFHS-5"},
    ]
    return profile


def variable_dictionary() -> list[dict[str, Any]]:
    rows = []
    for col in REFERENCE_COLUMNS:
        rows.append({
            "canonical_variable": col, "display_name": col.replace("_", " "),
            "description": f"Canonical {col.replace('_', ' ')} field for the Tamil Nadu reference template.",
            "data_type": "number" if col in NUMERIC_COLUMNS else "string",
            "level": "HOUSEHOLD" if "household" in col or col == "relationship_to_head" else "PERSON",
            "unit": "INR or survey weight" if any(token in col for token in ["income", "expenditure", "weight"]) else "",
            "allowed_values": "", "minimum": 0 if any(token in col for token in ["age", "income", "expenditure", "weight", "size"]) else "",
            "maximum": 120 if col == "age" else "", "missing_allowed": "YES",
            "source_ids": "SRC_PLFS_2024_OPENCITY_PUBLIC_MIRROR", "source_variables": "See PLFS layout workbook in data/raw/plfs.",
            "harmonization_method": "Mapped by data_foundation harmonizer modules.",
            "derivation_method": "Derived from PLFS source fields or left null if unsupported.", "reference_year": "2024",
            "quality_flag": "A", "sensitivity_class": "MODERATE_OR_SENSITIVE" if col in {"social_group", "individual_income", "household_income", "consumption_expenditure"} else "LOW",
            "notes": "Do not impute unsupported variables during Phase 1.",
        })
    return rows

