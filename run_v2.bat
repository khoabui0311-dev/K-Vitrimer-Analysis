@echo off
setlocal
cd /d "%~dp0"
echo === VitriFit 2.0 local development launcher ===

if not exist ".venv2\Scripts\python.exe" (
    where py >nul 2>nul
    if errorlevel 1 (
        echo Python launcher not found. Install Python 3.11+ and retry.
        pause
        exit /b 1
    )
    py -3 -m venv .venv2
    if errorlevel 1 goto :fail
    ".venv2\Scripts\python.exe" -m pip install -r requirements.txt -r requirements-v2.txt
    if errorlevel 1 goto :fail
)

if not exist "vitrifit2\web\dist\index.html" (
    where npm >nul 2>nul
    if errorlevel 1 (
        echo Node.js / npm is needed to build the web interface once.
        pause
        exit /b 1
    )
    pushd vitrifit2\web
    call npm install --no-audit --no-fund
    if errorlevel 1 (
        popd
        goto :fail
    )
    call npm run build
    if errorlevel 1 (
        popd
        goto :fail
    )
    popd
)

echo Open http://127.0.0.1:8000 in your browser.
echo The server runs locally only. Close this window to stop.
".venv2\Scripts\python.exe" run_v2.py
exit /b %errorlevel%

:fail
echo VitriFit 2 setup failed. No changes were made to the v1 application.
pause
exit /b 1
