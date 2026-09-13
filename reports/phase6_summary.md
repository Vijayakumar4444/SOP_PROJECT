# SOP Project - Phase 6 Policy Engine Execution Summary

## Overview
Phase 6 provides a deterministic, reusable Policy Execution Engine for Tamil Nadu.
It evaluates policy eligibility, applies capacity/budget constraints, computes decimal-safe benefit outlays,
and produces weighted population estimates using the Phase 5 calibrated synthetic population.

## Demonstration Policy Execution Results

| Policy ID | Name | Target Unit | Evaluated | Eligible (Weighted) | Beneficiaries (Weighted) | Total Program Cost (INR) | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `tn_elderly_pension_001` | Tamil Nadu Social Security Elderly Assistance Scheme | person | 12,000 | 1,835 (1,842.75) | 1,835 (1,842.75) | ₹33,169,417.45 | PASS |
| `tn_clean_cooking_subsidy_002` | Tamil Nadu Rural Household Clean Cooking Fuel Support Scheme | household | 12,000 | 6,058 (6,070.56) | 6,058 (6,070.56) | ₹43,708,027.34 | PASS |
| `tn_youth_skilling_stipend_003` | Tamil Nadu Youth Skill Enhancement Stipend | person | 12,000 | 189 (188.99) | 189 (188.99) | ₹4,535,736.37 | PASS |

## Phase 7 Callable Interface
Phase 6 exposes a clean callable interface for the Phase 7 Monte Carlo Engine:
```python
from backend.app.modules.policy_engine.service import Phase6PolicyService
service = Phase6PolicyService()
sim_summary = service.evaluate_simulation(
    policy_path='config/policy_engine/examples/tn_elderly_pension.yaml',
    population_df=sampled_df,
    weight_column='calibration_weight',
    seed=42,
    parameter_overrides={'total_budget': 10000000}
)
```
