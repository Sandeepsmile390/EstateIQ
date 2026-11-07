"""
EstateIQ Standalone Resource Simulator Physics Engine (resource-simulator-app/engine/physics.py).
Calculates realistic physical variables and maintains monotonic totalizers for:
  1. Electricity (P, kWh, V, I, PF, Hz)
  2. Water (Flow L/min, Volume m³, Pressure bar)
  3. Air Quality (CO2, PM2.5, PM10, Temp, Humidity, EPA AQI)
  4. Waste (Fill Level %, Derived Mass kg, Overflow Risk, Collection Status)
"""

import math
import random
from typing import Tuple
from engine.models import ElectricityState, WaterState, AirQualityState, WasteState

def clamp(val: float, min_val: float, max_val: float) -> float:
    return max(min_val, min(max_val, val))

def gaussian_noise(mean: float = 0.0, std: float = 1.0) -> float:
    return random.gauss(mean, std)

def calculate_epa_aqi(pm25: float) -> Tuple[float, str]:
    """Calculates official US EPA AQI category from PM2.5 concentration."""
    breakpoints = [
        (0.0, 12.0, 0, 50, "Good"),
        (12.1, 35.4, 51, 100, "Moderate"),
        (35.5, 55.4, 101, 150, "Unhealthy for Sensitive Groups"),
        (55.5, 150.4, 151, 200, "Unhealthy"),
        (150.5, 250.4, 201, 300, "Very Unhealthy"),
        (250.5, 500.0, 301, 500, "Hazardous")
    ]
    for c_low, c_high, i_low, i_high, cat in breakpoints:
        if c_low <= pm25 <= c_high:
            aqi = round(((i_high - i_low) / (c_high - c_low)) * (pm25 - c_low) + i_low)
            return float(aqi), cat
    if pm25 > 500.0:
        return 500.0, "Hazardous"
    return 25.0, "Good"

def update_electricity_physics(state: ElectricityState, dt_sec: float) -> None:
    """Updates electrical parameters according to active power formula: I = (1000 * P) / (V * PF)."""
    if not state.running:
        return

    base = state.baseline_kw
    scen = state.scenario

    if scen == "PEAK_DEMAND":
        # Chiller startup surge: 1.85x base, slight voltage sag, PF 0.91
        p_kw = base * (1.85 + gaussian_noise(0, 0.05))
        v_volt = 224.0 + gaussian_noise(0, 1.5)
        pf = clamp(0.91 + gaussian_noise(0, 0.012), 0.82, 0.94)
        freq = 49.88 + gaussian_noise(0, 0.04)
    elif scen == "AFTER_HOURS_WASTE":
        # Elevated off-peak baseline: 1.35x base
        p_kw = base * (1.35 + gaussian_noise(0, 0.03))
        v_volt = 232.0 + gaussian_noise(0, 1.0)
        pf = clamp(0.89 + gaussian_noise(0, 0.01), 0.80, 0.93)
        freq = 50.02 + gaussian_noise(0, 0.03)
    elif scen == "VOLTAGE_INSTABILITY":
        # Harmonics, sags, swells
        p_kw = base * (1.10 + gaussian_noise(0, 0.10))
        v_volt = clamp(230.0 + gaussian_noise(0, 14.0), 205.0, 255.0)
        pf = clamp(0.76 + gaussian_noise(0, 0.05), 0.62, 0.86)
        freq = clamp(50.0 + gaussian_noise(0, 0.35), 49.1, 50.9)
    else:  # NORMAL
        p_kw = base * (1.0 + gaussian_noise(0, 0.025))
        v_volt = 230.2 + gaussian_noise(0, 1.2)
        pf = clamp(0.95 + gaussian_noise(0, 0.01), 0.88, 0.98)
        freq = 50.01 + gaussian_noise(0, 0.03)

    p_kw = clamp(round(p_kw, 2), 1.0, 500.0)
    v_volt = clamp(round(v_volt, 1), 180.0, 280.0)
    pf = clamp(round(pf, 2), 0.50, 0.99)
    freq = clamp(round(freq, 2), 48.0, 52.0)

    # Consistent electrical relation: I = (1000 * P) / (V * PF) for single phase
    current_a = round((1000.0 * p_kw) / (v_volt * pf), 1)

    # Monotonic cumulative energy: dKwh = P * dt / 3600
    delta_kwh = (p_kw * dt_sec) / 3600.0
    state.cumulative_energy_kwh = round(state.cumulative_energy_kwh + delta_kwh, 4)

    state.active_power_kw = p_kw
    state.voltage_v = v_volt
    state.current_a = current_a
    state.power_factor = pf
    state.frequency_hz = freq

def update_water_physics(state: WaterState, dt_sec: float) -> None:
    """Updates water flow rate, pressure, and monotonic cumulative m³ totalizer."""
    if not state.running:
        return

    base = state.baseline_lmin
    scen = state.scenario

    if scen == "SUSTAINED_LEAK":
        # Continuous floor offset +26.5 L/min
        flow = base + 26.5 + gaussian_noise(0, 1.5)
        pres = clamp(2.8 + gaussian_noise(0, 0.1), 2.2, 3.2)
    elif scen == "BURST_FLOW":
        # Catastrophic fracture: massive flow spike, pressure sag
        flow = base * (4.2 + gaussian_noise(0, 0.3))
        pres = clamp(1.4 + gaussian_noise(0, 0.2), 0.8, 2.0)
    elif scen == "LOW_FLOW":
        # Night shutoff
        flow = clamp(0.5 + gaussian_noise(0, 0.2), 0.0, 1.5)
        pres = clamp(1.8 + gaussian_noise(0, 0.2), 1.2, 2.4)
    else:  # NORMAL
        flow = base * (1.0 + gaussian_noise(0, 0.08))
        pres = clamp(3.4 + gaussian_noise(0, 0.1), 3.0, 3.8)

    flow = clamp(round(flow, 1), 0.0, 600.0)
    pres = clamp(round(pres, 2), 0.2, 8.0)

    # Monotonic m³ volume: 1 m³ = 1000 Liters
    delta_m3 = (flow * (dt_sec / 60.0)) / 1000.0
    state.cumulative_water_m3 = round(state.cumulative_water_m3 + delta_m3, 5)

    state.flow_rate_lmin = flow
    state.water_pressure_bar = pres

