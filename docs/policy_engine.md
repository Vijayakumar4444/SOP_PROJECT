# Phase 6: Policy Engine Documentation

## 1. Overview & Purpose
Phase 6 implements a **deterministic, machine-readable, safe Policy Execution Engine** for Tamil Nadu policy evaluation. It consumes the calibrated synthetic population produced by Phase 5 (`population_calibrated.csv`) and evaluates policy eligibility, applies capacity/budget constraints, computes decimal-safe benefit outlays, and produces weighted population impact estimates.

Phase 6 strictly adheres to single-run deterministic evaluation. Stochastic sampling and parameter sweeps belong to Phase 7 (Monte Carlo & Uncertainty Engine).

---

## 2. Input from Phase 5
Phase 6 resolves its input via:
```text
data/synthetic/phase6_policy_engine_handoff.json
```
Which points to the Phase 5 calibrated population artifact:
```text
artifacts/calibrated_populations/<CALIBRATION_ID>/population_calibrated.csv
```
And identifies the weight column:
* `calibration_weight` (or `population_weight` for expanded population totals)

---

## 3. Policy Specification Schema (YAML/JSON)

Example policy configuration (`config/policy_engine/examples/tn_elderly_pension.yaml`):

```yaml
policy_id: tn_elderly_pension_001
name: Tamil Nadu Social Security Elderly Assistance Scheme
version: "1.0"
description: Deterministic elderly welfare pension for low-income senior citizens in Tamil Nadu.
jurisdiction:
  state: Tamil Nadu
  geographic_level: state
status: active

target_unit: person # 'person' or 'household'

eligibility:
  logical_operator: AND
  rules:
    - rule_id: R_AGE
      field: age
      operator: greater_than_or_equal
      value: 60
    - rule_id: R_INCOME
      field: individual_income
      operator: less_than_or_equal
      value: 120000

exclusions:
  logical_operator: OR
  rules:
    - rule_id: EX_GOVT_EMP
      field: employment_status
      operator: equals
      value: Government Employed

benefit:
  type: fixed_amount # fixed_amount, percentage_based, attribute_based, tiered, per_household, per_person
  amount: 1500
  frequency: monthly # monthly, one_time, annual
  currency: INR

constraints:
  total_budget: 5000000000
  maximum_beneficiaries: null
  allocation_strategy: all # all, lowest_income_first, highest_vulnerability_first, oldest_first, youngest_first, geographic_priority, seeded_lottery
  missing_value_behavior: ineligible

effective_period:
  start_date: "2026-04-01"
  end_date: "2027-03-31"

required_variables:
  - synthetic_person_id
  - age
  - individual_income
  - employment_status
```

---

## 4. Supported Rule Operators
The Safe Rule Engine evaluates rules using an allow-list without `eval()`:

| Operator | Description | Example |
| :--- | :--- | :--- |
| `equals` | Exact match (normalized) | `field: district, operator: equals, value: Chennai` |
| `not_equals` | Not equal to value | `field: employment_status, operator: not_equals, value: Government Employed` |
| `greater_than` | Value > threshold | `field: age, operator: greater_than, value: 18` |
| `greater_than_or_equal` | Value >= threshold | `field: age, operator: greater_than_or_equal, value: 60` |
| `less_than` | Value < threshold | `field: individual_income, operator: less_than, value: 100000` |
| `less_than_or_equal` | Value <= threshold | `field: individual_income, operator: less_than_or_equal, value: 120000` |
| `in` | Value in list | `field: employment_status, operator: in, value: ["Unemployed", "Not in Labour Force"]` |
| `not_in` | Value not in list | `field: district, operator: not_in, value: ["DistrictA", "DistrictB"]` |
| `between` | Value between [min, max] inclusive | `field: age, operator: between, value: [18, 30]` |
| `not_between` | Value outside [min, max] | `field: age, operator: not_between, value: [0, 17]` |
| `is_null` | Field is missing or null | `field: income, operator: is_null, value: null` |
| `is_not_null` | Field is present | `field: education_level, operator: is_not_null, value: null` |
| `contains` | Substring match | `field: social_group, operator: contains, value: Caste` |
| `starts_with` | Prefix match | `field: synthetic_person_id, operator: starts_with, value: TN` |
| `ends_with` | Suffix match | `field: district_code, operator: ends_with, value: 01` |

---

## 5. Person vs. Household Targeting
* **Person-Level (`target_unit: person`):** Evaluates each individual person record independently.
* **Household-Level (`target_unit: household`):** Groups records by household identifier (`household_id` / `synthetic_household_id`). Evaluates eligibility once per household and designates one primary household representative to prevent duplicate benefit allocation to multiple family members.

---

## 6. Weighted Estimates & Cost Formulas

$$\text{Weighted Eligible Population} = \sum_{i \in \text{Eligible}} w_i$$

$$\text{Weighted Beneficiary Population} = \sum_{i \in \text{Selected}} w_i$$

$$\text{Estimated Program Cost (INR)} = \sum_{i \in \text{Selected}} (\text{Annual Benefit}_i \times w_i)$$

Where $w_i$ is the calibrated population weight (`calibration_weight` or `population_weight`).

---

## 7. CLI Usage

Run a policy simulation:
```bash
python -m backend.app.modules.policy_engine.cli run --policy config/policy_engine/examples/tn_elderly_pension.yaml
```

Validate a policy configuration file:
```bash
python -m backend.app.modules.policy_engine.cli validate-policy --policy config/policy_engine/examples/tn_elderly_pension.yaml
```

Check data compatibility against population:
```bash
python -m backend.app.modules.policy_engine.cli check-compatibility --policy config/policy_engine/examples/tn_elderly_pension.yaml
```

Or via `npm`:
```bash
npm run phase6:execute
```

---

## 8. Phase 7 Callable Interface

Phase 7 (Monte Carlo Engine) calls Phase 6 via:

```python
from backend.app.modules.policy_engine.service import Phase6PolicyService

service = Phase6PolicyService()
sim_summary = service.evaluate_simulation(
    policy_path="config/policy_engine/examples/tn_elderly_pension.yaml",
    population_df=sampled_df,
    weight_column="calibration_weight",
    seed=42,
    parameter_overrides={"total_budget": 5000000000}
)
```
