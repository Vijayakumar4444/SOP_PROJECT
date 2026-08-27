$ErrorActionPreference = "Stop"

$candidates = @(
  "python",
  "py",
  "C:\Users\Vijayakumar\AppData\Local\Programs\Python\Python313\python.exe",
  "C:\Users\Vijayakumar\AppData\Local\Programs\Python\Python312\python.exe",
  "C:\Program Files\Python313\python.exe",
  "C:\Program Files\Python312\python.exe",
  "C:\Program Files\PostgreSQL\17\pgAdmin 4\python\python.exe"
)

foreach ($candidate in $candidates) {
  try {
    if ($candidate -eq "python" -or $candidate -eq "py" -or (Test-Path -LiteralPath $candidate)) {
      & $candidate "backend/app/modules/data_foundation/run_phase1.py"
      exit $LASTEXITCODE
    }
  } catch {
  }
}

throw "No usable Python interpreter found. Add Python to PATH or update scripts/run_phase1_python.ps1."
