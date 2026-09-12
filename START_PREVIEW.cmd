@echo off
setlocal
title Sentinel local preview - keep this window open
cd /d "%~dp0backend"
set "TEMP=%~dp0..\.install-temp"
set "TMP=%TEMP%"
if not exist "%TEMP%" mkdir "%TEMP%"
if not exist "..\.venv\Scripts\python.exe" (
  echo Python environment missing. Run setup.ps1 first.
  pause
  exit /b 1
)
if not exist "..\frontend\dist\index.html" (
  echo Frontend build missing. Run setup.ps1 first.
  pause
  exit /b 1
)
echo Open http://127.0.0.1:8000/dashboard/ in your browser.
echo Keep this window open while using the preview. Press Ctrl+C to stop.
"..\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pause
