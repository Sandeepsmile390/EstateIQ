"""
EstateIQ Standalone Resource Simulator Telemetry Client (resource-simulator-app/engine/client.py).
Constructs canonical telemetry packets with provenance metadata and dispatches them to EstateIQ backend.
"""

import time
import datetime
import urllib.request
import json
from typing import Dict, Any, List, Tuple
from engine.models import ElectricityState, WaterState, AirQualityState, WasteState

def build_telemetry_packets(
    elec: ElectricityState,
    water: WaterState,
    air: AirQualityState,
    waste: WasteState
) -> List[Dict[str, Any]]:
    """Builds canonical telemetry payloads with source_type='simulated_iot' and is_verified_hardware=False."""
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    packets = []

    # 1. Electricity
    if elec.running:
        packets.append({
            "message_id": f"MSG_SIM_ELEC_{int(time.time() * 1000)}",
            "simulator_id": "SIM_RESOURCE_STANDALONE_01",
            "device_id": elec.device_id,
            "device_name": elec.device_name,
            "facility_id": elec.facility_id,
            "building_id": elec.building_id,
            "source_type": "simulated_iot",
            "is_verified_hardware": False,
            "data_source_badge": "[SIMULATED IoT]",
            "event_timestamp": now_iso,
            "measurements": {
                "active_power_kw": elec.active_power_kw,
                "cumulative_energy_kwh": elec.cumulative_energy_kwh,
                "voltage_v": elec.voltage_v,
                "current_a": elec.current_a,
                "power_factor": elec.power_factor,
                "frequency_hz": elec.frequency_hz
            }
        })

    # 2. Water
    if water.running:
        packets.append({
            "message_id": f"MSG_SIM_WATER_{int(time.time() * 1000)}",
            "simulator_id": "SIM_RESOURCE_STANDALONE_01",
            "device_id": water.device_id,
            "device_name": water.device_name,
            "facility_id": water.facility_id,
            "building_id": water.building_id,
            "source_type": "simulated_iot",
            "is_verified_hardware": False,
            "data_source_badge": "[SIMULATED IoT]",
            "event_timestamp": now_iso,
            "measurements": {
                "water_flow_lmin": water.flow_rate_lmin,
                "cumulative_water_m3": water.cumulative_water_m3,
                "water_pressure_bar": water.water_pressure_bar
            }
        })

    # 3. Air Quality
    if air.running:
        packets.append({
            "message_id": f"MSG_SIM_AIR_{int(time.time() * 1000)}",
            "simulator_id": "SIM_RESOURCE_STANDALONE_01",
            "device_id": air.device_id,
            "device_name": air.device_name,
            "facility_id": air.facility_id,
            "building_id": air.building_id,
            "source_type": "simulated_iot",
            "is_verified_hardware": False,
            "data_source_badge": "[SIMULATED IoT]",
            "event_timestamp": now_iso,
            "measurements": {
                "co2_ppm": air.co2_ppm,
                "pm25": air.pm25,
                "pm10": air.pm10,
                "temperature_c": air.temperature_c,
                "humidity_pct": air.humidity_pct,
                "air_quality_aqi": air.air_quality_aqi
            }
        })

    # 4. Waste
    if waste.running:
        packets.append({
            "message_id": f"MSG_SIM_WASTE_{int(time.time() * 1000)}",
            "simulator_id": "SIM_RESOURCE_STANDALONE_01",
            "device_id": waste.device_id,
            "device_name": waste.device_name,
            "facility_id": waste.facility_id,
            "building_id": waste.building_id,
            "source_type": "simulated_iot",
            "is_verified_hardware": False,
            "data_source_badge": "[SIMULATED IoT]",
            "event_timestamp": now_iso,
            "measurements": {
                "fill_level_percent": waste.fill_level_percent,
                "estimated_waste_kg": waste.estimated_waste_kg
            }
        })

    return packets

def dispatch_telemetry(packets: List[Dict[str, Any]], target_url: str) -> Tuple[bool, int, str]:
    """Posts telemetry packets to the backend using standard library urllib."""
    if not packets:
        return True, 0, "No active packets to send"

    success_count = 0
    last_err = ""

    for pkt in packets:
        try:
            req_data = json.dumps(pkt).encode("utf-8")
            req = urllib.request.Request(
                target_url,
                data=req_data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=0.5) as resp:
                if resp.status in (200, 201, 202):
                    success_count += 1
                else:
                    last_err = f"HTTP {resp.status}"
        except Exception as e:
            last_err = str(e)

    all_ok = (success_count == len(packets))
    return all_ok, success_count, last_err
