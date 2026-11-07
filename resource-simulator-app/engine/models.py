"""
EstateIQ Standalone Resource Simulator Models (resource-simulator-app/engine/models.py).
Defines schemas for Electricity, Water, Air Quality, and Waste telemetry streams.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import datetime
import uuid

class ElectricityState(BaseModel):
    device_id: str = "SIM-ELEC-01"
    device_name: str = "Simulated Power Submeter (Block B)"
    facility_id: str = "FAC_GEC_CAMPUS"
    building_id: str = "Block B Hostel"
    running: bool = True
    baseline_kw: float = 55.0
    scenario: str = "NORMAL"  # NORMAL, PEAK_DEMAND, AFTER_HOURS_WASTE, VOLTAGE_INSTABILITY
    active_power_kw: float = 55.0
    cumulative_energy_kwh: float = 3420.5
    voltage_v: float = 230.2
    current_a: float = 251.5
    power_factor: float = 0.95
    frequency_hz: float = 50.01

class WaterState(BaseModel):
    device_id: str = "SIM-WATER-01"
    device_name: str = "Simulated Hydro Flow Sensor (Block B)"
    facility_id: str = "FAC_GEC_CAMPUS"
    building_id: str = "Block B Hostel"
    running: bool = True
    baseline_lmin: float = 35.0
    scenario: str = "NORMAL"  # NORMAL, SUSTAINED_LEAK, BURST_FLOW, LOW_FLOW
    flow_rate_lmin: float = 35.0
    cumulative_water_m3: float = 842.15
    water_pressure_bar: float = 3.4

class AirQualityState(BaseModel):
    device_id: str = "SIM-AIR-01"
    device_name: str = "Simulated Indoor Environmental Monitor (Block B)"
    facility_id: str = "FAC_GEC_CAMPUS"
    building_id: str = "Block B Hostel"
    running: bool = True
    baseline_occupancy: int = 120
    scenario: str = "NORMAL"  # NORMAL, POOR_VENTILATION, PARTICULATE_SPIKE, SENSOR_FAULT
    co2_ppm: float = 625.0
    pm25: float = 16.5
    pm10: float = 27.0
    temperature_c: float = 23.2
    humidity_pct: float = 48.5
    air_quality_aqi: float = 45.0
    aqi_category: str = "Good"

class WasteState(BaseModel):
    device_id: str = "SIM-WASTE-01"
    device_name: str = "Simulated Smart Ultrasonic Dumpster (Block B)"
    facility_id: str = "FAC_GEC_CAMPUS"
    building_id: str = "Block B Hostel"
    running: bool = True
    accumulation_rate_pct: float = 2.5
    scenario: str = "NORMAL"  # NORMAL, EVENT_RAPID, BIN_FULL, RESET_EMPTIED
    fill_level_percent: float = 38.0
    estimated_waste_kg: float = 62.7
    overflow_risk: str = "LOW"
    collection_status: str = "Normal Operation"

class GlobalSimulatorConfig(BaseModel):
    global_running: bool = True
    sample_interval_sec: float = 5.0
    backend_url: str = "http://localhost:8000/api/v1/iot/telemetry"
    auto_ingest: bool = True

class SimulatorStatusResponse(BaseModel):
    status: str  # RUNNING, PAUSED, STOPPED
    global_running: bool
    sample_interval_sec: float
    samples_generated: int
    last_sample_at: Optional[str]
    backend_url: str
    backend_connected: bool
    electricity: ElectricityState
    water: WaterState
    air: AirQualityState
    waste: WasteState
    provenance_badge: str = "[SIMULATED DATA]"
    is_verified_hardware: bool = False

