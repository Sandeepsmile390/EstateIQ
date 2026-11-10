@echo off
REM EstateIQ FastAPI REST API Windows Launcher
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
