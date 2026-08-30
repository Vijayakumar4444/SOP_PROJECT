# Synthetic Training Data Report

- Training rows: 8426
- Validation rows: 1790
- Holdout rows: 1784
- Total prepared rows: 12000
- Variables: district, district_code, urban_rural, age, gender, marital_status, relationship_to_head, household_size, household_type, literacy_status, education_level, labour_force_status, employment_status, individual_income, consumption_expenditure, social_group
- Variable types: {"age": "integer", "consumption_expenditure": "continuous", "district": "categorical", "district_code": "categorical", "education_level": "ordinal", "employment_status": "categorical", "gender": "categorical", "household_size": "integer", "household_type": "categorical", "individual_income": "continuous", "labour_force_status": "categorical", "literacy_status": "categorical", "marital_status": "categorical", "relationship_to_head": "categorical", "social_group": "categorical", "urban_rural": "categorical"}
- Missingness handling: categorical/ordinal blanks become Unknown; numeric blanks remain blank; fully missing fields are excluded.
- Weights: survey_weight, normalized_reference_weight, calibrated_reference_weight_gender_ur; preserved for weighted sampling, excluded from model features.
- Excluded variables: reference_person_id, reference_household_id, source_record_id, primary_source_id, state, state_code, age_group, employment_type, occupation_group, industry_group, household_income, income_band, dwelling_type, house_ownership, electricity, drinking_water, toilet_facility, cooking_fuel, health_insurance, survey_weight, normalized_reference_weight, calibrated_reference_weight_gender_ur, reference_year, record_quality_flag, disability_status
- Derived variables: age_group is derived after generation from age.
- Constraints: not implemented in this module; next module should add configurable hard constraints.
- Reference versions: phase3_training_v1 from data/processed/reference_template.csv.
- Output: data/synthetic/training/reference_training_v1.csv
