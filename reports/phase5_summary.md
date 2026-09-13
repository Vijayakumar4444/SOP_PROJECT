# Phase 5 Calibration & Reweighting Summary

- Calibration ID: CAL-RAKING-75B3B80E36
- Input population ID: SYNPOP-BOOTSTRAP-REPRESENTATIVE-12000-142-ACCEPTANCE
- Input model ID: TN_BOOTSTRAP_1D08E0184C
- Phase 4 quality score: 0.982663
- Calibration method: raking
- Calibration variables: gender, urban_rural, social_group
- Official data sources: SRC_TN_DES_GLANCE_2023_24;SRC_CENSUS_PCA_SD_2011
- Iteration count: 2
- Convergence status: CONVERGED
- Weight min/max/mean: 0.851541 / 1.200141 / 1.0
- Effective sample size: 11937.36654
- ESS ratio: 0.994781
- Pre-calibration mean TVD: 0.009891
- Post-calibration mean TVD: 0.000202
- Pre-calibration max marginal error: 0.029125
- Post-calibration max marginal error: 0.000373
- Unresolved targets: 0
- Final Phase 5 status: PASS_WITH_WARNINGS
- Calibrated population: artifacts/calibrated_populations/CAL-RAKING-75B3B80E36/population_calibrated.csv
- Phase 6 handoff: data/synthetic/phase6_policy_engine_handoff.json

## Quality Gates

- calibration_converged: PASS
- no_negative_weights: PASS
- no_nan_or_infinite_weights: PASS
- max_weight_below_threshold: PASS
- min_weight_above_threshold: PASS
- post_marginal_error_below_threshold: PASS
- ess_ratio_above_threshold: PASS
- unresolved_targets_below_tolerance: PASS

## Warnings

- Official marginal comparison weak for social_group score=0.611208
- gender: Synthetic categories not directly targeted: Other.
- social_group: Non-SC/ST target is an official residual grouping, not an official OBC/Others split.

## Phase 6 Handoff

- Policy weight column: calibration_weight
- Expansion weight column: population_weight
