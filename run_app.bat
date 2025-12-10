@echo off
setlocal
set VENV_DIR=.venv

where python >NUL 2>&1
if errorlevel 1 (
  echo Python 3.11+ is required. Install from https://www.python.org/downloads/windows/ and rerun this script.
  pause
  exit /b 1
)

if not exist "%VENV_DIR%\Scripts\python.exe" (
  echo Creating virtual environment in %VENV_DIR% ...
  python -m venv "%VENV_DIR%"
)

echo Activating virtual environment...
call "%VENV_DIR%\Scripts\activate.bat"

if errorlevel 1 (
  echo Failed to activate virtual environment.
  pause
  exit /b 1
)

echo Installing/upgrading dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt

if errorlevel 1 (
  echo Dependency installation failed.
  pause
  exit /b 1
)

echo Launching K Vitrimer Analysis...
streamlit run can_relax/gui/app.py

endlocal
