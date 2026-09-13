# SOP Project

Tamil Nadu-only policy simulation and synthetic population project.

This repository currently implements **Phase 1: Tamil Nadu Data Source Collection & Data Foundation** in the backend Python module. It does not generate synthetic people, run simulations, or implement policy engines.

## Phase 1 Build

```bash
npm install
npm run phase1:build
npm test
```

## Python Environment

Phase 3 neural generators require the Python dependencies in `requirements.txt`.
See `docs/python_environment.md` for the virtual environment setup and Phase 3 training commands.

The primary artifact is:

```text
data/exports/tamil_nadu_population_reference_template.xlsx
```

The authoritative pipeline is:

```text
backend/app/modules/data_foundation/run_phase1.py
```

It imports PLFS 2024 public-use Tamil Nadu records, keeps DES/Census/data.gov.in/NFHS/NSS provenance separate, writes official aggregate calibration tables, and creates the reference workbook/CSV outputs. NFHS and NSS remain manual-access sources until approved files are supplied.
