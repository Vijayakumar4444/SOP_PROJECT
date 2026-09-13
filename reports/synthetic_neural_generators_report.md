# Synthetic Neural Generators Report

- Training stack: SDV single-table neural synthesizers with pandas-backed tabular inputs.
- Unit-test policy: production-size CTGAN/TVAE training is kept out of ordinary unit tests.

## CTGAN

- Model ID: TN_CTGAN_A70E94D8A1
- Status: TRAINED
- Missing dependencies: None
- Blocking reason: 
- Training rows inspected: 12000
- Variables: district, district_code, urban_rural, age, gender, marital_status, relationship_to_head, household_size, household_type, literacy_status, education_level, labour_force_status, employment_status, individual_income, consumption_expenditure, social_group
- Artifact path: artifacts/synthetic_models/ctgan/TN_CTGAN_A70E94D8A1
- Result: trained artifacts are only reported when the SDV fit/save path succeeds.

## TVAE

- Model ID: TN_TVAE_7A020BB473
- Status: TRAINED
- Missing dependencies: None
- Blocking reason: 
- Training rows inspected: 12000
- Variables: district, district_code, urban_rural, age, gender, marital_status, relationship_to_head, household_size, household_type, literacy_status, education_level, labour_force_status, employment_status, individual_income, consumption_expenditure, social_group
- Artifact path: artifacts/synthetic_models/tvae/TN_TVAE_7A020BB473
- Result: trained artifacts are only reported when the SDV fit/save path succeeds.

- Registry path: artifacts/synthetic_models/model_registry.json
