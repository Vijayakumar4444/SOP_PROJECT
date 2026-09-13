# Population Validation Report: SYNPOP-TVAE-REPRESENTATIVE-12000-148-ACCEPTANCE

- Generator: tvae
- Model ID: TN_TVAE_7A020BB473
- Reference rows: 12000
- Synthetic rows: 12000
- Quality score: 0.846857
- Validation status: FAIL
- Distribution fidelity: 0.79047
- Correlation preservation: 0.836712
- Data validity: 0.999833
- Statistical similarity: 0.793679

## Warnings

- Gate failed: variable_fidelity:district observed=0.422408 threshold=0.8
- Gate failed: variable_fidelity:district_code observed=0.423696 threshold=0.65
- Gate failed: variable_fidelity:education_level observed=0.74984 threshold=0.8
- Gate failed: variable_fidelity:household_type observed=0.640456 threshold=0.65
- Gate failed: relationship:district:urban_rural observed=0.516649 threshold=0.65
- district: Reference categories are missing from synthetic population.
- district_code: Reference categories are missing from synthetic population.
- education_level: Reference categories are missing from synthetic population.
- employment_status: Reference categories are missing from synthetic population.
- gender: Reference categories are missing from synthetic population.
- household_type: Reference categories are missing from synthetic population.
- labour_force_status: Reference categories are missing from synthetic population.
- literacy_status: Reference categories are missing from synthetic population.
- marital_status: Reference categories are missing from synthetic population.
- relationship_to_head: Reference categories are missing from synthetic population.
- social_group: Reference categories are missing from synthetic population.
- Weak relationship preservation: age vs marital_status score=0.352939
- Weak relationship preservation: age vs relationship_to_head score=0.494097
- Weak relationship preservation: consumption_expenditure vs district score=0.608807
- Weak relationship preservation: consumption_expenditure vs district_code score=0.649037

## Lowest Variable Fidelity

- district: 0.422408 (categorical)
- district_code: 0.423696 (categorical)
- household_type: 0.640456 (categorical)
- education_level: 0.74984 (categorical)
- marital_status: 0.776175 (categorical)
- relationship_to_head: 0.783195 (categorical)
- consumption_expenditure: 0.825623 (numerical)
- employment_status: 0.833546 (categorical)

## Weakest Relationships

- district vs district_code: 0.141858 (cramers_v)
- age vs marital_status: 0.352939 (correlation_ratio_eta)
- employment_status vs labour_force_status: 0.384754 (cramers_v)
- age vs relationship_to_head: 0.494097 (correlation_ratio_eta)
- marital_status vs relationship_to_head: 0.514002 (cramers_v)
- district vs urban_rural: 0.516649 (cramers_v)
- household_type vs urban_rural: 0.554961 (cramers_v)
- household_size vs relationship_to_head: 0.556494 (correlation_ratio_eta)

## Holdout Check

- Holdout reference rows: 1784
- Holdout distribution fidelity: 0.790578
- Holdout correlation preservation: 0.814977

## Methodology Note

Scores are normalized before aggregation. Population validation does not prove causal validity, privacy protection, or policy outcome accuracy.
