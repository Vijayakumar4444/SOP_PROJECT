# Synthetic Neural Generators Report

- Dependency action: no packages were installed silently.
- Expected optional stack: SDV/pandas and their model dependencies.
- Unit-test policy: expensive CTGAN/TVAE training must not run in normal tests.

## CTGAN

- Model ID: TN_CTGAN_BLOCKED_DEPENDENCIES
- Status: BLOCKED
- Missing dependencies: sdv, pandas
- Blocking reason: ctgan training is blocked because optional dependencies are missing: sdv, pandas.
- Training rows inspected: 12000
- Variables: district, district_code, urban_rural, age, gender, marital_status, relationship_to_head, household_size, household_type, literacy_status, education_level, labour_force_status, employment_status, individual_income, consumption_expenditure, social_group
- Result: no model artifact or synthetic population was fabricated.

## TVAE

- Model ID: TN_TVAE_BLOCKED_DEPENDENCIES
- Status: BLOCKED
- Missing dependencies: sdv, pandas
- Blocking reason: tvae training is blocked because optional dependencies are missing: sdv, pandas.
- Training rows inspected: 12000
- Variables: district, district_code, urban_rural, age, gender, marital_status, relationship_to_head, household_size, household_type, literacy_status, education_level, labour_force_status, employment_status, individual_income, consumption_expenditure, social_group
- Result: no model artifact or synthetic population was fabricated.

- Registry path: artifacts/synthetic_models/model_registry.json
