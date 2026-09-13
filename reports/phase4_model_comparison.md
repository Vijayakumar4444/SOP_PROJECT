# Phase 4 Model Comparison

- Reference population: data/synthetic/training/reference_training_v1.csv
- Holdout reference: data/synthetic/training/reference_holdout_v1.csv
- Models evaluated: 4

## Scores

| Population | Generator | Distribution | Correlation | Validity | Similarity | Quality | Status |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| SYNPOP-BOOTSTRAP-REPRESENTATIVE-12000-142-ACCEPTANCE | bootstrap | 0.992149 | 0.984153 | 1.0 | 0.948864 | 0.982663 | PASS |
| SYNPOP-GAUSSIAN_COPULA-REPRESENTATIVE-12000-144-ACCEPTANCE | gaussian_copula | 0.997283 | 0.866864 | 0.993225 | 0.908397 | 0.939569 | FAIL |
| SYNPOP-CTGAN-REPRESENTATIVE-12000-146-ACCEPTANCE | ctgan | 0.970104 | 0.829574 | 0.992192 | 0.887413 | 0.915824 | FAIL |
| SYNPOP-TVAE-REPRESENTATIVE-12000-148-ACCEPTANCE | tvae | 0.79047 | 0.836712 | 0.999833 | 0.793679 | 0.846857 | FAIL |

## Selection

- Selected population: SYNPOP-BOOTSTRAP-REPRESENTATIVE-12000-142-ACCEPTANCE
- Selected model: TN_BOOTSTRAP_1D08E0184C
- Status: PASS
- Reason: Selected highest-scoring population that passed all configured Phase 4 gates.

## Known Limitations

- Population validation measures statistical fidelity, not causal validity or privacy protection.
- Official marginal comparison is limited to calibration files whose categories map directly to synthetic variables.
- Parquet validation outputs are emitted as CSV because no parquet writer dependency is available in this project runtime.
