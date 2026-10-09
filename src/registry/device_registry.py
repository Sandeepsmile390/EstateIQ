"""
EstateIQ IoT Device & Simulator Registry (src/registry/device_registry.py).
Authoritative backend registry for simulator instances, paired devices,
heartbeat tracking, single-use pairing codes, and telemetry ingestion buffer.
"""

import time
import uuid
import secrets
import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class SimulatorInstance(BaseModel):
    instance_id: str
    instance_name: str
    facility_id: str = "FAC_GEC_CAMPUS"
    building_id: str = "Block B Hostel"
    ip_address: Optional[str] = "127.0.0.1"
    status: str = "CONNECTED"  # CONNECTED, STALE, OFFLINE, REVOKED
    registered_at: str
    last_heartbeat_at: str
    last_telemetry_at: Optional[str] = None
    device_count: int = 0
    active_scenario: str = "Normal Campus Operation"
    sample_interval_sec: float = 5.0
    auth_token: str
    revoked: bool = False

class VirtualDevice(BaseModel):
    device_id: str
    device_name: str
    instance_id: str
    device_type: str  # electricity_meter, hvac_monitor, water_meter, transformer, dg, etc.
    facility_id: str = "FAC_GEC_CAMPUS"
    building_id: str = "Block B Hostel"
    floor_room: Optional[str] = "Floor 2 / Room 204"
    status: str = "ONLINE"  # ONLINE, PAUSED, STALE, OFFLINE
    sensors: List[str] = Field(default_factory=list)
    sampling_interval_sec: float = 5.0
    created_at: str
    last_sample_at: Optional[str] = None
    last_telemetry: Dict[str, Any] = Field(default_factory=dict)
    active_scenario: str = "Normal Campus Operation"
    data_source_badge: str = "[SIMULATED IoT]"

class TelemetryEnvelope(BaseModel):
    schema_version: str = "1.0"
    message_id: str = Field(default_factory=lambda: f"MSG_{uuid.uuid4().hex[:8].upper()}")
    simulator_id: str
    device_id: str
    facility_id: str = "FAC_GEC_CAMPUS"
    building_id: str = "Block B Hostel"
    source_type: str = "simulated_iot"
    event_timestamp: str
    sent_timestamp: str
    sequence_number: int = 1
    metrics: List[Dict[str, Any]] = Field(default_factory=list)

