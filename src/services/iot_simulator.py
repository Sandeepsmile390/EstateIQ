"""
EstateIQ Interactive IoT Simulator Engine (src/services/iot_simulator.py).
Maintains controllable real-time simulated telemetry streams, sensor override controls,
preset scenarios, tick loop, and ring buffer integration with DIF Engine & AI Copilot.
"""

import time
import threading
import datetime
import math
import random
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

class SensorControlState(BaseModel):
    # Electricity & Power
    active_power_kw: float = 145.2
    energy_kwh: float = 36.3
    voltage_v: float = 415.0
    current_a: float = 202.0
    power_factor: float = 0.94
    transformer_load_pct: float = 78.0
    submeter_kwh: float = 12.5
    dg_status: str = "OFF"
    dg_runtime_min: float = 0.0
    dg_fuel_pct: float = 85.0
    
    # Building Operations
    occupancy_count: int = 140
    occupancy_pct: float = 70.0
    hvac_status: str = "ON"
    hvac_load_kw: float = 58.0
    lighting_load_kw: float = 18.5
    equipment_status: str = "NORMAL"
    operating_schedule: str = "PEAK_DAY"

    # Environmental Conditions
    temperature_c: float = 32.0
    humidity_pct: float = 55.0
    air_quality_aqi: float = 110.5
    co2_ppm: float = 650.0

    # Water Systems
    water_flow_lmin: float = 50.0
    cumulative_water_m3: float = 12.4
    tank_level_pct: float = 82.0
    water_pressure_bar: float = 3.2