def update_air_quality_physics(state: AirQualityState, dt_sec: float) -> None:
    """Updates indoor air metrics and derives official EPA AQI."""
    if not state.running:
        return

    occ = state.baseline_occupancy
    scen = state.scenario

    if scen == "POOR_VENTILATION":
        co2 = clamp(1450.0 + (occ * 3.2) + gaussian_noise(0, 35.0), 1200.0, 3200.0)
        pm25 = clamp(36.0 + gaussian_noise(0, 3.5), 22.0, 60.0)
        pm10 = clamp(pm25 * 1.55 + gaussian_noise(0, 4.0), 35.0, 95.0)
        temp = clamp(25.6 + gaussian_noise(0, 0.4), 24.0, 28.0)
        hum = clamp(68.0 + gaussian_noise(0, 2.0), 60.0, 80.0)
    elif scen == "PARTICULATE_SPIKE":
        co2 = clamp(620.0 + (occ * 1.5) + gaussian_noise(0, 18.0), 500.0, 1200.0)
        pm25 = clamp(125.0 + gaussian_noise(0, 18.0), 75.0, 240.0)
        pm10 = clamp(pm25 * 1.65 + gaussian_noise(0, 22.0), 120.0, 380.0)
        temp = clamp(24.0 + gaussian_noise(0, 0.4), 22.0, 26.5)
        hum = clamp(52.0 + gaussian_noise(0, 2.0), 45.0, 60.0)
    elif scen == "SENSOR_FAULT":
        co2 = clamp(1800.0 + gaussian_noise(0, 500.0), 300.0, 5000.0)
        pm25 = clamp(85.0 + gaussian_noise(0, 35.0), 0.0, 300.0)
        pm10 = clamp(pm25 * 1.5 + gaussian_noise(0, 40.0), 0.0, 450.0)
        temp = clamp(31.0 + gaussian_noise(0, 2.5), 15.0, 42.0)
        hum = clamp(35.0 + gaussian_noise(0, 10.0), 10.0, 95.0)
    else:  # NORMAL
        co2 = clamp(410.0 + (occ * 1.8) + gaussian_noise(0, 12.0), 400.0, 1100.0)
        pm25 = clamp(15.0 + gaussian_noise(0, 2.2), 5.0, 28.0)
        pm10 = clamp(pm25 * 1.6 + gaussian_noise(0, 2.8), 10.0, 45.0)
        temp = clamp(23.2 + gaussian_noise(0, 0.3), 21.0, 25.0)
        hum = clamp(48.5 + gaussian_noise(0, 1.5), 40.0, 58.0)

    co2 = float(round(co2))
    pm25 = round(pm25, 1)
    pm10 = round(pm10, 1)
    temp = round(temp, 1)
    hum = round(hum, 1)
    aqi, cat = calculate_epa_aqi(pm25)

    state.co2_ppm = co2
    state.pm25 = pm25
    state.pm10 = pm10
    state.temperature_c = temp
    state.humidity_pct = hum
    state.air_quality_aqi = aqi
    state.aqi_category = cat

def update_waste_physics(state: WasteState, dt_sec: float) -> None:
    """Updates waste volumetric fill %, derived weight (kg), overflow risk, and collection status."""
    if not state.running:
        return

    rate = state.accumulation_rate_pct
    current_fill = state.fill_level_percent
    scen = state.scenario

    if scen == "EVENT_RAPID":
        current_fill += ((rate * 3.5) * (dt_sec / 5.0)) + gaussian_noise(0, 0.3)
    elif scen == "BIN_FULL":
        current_fill = clamp(94.0 + gaussian_noise(0, 1.5), 90.0, 99.5)
    elif scen == "RESET_EMPTIED":
        current_fill = clamp(4.0 + gaussian_noise(0, 0.4), 1.0, 8.0)
        state.scenario = "NORMAL"
    else:  # NORMAL
        current_fill += (rate * (dt_sec / 5.0)) + gaussian_noise(0, 0.15)

    current_fill = clamp(round(current_fill, 1), 0.0, 100.0)
    state.fill_level_percent = current_fill

    # Commercial 1100L dumpster: uncompacted density ~0.15 kg/L => max ~165 kg
    est_kg = round((current_fill / 100.0) * 165.0 * (0.95 + gaussian_noise(0, 0.02)), 1)
    est_kg = clamp(est_kg, 1.0, 185.0)
    state.estimated_waste_kg = est_kg

    if current_fill < 50.0:
        state.overflow_risk = "LOW"
        state.collection_status = "Normal Operation"
    elif current_fill < 75.0:
        state.overflow_risk = "MEDIUM"
        state.collection_status = "Approaching Capacity"
    elif current_fill < 90.0:
        state.overflow_risk = "HIGH"
        state.collection_status = "Collection Recommended"
    else:
        state.overflow_risk = "CRITICAL"
        state.collection_status = "Immediate Dispatch Required"

