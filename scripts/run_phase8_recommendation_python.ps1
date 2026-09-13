$ErrorActionPreference = "Stop"

Write-Host "Running Phase 8 Recommendation Engine using Python environment..." -ForegroundColor Cyan

$env:PYTHONPATH = (Get-Location).Path

$VenvPython = Join-Path $PSScriptRoot "..\.venv\Scripts\python.exe"
if (Test-Path $VenvPython) {
    $PythonExe = $VenvPython
} else {
    $PythonExe = "python"
}

Write-Host "Using Python executable: $PythonExe" -ForegroundColor Yellow

& $PythonExe backend/app/modules/recommendation/run_phase8_recommendation.py

if ($LASTEXITCODE -ne 0) {
    Write-Error "Phase 8 Recommendation Engine failed with exit code $LASTEXITCODE"
    exit $LASTEXITCODE
} else {
    Write-Host "Phase 8 Recommendation Engine completed successfully." -ForegroundColor Green
}
