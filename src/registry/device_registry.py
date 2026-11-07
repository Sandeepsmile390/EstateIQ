"""
EstateIQ IoT Device & Simulator Registry (src/registry/device_registry.py).
Authoritative backend registry for physical gateways, meters, simulator instances,
paired devices, heartbeat tracking, single-use pairing codes, and telemetry ingestion buffer.
"""

import os
import time
import uuid
import secrets
import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from src.data.telemetry_schema import (
    TelemetryEnvelope,
    SourceType,
    MetricQuality,
    DeviceHealthStatus,
    CanonicalMetric,
    normalize_telemetry_payload,
    resolve_provenance_badge,
    normalize_source_type
)

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
    is_verified_hardware: bool = False
    enrollment_mode: str = "DEVELOPMENT_DEMO_MODE"

class VirtualDevice(BaseModel):
    device_id: str
    device_name: str
    instance_id: str
    device_type: str  # electricity_meter, hvac_monitor, water_meter, transformer, dg, etc.
    facility_id: str = "FAC_GEC_CAMPUS"
    building_id: str = "Block B Hostel"
    floor_room: Optional[str] = "Floor 2 / Room 204"
    status: str = "ONLINE"  # ONLINE, PAUSED, STALE, OFFLINE, ERROR
    sensors: List[str] = Field(default_factory=list)
    sampling_interval_sec: float = 5.0
    created_at: str
    last_sample_at: Optional[str] = None
    last_telemetry: Dict[str, Any] = Field(default_factory=dict)
    active_scenario: str = "Normal Campus Operation"
    source_type: str = "simulated_iot"
    data_source_badge: str = "[SIMULATED IoT]"
    is_verified_hardware: bool = False
    last_counter_energy_kwh: Optional[float] = None
    last_counter_water_m3: Optional[float] = None
    counter_reset_detected: bool = False
    data_quality_warnings: List[str] = Field(default_factory=list)


