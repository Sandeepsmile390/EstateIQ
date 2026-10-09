"""
EstateIQ Standalone Multi-Device IoT Simulator Launcher (run.py).
Launches local web server for simulator management on http://localhost:8502.
"""

import sys
import os
import uvicorn
from pathlib import Path

# Add project directory to sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

if __name__ == "__main__":
    port = int(os.environ.get("SIMULATOR_PORT", 8502))
    print(f"===========================================================")
    print(f"🚀 Starting Standalone EstateIQ Multi-Device IoT Simulator")
    print(f"📍 Local Web Controller: http://localhost:{port}")
    print(f"===========================================================")
    uvicorn.run("simulator.app:app", host="0.0.0.0", port=port, reload=False)
