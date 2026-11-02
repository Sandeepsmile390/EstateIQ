#!/usr/bin/env python3
"""
EstateIQ Demo Reset Script.
Usage:
    python scripts/reset_demo.py
Resets database back to clean known deterministic demo state without manual editing.
"""

import sys
import os
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.data.seed_data import reset_demo_dataset

if __name__ == "__main__":
    print("\n[INFO] Resetting EstateIQ Demo Environment to Known Initial State...")
    res = reset_demo_dataset()
    print("[SUCCESS] Demo Reset Successfully Completed.")
    print(f"   Facility: {res['facility_name']} ({res['facility_id']})")
    print(f"   Readings: {res['readings_seeded']}")
    print(f"   Alerts: {res['alerts_seeded']}")
    print("   Application is in verified clean demo condition.\n")
