# Population Validation Report: SYNPOP-CTGAN-REPRESENTATIVE-12000-146-ACCEPTANCE

- Generator: ctgan
- Model ID: TN_CTGAN_A70E94D8A1
- Reference rows: 12000
- Synthetic rows: 12000
- Quality score: 0.915824
- Validation status: FAIL
- Distribution fidelity: 0.970104
- Correlation preservation: 0.829574
- Data validity: 0.992192
- Statistical similarity: 0.887413

## Warnings

- Gate failed: relationship:district:urban_rural observed=0.557025 threshold=0.65
- Weak relationship preservation: age vs marital_status score=0.210416
- Weak relationship preservation: age vs relationship_to_head score=0.188091
- Weak relationship preservation: consumption_expenditure vs district score=0.640359
- Weak relationship preservation: consumption_expenditure vs district_code score=0.646688
- Weak relationship preservation: district vs district_code score=0.055576
- Weak relationship preservation: district vs urban_rural score=0.557025
- Weak relationship preservation: district_code vs urban_rural score=0.555963
- Weak relationship preservation: education_level vs literacy_status score=0.011091
- Weak relationship preservation: employment_status vs labour_force_status score=0.012396
- Weak relationship preservation: employment_status vs relationship_to_head score=0.646403
- Official marginal comparison weak for social_group score=0.640623

## Lowest Variable Fidelity

- individual_income: 0.888165 (numerical)
- social_group: 0.932726 (categorical)
- consumption_expenditure: 0.953197 (numerical)
- district: 0.959518 (categorical)
- district_code: 0.965091 (categorical)
- age: 0.967016 (numerical)
- relationship_to_head: 0.970549 (categorical)
- household_size: 0.978669 (numerical)

## Weakest Relationships

- education_level vs literacy_status: 0.011091 (cramers_v)
- employment_status vs labour_force_status: 0.012396 (cramers_v)
- district vs district_code: 0.055576 (cramers_v)
- age vs relationship_to_head: 0.188091 (correlation_ratio_eta)
- age vs marital_status: 0.210416 (correlation_ratio_eta)
- marital_status vs relationship_to_head: 0.388849 (cramers_v)
- household_type vs urban_rural: 0.460464 (cramers_v)
- district_code vs urban_rural: 0.555963 (cramers_v)

## Holdout Check

- Holdout reference rows: 1784
- Holdout distribution fidelity: 0.969026
- Holdout correlation preservation: 0.80567

## Methodology Note

Scores are normalized before aggregation. Population validation does not prove causal validity, privacy protection, or policy outcome accuracy.
