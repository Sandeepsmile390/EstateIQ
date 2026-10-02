"""
Generator Configuration Module.
Enforces SEED = 42 for 100% deterministic, reproducible generation.
Sets up date range: 2026-01-01 00:00:00 to 2026-06-29 23:45:00 at 15-minute intervals.
"""

import os
import json
import logging
from pathlib import Path
import numpy as np
import pandas as pd

# Deterministic Seed
SEED = 42
np.random.seed(SEED)

# Time Range: 180 Days at 15-minute resolution
START_TIME = pd.Timestamp("2026-01-01 00:00:00", tz="Asia/Kolkata")
END_TIME = pd.Timestamp("2026-06-29 23:45:00", tz="Asia/Kolkata")
FREQ = "15min"

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
ML_DATA_DIR = DATA_DIR / "ml"
REPORTS_DIR = BASE_DIR / "reports"
DB_PATH = BASE_DIR / "facility.db"

# Ensure directories exist
for p in [RAW_DATA_DIR, PROCESSED_DATA_DIR, ML_DATA_DIR, REPORTS_DIR]:
    p.mkdir(parents=True, exist_ok=True)

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(REPORTS_DIR / "generator.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("FacilityGenerator")

def load_json_config(filename: str) -> dict:
    filepath = CONFIG_DIR / filename
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def get_master_timestamps() -> pd.DatetimeIndex:
    return pd.date_range(start=START_TIME, end=END_TIME, freq=FREQ)
