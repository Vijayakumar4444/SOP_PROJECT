$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$bundledPython = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$python = $null

if (Test-Path $bundledPython) {
  $python = $bundledPython
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
  $python = "python"
} else {
  throw "Python was not found. Install Python or use the Codex bundled runtime."
}

Set-Location $root
& $python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8010
