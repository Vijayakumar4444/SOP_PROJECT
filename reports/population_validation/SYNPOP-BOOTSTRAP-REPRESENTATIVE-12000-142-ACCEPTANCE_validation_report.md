# Population Validation Report: SYNPOP-BOOTSTRAP-REPRESENTATIVE-12000-142-ACCEPTANCE

- Generator: bootstrap
- Model ID: TN_BOOTSTRAP_1D08E0184C
- Reference rows: 12000
- Synthetic rows: 12000
- Quality score: 0.982663
- Validation status: PASS
- Distribution fidelity: 0.992149
- Correlation preservation: 0.984153
- Data validity: 1.0
- Statistical similarity: 0.948864

## Warnings

- Official marginal comparison weak for social_group score=0.611208

## Lowest Variable Fidelity

- district: 0.974866 (categorical)
- district_code: 0.974866 (categorical)
- urban_rural: 0.987396 (categorical)
- household_type: 0.990364 (categorical)
- education_level: 0.991466 (categorical)
- household_size: 0.991679 (numerical)
- age: 0.993214 (numerical)
- relationship_to_head: 0.993477 (categorical)

## Weakest Relationships

- district vs social_group: 0.944331 (cramers_v)
- district_code vs social_group: 0.944331 (cramers_v)
- district vs literacy_status: 0.95094 (cramers_v)
- district_code vs literacy_status: 0.95094 (cramers_v)
- age vs district: 0.951822 (correlation_ratio_eta)
- age vs district_code: 0.951822 (correlation_ratio_eta)
- household_size vs urban_rural: 0.957203 (correlation_ratio_eta)
- consumption_expenditure vs district: 0.957881 (correlation_ratio_eta)

## Holdout Check

- Holdout reference rows: 1784
- Holdout distribution fidelity: 0.989586
- Holdout correlation preservation: 0.975335

## Methodology Note

Scores are normalized before aggregation. Population validation does not prove causal validity, privacy protection, or policy outcome accuracy.
