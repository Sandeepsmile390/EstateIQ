"""
Scenario Engine & Anomaly Presets (simulator/scenario_engine.py).
Defines 14 operational scenarios that alter physics telemetry output for testing anomaly detection pipelines.
"""

from typing import Dict, Any, List

SCENARIOS: Dict[str, Dict[str, Any]] = {
    "Normal Campus Operation": {
        "id": "SCEN_01",
        "name": "Normal Campus Operation",
        "description": "Standard baseline operation following normal time-of-day occupancy and HVAC curves.",
        "fault_type": "NORMAL",
        "expected_observation": "All parameters within normal baseline limits."
    },
    "High HVAC Consumption": {
        "id": "SCEN_02",
        "name": "High HVAC Consumption",
        "description": "Chiller and AHU compressor runtime locked at maximum capacity.",
        "fault_type": "ANOMALY",
        "expected_observation": "HVAC electrical load surge +40-60% above contextual baseline."
    },
    "Low Occupancy with HVAC Running": {
        "id": "SCEN_03",
        "name": "Low Occupancy with HVAC Running",
        "description": "Occupancy drops to near zero during weekend/holiday while full HVAC remains active.",
        "fault_type": "WASTE",
        "expected_observation": "High energy consumption per occupant ratio."
    },
    "Transformer Load Increase": {
        "id": "SCEN_04",
        "name": "Transformer Load Increase",
        "description": "Main Substation Transformer loading exceeds 90% threshold.",
        "fault_type": "OVERLOAD",
        "expected_observation": "Transformer oil temperature rise and high kVA loading."
    },
    "DG Operating": {
        "id": "SCEN_05",
        "name": "DG Operating",
        "description": "Main grid power failure simulated; Standby Diesel Generator active.",
        "fault_type": "EMERGENCY_POWER",
        "expected_observation": "DG running at 1500 RPM with active fuel consumption."
    },
    "Sudden Energy Surge": {
        "id": "SCEN_06",
        "name": "Sudden Energy Surge",
        "description": "Instantaneous peak power spike across campus submeters.",
        "fault_type": "SURGE",
        "expected_observation": "Sharp spike in kW power demand."
    },
    "Gradual Water Leakage": {
        "id": "SCEN_07",
        "name": "Gradual Water Leakage",
        "description": "Continuous pipe seepage in riser network.",
        "fault_type": "LEAK",
        "expected_observation": "Persistent non-zero flow rate during off-peak night hours."
    },
    "Sensor Offline": {
        "id": "SCEN_08",
        "name": "Sensor Offline",
        "description": "Device stops transmitting telemetry packet stream.",
        "fault_type": "HARDWARE_FAULT",
        "expected_observation": "Stale status and missing heartbeat in EstateIQ dashboard."
    },
    "Frozen Sensor Value": {
        "id": "SCEN_09",
        "name": "Frozen Sensor Value",
        "description": "Sensor returns constant static value regardless of load changes.",
        "fault_type": "SENSOR_STUCK",
        "expected_observation": "Zero variance in telemetry readings over time."
    },
    "Invalid Sensor Reading": {
        "id": "SCEN_10",
        "name": "Invalid Sensor Reading",
        "description": "Sensor transmits out-of-range negative or impossible numbers.",
        "fault_type": "CORRUPTED_DATA",
        "expected_observation": "Data quality audit flags out-of-bounds metrics."
    },
    "High Ambient Temperature": {
        "id": "SCEN_11",
        "name": "High Ambient Temperature",
        "description": "Extreme summer heatwave with ambient temperature exceeding 39.5°C.",
        "fault_type": "WEATHER_EXTREME",
        "expected_observation": "Increased cooling demand across all hostel and academic blocks."
    },
    "Peak Occupancy": {
        "id": "SCEN_12",
        "name": "Peak Occupancy",
        "description": "Campus event causing 100% building occupancy.",
        "fault_type": "HIGH_DEMAND",
        "expected_observation": "Max occupancy count and elevated ventilation/lighting demand."
    },
    "Night-Time Energy Waste": {
        "id": "SCEN_13",
        "name": "Night-Time Energy Waste",
        "description": "All floor lighting and ventilation active past 02:00 AM.",
        "fault_type": "WASTE",
        "expected_observation": "Off-peak baseline deviation."
    },
    "Custom Scenario": {
        "id": "SCEN_14",
        "name": "Custom Scenario",
        "description": "User-configured custom parameter overrides.",
        "fault_type": "CUSTOM",
        "expected_observation": "Direct manual control via simulator sliders."
    }
}

class ScenarioEngine:
    @staticmethod
    def get_all_scenarios() -> List[Dict[str, Any]]:
        return list(SCENARIOS.values())

    @staticmethod
    def list_scenarios() -> List[Dict[str, Any]]:
        return list(SCENARIOS.values())

    @staticmethod
    def get_scenario(name: str) -> Dict[str, Any]:
        return SCENARIOS.get(name, SCENARIOS["Normal Campus Operation"])

    @staticmethod
    def apply_scenario(scenario_name: str, device_dict: Dict[str, Any], raw_sample: Dict[str, Any]) -> Dict[str, Any]:
        sample = dict(raw_sample)
        readings = dict(sample.get("readings", {}))
        
        if scenario_name == "High HVAC Consumption" and ("hvac_load" in readings or "hvac_power_kw" in readings):
            if "hvac_load" in readings:
                readings["hvac_load"] = float(readings["hvac_load"]) * 1.5
            if "hvac_power_kw" in readings:
                readings["hvac_power_kw"] = float(readings["hvac_power_kw"]) * 1.5
        elif scenario_name == "Gradual Water Leakage" and ("water_flow" in readings or "flow_rate_lmin" in readings):
            if "water_flow" in readings:
                readings["water_flow"] = float(readings["water_flow"]) + 35.0
            if "flow_rate_lmin" in readings:
                readings["flow_rate_lmin"] = float(readings["flow_rate_lmin"]) + 35.0

        sample["readings"] = readings
        return sample

GLOBAL_SCENARIO_ENGINE = ScenarioEngine()

