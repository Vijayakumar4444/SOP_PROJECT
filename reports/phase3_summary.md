# Phase 3 Summary

Phase 3 does not select a best model. Candidate populations must be evaluated in Phase 4 population validation before policy simulation use.

1. Phase 1 dataset used: `data/processed/reference_template.csv` through `data/synthetic/training/reference_training_v1.csv`.
2. Phase 2 requirements used: TN_YOUTH_EMPLOYMENT_ASSISTANCE, TN_EDUCATION_SKILLING, TN_HEALTH_INSURANCE_TOPUP.
3. Included variables: district, district_code, urban_rural, age, gender, marital_status, relationship_to_head, household_size, household_type, literacy_status, education_level, labour_force_status, employment_status, individual_income, consumption_expenditure, social_group.
4. Excluded variables: reference_person_id, reference_household_id, source_record_id, primary_source_id, state, state_code, age_group, employment_type, occupation_group, industry_group, household_income, income_band, dwelling_type, house_ownership, electricity, drinking_water, toilet_facility, cooking_fuel, health_insurance, survey_weight, normalized_reference_weight, calibrated_reference_weight_gender_ur, reference_year, record_quality_flag, disability_status. Identifiers, metadata, fully missing fields, aggregate-only fields, and unsupported variables were excluded or deferred.
5. Missing values: categorical/ordinal blanks use `Unknown`; numeric blanks are preserved; fully missing variables are excluded.
6. Survey weights: survey_weight, normalized_reference_weight, calibrated_reference_weight_gender_ur; preserved for weighted sampling and excluded from model features.
7. Implemented generators: bootstrap, gaussian_copula, ctgan, tvae.
8. Trained successfully: TN_BOOTSTRAP_1D08E0184C, TN_CTGAN_A70E94D8A1, TN_GAUSSIAN_COPULA_CB9DD0CE87, TN_TVAE_7A020BB473. Blocked/skipped: .
9. Synthetic populations generated in acceptance demo: 4.
10. Population sizes generated: [12000].
11. Hard constraints violated in acceptance demo: 0.
12. Dynamic sampling: explicit REPRESENTATIVE, CONDITIONAL, and SUBPOPULATION modes with supported size checks and batching metadata.
13. Conditional sampling: supported conditions are validated against trained model variables; impossible conditions fail before persistence.
14. Artifacts created: model registry, model artifacts, sampled CSVs, persisted population CSVs, metadata, generation reports, diagnostics, test manifests, comparison manifest, Phase 4 manifest, and documentation.
15. Limitations: neural generators require the Python SDV stack; Parquet export skipped without a local writer; bootstrap duplicates reference feature rows; full fidelity, privacy, calibration, and policy suitability remain unvalidated.
16. Phase 4 should validate: marginal distributions, joint distributions, correlations, KS statistics, Jensen-Shannon divergence, Wasserstein distance, categorical association, logical validity, official marginal comparison.

## Acceptance Demonstration

- bootstrap: TRAINED model=TN_BOOTSTRAP_1D08E0184C population=SYNPOP-BOOTSTRAP-REPRESENTATIVE-12000-142-ACCEPTANCE rows=12000 hard_violations=0 reason=None
- ctgan: TRAINED model=TN_CTGAN_A70E94D8A1 population=SYNPOP-CTGAN-REPRESENTATIVE-12000-146-ACCEPTANCE rows=12000 hard_violations=0 reason=None
- gaussian_copula: TRAINED model=TN_GAUSSIAN_COPULA_CB9DD0CE87 population=SYNPOP-GAUSSIAN_COPULA-REPRESENTATIVE-12000-144-ACCEPTANCE rows=12000 hard_violations=0 reason=None
- tvae: TRAINED model=TN_TVAE_7A020BB473 population=SYNPOP-TVAE-REPRESENTATIVE-12000-148-ACCEPTANCE rows=12000 hard_violations=0 reason=None

## Phase 4 Handoff

- Manifest: `data/synthetic/phase4_validation_manifest.json`
- Model comparison manifest: `data/synthetic/model_comparison_manifest.json` with 4 generator entries.
- Stop condition: do not continue into population validation, calibration, policy execution, Monte Carlo simulation, or recommendations in Phase 3.
