# Population Validation Report: SYNPOP-GAUSSIAN_COPULA-REPRESENTATIVE-12000-144-ACCEPTANCE

- Generator: gaussian_copula
- Model ID: TN_GAUSSIAN_COPULA_CB9DD0CE87
- Reference rows: 12000
- Synthetic rows: 12000
- Quality score: 0.939569
- Validation status: FAIL
- Distribution fidelity: 0.997283
- Correlation preservation: 0.866864
- Data validity: 0.993225
- Statistical similarity: 0.908397

## Warnings

- Gate failed: relationship:district:urban_rural observed=0.582729 threshold=0.65
- gender: Reference categories are missing from synthetic population.
- Weak relationship preservation: age vs relationship_to_head score=0.613018
- Weak relationship preservation: district vs district_code score=0.060957
- Weak relationship preservation: district vs urban_rural score=0.582729
- Weak relationship preservation: district_code vs urban_rural score=0.57598
- Weak relationship preservation: education_level vs literacy_status score=0.01123
- Weak relationship preservation: gender vs relationship_to_head score=0.608366
- Weak relationship preservation: gender vs urban_rural score=0.630466
- Weak relationship preservation: marital_status vs relationship_to_head score=0.511385
- Official marginal comparison weak for social_group score=0.60664

## Lowest Variable Fidelity

- district: 0.990661 (categorical)
- district_code: 0.990941 (categorical)
- relationship_to_head: 0.995887 (categorical)
- consumption_expenditure: 0.996436 (numerical)
- education_level: 0.997083 (categorical)
- household_size: 0.997344 (numerical)
- age: 0.997382 (numerical)
- individual_income: 0.997467 (numerical)

## Weakest Relationships

- education_level vs literacy_status: 0.01123 (cramers_v)
- district vs district_code: 0.060957 (cramers_v)
- marital_status vs relationship_to_head: 0.511385 (cramers_v)
- district_code vs urban_rural: 0.57598 (cramers_v)
- district vs urban_rural: 0.582729 (cramers_v)
- gender vs relationship_to_head: 0.608366 (cramers_v)
- age vs relationship_to_head: 0.613018 (correlation_ratio_eta)
- gender vs urban_rural: 0.630466 (cramers_v)

## Holdout Check

- Holdout reference rows: 1784
- Holdout distribution fidelity: 0.994372
- Holdout correlation preservation: 0.851382

## Methodology Note

Scores are normalized before aggregation. Population validation does not prove causal validity, privacy protection, or policy outcome accuracy.
