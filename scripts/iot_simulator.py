"""
EstateIQ Hardware & IoT Simulator (scripts/iot_simulator.py).
Simulates IoT telemetry stream (voltage, current, power, energy, power factor, frequency, occupancy, temperature).
Supports Normal mode, Anomaly mode, Device Offline mode, and Network Interruption mode.
"""

import time
import json
import random
from datetime import datetime, timezone, timedelta

class IoTSimulator:
    """Simulates real-world smart energy meter and environmental sensor network."""

    def __init__(
        self,
        device_id: str = "METER-BLOCK-B-001",
        facility_id: str = "FAC_GEC_CAMPUS",
        building_id: str = "Block B Hostel"
    ):
        self.device_id = device_id
        self.facility_id = facility_id
        self.building_id = building_id
        self.sequence = 1000
        self.total_energy_kwh = 12450.0

    def generate_reading(
        self,
        mode: str = "NORMAL",
        hour: int = 14
    ) -> dict:
        """Generates a structured telemetry reading matching the hardware MQTT schema."""
        self.sequence += 1
        now_str = datetime.now(timezone.utc).isoformat()

        # Offline / Failure mode
        if mode == "OFFLINE":
            return {
                "device_id": self.device_id,
                "facility_id": self.facility_id,
                "building_id": self.building_id,
                "status": "OFFLINE",
                "error": "Communication Timeout / Sensor Disconnected"
            }

        # Environmental variables
        base_temp = 25.0 + 7.0 * (1.0 if 8 <= hour <= 18 else 0.2)
        temp_c = round(base_temp + random.uniform(-1.5, 1.5), 2)

        if mode == "ANOMALY":
            # High HVAC surge mode
            voltage_v = round(random.uniform(220.0, 228.0), 1)
            current_a = round(random.uniform(35.0, 50.0), 1)
            power_kw = round((voltage_v * current_a * 0.92) / 1000.0 * 3.0, 2)
            occupancy = random.randint(40, 70) # Low occupancy + High power
            power_factor = round(random.uniform(0.78, 0.85), 2)
        else:
            # Normal operating mode
            voltage_v = round(random.uniform(228.0, 235.0), 1)
            current_a = round(random.uniform(15.0, 25.0), 1)
            power_kw = round((voltage_v * current_a * 0.95) / 1000.0, 2)
            occupancy = random.randint(120, 220) if 8 <= hour <= 18 else random.randint(10, 40)
            power_factor = round(random.uniform(0.92, 0.98), 2)

        frequency_hz = round(random.uniform(49.95, 50.05), 2)
        self.total_energy_kwh += round(power_kw * 0.25, 2)

        return {
            "device_id": self.device_id,
            "facility_id": self.facility_id,
            "building_id": self.building_id,
            "timestamp": now_str,
            "sequence": self.sequence,
            "measurements": {
                "voltage_v": voltage_v,
                "current_a": current_a,
                "power_kw": power_kw,
                "energy_kwh": round(self.total_energy_kwh, 2),
                "power_factor": power_factor,
                "frequency_hz": frequency_hz,
                "occupancy": occupancy,
                "temperature_c": temp_c
            },
            "quality": {
                "sensor_status": "DEGRADED" if mode == "ANOMALY" else "OK",
                "calibrated": True
            },
            "provenance": "SIMULATED_SENSOR"
        }

if __name__ == "__main__":
    simulator = IoTSimulator()
    print("Generating Normal Telemetry Reading:")
    print(json.dumps(simulator.generate_reading(mode="NORMAL"), indent=2))
    print("\nGenerating Anomaly Telemetry Reading:")
    print(json.dumps(simulator.generate_reading(mode="ANOMALY"), indent=2))
