# Synthetic Model Comparison Manifest Report

Do not select a best model from this manifest. It exists so Phase 4 can compare REFERENCE vs BOOTSTRAP vs GAUSSIAN COPULA vs CTGAN vs TVAE.

- Reference version: 0.3.0-modular
- Training dataset version: phase3_training_v1
- Population size: 12000

## Candidates

### bootstrap

- Model ID: TN_BOOTSTRAP_1D08E0184C
- Status: TRAINED
- Population IDs: ['SYNPOP-BOOTSTRAP-REPRESENTATIVE-1000-42-NONE', 'SYNPOP-BOOTSTRAP-CONDITIONAL-1000-43-COND54D3C7AA', 'SYNPOP-BOOTSTRAP-REPRESENTATIVE-12000-142-ACCEPTANCE']
- Blocking reason: None

### ctgan

- Model ID: TN_CTGAN_BLOCKED_DEPENDENCIES
- Status: BLOCKED
- Population IDs: None
- Blocking reason: ctgan training is blocked because optional dependencies are missing: sdv, pandas.

### gaussian_copula

- Model ID: TN_GAUSSIAN_COPULA_CB9DD0CE87
- Status: TRAINED
- Population IDs: ['SYNPOP-GAUSSIAN_COPULA-REPRESENTATIVE-1000-44-NONE', 'SYNPOP-GAUSSIAN_COPULA-REPRESENTATIVE-12000-144-ACCEPTANCE']
- Blocking reason: None

### tvae

- Model ID: TN_TVAE_BLOCKED_DEPENDENCIES
- Status: BLOCKED
- Population IDs: None
- Blocking reason: tvae training is blocked because optional dependencies are missing: sdv, pandas.