class IoTSimulatorEngine:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(IoTSimulatorEngine, cls).__new__(cls)
            cls._instance._init_engine()
        return cls._instance

    def _init_engine(self):
        self.status = "PAUSED"  # RUNNING, PAUSED, STOPPED
        self.speed = 1          # 1x, 2x, 5x, 10x
        self.facility_id = "FAC_GEC_CAMPUS"
        self.building_id = "Block B Hostel"
        self.active_scenario = "NORMAL_BASELINE"
        self.sample_interval_min = 15
        self.samples_generated = 0
        self.active_sensors_count = 12
        self.backend_connected = True
        self.latest_ingestion_status = "READY"
        self.data_source_mode = "simulated_iot"
        self.data_source_badge = "SIMULATED IoT — NOT PHYSICAL SENSOR DATA"
        
        # Virtual simulation clock
        self.simulated_clock = datetime.datetime.now()
        self.sensors = SensorControlState()
        self.history_buffer: List[Dict[str, Any]] = []
        self._max_buffer = 500
        
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # Seed initial sample in buffer
        self._generate_sample_tick()

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
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
                "sensors": self.sensors.model_dump() if hasattr(self.sensors, 'model_dump') else self.sensors.dict()
            }

    def start_simulation(self) -> Dict[str, Any]:
        with self._lock:
            if self.status == "RUNNING":
                return self._get_status_unlocked()
            self.status = "RUNNING"
            self.latest_ingestion_status = "STREAMING"
            self._start_thread_if_needed()
            return self._get_status_unlocked()

    def pause_simulation(self) -> Dict[str, Any]:
        with self._lock:
            self.status = "PAUSED"
            self.latest_ingestion_status = "PAUSED"
            return self._get_status_unlocked()

    def resume_simulation(self) -> Dict[str, Any]:
        return self.start_simulation()

    def stop_simulation(self) -> Dict[str, Any]:
        with self._lock:
            self.status = "STOPPED"
            self.latest_ingestion_status = "STOPPED"
            return self._get_status_unlocked()

    def step_simulation(self) -> Dict[str, Any]:
        with self._lock:
            self._generate_sample_tick()
            self.latest_ingestion_status = "STEP_GENERATED"
            return self._get_status_unlocked()

    def reset_state(self) -> Dict[str, Any]:
        with self._lock:
            self.status = "PAUSED"
            self.simulated_clock = datetime.datetime.now()
            self.samples_generated = 0
            self.active_scenario = "NORMAL_BASELINE"
            self.sensors = SensorControlState()
            self.latest_ingestion_status = "RESET_TO_INITIAL"
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
                        if k == "active_power_kw":
                            v = max(0.0, min(500.0, float(v)))
                        elif k == "temperature_c":
                            v = max(10.0, min(50.0, float(v)))
                        elif k in ["occupancy_count", "energy_kwh", "water_flow_lmin", "voltage_v", "current_a", "hvac_load_kw", "lighting_load_kw"]:
                            v = max(0.0, float(v))
                        if k in ["occupancy_pct", "power_factor", "transformer_load_pct", "humidity_pct", "tank_level_pct", "dg_fuel_pct"]:
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
            if scenario_key == "HVAC_PEAK_SURGE":
                self.sensors.hvac_status = "ON"
                self.sensors.hvac_load_kw = 95.0
                self.sensors.active_power_kw = 245.0
                self.sensors.energy_kwh = 61.2
                self.sensors.temperature_c = 38.5
                self.sensors.occupancy_count = 280
                self.sensors.occupancy_pct = 95.0
                self.sensors.transformer_load_pct = 92.0
            elif scenario_key == "WATER_PIPE_LEAK":
                self.sensors.water_flow_lmin = 185.0
                self.sensors.cumulative_water_m3 = 45.8
                self.sensors.tank_level_pct = 32.0
                self.sensors.water_pressure_bar = 1.4
            elif scenario_key == "BIN_OVERFLOW_HAZARD":
                self.sensors.occupancy_count = 320
                self.sensors.air_quality_aqi = 165.0
                self.sensors.co2_ppm = 1200.0
            elif scenario_key == "EQUIPMENT_VIBRATION_ANOMALY":
                self.sensors.equipment_status = "HIGH_VIBRATION_ALERT"
                self.sensors.active_power_kw = 185.0
                self.sensors.power_factor = 0.78
            elif scenario_key == "OFF_PEAK_SAVER":
                self.sensors.hvac_status = "SETBACK"
                self.sensors.hvac_load_kw = 22.0
                self.sensors.active_power_kw = 62.0
                self.sensors.energy_kwh = 15.5
                self.sensors.occupancy_count = 25
                self.sensors.occupancy_pct = 12.0
                self.sensors.transformer_load_pct = 35.0
            else: # NORMAL_BASELINE
                self.sensors = SensorControlState()
            
            self.latest_ingestion_status = f"SCENARIO_APPLIED_{scenario_key}"
            self._generate_sample_tick()
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
            "sensors": self.sensors.model_dump() if hasattr(self.sensors, 'model_dump') else self.sensors.dict()
        }

    def _generate_sample_tick(self):
        self.samples_generated += 1
        self.simulated_clock += datetime.timedelta(minutes=self.sample_interval_min)
        
        jitter_power = round(self.sensors.active_power_kw * random.uniform(0.98, 1.02), 2)
        jitter_temp = round(self.sensors.temperature_c + random.uniform(-0.2, 0.2), 1)
        jitter_flow = round(self.sensors.water_flow_lmin * random.uniform(0.97, 1.03), 1)
        
        record = {
            "sample_id": f"SIM_IOT_{self.samples_generated:06d}",
            "facility_id": self.facility_id,
            "building_id": self.building_id,
            "timestamp": self.simulated_clock.strftime("%Y-%m-%d %H:%M:%S"),
            "data_source": "simulated_iot",
            "provenance": "SIMULATED IoT DATA",
            "provenance_badge": "SIMULATED IoT — NOT PHYSICAL SENSOR DATA",
            "active_scenario": self.active_scenario,
            "telemetry": {
                "active_power_kw": jitter_power,
                "energy_kwh": round(jitter_power * (self.sample_interval_min / 60.0), 2),
                "voltage_v": self.sensors.voltage_v,
                "current_a": self.sensors.current_a,
                "power_factor": self.sensors.power_factor,
                "transformer_load_pct": self.sensors.transformer_load_pct,
                "occupancy_count": self.sensors.occupancy_count,
                "temperature_c": jitter_temp,
                "humidity_pct": self.sensors.humidity_pct,
                "air_quality_aqi": self.sensors.air_quality_aqi,
                "water_flow_lmin": jitter_flow,
                "hvac_load_kw": self.sensors.hvac_load_kw,
                "dg_status": self.sensors.dg_status
            }
        }
        
        self.history_buffer.append(record)
        if len(self.history_buffer) > self._max_buffer:
            self.history_buffer.pop(0)

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
