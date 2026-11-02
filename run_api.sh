#!/usr/bin/env bash
# EstateIQ FastAPI REST API Runner
uvicorn api.main:app --host 127.0.0.1 --port 8000
