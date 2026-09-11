# Synthetic Dynamic Sampling Report

- Supported population sizes: [1000, 5000, 10000, 12000, 50000, 100000]
- Supported modes: ['CONDITIONAL', 'REPRESENTATIVE', 'SUBPOPULATION']
- Note: generated outputs are candidate synthetic populations only; Phase 4 must validate fidelity before policy use.

## Demo Populations

### SYNPOP-BOOTSTRAP-REPRESENTATIVE-1000-42-NONE

- Model ID: TN_BOOTSTRAP_1D08E0184C
- Generator: bootstrap
- Mode: REPRESENTATIVE
- Requested / generated / accepted: 1000 / 1000 / 1000
- Acceptance rate: 100.0%
- Seed: 42
- Conditions: {}
- Batch count: 1 with max batch size 50000
- Hard constraint violations: 0
- Soft anomalies: 0
- Output path: data/synthetic/sampling/SYNPOP-BOOTSTRAP-REPRESENTATIVE-1000-42-NONE.csv

### SYNPOP-BOOTSTRAP-CONDITIONAL-1000-43-COND54D3C7AA

- Model ID: TN_BOOTSTRAP_1D08E0184C
- Generator: bootstrap
- Mode: CONDITIONAL
- Requested / generated / accepted: 1000 / 1000 / 1000
- Acceptance rate: 100.0%
- Seed: 43
- Conditions: {"urban_rural": "Rural"}
- Batch count: 1 with max batch size 50000
- Hard constraint violations: 0
- Soft anomalies: 0
- Output path: data/synthetic/sampling/SYNPOP-BOOTSTRAP-CONDITIONAL-1000-43-COND54D3C7AA.csv

### SYNPOP-GAUSSIAN_COPULA-REPRESENTATIVE-1000-44-NONE

- Model ID: TN_GAUSSIAN_COPULA_CB9DD0CE87
- Generator: gaussian_copula
- Mode: REPRESENTATIVE
- Requested / generated / accepted: 1000 / 1000 / 1000
- Acceptance rate: 100.0%
- Seed: 44
- Conditions: {}
- Batch count: 1 with max batch size 50000
- Hard constraint violations: 0
- Soft anomalies: 80
- Output path: data/synthetic/sampling/SYNPOP-GAUSSIAN_COPULA-REPRESENTATIVE-1000-44-NONE.csv
