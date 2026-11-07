@echo off
title EstateIQ Standalone Resource Simulator (Port 8503)
echo ============================================================
echo   Launching EstateIQ Standalone Resource Simulator
echo   URL: http://localhost:8503
echo ============================================================
cd /d "%~dp0resource-simulator-app"
python run.py
pause

