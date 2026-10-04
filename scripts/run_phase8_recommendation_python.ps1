$ErrorActionPreference = "Stop"

Write-Host "Running Phase 8 Recommendation Engine using Python environment..." -ForegroundColor Cyan

$env:PYTHONPATH = (Get-Location).Path
$env:PYTHONIOENCODING = "utf-8"

$VenvPython = Join-Path $PSScriptRoot "..\.venv\Scripts\python.exe"
$PgAdminPython = "C:\Program Files\PostgreSQL\17\pgAdmin 4\python\python.exe"
$BundledPython = "C:\Users\User\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$Candidates = @($VenvPython, $PgAdminPython, $BundledPython, "python", "py")
$PythonExe = $null

foreach ($Candidate in $Candidates) {
    try {
        if ($Candidate -ne "python" -and $Candidate -ne "py" -and -not (Test-Path -LiteralPath $Candidate)) {
            continue
        }
        & $Candidate -c "import sys; print(sys.executable)" *> $null
        if ($LASTEXITCODE -eq 0) {
            $PythonExe = $Candidate
            break
        }
    } catch {
    }
}

if (-not $PythonExe) {
    throw "No usable Python interpreter found."
}

Write-Host "Using Python executable: $PythonExe" -ForegroundColor Yellow

& $PythonExe backend/app/modules/recommendation/run_phase8_recommendation.py

if ($LASTEXITCODE -ne 0) {
    Write-Error "Phase 8 Recommendation Engine failed with exit code $LASTEXITCODE"
    exit $LASTEXITCODE
} else {
    Write-Host "Phase 8 Recommendation Engine completed successfully." -ForegroundColor Green
}
