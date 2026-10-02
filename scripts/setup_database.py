"""
Database & Dataset Initialization Script.
Usage:
    python scripts/setup_database.py
"""

import sys
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))
sys.path.append(str(BASE_DIR / "facility_dataset"))

from generator.main import run_master_generation

if __name__ == "__main__":
    print("Initializing Facility Database & IoT Synthetic Data Engine...")
    run_master_generation()
    print("Database initialization complete.")
