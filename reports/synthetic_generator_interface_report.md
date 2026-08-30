# Synthetic Generator Interface Report

## Implemented Contract

- fit(data, metadata, config)
- sample(size, seed=None, conditions=None)
- save(destination)
- load(source)
- get_model_metadata()
- get_training_summary()

## Generator Registry

- bootstrap: TRAINED. Available and trained through the shared interface.
- gaussian_copula: TRAINED. Available and trained through the shared interface.
- ctgan: BLOCKED. Dependency-gated neural generator; blocked status is recorded when optional dependencies are missing.
- tvae: BLOCKED. Dependency-gated neural generator; blocked status is recorded when optional dependencies are missing.

## Trained Candidate Models

### bootstrap

- Model ID: TN_BOOTSTRAP_1D08E0184C
- Status: TRAINED
- Training rows: 12000
- Variables: district, district_code, urban_rural, age, gender, marital_status, relationship_to_head, household_size, household_type, literacy_status, education_level, labour_force_status, employment_status, individual_income, consumption_expenditure, social_group
- Label: RESAMPLED_BASELINE
- Warning: Bootstrap records are resampled from reference rows and may duplicate source observations; do not call this privacy-preserving synthesis.
- Artifact path: artifacts/synthetic_models/bootstrap/TN_BOOTSTRAP_1D08E0184C
- Preview path: data/synthetic/bootstrap_preview_25.csv

### gaussian_copula

- Model ID: TN_GAUSSIAN_COPULA_CB9DD0CE87
- Status: TRAINED
- Training rows: 12000
- Variables: district, district_code, urban_rural, age, gender, marital_status, relationship_to_head, household_size, household_type, literacy_status, education_level, labour_force_status, employment_status, individual_income, consumption_expenditure, social_group
- Label: SYNTHETIC_GAUSSIAN_COPULA_CANDIDATE
- Warning: Pure-Python fallback generator; full statistical validation belongs to Phase 4.
- Artifact path: artifacts/synthetic_models/gaussian_copula/TN_GAUSSIAN_COPULA_CB9DD0CE87
- Preview path: data/synthetic/gaussian_copula_preview_25.csv

- Registry path: artifacts/synthetic_models/model_registry.json
