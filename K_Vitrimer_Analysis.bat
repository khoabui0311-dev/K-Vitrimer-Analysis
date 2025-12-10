@echo off
title K Vitrimer Analysis
color 0A

echo ========================================
echo  K Vitrimer Analysis v1.0
echo  Starting application...
echo ========================================
echo.

where python >NUL 2>&1
if errorlevel 1 (
  echo [ERROR] Python not found!
  echo Please install Python 3.11+ from:
  echo https://www.python.org/downloads/windows/
  echo.
  echo Make sure to check "Add python.exe to PATH" during installation.
  pause
  exit /b 1
)

if not exist "%~dp0can_relax\gui\app.py" (
  echo [ERROR] Cannot find app.py
  echo Make sure you extracted all files from the ZIP.
  pause
  exit /b 1
)

echo Installing/checking dependencies...
python -m pip install --quiet --upgrade pip
pip install --quiet -r "%~dp0requirements.txt"

if errorlevel 1 (
  echo [WARNING] Some dependencies may not have installed correctly.
  echo The app may still work. Continuing...
  echo.
)

echo.
echo ========================================
echo  Opening K Vitrimer Analysis...
echo  Your browser will open shortly.
echo ========================================
echo.
echo The app will open at: http://localhost:8501
echo.
echo Keep this window open while using the app.
echo Press Ctrl+C to stop the server.
echo.

cd /d "%~dp0"
python -m streamlit run can_relax\gui\app.py

pause
