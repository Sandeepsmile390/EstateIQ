"""
Local Configuration & Persistence Manager (simulator/config.py).
Persists simulator instance ID, name, EstateIQ server URL, pairing token,
and sample intervals across application restarts.
"""

import os
import json
import uuid
from pathlib import Path
from typing import Dict, Any, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CONFIG_FILE = DATA_DIR / "config.json"

class SimulatorConfig:
    """Manages local persistent configuration for standalone simulator app."""

    def __init__(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._config: Dict[str, Any] = self._load_default_config()
        self.load()

    def _load_default_config(self) -> Dict[str, Any]:
        inst_id = os.environ.get("SIMULATOR_INSTANCE_ID") or f"SIM_LAPTOP_{uuid.uuid4().hex[:6].upper()}"
        return {
            "instance_id": inst_id,
            "instance_name": os.environ.get("SIMULATOR_INSTANCE_NAME", f"Campus-Simulator-{inst_id}"),
            "estateiq_server_url": os.environ.get("ESTATEIQ_SERVER_URL", "http://127.0.0.1:8000"),
            "pairing_code": os.environ.get("PAIRING_CODE", "IQ-DEMO"),
            "facility_id": os.environ.get("FACILITY_ID", "FAC_GEC_CAMPUS"),
            "building_id": os.environ.get("BUILDING_ID", "Block B Hostel"),
            "sample_interval_sec": float(os.environ.get("SAMPLE_INTERVAL_SEC", 5.0)),
            "simulation_speed": 1,
            "auth_token": "",
            "registered": False,
            "active_scenario": "Normal Campus Operation",
            "offline_buffer_limit": 500
        }

    def load(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    self._config.update(saved)
            except Exception as e:
                print(f"Warning: Failed to load {CONFIG_FILE}, using defaults: {e}")

    def save(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=2)
        except Exception as e:
            print(f"Error saving config to {CONFIG_FILE}: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)

    def set(self, key: str, value: Any):
        self._config[key] = value
        self.save()

    def to_dict(self) -> Dict[str, Any]:
        return dict(self._config)

GLOBAL_SIM_CONFIG = SimulatorConfig()
