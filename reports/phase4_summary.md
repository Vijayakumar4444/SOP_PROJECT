# Phase 4 Summary

1. Reference data used: `data/synthetic/training/reference_training_v1.csv` with holdout `data/synthetic/training/reference_holdout_v1.csv`.
2. Synthetic populations validated: SYNPOP-BOOTSTRAP-REPRESENTATIVE-12000-142-ACCEPTANCE, SYNPOP-CTGAN-REPRESENTATIVE-12000-146-ACCEPTANCE, SYNPOP-GAUSSIAN_COPULA-REPRESENTATIVE-12000-144-ACCEPTANCE, SYNPOP-TVAE-REPRESENTATIVE-12000-148-ACCEPTANCE.
3. Models that produced them: bootstrap, ctgan, gaussian_copula, tvae
4. Variables validated: age, consumption_expenditure, district, district_code, education_level, employment_status, gender, household_size, household_type, individual_income, labour_force_status, literacy_status, marital_status, relationship_to_head, social_group, urban_rural
5. Variables skipped: calibrated_reference_weight_gender_ur: SKIPPED_WEIGHT; normalized_reference_weight: SKIPPED_WEIGHT; survey_weight: SKIPPED_WEIGHT; synthetic_person_id: SKIPPED_IDENTIFIER; training_split: SKIPPED_METADATA
6. Distribution fidelity: KS and scale-normalized Wasserstein for numeric fields; Jensen-Shannon divergence and total variation distance for categorical fields.
7. Correlation preservation: Pearson/Spearman average for numeric pairs, Cramer's V for categorical pairs, and eta for mixed pairs.
8. Data validity: reused the Phase 3 constraint engine for hard ranges, canonical categories, and configured soft anomalies.
9. Statistical similarity: average of distribution, relationship, and official-marginal similarity components.
10. Quality score: configurable weighted composite from `config/population_validation/scoring.yaml`.
11. Population that passed validation: SYNPOP-BOOTSTRAP-REPRESENTATIVE-12000-142-ACCEPTANCE
12. Best performing population: SYNPOP-BOOTSTRAP-REPRESENTATIVE-12000-142-ACCEPTANCE
13. Weaknesses remain: see per-population warnings and weakest relationships in `reports/population_validation/`.
14. Calibration phase should receive: `data/synthetic/phase5_calibration_handoff.json`.
