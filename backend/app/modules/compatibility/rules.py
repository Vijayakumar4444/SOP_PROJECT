ENGINE_VERSION = "TN_COMPATIBILITY_ENGINE_V0.1"
SCORING_CONFIG_VERSION = "compatibility_scoring_v0.1"

STATUS_SCORES = {
    "EXACT_AVAILABLE": 1.0,
    "DERIVABLE": 0.85,
    "PARTIALLY_AVAILABLE": 0.65,
    "PROXY_AVAILABLE": 0.45,
    "AGGREGATE_ONLY": 0.30,
    "MISSING": 0.0,
}

SCORING_WEIGHTS = {
    "domain": 0.15,
    "variable": 0.25,
    "availability": 0.20,
    "joint_availability": 0.15,
    "temporal": 0.10,
    "geographic": 0.10,
    "source_quality": 0.05,
}

ALIASES = {
    "sex": "gender", "unemployment_status": "employment_status", "work_status": "employment_status",
    "labour_status": "employment_status", "annual_household_income": "household_income",
    "household_annual_income": "household_income", "hh_income": "household_income",
    "earnings": "individual_income", "wage_income": "individual_income",
    "residence_state": "state", "district_name": "district", "residence_type": "urban_rural",
    "women_education": "education_level", "women_literacy": "literacy_status",
    "widow": "widow_status", "widowhood": "widow_status", "children": "number_of_children",
    "ration_card": "ration_card_type", "smart_card": "ration_card_type", "pds_card": "ration_card_type",
    "bank_account": "bank_account_ownership", "electricity_connection": "electricity",
}

DERIVATIONS = {
    "is_youth": ("age", "18 <= age <= 29"),
    "is_elderly": ("age", "age >= 60"),
    "is_unemployed": ("employment_status", "employment_status == 'Unemployed'"),
    "is_widow": ("widow_status", "widow_status == 'Yes'"),
    "is_female_head": ("female_head_of_household", "female_head_of_household == 'Yes'"),
}

PROXIES = {
    "household_income": {
        "proxy": "consumption_expenditure",
        "warning": "Household consumption expenditure is present, but it is not annual household income.",
    }
}

DOMAINS = {
    "EMPLOYMENT": {"core": {"employment_status", "labour_force_status", "occupation_category"}, "supporting": {"age", "gender", "education_level", "occupation_group", "industry_group", "industry_sector", "daily_wage", "formal_informal_work", "employment_sector", "district", "urban_rural"}},
    "INCOME": {"core": {"household_income", "individual_income", "income_band", "monthly_income"}, "supporting": {"consumption_expenditure", "bank_account_ownership", "social_group", "district", "urban_rural"}},
    "DEMOGRAPHICS": {"core": {"age", "gender", "state"}, "supporting": {"district", "urban_rural", "household_size", "female_head_of_household", "widow_status", "number_of_children", "number_of_dependents"}},
    "EDUCATION": {"core": {"age", "education_level"}, "supporting": {"gender", "literacy_status", "school_enrollment_status", "highest_qualification", "district", "urban_rural"}},
    "SOCIAL_WELFARE": {"core": {"social_group", "ration_card_type", "widow_status", "scheme_enrollment"}, "supporting": {"age", "gender", "district", "household_size", "state", "female_head_of_household", "number_of_children", "pds_benefits_received"}},
    "HOUSING": {"core": {"housing_type", "house_ownership", "dwelling_type", "electricity"}, "supporting": {"drinking_water", "toilet_facility", "cooking_fuel", "household_size", "district"}},
    "HEALTH": {"core": {"health_insurance", "disability_type", "health_status"}, "supporting": {"healthcare_access", "age", "gender", "district"}},
    "FINANCIAL_INCLUSION": {"core": {"bank_account_ownership", "income_band", "credit_access"}, "supporting": {"savings_account", "loan_outstanding", "individual_income", "consumption_expenditure", "gender", "district"}},
    "AGRICULTURE": {"core": {"land_ownership_status", "principal_crop"}, "supporting": {"land_size_acres", "irrigation_access", "district", "urban_rural"}},
    "MIGRATION": {"core": {"migration_status"}, "supporting": {"origin_district_state", "migration_reason", "age", "gender", "district"}},
    "WEALTH_AND_POVERTY": {"core": {"poverty_status", "wealth_quintile"}, "supporting": {"income_band", "consumption_expenditure", "social_group", "housing_type"}},
    "INFRASTRUCTURE_AND_CONNECTIVITY": {"core": {"electricity", "internet_access"}, "supporting": {"transport_access", "drinking_water", "toilet_facility", "cooking_fuel"}},
    "GOVERNMENT_WORKFORCE": {"core": {"is_government_employee", "government_department"}, "supporting": {"government_employment_type", "government_job_level", "government_service_type", "employment_sector"}},
    "HEALTHCARE_WORKFORCE": {"core": {"healthcare_worker", "healthcare_occupation"}, "supporting": {"medical_specialization", "healthcare_employment_sector", "health_insurance"}},
    "TEACHER_WORKFORCE": {"core": {"education_worker", "education_occupation"}, "supporting": {"teacher_type", "teaching_level", "education_level"}},
    "STUDENTS": {"core": {"is_student", "student_level"}, "supporting": {"school_type", "education_board", "institution_type", "currently_studying", "school_attendance_status", "not_studying_reason"}},
    "IT_SECTOR": {"core": {"it_sector_worker", "it_occupation"}, "supporting": {"technology_specialization", "employment_sector", "education_level"}},
    "UNEMPLOYMENT": {"core": {"actively_seeking_work", "duration_of_unemployment"}, "supporting": {"previous_occupation", "previous_employment_sector", "education_level", "work_experience_years"}},
}

TEMPORAL_SENSITIVITY = {
    "age": "MODERATE_CHANGE", "age_group": "MODERATE_CHANGE", "gender": "LOW_CHANGE",
    "state": "LOW_CHANGE", "district": "MODERATE_CHANGE", "urban_rural": "MODERATE_CHANGE",
    "household_size": "MODERATE_CHANGE", "employment_status": "HIGH_CHANGE",
    "labour_force_status": "HIGH_CHANGE", "individual_income": "HIGH_CHANGE",
    "household_income": "HIGH_CHANGE", "consumption_expenditure": "HIGH_CHANGE",
    "education_level": "MODERATE_CHANGE", "social_group": "LOW_CHANGE",
}

TEMPORAL_THRESHOLDS = {
    "LOW_CHANGE": (2, 5, 10),
    "MODERATE_CHANGE": (1, 3, 6),
    "HIGH_CHANGE": (1, 2, 4),
}
