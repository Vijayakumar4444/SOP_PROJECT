# Phase 5 - Calibration & Reweighting

Phase 5 consumes the population selected by Phase 4 and adds calibration
weights. It does not retrain synthetic generators and it does not mutate
demographic attributes such as district, gender, age, education, employment, or
social group.

The default command is:

```powershell
npm run phase5:calibrate
```

The pipeline reads `data/synthetic/phase5_calibration_handoff.json`, resolves
the selected population through `data/synthetic/phase4_validation_manifest.json`,
loads official Phase 1 calibration targets from `data/calibration/`, compares
pre-calibration marginals, applies raking/IPF, writes diagnostics, and creates
`data/synthetic/phase6_policy_engine_handoff.json`.

Current target variables are configured in
`config/calibration/calibration.yaml`:

- `gender`
- `urban_rural`
- `social_group`

`social_group` uses exact official Scheduled Caste and Scheduled Tribe targets
plus an explicit non-SC/ST residual target derived from the official Tamil Nadu
population total minus official SC/ST counts. That residual maps to the
synthetic `Other Backward Class` and `Others` categories as a grouped target.

Important outputs:

- `artifacts/calibrated_populations/<CALIBRATION_ID>/population_calibrated.csv`
- `artifacts/calibrated_populations/<CALIBRATION_ID>/calibration_metadata.json`
- `artifacts/calibrated_populations/<CALIBRATION_ID>/weight_diagnostics.json`
- `artifacts/calibrated_populations/<CALIBRATION_ID>/convergence_history.csv`
- `artifacts/calibrated_populations/<CALIBRATION_ID>/marginal_comparison_before.csv`
- `artifacts/calibrated_populations/<CALIBRATION_ID>/marginal_comparison_after.csv`
- `reports/calibration/phase5_summary.md`
- `reports/phase5_summary.md`
- `data/synthetic/phase6_policy_engine_handoff.json`

The column intended for Phase 6 analytical use is `calibration_weight`.
`population_weight` is also emitted when a valid official Tamil Nadu population
total is available.
