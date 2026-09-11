$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$env:PYTHONPATH = $projectRoot
Set-Location $projectRoot
$candidates = @("python", "py", "C:\Users\Vijayakumar\AppData\Local\Programs\Python\Python313\python.exe", "C:\Users\Vijayakumar\AppData\Local\Programs\Python\Python312\python.exe", "C:\Program Files\Python313\python.exe", "C:\Program Files\Python312\python.exe", "C:\Program Files\PostgreSQL\17\pgAdmin 4\python\python.exe", "C:\Users\User\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe")
foreach ($candidate in $candidates) {
  try {
    if ($candidate -eq "python" -or $candidate -eq "py" -or (Test-Path -LiteralPath $candidate)) {
      & $candidate "backend/app/modules/synthetic_population/run_phase3_tests_and_comparison_smoke.py"
      exit $LASTEXITCODE
    }
  } catch {}
}
throw "No usable Python interpreter found."
