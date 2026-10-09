#!/usr/bin/env bash
echo "==========================================================="
echo "🚀 EstateIQ Standalone Multi-Device IoT Simulator Launcher"
echo "==========================================================="

if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

echo "Installing / updating simulator dependencies..."
pip install -r requirements.txt --quiet

echo ""
echo "Launching Standalone Simulator Web Interface..."
python3 run.py
