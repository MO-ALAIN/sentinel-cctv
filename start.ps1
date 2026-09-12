$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Run setup.ps1 first.' }
if (-not (Test-Path -LiteralPath (Join-Path $projectRoot 'frontend\dist\index.html'))) { throw 'Build frontend first: cd frontend; npm run build' }
Push-Location (Join-Path $projectRoot 'backend')
try { & $pythonPath -m uvicorn app.main:app --host 127.0.0.1 --port 8000 }
finally { Pop-Location }
