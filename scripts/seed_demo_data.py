#!/usr/bin/env python3
"""
EstateIQ Deterministic Demo Seeding Script.
Usage:
    python scripts/seed_demo_data.py
Seeds the campus dataset with known energy, water, air, and waste anomalies.
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

from src.data.seed_data import seed_demo_dataset

if __name__ == "__main__":
    print("\n[INFO] Seeding EstateIQ Deterministic Demo Dataset...")
    res = seed_demo_dataset()
    print("[SUCCESS] Seed Complete:")
    print(f"   Facility: {res['facility_name']} ({res['facility_id']})")
    print(f"   Zones Seeded: {res['zones_seeded']}")
    print(f"   Readings Seeded: {res['readings_seeded']}")
    print(f"   Alerts Seeded: {res['alerts_seeded']}")
    print(f"   Injected Anomalies:")
    for a in res["injected_anomalies"]:
        print(f"     * {a}")
    print("\nLocal demo is ready and repeatable.\n")