class DeviceRegistryEngine:
    """Master backend manager for IoT simulators, physical gateways, pairing keys, and telemetry streams."""

    def __init__(self):
        self.simulators: Dict[str, SimulatorInstance] = {}
        self.devices: Dict[str, VirtualDevice] = {}
        self.gateways: Dict[str, Dict[str, Any]] = {}
        self.pairing_codes: Dict[str, Dict[str, Any]] = {}
        self.telemetry_history: List[Dict[str, Any]] = []
        self.max_telemetry_history: int = 2000
        self.seen_message_ids: Dict[str, float] = {}
        self.max_seen_messages: int = 5000
        is_prod = os.getenv("ENVIRONMENT", "development").lower() in ("production", "prod")
        self.allow_unverified_demo_mode: bool = os.getenv("ALLOW_UNVERIFIED_DEMO_INGESTION", "false" if is_prod else "true").lower() in ("true", "1", "yes")
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
            device_count=6,
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
                sensors=["active_power_kw", "cumulative_energy_kwh", "voltage_v", "current_a", "power_factor", "frequency_hz"],
                sampling_interval_sec=5.0,
                created_at=now_iso,
                last_sample_at=now_iso,
                last_telemetry={"active_power_kw": 58.4, "cumulative_energy_kwh": 145.2, "energy_kwh": 145.2, "voltage_v": 230.5, "current_a": 253.2, "power_factor": 0.95, "frequency_hz": 50.0},
                active_scenario="Normal Campus Operation",
                source_type="simulated_iot",
                data_source_badge="[SIMULATED IoT]"
            ),
            VirtualDevice(
                device_id="HVAC-BLOCK-B-001",
                device_name="Block B Chiller & AHU Unit",
                instance_id="SIM_CAMPUS_01",
                device_type="hvac_monitor",
                facility_id="FAC_GEC_CAMPUS",
                building_id="Block B Hostel",
                status="ONLINE",
                sensors=["hvac_load_kw", "chiller_temp_c", "fan_speed_rpm", "vibration_mm_s"],
                sampling_interval_sec=5.0,
                created_at=now_iso,
                last_sample_at=now_iso,
                last_telemetry={"hvac_load_kw": 42.0, "chiller_temp_c": 7.2, "fan_speed_rpm": 1450, "vibration_mm_s": 1.2},
                active_scenario="High HVAC Consumption",
                source_type="simulated_iot",
                data_source_badge="[SIMULATED IoT]"
            ),
            VirtualDevice(
                device_id="WATER-BLOCK-A-001",
                device_name="Block A Hydro Flow Meter",
                instance_id="SIM_CAMPUS_01",
                device_type="water_meter",
                facility_id="FAC_GEC_CAMPUS",
                building_id="Block A Academic",
                status="ONLINE",
                sensors=["water_flow_lmin", "cumulative_water_m3", "water_pressure_bar", "tank_level_pct"],
                sampling_interval_sec=5.0,
                created_at=now_iso,
                last_sample_at=now_iso,
                last_telemetry={"water_flow_lmin": 48.2, "cumulative_water_m3": 1240.5, "water_pressure_bar": 3.4, "tank_level_pct": 78.0},
                active_scenario="Normal Campus Operation",
                source_type="simulated_iot",
                data_source_badge="[SIMULATED IoT]"
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
                active_scenario="Normal Campus Operation",
                source_type="simulated_iot",
                data_source_badge="[SIMULATED IoT]"
            ),
            VirtualDevice(
                device_id="AIR-BLOCK-B-001",
                device_name="Block B Indoor Air & Climate Station",
                instance_id="SIM_CAMPUS_01",
                device_type="air_quality_monitor",
                facility_id="FAC_GEC_CAMPUS",
                building_id="Block B Hostel",
                status="ONLINE",
                sensors=["co2_ppm", "pm25", "pm10", "temperature_c", "humidity_pct", "air_quality_aqi"],
                sampling_interval_sec=5.0,
                created_at=now_iso,
                last_sample_at=now_iso,
                last_telemetry={"co2_ppm": 620.0, "pm25": 18.5, "pm10": 28.0, "temperature_c": 23.2, "humidity_pct": 48.0, "air_quality_aqi": 42.0},
                active_scenario="Normal Indoor Air",
                source_type="simulated_iot",
                data_source_badge="[SIMULATED IoT]"
            ),
            VirtualDevice(
                device_id="WASTE-BLOCK-B-001",
                device_name="Block B Smart Ultrasonic Waste Bin",
                instance_id="SIM_CAMPUS_01",
                device_type="waste_monitor",
                facility_id="FAC_GEC_CAMPUS",
                building_id="Block B Hostel",
                status="ONLINE",
                sensors=["fill_level_percent", "estimated_waste_kg"],
                sampling_interval_sec=5.0,
                created_at=now_iso,
                last_sample_at=now_iso,
                last_telemetry={"fill_level_percent": 34.0, "estimated_waste_kg": 56.1},
                active_scenario="Normal Weekday Accumulation",
                source_type="simulated_iot",
                data_source_badge="[SIMULATED IoT]"
            )
        ]
        for d in demo_devices:
            self.devices[d.device_id] = d

        # Physical gateways must be provisioned with secrets loaded from environment or local config.
        # Do not keep hardcoded physical gateway API keys as defaults in production.
        env_gw_key = os.getenv("ESTATEIQ_GATEWAY_API_KEY") or os.getenv("GATEWAY_API_KEY")
        if not env_gw_key and self.allow_unverified_demo_mode:
            env_gw_key = "gw_secret_estateiq_hw_2026"

        if env_gw_key and not env_gw_key.startswith("UNCONFIGURED_"):
            self.gateways["ESP32_EDGE_GATEWAY_01"] = {
                "gateway_id": "ESP32_EDGE_GATEWAY_01",
                "gateway_name": "ESP32 Bench Edge Node (Modbus/Pulse)",
                "api_key": env_gw_key,
                "is_verified_hardware": True,
                "revoked": False,
                "registered_at": now_iso
            }

    def generate_pairing_code(self, ttl_minutes: int = 15) -> Dict[str, Any]:
        """Generates a single-use pairing code for connecting new standalone simulator laptops or gateways."""
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
            "instruction": "Enter this pairing code in the standalone EstateIQ IoT Simulator app or edge gateway on your local network."
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
        ip_address: str = "127.0.0.1",
        software_version: Optional[str] = "1.0.0"
    ) -> Dict[str, Any]:
        """Registers a standalone simulator or gateway instance after pairing code validation."""
        is_demo_mode = False
        if not self.validate_pairing_code(pairing_code):
            if pairing_code.strip().upper() == "IQ-DEMO":
                is_demo_mode = True
            else:
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
            revoked=False,
            is_verified_hardware=not is_demo_mode,
            enrollment_mode="DEVELOPMENT_DEMO_MODE" if is_demo_mode else "VERIFIED_GATEWAY_CREDENTIAL"
        )
        self.simulators[instance_id] = sim

        return {
            "success": True,
            "instance_id": instance_id,
            "instance_name": instance_name,
            "auth_token": auth_token,
            "status": "REGISTERED_SUCCESSFULLY",
            "mode": "DEVELOPMENT_DEMO_MODE" if is_demo_mode else "VERIFIED_HARDWARE",
            "is_verified_hardware": not is_demo_mode,
            "estateiq_time": now_iso
        }

    register_instance = register_simulator  # Alias for backward compatibility

    def register_gateway(self, gateway_id: str, gateway_name: str, api_key: Optional[str] = None, is_verified: bool = True) -> Dict[str, Any]:
        """Provisions a physical hardware gateway with a server-validated secret credential."""
        key = api_key or f"gw_key_{secrets.token_hex(16)}"
        now_iso = datetime.datetime.now().isoformat()
        gw_entry = {
            "gateway_id": gateway_id,
            "gateway_name": gateway_name,
            "api_key": key,
            "is_verified_hardware": is_verified,
            "revoked": False,
            "registered_at": now_iso
        }
        self.gateways[gateway_id] = gw_entry
        return {"success": True, "gateway_id": gateway_id, "api_key": key, "is_verified_hardware": is_verified}

    def revoke_gateway(self, gateway_id: str) -> bool:
        """Revokes a physical gateway identity and invalidates its telemetry ingestion."""
        if gateway_id in self.gateways:
            self.gateways[gateway_id]["revoked"] = True
            return True
        return False

    def record_heartbeat(self, instance_id: str, active_devices_count: int = 0, scenario: str = "Normal Campus Operation") -> Dict[str, Any]:
        """Updates heartbeat and connection status for a simulator/gateway instance."""
        sim = self.simulators.get(instance_id)
        if sim and sim.revoked:
            return {"success": False, "error": "UNAUTHORIZED_SIMULATOR"}

        now_iso = datetime.datetime.now().isoformat()
        if not sim:
            sim = SimulatorInstance(
                instance_id=instance_id,
                instance_name=f"Gateway-{instance_id}",
                facility_id="FAC_GEC_CAMPUS",
                building_id="Block B Hostel",
                status="CONNECTED",
                registered_at=now_iso,
                last_heartbeat_at=now_iso,
                device_count=active_devices_count,
                active_scenario=scenario,
                auth_token=f"sim_tok_auto_{uuid.uuid4().hex[:8]}"
            )
            self.simulators[instance_id] = sim

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
        """Registers a virtual or physical IoT device attached to an instance."""
        inst_id = device_data.get("instance_id") or "SIM_DEFAULT_01"
        if inst_id in self.simulators and self.simulators[inst_id].revoked:
            return {"success": False, "error": "UNREGISTERED_SIMULATOR_INSTANCE"}

        dev_id = device_data.get("device_id") or f"DEV_{uuid.uuid4().hex[:8].upper()}"
        now_iso = datetime.datetime.now().isoformat()
        src_type = normalize_source_type(device_data.get("source_type")).value
        badge = resolve_provenance_badge(normalize_source_type(device_data.get("source_type")))

        dev = VirtualDevice(
            device_id=dev_id,
            device_name=device_data.get("device_name", dev_id),
            instance_id=inst_id,
            device_type=device_data.get("device_type", "electricity_meter"),
            facility_id=device_data.get("facility_id", "FAC_GEC_CAMPUS"),
            building_id=device_data.get("building_id", "Block B Hostel"),
            floor_room=device_data.get("floor_room", "Floor 1"),
            status="ONLINE",
            sensors=device_data.get("sensors", ["active_power_kw", "cumulative_energy_kwh"]),
            sampling_interval_sec=float(device_data.get("sampling_interval_sec", 5.0)),
            created_at=now_iso,
            last_sample_at=now_iso,
            active_scenario=device_data.get("active_scenario", "Normal Campus Operation"),
            source_type=src_type,
            data_source_badge=badge
        )
        self.devices[dev_id] = dev
        if inst_id in self.simulators:
            self.simulators[inst_id].device_count = len([d for d in self.devices.values() if d.instance_id == inst_id])

        return {"success": True, "device_id": dev_id, "status": "REGISTERED"}

    def register_devices(self, instance_id: str, devices: List[Dict[str, Any]]) -> int:
        """Batch registers devices for an instance."""
        count = 0
        for d in devices:
            d["instance_id"] = instance_id
            res = self.register_device(d)
            if res.get("success"):
                count += 1
        return count

    def ingest_telemetry(self, payload: Dict[str, Any], default_source: Optional[SourceType] = None) -> Dict[str, Any]:
        """
        Unified ingestion path for real sensor telemetry, edge MQTT, and simulator envelopes.
        Validates schema, checks idempotency, detects counter resets, updates device health,
        and preserves source provenance.
        """
        # 1. Normalize and validate schema
        try:
            envelope, metrics_map, warnings = normalize_telemetry_payload(payload, default_source=default_source)
        except Exception as e:
            return {"success": False, "accepted": False, "error": f"SCHEMA_VALIDATION_ERROR: {str(e)}"}

        now_iso = datetime.datetime.now().isoformat()

        # 2. Idempotency Check (Duplicate message_id)
        if envelope.message_id in self.seen_message_ids:
            return {
                "success": True,
                "accepted": True,
                "duplicate": True,
                "message_id": envelope.message_id,
                "device_id": envelope.device_id,
                "status": "DUPLICATE_IGNORED",
                "message": "Duplicate message_id previously ingested. No-op acknowledgment."
            }

        # Track message_id in bounded cache
        self.seen_message_ids[envelope.message_id] = time.time()
        if len(self.seen_message_ids) > self.max_seen_messages:
            # Purge oldest 1000 entries
            sorted_keys = sorted(self.seen_message_ids.keys(), key=lambda k: self.seen_message_ids[k])
            for k in sorted_keys[:1000]:
                self.seen_message_ids.pop(k, None)

        # 3. Check revoked simulator / gateway
        gw_id = envelope.gateway_id or payload.get("gateway_id")
        sim_id = envelope.simulator_id or payload.get("simulator_id") or payload.get("instance_id")
        inst_id = sim_id or gw_id or "SIM_DEFAULT_01"

        gw = self.gateways.get(gw_id) if gw_id else None
        sim = self.simulators.get(sim_id) if sim_id else self.simulators.get(inst_id)

        if (gw and gw.get("revoked")):
            return {"success": False, "accepted": False, "error": "REVOKED_GATEWAY_CREDENTIAL", "status": "REJECTED"}
        if (sim and sim.revoked):
            return {"success": False, "accepted": False, "error": "REVOKED_SIMULATOR_CREDENTIAL", "status": "REJECTED"}

        if not sim and not gw:
            # Auto-register simulator instance for demo tracking
            sim = SimulatorInstance(
                instance_id=inst_id,
                instance_name=f"Instance-{inst_id}",
                facility_id=envelope.facility_id,
                building_id=envelope.building_id,
                status="CONNECTED",
                registered_at=now_iso,
                last_heartbeat_at=now_iso,
                last_telemetry_at=now_iso,
                device_count=1,
                active_scenario="Normal Campus Operation",
                auth_token=f"sim_tok_auto_{uuid.uuid4().hex[:8]}",
                is_verified_hardware=False,
                enrollment_mode="DEVELOPMENT_DEMO_MODE"
            )
            self.simulators[inst_id] = sim

        # Credential & Provenance Verification
        provided_token = payload.get("auth_token") or payload.get("api_key")
        is_verified = False

        if envelope.source_type == SourceType.REAL_SENSOR:
            # Physical sensor claim: MUST be authenticated by a registered physical gateway
            if gw:
                if not provided_token:
                    if self.allow_unverified_demo_mode:
                        is_verified = False
                        warnings.append("Missing gateway credential for real_sensor claim; accepted in unverified demo mode.")
                    else:
                        return {"success": False, "accepted": False, "error": "MISSING_GATEWAY_CREDENTIAL", "status": "REJECTED"}
                elif provided_token != gw.get("api_key"):
                    return {"success": False, "accepted": False, "error": "INVALID_GATEWAY_CREDENTIAL", "status": "REJECTED"}
                else:
                    is_verified = gw.get("is_verified_hardware", True)
            else:
                # No registered physical gateway matched
                if provided_token:
                    # Token provided but no gateway registered under gw_id (or unknown token)
                    return {"success": False, "accepted": False, "error": "INVALID_GATEWAY_CREDENTIAL", "status": "REJECTED"}
                else:
                    # Missing credentials and no registered gateway
                    if self.allow_unverified_demo_mode:
                        is_verified = False
                        warnings.append("Unauthenticated real_sensor claim without registered gateway; accepted in unverified demo mode.")
                    else:
                        return {"success": False, "accepted": False, "error": "MISSING_GATEWAY_CREDENTIAL", "status": "REJECTED"}
        else:
            # Simulated, Synthetic, or Derived telemetry
            is_verified = False
            if sim:
                if provided_token and provided_token != sim.auth_token:
                    return {"success": False, "accepted": False, "error": "INVALID_SIMULATOR_CREDENTIAL", "status": "REJECTED"}
                sim.last_telemetry_at = now_iso
                sim.last_heartbeat_at = now_iso
                sim.status = "CONNECTED"

        badge = resolve_provenance_badge(envelope.source_type, is_verified=is_verified)

        # 4. Quarantine Invalid or Missing Timestamps
        if not envelope.is_valid_timestamp or not envelope.event_timestamp:
            record = {
                "message_id": envelope.message_id,
                "gateway_id": envelope.gateway_id,
                "simulator_id": envelope.simulator_id or envelope.gateway_id,
                "device_id": envelope.device_id,
                "facility_id": envelope.facility_id,
                "building_id": envelope.building_id,
                "source_type": envelope.source_type.value,
                "data_source_badge": badge,
                "event_timestamp": envelope.event_timestamp,
                "sent_timestamp": envelope.sent_timestamp,
                "ingested_at": now_iso,
                "sequence_number": envelope.sequence_number,
                "metrics": metrics_map,
                "is_verified_hardware": is_verified,
                "is_valid_sample": False,
                "is_late_sample": False,
                "quarantined": True,
                "timestamp_error": envelope.timestamp_error or "INVALID_OR_MISSING_TIMESTAMP",
                "quality_warnings": warnings
            }
            self.telemetry_history.insert(0, record)
            if len(self.telemetry_history) > self.max_telemetry_history:
                self.telemetry_history.pop()

            return {
                "success": False,
                "accepted": False,
                "quarantined": True,
                "message_id": envelope.message_id,
                "device_id": envelope.device_id,
                "source_type": envelope.source_type.value,
                "data_source_badge": badge,
                "is_verified_hardware": is_verified,
                "status": "QUARANTINED_INVALID_TIMESTAMP",
                "error": envelope.timestamp_error or "Invalid or missing event timestamp.",
                "warnings": warnings
            }

        # 5. Device state lookup
        dev = self.devices.get(envelope.device_id)

        if not dev:
            # Determine appropriate device type
            dev_type = "generic_sensor"
            if "cumulative_energy_kwh" in metrics_map or "active_power_kw" in metrics_map:
                dev_type = "electricity_meter"
            elif "water_flow_lmin" in metrics_map or "cumulative_water_m3" in metrics_map:
                dev_type = "water_meter"

            dev = VirtualDevice(
                device_id=envelope.device_id,
                device_name=envelope.device_id,
                instance_id=inst_id,
                device_type=dev_type,
                facility_id=envelope.facility_id,
                building_id=envelope.building_id,
                status="ONLINE",
                created_at=now_iso,
                source_type=envelope.source_type.value,
                data_source_badge=badge,
                is_verified_hardware=is_verified
            )
            self.devices[envelope.device_id] = dev

        # 6. Chronological ordering & Clock Skew / Late Sample Check
        is_late_sample = False
        sample_time_diff_sec = None
        curr_ts = None
        try:
            curr_ts = datetime.datetime.fromisoformat(envelope.event_timestamp.replace("Z", "+00:00")).timestamp()
        except Exception:
            curr_ts = time.time()

        if dev.last_sample_at:
            try:
                prev_ts = datetime.datetime.fromisoformat(dev.last_sample_at.replace("Z", "+00:00")).timestamp()
                sample_time_diff_sec = curr_ts - prev_ts
                if sample_time_diff_sec <= 0:
                    is_late_sample = True
                    warnings.append(
                        f"Non-chronological/late telemetry sample retained for audit: curr={envelope.event_timestamp}, prev={dev.last_sample_at} (diff={sample_time_diff_sec:.1f}s)"
                    )
            except Exception as e:
                is_late_sample = True
                warnings.append(f"Timestamp comparison error ({str(e)}); treated as late sample.")

        if is_late_sample:
            # A late sample may be retained for audit, but it must NOT:
            # - become latest live value
            # - restore a stale/offline device to ONLINE
            # - update dev.last_telemetry live snapshot
            # - advance counter baselines or derive interval deltas
            # Re-evaluate device freshness from dev.last_sample_at
            try:
                prev_ts = datetime.datetime.fromisoformat(dev.last_sample_at.replace("Z", "+00:00")).timestamp()
                age_prev = max(0.0, time.time() - prev_ts)
                if age_prev > 300.0:
                    dev.status = "OFFLINE"
                elif age_prev > 45.0:
                    dev.status = "STALE"
            except Exception:
                pass

            record = {
                "message_id": envelope.message_id,
                "gateway_id": envelope.gateway_id,
                "simulator_id": envelope.simulator_id or envelope.gateway_id,
                "device_id": envelope.device_id,
                "facility_id": envelope.facility_id,
                "building_id": envelope.building_id,
                "source_type": envelope.source_type.value,
                "data_source_badge": badge,
                "event_timestamp": envelope.event_timestamp,
                "sent_timestamp": envelope.sent_timestamp,
                "ingested_at": now_iso,
                "sequence_number": envelope.sequence_number,
                "metrics": metrics_map,
                "is_verified_hardware": is_verified,
                "is_valid_sample": True,
                "is_late_sample": True,
                "quarantined": False,
                "quality_warnings": warnings
            }
            self.telemetry_history.insert(0, record)
            if len(self.telemetry_history) > self.max_telemetry_history:
                self.telemetry_history.pop()

            return {
                "success": True,
                "accepted": True,
                "is_late_sample": True,
                "quarantined": False,
                "message_id": envelope.message_id,
                "device_id": envelope.device_id,
                "source_type": envelope.source_type.value,
                "data_source_badge": badge,
                "is_verified_hardware": is_verified,
                "status": "ACCEPTED_LATE_SAMPLE_AUDIT_ONLY",
                "ingested_metrics_count": len(metrics_map),
                "warnings": warnings
            }

        # 7. Valid Chronological Sample: Update live state & baselines
        age_from_now_sec = max(0.0, time.time() - curr_ts)
        if age_from_now_sec > 300.0:
            dev.status = "OFFLINE"
        elif age_from_now_sec > 45.0:
            dev.status = "STALE"
        else:
            dev.status = "ONLINE"

        dev.last_sample_at = envelope.event_timestamp
        dev.source_type = envelope.source_type.value
        dev.data_source_badge = badge
        dev.is_verified_hardware = is_verified

        # Counter Reset / Rollover Detection for Energy and Water
        if "cumulative_energy_kwh" in metrics_map:
            new_e = float(metrics_map["cumulative_energy_kwh"])
            if dev.last_counter_energy_kwh is not None:
                if new_e < dev.last_counter_energy_kwh:
                    dev.counter_reset_detected = True
                    warnings.append(
                        f"Energy counter rollback/reset detected: prior={dev.last_counter_energy_kwh} kWh, new={new_e} kWh. Interval derivation skipped."
                    )
                    # Establish new baseline after genuine forward reset, but do NOT produce interval delta
                    dev.last_counter_energy_kwh = new_e
                elif sample_time_diff_sec is None or sample_time_diff_sec <= 3600:
                    # Derive interval consumption only from two valid consecutive readings in chronological order.
                    delta_e = round(new_e - dev.last_counter_energy_kwh, 4)
                    if delta_e >= 0:
                        metrics_map["interval_energy_kwh"] = delta_e
                        if "energy_kwh" not in metrics_map:
                            metrics_map["energy_kwh"] = delta_e
                    dev.last_counter_energy_kwh = new_e
                elif sample_time_diff_sec and sample_time_diff_sec > 3600:
                    warnings.append(f"Excessive gap between energy samples ({round(sample_time_diff_sec)}s); interval energy suppressed.")
                    dev.last_counter_energy_kwh = new_e
            else:
                # First valid reading establishes baseline; no interval delta
                dev.last_counter_energy_kwh = new_e

        if "cumulative_water_m3" in metrics_map:
            new_w = float(metrics_map["cumulative_water_m3"])
            if dev.last_counter_water_m3 is not None:
                if new_w < dev.last_counter_water_m3:
                    dev.counter_reset_detected = True
                    warnings.append(
                        f"Water counter rollback/reset detected: prior={dev.last_counter_water_m3} m³, new={new_w} m³. Interval derivation skipped."
                    )
                    dev.last_counter_water_m3 = new_w
                elif sample_time_diff_sec is None or sample_time_diff_sec <= 3600:
                    delta_w = round(new_w - dev.last_counter_water_m3, 4)
                    if delta_w >= 0:
                        metrics_map["interval_water_m3"] = delta_w
                    dev.last_counter_water_m3 = new_w
                elif sample_time_diff_sec and sample_time_diff_sec > 3600:
                    warnings.append(f"Excessive gap between water samples ({round(sample_time_diff_sec)}s); interval water volume suppressed.")
                    dev.last_counter_water_m3 = new_w
            else:
                dev.last_counter_water_m3 = new_w

        dev.last_telemetry.update(metrics_map)
        dev.data_quality_warnings = warnings

        # 8. Record to persistent In-Memory ring history
        record = {
            "message_id": envelope.message_id,
            "gateway_id": envelope.gateway_id,
            "simulator_id": envelope.simulator_id or envelope.gateway_id,
            "device_id": envelope.device_id,
            "facility_id": envelope.facility_id,
            "building_id": envelope.building_id,
            "source_type": envelope.source_type.value,
            "data_source_badge": badge,
            "event_timestamp": envelope.event_timestamp,
            "sent_timestamp": envelope.sent_timestamp,
            "ingested_at": now_iso,
            "sequence_number": envelope.sequence_number,
            "metrics": metrics_map,
            "is_verified_hardware": is_verified,
            "is_valid_sample": True,
            "is_late_sample": False,
            "quarantined": False,
            "quality_warnings": warnings
        }
        self.telemetry_history.insert(0, record)
        if len(self.telemetry_history) > self.max_telemetry_history:
            self.telemetry_history.pop()

        return {
            "success": True,
            "accepted": True,
            "message_id": envelope.message_id,
            "device_id": envelope.device_id,
            "source_type": envelope.source_type.value,
            "data_source_badge": badge,
            "is_verified_hardware": is_verified,
            "status": "ACCEPTED",
            "ingested_metrics_count": len(metrics_map),
            "warnings": warnings
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

    def list_instances(self) -> List[SimulatorInstance]:
        """Returns list of all registered simulator/gateway instances."""
        return list(self.simulators.values())

    def list_devices(self, facility_id: Optional[str] = None, building_id: Optional[str] = None) -> List[VirtualDevice]:
        """Returns list of all registered devices with optional facility/building filter."""
        devs = list(self.devices.values())
        if facility_id:
            devs = [d for d in devs if d.facility_id == facility_id]
        if building_id:
            devs = [d for d in devs if d.building_id == building_id]
        return devs

    def get_device(self, device_id: str) -> Optional[VirtualDevice]:
        return self.devices.get(device_id)

    def get_instance(self, instance_id: str) -> Optional[SimulatorInstance]:
        return self.simulators.get(instance_id)

    def disable_device(self, device_id: str) -> bool:
        dev = self.devices.get(device_id)
        if dev:
            dev.status = "OFFLINE"
            return True
        return False

    def get_latest_telemetry(self, device_id: str) -> Optional[Dict[str, Any]]:
        dev = self.devices.get(device_id)
        if not dev:
            return None
        return {
            "device_id": device_id,
            "last_sample_at": dev.last_sample_at,
            "telemetry": dev.last_telemetry,
            "source_type": dev.source_type,
            "data_source_badge": dev.data_source_badge,
            "status": dev.status
        }

    def get_telemetry_history(self, device_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        if device_id:
            return [t for t in self.telemetry_history if t.get("device_id") == device_id][:limit]
        return list(reversed(self.telemetry_history))[:limit]

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
                if diff > 300:
                    sim.status = "OFFLINE"
                elif diff > 60:
                    sim.status = "STALE"
            except Exception:
                pass

        for dev in self.devices.values():
            if not dev.last_sample_at:
                continue
            try:
                # Strip Z or offset
                ts_clean = dev.last_sample_at.replace("Z", "+00:00")
                last_ts = datetime.datetime.fromisoformat(ts_clean).timestamp()
                diff = now - last_ts
                if diff > 300:
                    dev.status = "OFFLINE"
                elif diff > 45:
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

    revoke_instance = revoke_simulator  # Alias


GLOBAL_DEVICE_REGISTRY = DeviceRegistryEngine()
