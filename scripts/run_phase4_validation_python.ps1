$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$env:PYTHONPATH = $projectRoot
Set-Location $projectRoot
$candidates = @("python", "py", "C:\Program Files\PostgreSQL\17\pgAdmin 4\python\python.exe")

foreach ($candidate in $candidates) {
  try {
    if ($candidate -ne "python" -and $candidate -ne "py" -and -not (Test-Path -LiteralPath $candidate)) {
      continue
    }
    & $candidate -c "import sys; print(sys.executable)" *> $null
    if ($LASTEXITCODE -ne 0) {
      continue
    }
    & $candidate "backend/app/modules/population_validation/run_phase4_validation.py"
    exit $LASTEXITCODE
  } catch {}
}

throw "No usable Python interpreter found."
