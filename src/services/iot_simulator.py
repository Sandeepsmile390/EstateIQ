"""
EstateIQ Interactive IoT Simulator Engine (src/services/iot_simulator.py).
Maintains controllable real-time simulated telemetry streams across Electricity, Water,
Air, Waste, and HVAC subsystems with deterministic anomaly scenarios, seed/replay support,
and canonical ingestion into the Global Device Registry.
"""

import time
import threading
import datetime
import math
import random
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class SensorControlState(BaseModel):
    # Electricity & Metrology
    active_power_kw: float = 145.2
    energy_kwh: float = 36.3
    cumulative_energy_kwh: float = 5420.0
    voltage_v: float = 415.0
    current_a: float = 202.0
    power_factor: float = 0.94
    frequency_hz: float = 50.0
    transformer_load_pct: float = 78.0
    submeter_kwh: float = 12.5
    dg_status: str = "OFF"
    dg_runtime_min: float = 0.0
    dg_fuel_pct: float = 85.0

    # Building Operations & HVAC
    occupancy_count: int = 140
    occupancy_pct: float = 70.0
    hvac_status: str = "ON"
    hvac_load_kw: float = 58.0
    lighting_load_kw: float = 18.5
    equipment_status: str = "NORMAL"
    operating_schedule: str = "PEAK_DAY"

    # Environmental & Climate
    temperature_c: float = 32.0
    humidity_pct: float = 55.0
    air_quality_aqi: float = 110.5
    co2_ppm: float = 650.0
    heat_index_c: float = 34.2

    # Water Systems
    water_flow_lmin: float = 50.0
    cumulative_water_m3: float = 12.4
    water_cumulative_liters: float = 12400.0
    tank_level_pct: float = 82.0
    tank_distance_cm: float = 55.0
    water_pressure_bar: float = 3.2

    # Smart Waste Management
    bin_distance_cm: float = 28.0
    fill_level_percent: float = 48.0
    fill_level_pct: float = 48.0


