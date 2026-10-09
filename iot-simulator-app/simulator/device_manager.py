"""
Virtual Device Manager (simulator/device_manager.py).
Manages virtual IoT device creation, editing, status tracking (Running, Paused, Stopped),
profile assignments, interactive control overrides, and telemetry generation loop.
"""

import uuid
import datetime
from typing import Dict, Any, List, Optional
from simulator.config import GLOBAL_SIM_CONFIG
from simulator.sensor_models import SensorProfile
from simulator.scenario_engine import ScenarioEngine

class VirtualDeviceItem:
    def __init__(self, data: Dict[str, Any]):
        self.device_id = data.get("device_id") or f"DEV_{uuid.uuid4().hex[:8].upper()}"
        self.device_name = data.get("device_name", self.device_id)
        self.device_type = data.get("device_type", "electricity_meter")
        self.facility_id = data.get("facility_id", GLOBAL_SIM_CONFIG.get("facility_id", "FAC_GEC_CAMPUS"))
        self.building_id = data.get("building_id", GLOBAL_SIM_CONFIG.get("building_id", "Block B Hostel"))
        self.floor_room = data.get("floor_room", "Floor 1 / Room 101")
        self.status = data.get("status", "ONLINE")  # ONLINE, PAUSED, STOPPED
        self.sampling_interval_sec = float(data.get("sampling_interval_sec", GLOBAL_SIM_CONFIG.get("sample_interval_sec", 5.0)))
        self.active_scenario = data.get("active_scenario", GLOBAL_SIM_CONFIG.get("active_scenario", "Normal Campus Operation"))
        self.created_at = data.get("created_at") or datetime.datetime.now().isoformat()
        self.last_sample_at = data.get("last_sample_at")
        self.overrides: Dict[str, Any] = data.get("overrides", {})
        self.readings: Dict[str, Any] = data.get("readings", {})
        self.sequence_number: int = data.get("sequence_number", 1)

    def generate_next_sample(self) -> Dict[str, Any]:
        """Generates physics-based telemetry for active device profile."""
        if self.status != "ONLINE":
            return {}

        metrics = SensorProfile.generate_metrics(
            device_type=self.device_type,
            current_readings=self.readings,
            scenario=self.active_scenario,
            overrides=self.overrides
        )
        self.readings.update(metrics)
        self.last_sample_at = datetime.datetime.now().isoformat()
        self.sequence_number += 1

        formatted_metrics = []
        for k, v in metrics.items():
            unit = "kW" if "kw" in k else ("kWh" if "kwh" in k else ("°C" if "c" in k or "temp" in k else ("%" if "pct" in k or "factor" in k else ("A" if "a" in k else ("V" if "v" in k else ("L/min" if "lmin" in k else ("m³" if "m3" in k else ("bar" if "bar" in k else ("count" if "count" in k else "val")))))))))
            formatted_metrics.append({
                "metric": k,
                "value": v,
                "unit": unit,
                "quality": "bad" if self.active_scenario == "Invalid Sensor Reading" and k == "active_power_kw" else "good"
            })

        return {
            "schema_version": "1.0",
            "message_id": f"MSG_{uuid.uuid4().hex[:8].upper()}",
            "simulator_id": GLOBAL_SIM_CONFIG.get("instance_id"),
            "device_id": self.device_id,
            "facility_id": self.facility_id,
            "building_id": self.building_id,
            "source_type": "simulated_iot",
            "event_timestamp": self.last_sample_at,
            "sent_timestamp": datetime.datetime.now().isoformat(),
            "sequence_number": self.sequence_number,
            "metrics": formatted_metrics
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "device_id": self.device_id,
            "device_name": self.device_name,
            "device_type": self.device_type,
            "facility_id": self.facility_id,
            "building_id": self.building_id,
            "floor_room": self.floor_room,
            "status": self.status,
            "sampling_interval_sec": self.sampling_interval_sec,
            "active_scenario": self.active_scenario,
            "created_at": self.created_at,
            "last_sample_at": self.last_sample_at,
            "overrides": self.overrides,
            "readings": self.readings,
            "sequence_number": self.sequence_number
        }

VirtualDevice = VirtualDeviceItem

