@echo off
setlocal
cd /d "%~dp0"
if not exist .venv (
  py -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
if not exist .env copy .env.example .env
 echo.
echo Setup complete.
echo Add your Google PageSpeed key, Google Places key and Razorpay test keys to .env.
echo Then run run.bat
pause
