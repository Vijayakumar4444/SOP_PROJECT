# Synthetic Operational Diagnostics Report

Synthetic data is not automatically anonymous. Phase 3 exact-duplicate checks are memorization-risk prechecks only, not a formal privacy guarantee or disclosure-risk evaluation.

- Diagnostic size: 1000
- Diagnostic seed: 314159
- Randomness: {"numpy": "unavailable", "python_random": "set", "seed": 314159}
- GPU policy: CPU-compatible generation is required; Phase 3 does not assume GPU availability.

## Models

### TN_BOOTSTRAP_1D08E0184C

- Generator: bootstrap
- Reproducible for same seed: True
- Rows per second: 12795.17
- Generation duration seconds: 0.078155
- Model artifact bytes: 3703
- Persisted population artifact bytes: 348435
- Hard constraint violations: 0
- Soft anomalies: 0
- Exact duplicate rates from persisted outputs: [100.0, 100.0]

### TN_GAUSSIAN_COPULA_CB9DD0CE87

- Generator: gaussian_copula
- Reproducible for same seed: True
- Rows per second: 10569.48
- Generation duration seconds: 0.094612
- Model artifact bytes: 3664260
- Persisted population artifact bytes: 178924
- Hard constraint violations: 0
- Soft anomalies: 80
- Exact duplicate rates from persisted outputs: [0.0]
