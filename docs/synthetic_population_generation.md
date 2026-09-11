# Synthetic Population Generation

Phase 3 creates candidate synthetic Tamil Nadu populations from Phase 1 reference data and Phase 2 compatibility decisions. It does not validate final fidelity, calibrate populations, execute policies, or select a best model.

## Architecture

Input assessment -> variable selection -> training preparation -> common generator interface -> model registry -> dynamic sampling -> population persistence -> Phase 4 validation manifest.

## Input Data

- Reference template: `data/processed/reference_template.csv`
- Prepared training data: `data/synthetic/training/reference_training_v1.csv`
- Reference version: `0.3.0-modular`

## Variable Selection

Included variables are: district, district_code, urban_rural, age, gender, marital_status, relationship_to_head, household_size, household_type, literacy_status, education_level, labour_force_status, employment_status, individual_income, consumption_expenditure, social_group. Identifiers, provenance metadata, unsupported aggregate-only variables, and fully missing fields are excluded.

## Generators

Weighted Bootstrap and Gaussian Copula are trained candidates. CTGAN and TVAE have interface/registry entries but are dependency-gated in this environment.

## Missing Data And Weights

Missing categorical/ordinal values use `Unknown`. Weight columns are preserved for sampling strategy: survey_weight, normalized_reference_weight, calibrated_reference_weight_gender_ur.

## Constraints And Sampling

Hard constraints cover age, household size, non-negative economic fields, and configured categories. Sampling supports REPRESENTATIVE, CONDITIONAL, and SUBPOPULATION modes with explicit size and condition checks.

## Persistence And Reproducibility

Models are referenced by model_id and persisted under `artifacts/synthetic_models/`. Populations receive synthetic IDs unrelated to reference identifiers and are persisted under `artifacts/synthetic_populations/` with metadata and generation reports.

## Privacy Limitations

Synthetic data is not automatically anonymous. Exact duplicate diagnostics are memorization-risk prechecks only, not privacy guarantees.

## Research Transparency

Multiple synthetic-data generators are implemented because no single model is guaranteed to reproduce every type of tabular distribution or dependency. Gaussian Copula provides a relatively simple statistical benchmark, CTGAN targets complex mixed tabular distributions, and TVAE provides a variational generative alternative. Their outputs are evaluated in the subsequent Population Validation phase before one is selected for policy simulation.

## Known Limitations

CTGAN/TVAE are blocked by optional dependencies; Parquet export is skipped without a local writer; full validation, calibration, policy execution, fairness analysis, and recommendations belong to later phases.
