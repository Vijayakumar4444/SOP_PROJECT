# Phase 4 Validation Handoff

Phase 3 does not select a best model. Candidate populations must be evaluated in Phase 4 population validation before policy simulation use.

- Reference population artifact: data/processed/reference_template.csv
- Prepared reference artifact: data/synthetic/training/reference_training_v1.csv
- Holdout reference artifact: data/synthetic/training/reference_holdout_v1.csv
- Synthetic population artifacts: 4
- Expected validation: marginal distributions, joint distributions, correlations, KS statistics, Jensen-Shannon divergence, Wasserstein distance, categorical association, logical validity, official marginal comparison
- Explicitly not in Phase 3: best model selection, full population validation, calibration/reweighting, policy execution, Monte Carlo simulation, recommendations
