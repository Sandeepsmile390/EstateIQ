"""
Master Model Training Script.
Usage:
    python scripts/train_models.py
"""

import sys
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from train_all_modules import train_entire_facility_system

if __name__ == "__main__":
    print("Starting ML Model Training across all 9 facility domain modules...")
    train_entire_facility_system()
    print("Model training complete.")
