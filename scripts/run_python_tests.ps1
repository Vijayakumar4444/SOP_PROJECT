$ErrorActionPreference = "Stop"

$candidates = @(
  "python",
  "py",
  "C:\Program Files\PostgreSQL\17\pgAdmin 4\python\python.exe"
)

$env:PYTHONPATH = (Get-Location).Path

foreach ($candidate in $candidates) {
  try {
    & $candidate -m unittest discover -s backend\app\tests -p "test_*.py"
    exit $LASTEXITCODE
  } catch {
  }
}

throw "No usable Python runtime was found for unit tests."