class IoTSimulatorEngine:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(IoTSimulatorEngine, cls).__new__(cls)
            cls._instance._init_engine()
        return cls._instance

    def _init_engine(self):
        self.status = "STOPPED"  # RUNNING, PAUSED, STOPPED
        self.speed = 1           # 1x, 2x, 5x, 10x
        self.facility_id = "FAC_GEC_CAMPUS"
        self.building_id = "Block B Hostel"
        self.active_scenario = "NORMAL_BASELINE"
        self.sample_interval_min = 15
        self.samples_generated = 0
        self.active_sensors_count = 18
        self.backend_connected = True
        self.latest_ingestion_status = "STOPPED"
        self.data_source_mode = "simulated_iot"
        self.data_source_badge = "SIMULATED IoT — NOT PHYSICAL SENSOR DATA"
        self.random_seed: Optional[int] = None

        # Virtual simulation clock
        self.simulated_clock = datetime.datetime.now(datetime.timezone.utc)
        self.sensors = SensorControlState()
        self.history_buffer: List[Dict[str, Any]] = []
        self._max_buffer = 500

        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def set_seed(self, seed: Optional[int]) -> Dict[str, Any]:
        """Sets a deterministic seed for judging and automated repeatable tests."""
        with self._lock:
            self.random_seed = seed
            if seed is not None:
                random.seed(seed)
            return self._get_status_unlocked()

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return self._get_status_unlocked()

    def _get_status_unlocked(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "speed": self.speed,
            "facility_id": self.facility_id,
            "building_id": self.building_id,
            "active_scenario": self.active_scenario,
            "simulated_timestamp": self.simulated_clock.strftime("%Y-%m-%d %H:%M:%S"),
            "sample_interval_min": self.sample_interval_min,
            "samples_generated": self.samples_generated,
            "active_sensors_count": self.active_sensors_count,
            "backend_connected": self.backend_connected,
            "latest_ingestion_status": self.latest_ingestion_status,
            "data_source_mode": self.data_source_mode,
            "data_source_badge": self.data_source_badge,
            "random_seed": self.random_seed,
            "sensors": self.sensors.model_dump() if hasattr(self.sensors, 'model_dump') else self.sensors.dict()
        }

    def start_simulation(self) -> Dict[str, Any]:
        with self._lock:
            if self.status == "RUNNING":
                return self._get_status_unlocked()
            self.status = "RUNNING"
            self.latest_ingestion_status = "STREAMING"
            self._update_registry_simulator_status("CONNECTED")
            self._start_thread_if_needed()
            # Generate tick immediately on start so dashboard updates with zero delay
            self._generate_sample_tick()
            return self._get_status_unlocked()

    def pause_simulation(self) -> Dict[str, Any]:
        with self._lock:
            self.status = "PAUSED"
            self.latest_ingestion_status = "PAUSED"
            self._update_registry_simulator_status("PAUSED")
            return self._get_status_unlocked()

    def resume_simulation(self) -> Dict[str, Any]:
        return self.start_simulation()

    def stop_simulation(self) -> Dict[str, Any]:
        with self._lock:
            self.status = "STOPPED"
            self.latest_ingestion_status = "STOPPED"
            self._update_registry_simulator_status("STOPPED")
            return self._get_status_unlocked()

    def step_simulation(self) -> Dict[str, Any]:
        with self._lock:
            self._generate_sample_tick()
            self.latest_ingestion_status = "STEP_GENERATED"
            return self._get_status_unlocked()

    def reset_state(self) -> Dict[str, Any]:
        with self._lock:
            self.status = "PAUSED"
            self.simulated_clock = datetime.datetime.now(datetime.timezone.utc)
            self.samples_generated = 0
            self.active_scenario = "NORMAL_BASELINE"
            self.sensors = SensorControlState()
            self.latest_ingestion_status = "RESET_TO_INITIAL"
            self._update_registry_simulator_status("CONNECTED")
            self._generate_sample_tick()
            return self._get_status_unlocked()

    def reset_controls(self) -> Dict[str, Any]:
        with self._lock:
            self.sensors = SensorControlState()
            self.latest_ingestion_status = "CONTROLS_RESET"
            return self._get_status_unlocked()

    def set_speed(self, speed: int) -> Dict[str, Any]:
        with self._lock:
            if speed in [1, 2, 5, 10]:
                self.speed = speed
            return self._get_status_unlocked()

    def set_building(self, building_id: str) -> Dict[str, Any]:
        with self._lock:
            self.building_id = building_id
            return self._get_status_unlocked()

    def update_sensors(self, overrides: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            cur = self.sensors.model_dump() if hasattr(self.sensors, 'model_dump') else self.sensors.dict()
            for k, v in overrides.items():
                if k in cur:
                    if isinstance(cur[k], (int, float)) and isinstance(v, (int, float)):
                        if math.isnan(v) or math.isinf(v):
                            continue
                        if k in ["active_power_kw", "hvac_load_kw", "lighting_load_kw"]:
                            v = max(0.0, min(10000.0, float(v)))
                        elif k == "temperature_c":
                            v = max(-20.0, min(70.0, float(v)))
                        elif k in ["occupancy_count", "energy_kwh", "cumulative_energy_kwh", "water_flow_lmin", "cumulative_water_m3", "voltage_v", "current_a"]:
                            v = max(0.0, float(v))
                        elif k in ["occupancy_pct", "power_factor", "transformer_load_pct", "humidity_pct", "tank_level_pct", "fill_level_percent", "dg_fuel_pct"]:
                            v = max(0.0, min(100.0 if k != "power_factor" else 1.0, float(v)))
                        cur[k] = type(cur[k])(v)
                    elif isinstance(cur[k], str) and isinstance(v, str):
                        cur[k] = v.strip()
            self.sensors = SensorControlState(**cur)
            self.latest_ingestion_status = "SENSOR_OVERRIDDEN"
            return self._get_status_unlocked()

    def apply_scenario_preset(self, scenario_key: str) -> Dict[str, Any]:
        with self._lock:
            self.active_scenario = scenario_key
            key_upper = scenario_key.upper()

            if "HVAC" in key_upper or "SURGE" in key_upper or "SPIKE" in key_upper:
                # 1. Electrical & HVAC Power Surge Anomaly
                self.sensors.hvac_status = "ON"
                self.sensors.hvac_load_kw = 95.0
                self.sensors.active_power_kw = 245.0
                self.sensors.energy_kwh = 165.0
                self.sensors.temperature_c = 38.5
                self.sensors.occupancy_count = 280
                self.sensors.occupancy_pct = 95.0
                self.sensors.transformer_load_pct = 92.0

            elif "LEAK" in key_upper or "BURST" in key_upper or "PIPE" in key_upper:
                # 2. Water Pipe Burst / Massive Leak Anomaly
                self.sensors.water_flow_lmin = 185.0
                self.sensors.cumulative_water_m3 += 5.2
                self.sensors.tank_level_pct = 24.0
                self.sensors.tank_distance_cm = 85.0
                self.sensors.water_pressure_bar = 1.2

            elif "BIN" in key_upper or "OVERFLOW" in key_upper or "WASTE" in key_upper:
                # 3. Smart Waste Bin Near Overflow Anomaly
                self.sensors.fill_level_percent = 94.5
                self.sensors.fill_level_pct = 94.5
                self.sensors.bin_distance_cm = 6.2

            elif "VOLTAGE" in key_upper or "UNSTABLE" in key_upper or "SAG" in key_upper:
                # 4. Voltage Sag / Supply Instability Anomaly
                self.sensors.voltage_v = 182.0
                self.sensors.current_a = 28.5
                self.sensors.power_factor = 0.72

            elif "AIR" in key_upper or "POLLUTION" in key_upper:
                # 5. Air Pollution / Ventilation Degradation Anomaly
                self.sensors.air_quality_aqi = 230.0
                self.sensors.co2_ppm = 1650.0
                self.sensors.temperature_c = 34.5
                self.sensors.humidity_pct = 78.0

            elif "DROPOUT" in key_upper or "STALE" in key_upper:
                # 6. Sensor Dropout State (Zero / Standby)
                self.sensors.active_power_kw = 0.0
                self.sensors.water_flow_lmin = 0.0

            elif "RECOVERY" in key_upper or "NORMAL" in key_upper or "BASELINE" in key_upper:
                # 7. Recovery Confirmation back to nominal baseline
                self.sensors = SensorControlState()

            else:
                self.sensors = SensorControlState()

            self.latest_ingestion_status = f"SCENARIO_APPLIED_{scenario_key}"
            self._generate_sample_tick()
            return self._get_status_unlocked()

    def _update_registry_simulator_status(self, status_val: str):
        try:
            from src.registry.device_registry import GLOBAL_DEVICE_REGISTRY
            if "SIM_DEFAULT_01" in GLOBAL_DEVICE_REGISTRY.simulators:
                GLOBAL_DEVICE_REGISTRY.simulators["SIM_DEFAULT_01"].status = status_val
        except Exception:
            pass

    def _generate_sample_tick(self):
        self.samples_generated += 1
        self.simulated_clock += datetime.timedelta(minutes=self.sample_interval_min)

        jitter_power = round(self.sensors.active_power_kw * random.uniform(0.98, 1.02), 2)
        jitter_temp = round(self.sensors.temperature_c + random.uniform(-0.2, 0.2), 1)
        jitter_flow = round(self.sensors.water_flow_lmin * random.uniform(0.97, 1.03), 1)
        jitter_bin = round(max(3.0, min(100.0, self.sensors.bin_distance_cm + random.uniform(-0.5, 0.5))), 1)
        fill_pct = round(max(0.0, min(100.0, self.sensors.fill_level_percent + random.uniform(-0.5, 0.5))), 1)

        # Update cumulative counters
        self.sensors.cumulative_energy_kwh += round(jitter_power * (self.sample_interval_min / 60.0), 3)
        self.sensors.cumulative_water_m3 += round((jitter_flow * self.sample_interval_min) / 1000.0, 4)
        self.sensors.water_cumulative_liters = round(self.sensors.cumulative_water_m3 * 1000.0, 1)

        now_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # 1. Internal Simulator Ring Buffer Record (Aggregate Snapshot)
        record = {
            "sample_id": f"SIM_IOT_{self.samples_generated:06d}",
            "facility_id": self.facility_id,
            "building_id": self.building_id,
            "timestamp": now_iso,
            "data_source": "simulated_iot",
            "provenance": "SIMULATED IoT DATA",
            "provenance_badge": "SIMULATED IoT — NOT PHYSICAL SENSOR DATA",
            "active_scenario": self.active_scenario,
            "telemetry": {
                "active_power_kw": jitter_power,
                "cumulative_energy_kwh": round(self.sensors.cumulative_energy_kwh, 2),
                "voltage_v": self.sensors.voltage_v,
                "current_a": self.sensors.current_a,
                "power_factor": self.sensors.power_factor,
                "frequency_hz": self.sensors.frequency_hz,
                "transformer_load_pct": self.sensors.transformer_load_pct,
                "occupancy_count": self.sensors.occupancy_count,
                "temperature_c": jitter_temp,
                "humidity_pct": self.sensors.humidity_pct,
                "air_quality_aqi": self.sensors.air_quality_aqi,
                "co2_ppm": self.sensors.co2_ppm,
                "water_flow_lmin": jitter_flow,
                "cumulative_water_m3": round(self.sensors.cumulative_water_m3, 3),
                "tank_level_pct": self.sensors.tank_level_pct,
                "tank_distance_cm": self.sensors.tank_distance_cm,
                "bin_distance_cm": jitter_bin,
                "fill_level_percent": fill_pct,
                "hvac_load_kw": self.sensors.hvac_load_kw,
                "dg_status": self.sensors.dg_status
            }
        }
        self.history_buffer.append(record)
        if len(self.history_buffer) > self._max_buffer:
            self.history_buffer.pop(0)

        # 2. Transmit to Canonical Device Registry across all 5 domain endpoints
        try:
            from src.registry.device_registry import GLOBAL_DEVICE_REGISTRY

            # Packet A: HVAC Controller (DEV_HVAC_01)
            GLOBAL_DEVICE_REGISTRY.ingest_telemetry({
                "schema_version": "1.0",
                "message_id": f"SIM_HVAC_{self.samples_generated:06d}",
                "simulator_id": "SIM_DEFAULT_01",
                "device_id": "DEV_HVAC_01",
                "facility_id": self.facility_id,
                "building_id": self.building_id,
                "source_type": "simulated_iot",
                "event_timestamp": now_iso,
                "sent_timestamp": now_iso,
                "sequence_number": self.samples_generated,
                "metrics": [
                    {"metric": "hvac_load_kw", "value": float(self.sensors.hvac_load_kw), "unit": "kW", "quality": "good"},
                    {"metric": "temperature_c", "value": float(jitter_temp), "unit": "°C", "quality": "good"},
                    {"metric": "chiller_temp_c", "value": 7.4, "unit": "°C", "quality": "good"},
                    {"metric": "fan_speed_rpm", "value": 1420.0, "unit": "RPM", "quality": "good"}
                ]
            })

            # Packet B: Main Electrical Meter (DEV_ELEC_01)
            GLOBAL_DEVICE_REGISTRY.ingest_telemetry({
                "schema_version": "1.0",
                "message_id": f"SIM_ELEC_{self.samples_generated:06d}",
                "simulator_id": "SIM_DEFAULT_01",
                "device_id": "DEV_ELEC_01",
                "facility_id": self.facility_id,
                "building_id": self.building_id,
                "source_type": "simulated_iot",
                "event_timestamp": now_iso,
                "sent_timestamp": now_iso,
                "sequence_number": self.samples_generated,
                "metrics": [
                    {"metric": "active_power_kw", "value": float(jitter_power), "unit": "kW", "quality": "good"},
                    {"metric": "cumulative_energy_kwh", "value": float(self.sensors.cumulative_energy_kwh), "unit": "kWh", "quality": "good"},
                    {"metric": "voltage_v", "value": float(self.sensors.voltage_v), "unit": "V", "quality": "good"},
                    {"metric": "current_a", "value": float(self.sensors.current_a), "unit": "A", "quality": "good"},
                    {"metric": "power_factor", "value": float(self.sensors.power_factor), "unit": "ratio", "quality": "good"},
                    {"metric": "frequency_hz", "value": float(self.sensors.frequency_hz), "unit": "Hz", "quality": "good"}
                ]
            })

            # Packet C: Water Flow & Storage Tank (DEV_WATER_01)
            GLOBAL_DEVICE_REGISTRY.ingest_telemetry({
                "schema_version": "1.0",
                "message_id": f"SIM_WATER_{self.samples_generated:06d}",
                "simulator_id": "SIM_DEFAULT_01",
                "device_id": "DEV_WATER_01",
                "facility_id": self.facility_id,
                "building_id": self.building_id,
                "source_type": "simulated_iot",
                "event_timestamp": now_iso,
                "sent_timestamp": now_iso,
                "sequence_number": self.samples_generated,
                "metrics": [
                    {"metric": "water_flow_lmin", "value": float(jitter_flow), "unit": "L/min", "quality": "good"},
                    {"metric": "cumulative_water_m3", "value": float(self.sensors.cumulative_water_m3), "unit": "m3", "quality": "good"},
                    {"metric": "water_cumulative_liters", "value": float(self.sensors.water_cumulative_liters), "unit": "L", "quality": "good"},
                    {"metric": "tank_level_pct", "value": float(self.sensors.tank_level_pct), "unit": "%", "quality": "good"},
                    {"metric": "tank_distance_cm", "value": float(self.sensors.tank_distance_cm), "unit": "cm", "quality": "good"},
                    {"metric": "water_pressure_bar", "value": float(self.sensors.water_pressure_bar), "unit": "bar", "quality": "good"}
                ]
            })

            # Packet D: Smart Waste Bin (DEV_WASTE_01)
            GLOBAL_DEVICE_REGISTRY.ingest_telemetry({
                "schema_version": "1.0",
                "message_id": f"SIM_WASTE_{self.samples_generated:06d}",
                "simulator_id": "SIM_DEFAULT_01",
                "device_id": "DEV_WASTE_01",
                "facility_id": self.facility_id,
                "building_id": self.building_id,
                "source_type": "simulated_iot",
                "event_timestamp": now_iso,
                "sent_timestamp": now_iso,
                "sequence_number": self.samples_generated,
                "metrics": [
                    {"metric": "bin_distance_cm", "value": float(jitter_bin), "unit": "cm", "quality": "good"},
                    {"metric": "fill_level_percent", "value": float(fill_pct), "unit": "%", "quality": "good"},
                    {"metric": "fill_level_pct", "value": float(fill_pct), "unit": "%", "quality": "good"}
                ]
            })

            # Packet E: Environmental & Indoor Air Quality (DEV_AIR_01)
            GLOBAL_DEVICE_REGISTRY.ingest_telemetry({
                "schema_version": "1.0",
                "message_id": f"SIM_AIR_{self.samples_generated:06d}",
                "simulator_id": "SIM_DEFAULT_01",
                "device_id": "DEV_AIR_01",
                "facility_id": self.facility_id,
                "building_id": self.building_id,
                "source_type": "simulated_iot",
                "event_timestamp": now_iso,
                "sent_timestamp": now_iso,
                "sequence_number": self.samples_generated,
                "metrics": [
                    {"metric": "temperature_c", "value": float(jitter_temp), "unit": "°C", "quality": "good"},
                    {"metric": "humidity_pct", "value": float(self.sensors.humidity_pct), "unit": "%", "quality": "good"},
                    {"metric": "air_quality_aqi", "value": float(self.sensors.air_quality_aqi), "unit": "AQI", "quality": "good"},
                    {"metric": "co2_ppm", "value": float(self.sensors.co2_ppm), "unit": "ppm", "quality": "good"}
                ]
            })

        except Exception as e:
            pass

    def _start_thread_if_needed(self):
        if self._thread is None or not self._thread.is_alive():
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()

    def _loop(self):
        while not self._stop_event.is_set():
            time.sleep(3.0 / max(1, self.speed))
            with self._lock:
                if self.status == "RUNNING":
                    self._generate_sample_tick()

    def get_stream(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            return list(reversed(self.history_buffer[-limit:]))


GLOBAL_IOT_SIMULATOR = IoTSimulatorEngine()

def get_iot_simulator() -> IoTSimulatorEngine:
    return GLOBAL_IOT_SIMULATOR
