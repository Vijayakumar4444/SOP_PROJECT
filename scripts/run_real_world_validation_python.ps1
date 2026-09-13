$ErrorActionPreference = "Stop"

Write-Host "Running Real-World Policy Validation Experiment using Python environment..." -ForegroundColor Cyan

$env:PYTHONPATH = (Get-Location).Path

$VenvPython = Join-Path $PSScriptRoot "..\.venv\Scripts\python.exe"
if (Test-Path $VenvPython) {
    $PythonExe = $VenvPython
} else {
    $PythonExe = "python"
}

Write-Host "Using Python executable: $PythonExe" -ForegroundColor Yellow

& $PythonExe backend/app/modules/real_world_validation/run_real_world_validation.py

if ($LASTEXITCODE -ne 0) {
    Write-Error "Real-World Policy Validation Experiment failed with exit code $LASTEXITCODE"
    exit $LASTEXITCODE
} else {
    Write-Host "Real-World Policy Validation Experiment completed successfully." -ForegroundColor Green
}
