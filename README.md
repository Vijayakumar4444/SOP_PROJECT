# SOP Project

Tamil Nadu policy simulation platform with a React frontend, FastAPI backend, Supabase policy-memory database, synthetic population pipeline, Monte Carlo uncertainty engine, and recommendation output.

The current project is no longer only a Phase 1 data foundation project. It now supports an 8-phase backend pipeline and returns frontend-ready results only after the full backend pipeline reaches Phase 8.

## What This Project Does

The application lets a user define a government policy, run it through the backend simulation pipeline, and view a final recommendation result.

The intended flow is:

```text
User enters policy in frontend
Backend stores policy run in Supabase
Backend checks exact policy hash cache
Backend finds similar completed policies as memory
Backend writes DB priors for calibration and Monte Carlo
Backend runs all 8 phases
Backend reads Phase 8 recommendation artifacts
Frontend receives only final artifact-backed result
```

The database does not replace simulation. It works as memory and calibration context. The synthetic population, policy engine, Monte Carlo engine, and recommendation engine still run freshly.

## Main Components

```text
frontend/
  React + Vite UI
  New policy input page
  Progress/loading page
  Results dashboard

backend/app/main.py
  FastAPI API
  Policy submission
  Pipeline start endpoint
  Real progress endpoint
  Final results endpoint

backend/app/policy_memory.py
  Supabase/Postgres tables
  Policy hashing
  Exact-match cache
  Similar-policy search
  Phase log reads/writes

backend/app/policy_priors.py
  Converts similar-policy history into priors
  Writes data/synthetic/policy_memory_priors.json
  Tunes Monte Carlo assumptions without replacing simulation

backend/app/pipeline_orchestrator.py
  Runs all 8 phases in order
  Logs phase status to Supabase

backend/app/pipeline_results.py
  Reads backend artifacts
  Maps Phase 7 and Phase 8 outputs into frontend result shape

backend/app/modules/
  Individual backend phase engines
```

## Current Implementation Status

Completed implementation order:

1. Supabase tables for policy runs and phase logs
2. Policy fingerprint/hash
3. Save frontend-submitted policies to DB
4. Exact-match cache check
5. Full pipeline orchestration endpoint
6. `/api/simulations/{id}/progress` reads real phase status
7. `/api/simulations/{id}/results` reads real backend outputs
8. Similar-policy search
9. DB priors for Monte Carlo/calibration
10. Frontend display for "Similar Policies Used"

## Backend Rule For Results

The backend does not return a fake/lightweight estimator result anymore.

`/api/simulations/{id}/results` returns a successful result only when:

- the exact-match cache contains a previous `pipeline_artifacts` result, or
- the current run status is `completed`, and
- `phase8_recommendation` is completed.

If Phase 8 has not completed, the endpoint returns:

```text
409 not_ready
```

This prevents the frontend from showing estimated output before the backend has finished all phases.

## The 8 Backend Phases

### Phase 1: Data Foundation

Script:

```text
npm run phase1:build
```

Primary artifact:

```text
data/processed/reference_template.csv
```

Purpose:

- Build Tamil Nadu reference data foundation
- Prepare source registry and processed population reference artifacts
- Maintain provenance for official data sources

### Phase 2: Policy-Data Compatibility

Script:

```text
npm run phase2:build
```

Primary artifact:

```text
data/synthetic/variable_selection.json
```

Purpose:

- Check whether policy rules can be represented with available data
- Produce compatibility reports
- Select usable variables for later phases

### Phase 3: Synthetic Population Generation

Script:

```text
npm run phase3:finalize
```

Primary artifact:

```text
data/synthetic/phase4_validation_manifest.json
```

Purpose:

- Prepare candidate synthetic population outputs
- Produce model comparison and acceptance manifests
- Hand off selected candidates to validation

### Phase 4: Population Validation

Script:

```text
npm run phase4:validate
```

Primary artifact:

```text
data/synthetic/phase5_calibration_handoff.json
```

Purpose:

- Validate synthetic population quality
- Compare candidates
- Select a population for calibration

