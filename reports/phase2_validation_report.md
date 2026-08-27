# Phase 2 Validation Report

## Tamil Nadu Youth Employment Assistance

- Domains: EMPLOYMENT, INCOME, DEMOGRAPHICS, EDUCATION, SOCIAL_WELFARE
- Reliability score: 82.66
- Readiness: READY_WITH_WARNINGS
- Blocking issues: None
- Warnings: household_income: Household consumption expenditure is present, but it is not annual household income.; household_income: UNIT_SEMANTIC_MISMATCH: consumption expenditure is not INR/year household income; district: GEOGRAPHIC_VERSION_WARNING: district codes include known boundary/code conflict

## Tamil Nadu Education-linked Skilling Support

- Domains: DEMOGRAPHICS, EDUCATION, SOCIAL_WELFARE
- Reliability score: 89.69
- Readiness: READY_WITH_WARNINGS
- Blocking issues: None
- Warnings: district: GEOGRAPHIC_VERSION_WARNING: district codes include known boundary/code conflict

## Tamil Nadu Health Insurance Top-up

- Domains: INCOME, DEMOGRAPHICS, SOCIAL_WELFARE, HEALTH
- Reliability score: 62.59
- Readiness: NOT_READY
- Blocking issues: Critical variable health_insurance is MISSING.; Critical variable disability_status is AGGREGATE_ONLY.
- Warnings: disability_status: disability_status is available only as aggregate data and cannot directly evaluate person-level eligibility.; disability_status: AGGREGATE_ONLY_LEVEL: requires PERSON, available STATE; household_income: Household consumption expenditure is present, but it is not annual household income.; household_income: UNIT_SEMANTIC_MISMATCH: consumption expenditure is not INR/year household income; district: GEOGRAPHIC_VERSION_WARNING: district codes include known boundary/code conflict
