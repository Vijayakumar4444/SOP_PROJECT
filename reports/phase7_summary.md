# SOP Project - Phase 7 Monte Carlo & Uncertainty Engine Summary

## Overview
Phase 7 evaluates policy outcome uncertainty for Tamil Nadu using stochastic Monte Carlo simulation.
It measures outcome variability across sampled populations, policy parameter distributions, and take-up rates,
calculates percentiles and 95% confidence intervals, quantifies Monte Carlo standard error, tracks convergence,
and computes risk probabilities (e.g. probability of budget exceedance).

## Demonstration Experiment Results

| Experiment ID | Completed (Valid/Failed) | Converged | Mean Cost (INR) | Std Dev (INR) | 95% Uncertainty Interval (P2.5 - P97.5) | Rel MC Error | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `tn_exp_001_pop_uncertainty` | 30 / 0 | True | ₹33,169,432.91 | ₹0.00 | ₹33,169,432.91 – ₹33,169,432.91 | 0.0000 | PASS |
| `tn_exp_002_param_uncertainty` | 30 / 0 | False | ₹3,556,855.66 | ₹595,474.98 | ₹2,753,329.92 – ₹4,752,427.46 | 0.0306 | PASS |
| `tn_exp_003_combined_uncertainty` | 30 / 0 | False | ₹5,972.12 | ₹3,401.85 | ₹0.00 – ₹8,793.92 | 0.1040 | PASS |

## Phase 8 Recommendation & Reporting Handoff
Phase 7 exposes experiment artifacts and handoff metrics for Phase 8:
```json
{
  "phase": 7,
  "status": "PASS",
  "handoff_manifest": "data/synthetic/phase8_recommendation_handoff.json"
}
```