class DeviceManager:
    """Manages virtual IoT device inventory."""

    def __init__(self):
        self.devices: Dict[str, VirtualDeviceItem] = {}
        self._create_default_virtual_devices()

    def _create_default_virtual_devices(self):
        inst_id = GLOBAL_SIM_CONFIG.get("instance_id")
        defaults = [
            {
                "device_id": f"METER-BLOCK-A-001",
                "device_name": "Block A Main Power Meter",
                "device_type": "electricity_meter",
                "facility_id": GLOBAL_SIM_CONFIG.get("facility_id"),
                "building_id": "Block A Academic",
                "status": "ONLINE"
            },
            {
                "device_id": f"METER-BLOCK-B-001",
                "device_name": "Block B Main Power Meter",
                "device_type": "electricity_meter",
                "facility_id": GLOBAL_SIM_CONFIG.get("facility_id"),
                "building_id": "Block B Hostel",
                "status": "ONLINE"
            },
            {
                "device_id": f"HVAC-BLOCK-B-001",
                "device_name": "Block B Central HVAC Monitor",
                "device_type": "hvac_monitor",
                "facility_id": GLOBAL_SIM_CONFIG.get("facility_id"),
                "building_id": "Block B Hostel",
                "status": "ONLINE"
            },
            {
                "device_id": f"WATER-BLOCK-A-001",
                "device_name": "Block A Water Flow Meter",
                "device_type": "water_meter",
                "facility_id": GLOBAL_SIM_CONFIG.get("facility_id"),
                "building_id": "Block A Academic",
                "status": "ONLINE"
            },
            {
                "device_id": f"XFMR-MAIN-001",
                "device_name": "Substation Transformer 01",
                "device_type": "transformer",
                "facility_id": GLOBAL_SIM_CONFIG.get("facility_id"),
                "building_id": "Main Substation",
                "status": "ONLINE"
            },
            {
                "device_id": f"DG-CAMPUS-001",
                "device_name": "Standby Diesel Generator 500kVA",
                "device_type": "dg_monitor",
                "facility_id": GLOBAL_SIM_CONFIG.get("facility_id"),
                "building_id": "Power House",
                "status": "ONLINE"
            },
            {
                "device_id": f"TANK-LEVEL-001",
                "device_name": "Hostel Overhead Water Tank Sensor",
                "device_type": "water_tank",
                "facility_id": GLOBAL_SIM_CONFIG.get("facility_id"),
                "building_id": "Block B Hostel",
                "status": "ONLINE"
            },
            {
                "device_id": f"OCCUPANCY-LAB-001",
                "device_name": "Central Lab Occupancy Counter",
                "device_type": "occupancy_sensor",
                "facility_id": GLOBAL_SIM_CONFIG.get("facility_id"),
                "building_id": "Block A Academic",
                "status": "ONLINE"
            },
            {
                "device_id": f"AQI-CAMPUS-001",
                "device_name": "Campus Environmental AQI Monitor",
                "device_type": "air_quality",
                "facility_id": GLOBAL_SIM_CONFIG.get("facility_id"),
                "building_id": "Main Quadrangle",
                "status": "ONLINE"
            }
        ]
        for d in defaults:
            item = VirtualDeviceItem(d)
            self.devices[item.device_id] = item

    def initialize_default_devices(self):
        self._create_default_virtual_devices()

    def create_device(self, data: Dict[str, Any]) -> VirtualDeviceItem:
        item = VirtualDeviceItem(data)
        self.devices[item.device_id] = item
        return item

    def update_device_overrides(self, device_id: str, overrides: Dict[str, Any]) -> Optional[VirtualDeviceItem]:
        dev = self.devices.get(device_id)
        if dev:
            dev.overrides.update(overrides)
            return dev
        return None

    def set_device_status(self, device_id: str, status: str) -> Optional[VirtualDeviceItem]:
        dev = self.devices.get(device_id)
        if dev:
            dev.status = status
            return dev
        return None

    def set_device_scenario(self, device_id: str, scenario: str) -> Optional[VirtualDeviceItem]:
        dev = self.devices.get(device_id)
        if dev:
            dev.active_scenario = scenario
            return dev
        return None

    def delete_device(self, device_id: str) -> bool:
        if device_id in self.devices:
            del self.devices[device_id]
            return True
        return False

    def list_devices(self) -> List[Dict[str, Any]]:
        return [d.to_dict() for d in self.devices.values()]

GLOBAL_DEVICE_MANAGER = DeviceManager()
