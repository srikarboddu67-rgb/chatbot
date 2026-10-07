@echo off
REM ============================================================
REM  run.bat - double-click to start the AI chatbot (Windows)
REM  - creates the virtual environment if missing
REM  - installs the packages
REM  - starts the server
REM ============================================================
cd /d "%~dp0"

if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

call venv\Scripts\activate.bat

echo Installing packages (only if missing)...
pip install -r requirements.txt

echo.
echo Starting the chatbot... open http://127.0.0.1:5000
echo Press Ctrl+C to stop.
echo.
python backend\app.py

pause
