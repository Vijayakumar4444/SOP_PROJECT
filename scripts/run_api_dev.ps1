$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$projectVenv = Join-Path $root ".venv\Scripts\python.exe"
$bundledPython = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$pgAdminPython = "C:\Program Files\PostgreSQL\17\pgAdmin 4\python\python.exe"
$python = $null

$candidates = @(
  $projectVenv,
  $pgAdminPython,
  $bundledPython,
  "python"
)

foreach ($candidate in $candidates) {
  if ($candidate -ne "python" -and -not (Test-Path $candidate)) {
    continue
  }
  try {
    & $candidate -c "import uvicorn" *> $null
    if ($LASTEXITCODE -eq 0) {
      $python = $candidate
      break
    }
  } catch {
  }
}

if (-not $python) {
  throw "No usable Python runtime with uvicorn was found. Install project requirements first."
}

Set-Location $root
& $python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8010
