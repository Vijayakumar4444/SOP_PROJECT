# Phase 3 Input Assessment

## Decision

- Implementation mode: PERSON-LEVEL SYNTHESIS
- Rationale: Phase 1 contains household IDs and household-size attributes, but there is no separate validated household table and several household-level variables are empty or proxy-limited. Phase 3 should therefore start with a person-level MVP.

## Phase 1 Reference Data

- Reference template path: data/processed/reference_template.csv
- Reference row count: 12000
- Reference household count: 3905
- Template metadata version: 0.3.0-modular
- Data foundation version: 0.3.0-modular
- Geographic coverage: Tamil Nadu; 37 district labels; urban/rural values: Rural, Urban
- Reference years: 2024

## Canonical Variables

- Canonical variables in reference template: 40
- Person-level variables: age, age_group, calibrated_reference_weight_gender_ur, consumption_expenditure, cooking_fuel, district, district_code, drinking_water, dwelling_type, education_level, electricity, employment_status, employment_type, gender, health_insurance, house_ownership, income_band, individual_income, industry_group, labour_force_status, literacy_status, marital_status, normalized_reference_weight, occupation_group, primary_source_id, record_quality_flag, reference_person_id, reference_year, social_group, source_record_id, state, state_code, survey_weight, toilet_facility, urban_rural
- Household-level variables: household_income, household_size, household_type, reference_household_id, relationship_to_head
- Identifier variables: reference_household_id, reference_person_id, source_record_id
- Metadata variables: primary_source_id, record_quality_flag, reference_year
- Continuous variables: consumption_expenditure, household_income, individual_income
- Integer variables: age, household_size
- Categorical variables: cooking_fuel, district, district_code, drinking_water, dwelling_type, electricity, employment_status, employment_type, gender, health_insurance, house_ownership, household_type, industry_group, labour_force_status, literacy_status, marital_status, occupation_group, relationship_to_head, social_group, state, state_code, toilet_facility, urban_rural
- Ordinal variables: age_group, education_level, income_band
- Boolean variables: None
- Derived variables: age_group

## Phase 2 Policy Requirements

- Policy-required variables: age, disability_status, district, education_level, employment_status, health_insurance, household_income, state
- Critical variables: age, disability_status, district, education_level, employment_status, health_insurance, household_income, state
- Optional analysis variables: None
- Approved derivations: None
- Approved proxies requiring explicit acknowledgement: household_income
- Calibration variables requested for later phases: gender, social_group, urban_rural, worker_category

## Weights And Missingness

- Survey-weight fields: calibrated_reference_weight_gender_ur, normalized_reference_weight, survey_weight
- Missingness summary:
  - district: 155 missing (1.2917%)
  - employment_type: 12000 missing (100.0%)
  - occupation_group: 6415 missing (53.4583%)
  - industry_group: 6415 missing (53.4583%)
  - household_income: 12000 missing (100.0%)
  - income_band: 12000 missing (100.0%)
  - dwelling_type: 12000 missing (100.0%)
  - house_ownership: 12000 missing (100.0%)
  - electricity: 12000 missing (100.0%)
  - drinking_water: 12000 missing (100.0%)
  - toilet_facility: 12000 missing (100.0%)
  - cooking_fuel: 12000 missing (100.0%)
  - health_insurance: 12000 missing (100.0%)

## Category Diagnostics

- High-cardinality variables: industry_group (532 values), occupation_group (113 values)
- Rare categories below 1%:
  - district: Karur (93, 0.775%); Nagapattinam (43, 0.358%); Perambalur (102, 0.85%); The Nilgiris (88, 0.733%)
  - district_code: 10 (88, 0.733%); 12 (93, 0.775%); 14 (102, 0.85%); 17 (43, 0.358%)
  - gender: Other (2, 0.017%)
  - industry_group: 01 (3, 0.025%); 01112 (82, 0.683%); 01113 (51, 0.425%); 01114 (10, 0.083%); 01116 (56, 0.467%); 01122 (6, 0.05%); 01123 (3, 0.025%); 01132 (3, 0.025%); 01133 (11, 0.092%); 01134 (26, 0.217%); 01135 (12, 0.1%); 01139 (39, 0.325%)
  - marital_status: 4 (84, 0.7%)
  - occupation_group: 111 (2, 0.017%); 121 (37, 0.308%); 122 (28, 0.233%); 131 (1, 0.008%); 132 (17, 0.142%); 133 (3, 0.025%); 134 (6, 0.05%); 141 (6, 0.05%); 142 (8, 0.067%); 143 (4, 0.033%); 214 (20, 0.167%); 215 (5, 0.042%)
  - relationship_to_head: 9 (5, 0.042%)
  - social_group: Scheduled Tribe (81, 0.675%)

## Official Marginals

- Available calibration/marginal files: data/calibration/calibration_diagnostics.csv, data/calibration/current_district_geography.csv, data/calibration/gender_marginals.csv, data/calibration/social_group_marginals.csv, data/calibration/state_population_marginals.csv, data/calibration/urban_rural_marginals.csv, data/calibration/worker_marginals.csv

## Known Limitations

- PLFS-only row template; DES/Census/data.gov.in are aggregate/provenance sources; NFHS/NSS manual access pending.
- Synthetic records must be explicitly labelled artificial and must not be treated as real residents or survey respondents.
- Aggregate-only variables must not be expanded into person-level values in Phase 3 without an explicit approved method.
- Full population validation, model selection, calibration/reweighting, policy execution, and Monte Carlo simulation belong to later phases.
