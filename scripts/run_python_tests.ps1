$ErrorActionPreference = "Stop"

$candidates = @(
  ".\.venv\Scripts\python.exe",
  "python",
  "py",
  "C:\Program Files\PostgreSQL\17\pgAdmin 4\python\python.exe"
)

$env:PYTHONPATH = (Get-Location).Path

foreach ($candidate in $candidates) {
  try {
    if ($candidate -ne "python" -and $candidate -ne "py" -and -not (Test-Path -LiteralPath $candidate)) {
      continue
    }
    & $candidate -c "import sys; print(sys.executable)" *> $null
    if ($LASTEXITCODE -ne 0) {
      continue
    }
    & $candidate -m unittest discover -s backend\app\tests -p "test_*.py"
    exit $LASTEXITCODE
  } catch {
  }
}

throw "No usable Python runtime was found for unit tests."
