@echo off
TITLE EstateIQ Standalone Multi-Device IoT Simulator
echo ===========================================================
echo 🚀 EstateIQ Standalone Multi-Device IoT Simulator Launcher
echo ===========================================================

IF NOT EXIST venv (
    echo Creating Python virtual environment...
    python -m venv venv
)

call venv\Scripts\activate

echo Installing / updating simulator dependencies...
pip install -r requirements.txt --quiet

echo.
echo Launching Standalone Simulator Web Interface...
python run.py
pause
