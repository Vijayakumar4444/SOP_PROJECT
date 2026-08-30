# Synthetic Variable Selection

## Summary

- Included model features: 16
- Included variables: district, district_code, urban_rural, age, gender, marital_status, relationship_to_head, household_size, household_type, literacy_status, education_level, labour_force_status, employment_status, individual_income, consumption_expenditure, social_group
- household_income is not synthesized directly; consumption_expenditure is retained as the explicit proxy-backed economic field.
- Reference/source identifiers are excluded; new synthetic IDs will be generated later.

## Decisions

| Variable | Decision | Type | Policy Requirement | Structural | Missing % | Source Quality | Training Suitability | Reason |
| --- | --- | --- | --- | --- | ---: | --- | --- | --- |
| reference_person_id | EXCLUDE | identifier | NONE | NONE | 0.0 | A | NOT_SUITABLE | Identifier must not be learned by a generator. |
| reference_household_id | EXCLUDE | identifier | NONE | NONE | 0.0 | A | NOT_SUITABLE | Identifier must not be learned by a generator. |
| source_record_id | EXCLUDE | identifier | NONE | NONE | 0.0 | A | NOT_SUITABLE | Identifier must not be learned by a generator. |
| primary_source_id | EXCLUDE | metadata | NONE | NONE | 0.0 | A | NOT_SUITABLE | Provenance metadata must not be used as behavioural features. |
| state | ATTACH_AFTER_GENERATION | categorical | CRITICAL | NONE | 0.0 | A | DETERMINISTIC | Tamil Nadu-only deterministic field; attach after synthesis. |
| state_code | ATTACH_AFTER_GENERATION | categorical | NONE | NONE | 0.0 | A | DETERMINISTIC | Tamil Nadu-only deterministic field; attach after synthesis. |
| district | INCLUDE | categorical | CRITICAL | CORE | 1.2917 | A | SUITABLE | Supported core/policy variable with usable reference data. |
| district_code | INCLUDE | categorical | NONE | NONE | 0.0 | A | SUITABLE_OPTIONAL | Usable optional analysis variable with acceptable missingness. |
| urban_rural | INCLUDE | categorical | CALIBRATION | CORE | 0.0 | A | SUITABLE | Supported core/policy variable with usable reference data. |
| age | INCLUDE | integer | CRITICAL | CORE | 0.0 | A | SUITABLE | Supported core/policy variable with usable reference data. |
| age_group | DERIVE_AFTER_GENERATION | ordinal | NONE | NONE | 0.0 | A | DERIVED | Derive deterministically from age after synthesis. |
| gender | INCLUDE | categorical | CALIBRATION | CORE | 0.0 | A | SUITABLE | Supported core/policy variable with usable reference data. |
| marital_status | INCLUDE | categorical | NONE | NONE | 0.0 | A | SUITABLE_OPTIONAL | Usable optional analysis variable with acceptable missingness. |
| relationship_to_head | INCLUDE | categorical | NONE | NONE | 0.0 | A | SUITABLE_OPTIONAL | Usable optional analysis variable with acceptable missingness. |
| household_size | INCLUDE | integer | NONE | CORE | 0.0 | A | SUITABLE | Supported core/policy variable with usable reference data. |
| household_type | INCLUDE | categorical | NONE | NONE | 0.0 | A | SUITABLE_OPTIONAL | Usable optional analysis variable with acceptable missingness. |
| literacy_status | INCLUDE | categorical | NONE | NONE | 0.0 | A | SUITABLE_OPTIONAL | Usable optional analysis variable with acceptable missingness. |
| education_level | INCLUDE | ordinal | CRITICAL | CORE | 0.0 | A | SUITABLE | Supported core/policy variable with usable reference data. |
| labour_force_status | INCLUDE | categorical | NONE | NONE | 0.0 | A | SUITABLE_OPTIONAL | Usable optional analysis variable with acceptable missingness. |
| employment_status | INCLUDE | categorical | CRITICAL | CORE | 0.0 | A | SUITABLE | Supported core/policy variable with usable reference data. |
| employment_type | EXCLUDE | categorical | NONE | NONE | 100.0 | A | NOT_SUITABLE | Field is fully missing in the reference template. |
| occupation_group | EXCLUDE | categorical | NONE | NONE | 53.4583 | A | LOW_SUITABILITY | High missingness and no current policy need; defer. |
| industry_group | EXCLUDE | categorical | NONE | NONE | 53.4583 | A | LOW_SUITABILITY | High missingness and no current policy need; defer. |
| individual_income | INCLUDE | continuous | NONE | NONE | 0.0 | A | SUITABLE_OPTIONAL | Usable optional analysis variable with acceptable missingness. |
| household_income | EXCLUDE | continuous | CRITICAL | NONE | 100.0 | A | NOT_SUITABLE | Field is fully missing in the reference template. |
| consumption_expenditure | INCLUDE | continuous | PROXY_FOR_household_income | NONE | 0.0 | A | SUITABLE | Supported core/policy variable with usable reference data. |
| income_band | EXCLUDE | ordinal | NONE | NONE | 100.0 | A | NOT_SUITABLE | Field is fully missing in the reference template. |
| dwelling_type | EXCLUDE | categorical | NONE | NONE | 100.0 | A | NOT_SUITABLE | Field is fully missing in the reference template. |
| house_ownership | EXCLUDE | categorical | NONE | NONE | 100.0 | A | NOT_SUITABLE | Field is fully missing in the reference template. |
| electricity | EXCLUDE | categorical | NONE | NONE | 100.0 | A | NOT_SUITABLE | Field is fully missing in the reference template. |
| drinking_water | EXCLUDE | categorical | NONE | NONE | 100.0 | A | NOT_SUITABLE | Field is fully missing in the reference template. |
| toilet_facility | EXCLUDE | categorical | NONE | NONE | 100.0 | A | NOT_SUITABLE | Field is fully missing in the reference template. |
| cooking_fuel | EXCLUDE | categorical | NONE | NONE | 100.0 | A | NOT_SUITABLE | Field is fully missing in the reference template. |
| health_insurance | EXCLUDE | categorical | CRITICAL | NONE | 100.0 | A | NOT_SUITABLE | Field is fully missing in the reference template. |
| social_group | INCLUDE | categorical | CALIBRATION | CORE | 0.0 | A | SUITABLE | Supported core/policy variable with usable reference data. |
| survey_weight | EXCLUDE_FROM_FEATURES | weight | NONE | NONE | 0.0 | A | WEIGHT_ONLY | Weight retained for sampling strategy, not model features. |
| normalized_reference_weight | EXCLUDE_FROM_FEATURES | weight | NONE | NONE | 0.0 | A | WEIGHT_ONLY | Weight retained for sampling strategy, not model features. |
| calibrated_reference_weight_gender_ur | EXCLUDE_FROM_FEATURES | weight | NONE | NONE | 0.0 | UNKNOWN | WEIGHT_ONLY | Weight retained for sampling strategy, not model features. |
| reference_year | EXCLUDE | metadata | NONE | NONE | 0.0 | A | NOT_SUITABLE | Provenance metadata must not be used as behavioural features. |
| record_quality_flag | EXCLUDE | metadata | NONE | NONE | 0.0 | A | NOT_SUITABLE | Provenance metadata must not be used as behavioural features. |
| disability_status | EXCLUDE | unavailable | CRITICAL | NONE | 100.0 | AGGREGATE_ONLY | NOT_SUITABLE | Required by Phase 2 but unavailable as a usable reference-template field. |
