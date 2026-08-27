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
}

DERIVATIONS = {
    "is_youth": ("age", "18 <= age <= 29"),
    "is_elderly": ("age", "age >= 60"),
    "is_unemployed": ("employment_status", "employment_status == 'Unemployed'"),
}

PROXIES = {
    "household_income": {
        "proxy": "consumption_expenditure",
        "warning": "Household consumption expenditure is present, but it is not annual household income.",
    }
}

DOMAINS = {
    "EMPLOYMENT": {"core": {"employment_status", "labour_force_status"}, "supporting": {"age", "gender", "education_level", "occupation_group", "industry_group", "district", "urban_rural"}},
    "INCOME": {"core": {"household_income", "individual_income"}, "supporting": {"consumption_expenditure", "social_group", "district", "urban_rural"}},
    "DEMOGRAPHICS": {"core": {"age", "gender", "state"}, "supporting": {"district", "urban_rural", "household_size"}},
    "EDUCATION": {"core": {"age", "education_level"}, "supporting": {"gender", "district", "urban_rural"}},
    "SOCIAL_WELFARE": {"core": {"social_group", "state"}, "supporting": {"age", "gender", "district", "household_size"}},
    "HOUSING": {"core": {"house_ownership", "dwelling_type"}, "supporting": {"household_size", "district"}},
    "HEALTH": {"core": {"health_insurance", "disability_status"}, "supporting": {"age", "gender", "district"}},
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
