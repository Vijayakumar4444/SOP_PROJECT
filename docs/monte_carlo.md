# Phase 7: Monte Carlo and Uncertainty Engine Documentation

## 1. Overview & Purpose
Phase 7 implements a **reproducible, stochastic Monte Carlo Simulation Engine** for evaluating Tamil Nadu public policy scenarios under uncertainty.

While Phase 6 executes a single policy deterministically on one population, Phase 7 orchestrates repeated calls across $N$ iterations to answer critical policy questions:
* How much can policy outcomes vary across plausible synthetic population draws?
* How stable is the estimated beneficiary count and programme outlay?
* What is the probability that a policy exceeds its total budget ($\mathbb{P}(\text{total\_cost} > \text{budget})$)?
* Has the simulation run for enough iterations to achieve convergence?
* Which uncertain policy assumptions (income thresholds, stipend amounts) contribute most to cost variance?

---

## 2. Iteration Architecture & Workflow

```text
Load Simulation Config
        │
        ▼
Validate Schema & Bounds
        │
        ▼
Derive Hierarchical Iteration Seed Bundle (Base Seed ➔ Pop Seed, Calib Seed, Param Seed, Policy Seed)
        │
        ▼
Sample Uncertain Parameters (DistributionSampler)
        │
        ▼
Obtain Population Sample (PopulationProvider: Household Bootstrap / Regeneration / Fixed)
        │
        ▼
Validate Population Quality (Phase 4 Validator)
        │
        ▼
Calibrate Weights (Phase 5 IPF Raking)
        │
        ▼
Apply Policy Engine (Phase 6 Deterministic Policy Execution)
        │
        ▼
Extract Iteration Metrics & Save Checkpoint
        │
        ▼
Repeat N Times ➔ Compute Uncertainty Summaries, Risk Probabilities, Convergence & Sensitivity Analysis
```

---

## 3. Simulation Configuration Schema (YAML/JSON)

Example configuration (`config/monte_carlo/examples/experiment_1_population_uncertainty.yaml`):

```yaml
experiment:
  experiment_id: tn_exp_001_pop_uncertainty
  name: Tamil Nadu Policy Population Uncertainty Analysis
  description: Monte Carlo evaluation of outcome variability across resampled synthetic populations.
  base_seed: 20260913
  number_of_iterations: 100
  execution_mode: local
  parallel_workers: 1
  fail_fast: false
  resume_enabled: true
  checkpoint_interval: 20

population:
  mode: resampling # resampling, regeneration, fixed
  sampling_strategy: household_bootstrap # household_bootstrap, bootstrap, stratified
  population_size: 12000
  preserve_households: true

calibration:
  enabled: true
  method: raking
  weight_column: calibration_weight

policy:
  policy_path: config/policy_engine/examples/tn_elderly_pension.yaml
  parameter_overrides: {}

uncertainty:
  population_uncertainty:
    enabled: true
  policy_parameter_uncertainty:
    enabled: false

take_up:
  enabled: false

convergence:
  enabled: true
  minimum_iterations: 20
  check_interval: 10
  metrics:
    - total_policy_cost
    - weighted_beneficiary_population
    - coverage_rate
  relative_mc_error_threshold: 0.02
  early_stopping: false

risk_metrics:
  - metric: total_policy_cost
    operator: greater_than
    threshold: 35000000
    output_name: probability_cost_exceeds_35m

outputs:
  confidence_level: 0.95
  percentiles:
    - 0.025
    - 0.05
    - 0.25
    - 0.50
    - 0.75
    - 0.95
    - 0.975
```

---

## 4. Supported Uncertainty Sources & Distributions

### A. Population Uncertainty Modes
* **Resampling (`household_bootstrap`):** Resamples entire household clusters with replacement, preserving household composition.
* **Regeneration:** Calls Phase 3 generator (`BootstrapBaselineGenerator`, CTGAN, TVAE, Copula) with deterministic iteration seeds.
* **Fixed:** Uses base calibrated population for pure parameter uncertainty.

### B. Supported Parameter Distributions
* `fixed`, `uniform`, `discrete_uniform`, `normal`, `truncated_normal`, `lognormal`, `triangular`, `beta`, `bernoulli`, `categorical`.

---

## 5. Statistical Uncertainty & Risk Formulas

### Monte Carlo Standard Error (MCSE)
$$\text{MCSE} = \frac{\sigma_Y}{\sqrt{N}}$$

$$\text{Relative MC Error} = \frac{\text{MCSE}}{|\mu_Y|}$$

### Outcome Risk Probabilities
$$\hat{P}(\text{Condition}) = \frac{\text{Count of valid iterations satisfying condition}}{N_{\text{valid}}}$$

Emits 95% Wilson Score Confidence Intervals for all estimated probabilities.

---

## 6. CLI Usage

Run a Monte Carlo simulation experiment:
```bash
python -m backend.app.modules.monte_carlo.cli run --config config/monte_carlo/examples/experiment_1_population_uncertainty.yaml
```

Validate simulation configuration file:
```bash
python -m backend.app.modules.monte_carlo.cli validate --config config/monte_carlo/examples/experiment_1_population_uncertainty.yaml
```

Run via npm:
```bash
npm run phase7:simulate
```

---

## 7. Phase 8 Recommendation Engine Handoff

Phase 7 emits experiment artifacts and handoff manifest:
```text
data/synthetic/phase8_recommendation_handoff.json
```
Pointing to experiment output files:
* `experiment_config.yaml`
* `experiment_metadata.json`
* `iteration_results.csv`
* `uncertainty_summary.json`
* `risk_probabilities.json`
* `convergence_report.json`
* `sensitivity_report.json`
