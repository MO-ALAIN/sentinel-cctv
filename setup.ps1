param([switch]$WithAI)
$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$installTemp = Join-Path $projectRoot '.install-temp'
New-Item -ItemType Directory -Path $installTemp -Force | Out-Null
$env:TEMP = $installTemp
$env:TMP = $installTemp
Push-Location $projectRoot
try {
  if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) { python -m venv .venv }
  & '.\.venv\Scripts\python.exe' -m pip install --no-cache-dir -r backend/requirements.txt
  if ($LASTEXITCODE -ne 0) { throw 'Backend dependency installation failed' }
  if ($WithAI) {
    & '.\.venv\Scripts\python.exe' -m pip install --no-cache-dir torch==2.6.0 torchvision==0.21.0 --index-url https://download.pytorch.org/whl/cu124
    if ($LASTEXITCODE -ne 0) { throw 'PyTorch installation failed' }
    & '.\.venv\Scripts\python.exe' -m pip install --no-cache-dir -r backend/requirements-ai.txt
    if ($LASTEXITCODE -ne 0) { throw 'AI dependency installation failed' }
  }
  Push-Location frontend
  try {
    npm.cmd ci --cache (Join-Path $projectRoot '.npm-cache')
    if ($LASTEXITCODE -ne 0) { throw 'Frontend installation failed' }
    npm.cmd run build
    if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed' }
  } finally { Pop-Location }
} finally { Pop-Location }