class DeviceRegistryEngine:
    """Master backend manager for IoT simulators, pairing keys, and telemetry streams."""

    def __init__(self):
        self.simulators: Dict[str, SimulatorInstance] = {}
        self.devices: Dict[str, VirtualDevice] = {}
        self.pairing_codes: Dict[str, Dict[str, Any]] = {}
        self.telemetry_history: List[Dict[str, Any]] = []
        self.max_telemetry_history: int = 2000
        self._init_default_demo_simulators()

    def _init_default_demo_simulators(self):
        """Populates default demonstration simulator instance if none exist."""
        now_iso = datetime.datetime.now().isoformat()
        demo_sim = SimulatorInstance(
            instance_id="SIM_CAMPUS_01",
            instance_name="Campus-Simulator-01 (Main Gate)",
            facility_id="FAC_GEC_CAMPUS",
            building_id="Block B Hostel",
            ip_address="192.168.1.35",
            status="CONNECTED",
            registered_at=now_iso,
            last_heartbeat_at=now_iso,
            last_telemetry_at=now_iso,
            device_count=4,
            active_scenario="Normal Campus Operation",
            sample_interval_sec=5.0,
            auth_token="sim_tok_demo_123456789"
        )
        self.simulators[demo_sim.instance_id] = demo_sim

        demo_devices = [
            VirtualDevice(
                device_id="METER-BLOCK-B-001",
                device_name="Block B Main Power Meter",
                instance_id="SIM_CAMPUS_01",
                device_type="electricity_meter",
                facility_id="FAC_GEC_CAMPUS",
                building_id="Block B Hostel",
                status="ONLINE",
                sensors=["active_power_kw", "energy_kwh", "voltage_v", "current_a", "power_factor"],
                sampling_interval_sec=5.0,
                created_at=now_iso,
                last_sample_at=now_iso,
                last_telemetry={"active_power_kw": 58.4, "energy_kwh": 145.2, "voltage_v": 230.5, "current_a": 253.2, "power_factor": 0.95},
                active_scenario="Normal Campus Operation"
            ),
            VirtualDevice(
                device_id="HVAC-BLOCK-B-001",
                device_name="Block B Chiller & AHU Unit",
                instance_id="SIM_CAMPUS_01",
                device_type="hvac_monitor",
                facility_id="FAC_GEC_CAMPUS",
                building_id="Block B Hostel",
                status="ONLINE",
                sensors=["hvac_power_kw", "chiller_temp_c", "fan_speed_rpm", "vibration_mm_s"],
                sampling_interval_sec=5.0,
                created_at=now_iso,
                last_sample_at=now_iso,
                last_telemetry={"hvac_power_kw": 42.0, "chiller_temp_c": 7.2, "fan_speed_rpm": 1450, "vibration_mm_s": 1.2},
                active_scenario="High HVAC Consumption"
            ),
            VirtualDevice(
                device_id="WATER-BLOCK-A-001",
                device_name="Block A Hydro Flow Meter",
                instance_id="SIM_CAMPUS_01",
                device_type="water_meter",
                facility_id="FAC_GEC_CAMPUS",
                building_id="Block A Academic",
                status="ONLINE",
                sensors=["flow_rate_lmin", "cumulative_m3", "pressure_bar"],
                sampling_interval_sec=5.0,
                created_at=now_iso,
                last_sample_at=now_iso,
                last_telemetry={"flow_rate_lmin": 48.2, "cumulative_m3": 1240.5, "pressure_bar": 3.4},
                active_scenario="Normal Campus Operation"
            ),
            VirtualDevice(
                device_id="DG-CAMPUS-001",
                device_name="Main Diesel Generator (500 kVA)",
                instance_id="SIM_CAMPUS_01",
                device_type="dg_monitor",
                facility_id="FAC_GEC_CAMPUS",
                building_id="Main Campus Substation",
                status="ONLINE",
                sensors=["fuel_level_pct", "engine_rpm", "oil_pressure_psi", "run_hours"],
                sampling_interval_sec=10.0,
                created_at=now_iso,
                last_sample_at=now_iso,
                last_telemetry={"fuel_level_pct": 82.5, "engine_rpm": 1500, "oil_pressure_psi": 55.0, "run_hours": 342.0},
                active_scenario="Normal Campus Operation"
            )
        ]
        for d in demo_devices:
            self.devices[d.device_id] = d

    def generate_pairing_code(self, ttl_minutes: int = 15) -> Dict[str, Any]:
        """Generates a single-use pairing code for connecting new standalone simulator laptops."""
        code = f"IQ-{secrets.randbelow(899999) + 100000}"
        expires_at = time.time() + (ttl_minutes * 60)
        self.pairing_codes[code] = {
            "code": code,
            "created_at": datetime.datetime.now().isoformat(),
            "expires_at": expires_at,
            "used": False
        }
        return {
            "pairing_code": code,
            "expires_in_minutes": ttl_minutes,
            "instruction": "Enter this pairing code in the standalone EstateIQ IoT Simulator app on your simulator laptop."
        }

    def validate_pairing_code(self, code: str) -> bool:
        """Validates if pairing code is valid, unexpired, and single-use."""
        code_entry = self.pairing_codes.get(code.strip().upper())
        if not code_entry:
            return False
        if code_entry["used"] or time.time() > code_entry["expires_at"]:
            return False
        code_entry["used"] = True
        return True

    def register_simulator(
        self,
        instance_id: str,
        instance_name: str,
        pairing_code: str,
        facility_id: str = "FAC_GEC_CAMPUS",
        building_id: str = "Block B Hostel",
        ip_address: str = "127.0.0.1"
    ) -> Dict[str, Any]:
        """Registers a standalone simulator instance after pairing code validation."""
        if not self.validate_pairing_code(pairing_code):
            # If code is invalid/expired, raise or allow fallback for local demo pairing code "IQ-DEMO"
            if pairing_code.strip().upper() != "IQ-DEMO":
                return {"success": False, "error": "INVALID_PAIRING_CODE", "message": "Pairing code is invalid, expired, or already used."}

        now_iso = datetime.datetime.now().isoformat()
        auth_token = f"sim_tok_{uuid.uuid4().hex}"

        sim = SimulatorInstance(
            instance_id=instance_id,
            instance_name=instance_name,
            facility_id=facility_id,
            building_id=building_id,
            ip_address=ip_address,
            status="CONNECTED",
            registered_at=now_iso,
            last_heartbeat_at=now_iso,
            last_telemetry_at=now_iso,
            device_count=0,
            active_scenario="Normal Campus Operation",
            auth_token=auth_token,
            revoked=False
        )
        self.simulators[instance_id] = sim

        return {
            "success": True,
            "instance_id": instance_id,
            "instance_name": instance_name,
            "auth_token": auth_token,
            "status": "REGISTERED_SUCCESSFULLY",
            "estateiq_time": now_iso
        }

    def record_heartbeat(self, instance_id: str, active_devices_count: int = 0, scenario: str = "Normal Campus Operation") -> Dict[str, Any]:
        """Updates heartbeat and connection status for a simulator instance."""
        sim = self.simulators.get(instance_id)
        if not sim or sim.revoked:
            return {"success": False, "error": "UNAUTHORIZED_SIMULATOR"}

        now_iso = datetime.datetime.now().isoformat()
        sim.last_heartbeat_at = now_iso
        sim.status = "CONNECTED"
        sim.device_count = active_devices_count
        sim.active_scenario = scenario

        return {
            "success": True,
            "instance_id": instance_id,
            "status": "CONNECTED",
            "server_timestamp": now_iso
        }

    def register_device(self, device_data: Dict[str, Any]) -> Dict[str, Any]:
        """Registers a virtual IoT device attached to a paired simulator instance."""
        inst_id = device_data.get("instance_id")
        if not inst_id or inst_id not in self.simulators or self.simulators[inst_id].revoked:
            return {"success": False, "error": "UNREGISTERED_SIMULATOR_INSTANCE"}

        dev_id = device_data.get("device_id") or f"DEV_{uuid.uuid4().hex[:8].upper()}"
        now_iso = datetime.datetime.now().isoformat()

        dev = VirtualDevice(
            device_id=dev_id,
            device_name=device_data.get("device_name", dev_id),
            instance_id=inst_id,
            device_type=device_data.get("device_type", "electricity_meter"),
            facility_id=device_data.get("facility_id", self.simulators[inst_id].facility_id),
            building_id=device_data.get("building_id", self.simulators[inst_id].building_id),
            floor_room=device_data.get("floor_room", "Floor 1"),
            status="ONLINE",
            sensors=device_data.get("sensors", ["active_power_kw", "energy_kwh"]),
            sampling_interval_sec=float(device_data.get("sampling_interval_sec", 5.0)),
            created_at=now_iso,
            last_sample_at=now_iso,
            active_scenario=device_data.get("active_scenario", "Normal Campus Operation")
        )
        self.devices[dev_id] = dev
        self.simulators[inst_id].device_count = len([d for d in self.devices.values() if d.instance_id == inst_id])

        return {"success": True, "device_id": dev_id, "status": "REGISTERED"}

    def ingest_telemetry(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Ingests a telemetry envelope or batch, validates payload, and updates device state."""
        envelope = TelemetryEnvelope(**payload) if "simulator_id" in payload else None
        if not envelope:
            return {"success": False, "error": "INVALID_ENVELOPE_SCHEMA"}

        sim = self.simulators.get(envelope.simulator_id)
        if not sim or sim.revoked:
            return {"success": False, "error": "REVOKED_OR_UNKNOWN_SIMULATOR"}

        dev = self.devices.get(envelope.device_id)
        if not dev:
            # Auto-register device if unknown
            dev = VirtualDevice(
                device_id=envelope.device_id,
                device_name=envelope.device_id,
                instance_id=envelope.simulator_id,
                device_type="generic_sensor",
                facility_id=envelope.facility_id,
                building_id=envelope.building_id,
                status="ONLINE",
                created_at=datetime.datetime.now().isoformat()
            )
            self.devices[envelope.device_id] = dev

        now_iso = datetime.datetime.now().isoformat()
        sim.last_telemetry_at = now_iso
        sim.last_heartbeat_at = now_iso
        sim.status = "CONNECTED"

        dev.last_sample_at = envelope.event_timestamp
        dev.status = "ONLINE"

        metrics_map = {}
        for item in envelope.metrics:
            if isinstance(item, dict) and "metric" in item and "value" in item:
                metrics_map[item["metric"]] = item["value"]
        dev.last_telemetry.update(metrics_map)

        record = {
            "message_id": envelope.message_id,
            "simulator_id": envelope.simulator_id,
            "device_id": envelope.device_id,
            "facility_id": envelope.facility_id,
            "building_id": envelope.building_id,
            "source_type": "simulated_iot",
            "data_source_badge": "[SIMULATED IoT]",
            "event_timestamp": envelope.event_timestamp,
            "ingested_at": now_iso,
            "sequence_number": envelope.sequence_number,
            "metrics": metrics_map
        }
        self.telemetry_history.insert(0, record)
        if len(self.telemetry_history) > self.max_telemetry_history:
            self.telemetry_history.pop()

        return {
            "success": True,
            "message_id": envelope.message_id,
            "status": "ACCEPTED",
            "ingested_metrics_count": len(metrics_map)
        }

    def get_summary_stats(self) -> Dict[str, Any]:
        """Returns overview stats of registered simulators and devices."""
        self._update_stale_statuses()
        sim_list = list(self.simulators.values())
        dev_list = list(self.devices.values())

        online_sims = len([s for s in sim_list if s.status == "CONNECTED"])
        offline_sims = len([s for s in sim_list if s.status in ["OFFLINE", "REVOKED"]])
        online_devs = len([d for d in dev_list if d.status == "ONLINE"])
        stale_devs = len([d for d in dev_list if d.status == "STALE"])

        return {
            "total_simulators": len(sim_list),
            "online_simulators": online_sims,
            "offline_simulators": offline_sims,
            "total_devices": len(dev_list),
            "online_devices": online_devs,
            "stale_devices": stale_devs,
            "total_telemetry_records": len(self.telemetry_history),
            "rejected_records": 0
        }

    def _update_stale_statuses(self):
        """Marks simulators/devices stale or offline if heartbeat/telemetry threshold exceeded."""
        now = time.time()
        for sim in self.simulators.values():
            if sim.revoked:
                sim.status = "REVOKED"
                continue
            try:
                last_hb = datetime.datetime.fromisoformat(sim.last_heartbeat_at).timestamp()
                diff = now - last_hb
                if diff > 60:
                    sim.status = "OFFLINE"
                elif diff > 20:
                    sim.status = "STALE"
            except Exception:
                pass

        for dev in self.devices.values():
            if not dev.last_sample_at:
                continue
            try:
                last_ts = datetime.datetime.fromisoformat(dev.last_sample_at).timestamp()
                diff = now - last_ts
                if diff > 60:
                    dev.status = "STALE"
            except Exception:
                pass

    def revoke_simulator(self, instance_id: str) -> bool:
        """Revokes a simulator instance credentials."""
        sim = self.simulators.get(instance_id)
        if sim:
            sim.revoked = True
            sim.status = "REVOKED"
            return True
        return False

GLOBAL_DEVICE_REGISTRY = DeviceRegistryEngine()
