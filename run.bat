@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo Virtual environment not found. Run setup.bat first.
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
echo.
echo WebPerf Diagnostics - starting...
echo .env file: %CD%\.env
if exist .env (echo .env found. Configuration will be loaded at startup.) else (echo WARNING: .env not found in this folder.)
echo Database: %CD%\webperf.db
echo Note: restart this window after changing .env values.
echo.
python app.py
pause
