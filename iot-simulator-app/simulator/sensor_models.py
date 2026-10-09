"""
Realistic Sensor Models & Physics Generator (simulator/sensor_models.py).
Defines 12 reusable device profiles with inter-sensor mathematical relationships
(e.g., HVAC demand driving energy, occupancy driving demand, water flow driving cumulative volume).
"""

import math
import random
import datetime
from typing import Dict, Any, List, Optional

class SensorProfile:
    @staticmethod
    def generate_metrics(
        device_type: str,
        current_readings: Dict[str, Any],
        scenario: str = "Normal Campus Operation",
        overrides: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generates next realistic telemetry sample for a given device profile."""
        now = datetime.datetime.now()
        overrides = overrides or {}
        readings = dict(current_readings)

        # Baseline time-of-day variations
        hour = now.hour
        is_peak = 9 <= hour <= 18

        if device_type in ["electricity_meter", "building_submeter"]:
            base_kw = overrides.get("active_power_kw", readings.get("active_power_kw", 55.0))
            if scenario == "High HVAC Consumption":
                base_kw += 25.0
            elif scenario == "Sudden Energy Surge":
                base_kw += 45.0
            elif scenario == "Night-Time Energy Waste" and not is_peak:
                base_kw += 30.0

            kw = max(5.0, round(base_kw + random.uniform(-1.5, 1.5), 2))
            voltage = round(overrides.get("voltage_v", 230.0 + random.uniform(-2.5, 2.5)), 1)
            pf = round(min(0.99, max(0.85, overrides.get("power_factor", 0.95 + random.uniform(-0.02, 0.02)))), 2)
            current = round((kw * 1000.0) / (voltage * pf * math.sqrt(3)), 1)
            prev_kwh = readings.get("energy_kwh", 140.0)
            kwh = round(prev_kwh + (kw * (5.0 / 3600.0)), 2)

            return {
                "active_power_kw": kw,
                "energy_kwh": kwh,
                "voltage_v": voltage,
                "current_a": current,
                "power_factor": pf
            }

        elif device_type == "hvac_monitor":
            hvac_kw = overrides.get("hvac_power_kw", readings.get("hvac_power_kw", 42.0))
            if scenario == "High HVAC Consumption":
                hvac_kw = 68.0
            elif scenario == "Low Occupancy with HVAC Running":
                hvac_kw = 50.0

            chiller_temp = overrides.get("chiller_temp_c", readings.get("chiller_temp_c", 7.2))
            if scenario == "High Ambient Temperature":
                chiller_temp = 11.5

            vib = overrides.get("vibration_mm_s", readings.get("vibration_mm_s", 1.2))
            rpm = int(overrides.get("fan_speed_rpm", readings.get("fan_speed_rpm", 1450)))

            return {
                "hvac_power_kw": round(hvac_kw + random.uniform(-0.8, 0.8), 1),
                "chiller_temp_c": round(chiller_temp + random.uniform(-0.2, 0.2), 1),
                "fan_speed_rpm": rpm + random.randint(-10, 10),
                "vibration_mm_s": round(vib + random.uniform(-0.05, 0.05), 2)
            }

        elif device_type == "transformer":
            load_pct = overrides.get("load_pct", readings.get("load_pct", 68.0))
            if scenario == "Transformer Load Increase":
                load_pct = 92.5

            oil_temp = round(45.0 + (load_pct * 0.4) + random.uniform(-1.0, 1.0), 1)
            kva = round(750.0 * (load_pct / 100.0), 1)

            return {
                "load_pct": round(load_pct, 1),
                "oil_temp_c": oil_temp,
                "apparent_power_kva": kva,
                "health_index": 95 if load_pct < 85 else 78
            }

        elif device_type == "dg_monitor":
            is_running = scenario == "DG Operating" or overrides.get("is_running", False)
            fuel = overrides.get("fuel_level_pct", readings.get("fuel_level_pct", 82.5))
            if is_running:
                fuel = max(0.0, fuel - 0.05)
                rpm = 1500 + random.randint(-5, 5)
                oil_psi = round(58.0 + random.uniform(-1.0, 1.0), 1)
            else:
                rpm = 0
                oil_psi = 0.0

            return {
                "is_running": is_running,
                "fuel_level_pct": round(fuel, 1),
                "engine_rpm": rpm,
                "oil_pressure_psi": oil_psi
            }

        elif device_type == "water_meter":
            flow = overrides.get("flow_rate_lmin", readings.get("flow_rate_lmin", 45.0))
            if scenario == "Gradual Water Leakage":
                flow += 25.0

            cum_m3 = readings.get("cumulative_m3", 1240.0) + ((flow * 5.0) / 60000.0)
            pressure = round(overrides.get("pressure_bar", 3.4 + random.uniform(-0.1, 0.1)), 2)

            return {
                "flow_rate_lmin": round(flow + random.uniform(-1.0, 1.0), 1),
                "cumulative_m3": round(cum_m3, 3),
                "pressure_bar": pressure
            }

        elif device_type == "water_tank":
            lvl = overrides.get("water_level_pct", readings.get("water_level_pct", 78.0))
            if scenario == "Gradual Water Leakage":
                lvl = max(10.0, lvl - 0.2)

            return {
                "water_level_pct": round(lvl, 1),
                "volume_liters": int(10000 * (lvl / 100.0)),
                "pump_status": "AUTO_OFF" if lvl > 80 else "PUMPING"
            }

        elif device_type == "occupancy_sensor":
            occ = int(overrides.get("occupancy_count", readings.get("occupancy_count", 140 if is_peak else 25)))
            if scenario == "Peak Occupancy":
                occ = 240
            elif scenario == "Low Occupancy with HVAC Running":
                occ = 10

            return {
                "occupancy_count": max(0, occ + random.randint(-2, 2)),
                "occupancy_rate_pct": round(min(100.0, (occ / 250.0) * 100.0), 1)
            }

        elif device_type == "temp_humidity":
            temp = overrides.get("temperature_c", readings.get("temperature_c", 32.0 if is_peak else 26.0))
            if scenario == "High Ambient Temperature":
                temp = 39.5

            hum = overrides.get("humidity_pct", readings.get("humidity_pct", 58.0))

            return {
                "temperature_c": round(temp + random.uniform(-0.3, 0.3), 1),
                "humidity_pct": round(hum + random.uniform(-0.5, 0.5), 1)
            }

        elif device_type == "air_quality":
            pm25 = overrides.get("pm25_ug_m3", readings.get("pm25_ug_m3", 42.0))
            co2 = overrides.get("co2_ppm", readings.get("co2_ppm", 650.0))

            return {
                "pm25_ug_m3": round(pm25 + random.uniform(-1.0, 1.0), 1),
                "co2_ppm": round(co2 + random.uniform(-5.0, 5.0), 1),
                "aqi_category": "Good" if pm25 < 50 else "Moderate"
            }

        elif device_type == "lighting_controller":
            active_lights = overrides.get("active_fixtures", readings.get("active_fixtures", 120 if is_peak else 20))
            if scenario == "Night-Time Energy Waste" and not is_peak:
                active_lights = 140

            return {
                "active_fixtures": active_lights,
                "lighting_power_kw": round(active_lights * 0.04, 2),
                "lux_level": 450 if is_peak else 50
            }

        else: # generic_sensor
            val = overrides.get("value", readings.get("value", 50.0))
            return {
                "value": round(val + random.uniform(-0.5, 0.5), 2),
                "unit": "pct",
                "status": "NORMAL"
            }
