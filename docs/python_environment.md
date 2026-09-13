# Python Environment

The Phase 1-3 Python pipeline is designed to run in a project-local virtual environment.

Supported Python version:

- Python >=3.9,<3.15, matching the supported SDV runtime range.

Create and install the environment from the repository root:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Run the lightweight Python integration tests:

```powershell
$env:PYTHONPATH = (Resolve-Path .).Path
.\.venv\Scripts\python.exe -m unittest discover -s backend\app\tests -p "test_*.py"
```

Train the Phase 3 neural generators:

```powershell
$env:PYTHONPATH = (Resolve-Path .).Path
.\.venv\Scripts\python.exe backend\app\modules\synthetic_population\run_phase3_neural_generators.py
```

Generate Phase 3 acceptance populations and the Phase 4 handoff manifest:

```powershell
$env:PYTHONPATH = (Resolve-Path .).Path
.\.venv\Scripts\python.exe backend\app\modules\synthetic_population\run_phase3_finalization.py
```
