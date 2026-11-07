@echo off
title EstateIQ Standalone Resource Simulator (Port 8503)
echo ============================================================
echo   Starting Standalone EstateIQ Resource Simulator
echo   Web UI: http://localhost:8503
echo ============================================================
cd /d "%~dp0"
python run.py
pause