### Phase 5: Calibration And Reweighting

Script:

```text
npm run phase5:calibrate
```

Primary artifact:

```text
data/synthetic/phase6_policy_engine_handoff.json
```

Purpose:

- Calibrate synthetic population weights against official targets
- Produce calibrated population artifact
- Attach policy memory priors path when available

### Phase 6: Policy Engine

Script:

```text
npm run phase6:execute
```

Primary artifact:

```text
data/synthetic/phase7_monte_carlo_handoff.json
```

Purpose:

- Apply policy eligibility rules
- Select beneficiaries
- Calculate costs
- Produce policy run summaries

### Phase 7: Monte Carlo And Uncertainty

Script:

```text
npm run phase7:simulate
```

Primary artifact:

```text
data/synthetic/phase8_recommendation_handoff.json
```

Purpose:

- Run Monte Carlo uncertainty experiments
- Compute confidence intervals, p5/p95, risk probabilities
- Use DB priors to tune assumptions and risk checks when similar policy history exists

### Phase 8: Recommendation Engine

Script:

```text
npm run phase8:recommend
```

Primary artifact:

```text
artifacts/recommendation/recommendation_summary.json
```

Purpose:

- Rank policy options
- Evaluate feasibility
- Produce final recommendation
- Generate fairness, tradeoff, and summary artifacts

The frontend result page should receive output only after this phase has completed.

## Supabase Database Memory

The backend uses Supabase Postgres through the connection values in `.env`.

Important tables:

```text
policy_simulation_runs
policy_simulation_parameters
phase_run_logs
```

### `policy_simulation_runs`

Stores:

- run ID
- policy hash
- policy name
- department
- policy payload
- configuration payload
- run status
- cached source run
- final result payload

### `policy_simulation_parameters`

Stores searchable/calibration fields:

- target group
- rule attributes
- benefit amount
- coverage
- target fit
- fiscal pressure
- risk score
- equity score
- final outcome

### `phase_run_logs`

Stores real pipeline progress:

- run ID
- phase name
- status
- artifact path
- message
- metadata
- timestamp

## Policy Hashing

Policy hashing is deterministic.

It uses:

- policy name
- description
- eligibility rules
- department
- scope
- selected districts
- configuration

Rule IDs are ignored so changing frontend-generated UUIDs does not create a new hash.

## Exact-Match Cache

If the same policy hash already exists in DB with a completed `pipeline_artifacts` result, the backend can return the stored result directly.

Important safety rule:

Old lightweight/estimator results are ignored. Only real Phase 8 pipeline artifact results can be cached.

## Similar-Policy Search

When a new policy is submitted, the backend searches previous completed pipeline artifact results.

Similarity uses:

- overlapping rule attributes
- same department
- similar target group
- similar benefit amount

The similar policies are returned in the final `memory` payload and displayed on the frontend results page.

## DB Priors

Before the full pipeline starts, the backend writes:

```text
data/synthetic/policy_memory_priors.json
```

This file is derived from similar completed policies.

It can include priors for:

- coverage
- fiscal pressure
- risk score
- equity score
- benefit amount

How priors are used:

- add memory-based coverage risk checks
- narrow benefit amount uncertainty ranges when safe
- attach fiscal prior context to calibration metadata

How priors are not used:

- they do not replace synthetic population generation
- they do not copy old results
- they do not skip the policy engine
- they do not skip Monte Carlo
- they do not skip recommendation

## API Endpoints

### Health

```text
GET /api/health
GET /api/db/health
```

### Policy Helpers

```text
POST /api/policies/validate
POST /api/policies/parse
```

### Simulations

Create a simulation:

```text
POST /api/simulations
```

Start full backend pipeline:

```text
POST /api/simulations/{simulation_id}/pipeline
```

Read real phase progress:

```text
GET /api/simulations/{simulation_id}/progress
```

Read final result:

```text
GET /api/simulations/{simulation_id}/results
```

List simulations:

```text
GET /api/simulations
```

## Frontend Flow

Main frontend files:

```text
frontend/src/pages/NewSimulation/NewSimulation.tsx
frontend/src/pages/SimulationProgress/SimulationProgress.tsx
frontend/src/pages/SimulationResults/SimulationResults.tsx
frontend/src/api/simulations.api.ts
frontend/src/types/index.ts
```

The results page now displays:

- policy outcome
- beneficiary coverage
- fiscal analysis
- district chart
- Tamil Nadu map
- demographic breakdowns
- Monte Carlo distribution
- confidence intervals
- fiscal risk
- fairness/equity score
- policy improvements
- similar policies used

The "Similar Policies Used" panel appears only when the backend returns `memory.similarPolicies`.

## Environment Setup

Install Node dependencies:

```bash
npm install
npm --prefix frontend install
```

Install Python dependencies:

```bash
pip install -r requirements.txt
```

If Windows selects a Python runtime without required packages, the phase runner scripts prefer:

```text
.\.venv\Scripts\python.exe
C:\Program Files\PostgreSQL\17\pgAdmin 4\python\python.exe
C:\Users\User\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe
```

This avoids phase failures from generic `python` aliases missing packages like `PyYAML`.

## Environment Variables

Create a local `.env` file at the project root.

Do not commit `.env`.

Expected values include the Supabase/Postgres connection details used by `backend/app/database.py`.

The backend reads `.env` automatically before opening the DB connection.

## Running The Project

Start backend:

```bash
npm run api:dev
```

Backend URL:

```text
http://127.0.0.1:8010
```

Start frontend:

```bash
npm run frontend:dev
```

Frontend URL:

```text
http://127.0.0.1:5173
```

Vite proxies `/api` to:

```text
http://127.0.0.1:8010
```

## Running The Full Pipeline Manually

```bash
npm run phase1:build
npm run phase2:build
npm run phase3:finalize
npm run phase4:validate
npm run phase5:calibrate
npm run phase6:execute
npm run phase7:simulate
npm run phase8:recommend
```

## Running Tests

Run all tests:

```bash
npm test
```

Latest verification:

```text
Ran 75 tests
OK
```

Frontend build:

```bash
npm --prefix frontend run build
```

Latest verification:

```text
built successfully
```

## End-To-End Verification

A fresh policy run was verified end to end:

```text
simulationId = SIM-TN-094869
runStatus = completed
completedPhaseCount = 8
```

Completed phases:

```text
phase1_data_foundation
phase2_compatibility
phase3_synthetic_population
phase4_population_validation
phase5_calibration
phase6_policy_engine
phase7_monte_carlo
phase8_recommendation
```

Final `/results` response included:

```text
backendOutput.source = pipeline_artifacts
recommendationId = tn_rec_001_policy_comparison
topRecommendedCandidate = tn_exp_001_pop_uncertainty
classification = Success
beneficiaries = 1835
meanCost = 33169432.91
```

## Important Notes For Team Members

- Do not show frontend final results before Phase 8 completes.
- Do not use the old lightweight estimator as a final result.
- Exact cache should use only `pipeline_artifacts` results.
- Similar-policy memory should use only completed Phase 8 pipeline results.
- DB memory calibrates assumptions. It must not replace simulation.
- Generated artifact files can change during tests and pipeline runs.
- `.env` is local-only and must not be committed.

## Useful Source Files

```text
backend/app/main.py
backend/app/database.py
backend/app/policy_memory.py
backend/app/policy_priors.py
backend/app/pipeline_orchestrator.py
backend/app/pipeline_results.py
backend/app/modules/monte_carlo/config_loader.py
backend/app/modules/calibration/handoff.py
frontend/src/pages/SimulationResults/SimulationResults.tsx
frontend/src/types/index.ts
```

## Current Branch Purpose

The `haran-main` branch contains the up-to-date connected version of the project:

- Supabase connected backend memory
- all 8 phases orchestrated
- DB-backed real progress
- Phase 8 artifact-backed final results
- similar policy memory
- DB priors for Monte Carlo/calibration
- frontend display for similar policies used
- updated README for team onboarding
