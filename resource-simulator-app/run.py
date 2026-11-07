"""
EstateIQ Standalone Multi-Utility Resource Simulator Launcher (resource-simulator-app/run.py).
Launches local web server for the resource simulator on http://localhost:8503.
"""

import sys
import os
from pathlib import Path
import uvicorn

# Add current directory to sys.path so engine and server are resolvable
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

if __name__ == "__main__":
    port = int(os.environ.get("RESOURCE_SIMULATOR_PORT", os.environ.get("PORT", 8503)))
    print("=" * 68)
    print("  EstateIQ Standalone Multi-Utility Resource Simulator")
    print(f"  Web Controller UI: http://localhost:{port}")
    print(f"  REST API Docs:     http://localhost:{port}/docs")
    print(f"  Utilities:         Electricity, Water, Air Quality, Waste")
    print("  Provenance:        [SIMULATED DATA] - NOT PHYSICAL HARDWARE")
    print("=" * 68)
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)

