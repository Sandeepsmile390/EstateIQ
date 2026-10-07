"""
EstateIQ Multi-Domain Registry (src/ai/domain_registry.py).
Defines metadata, data sources, key metrics, units, available questions, and recommendation rules
across all 11 EstateIQ facility management domains.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

@dataclass
class DomainDefinition:
    domain_id: str
    display_name: str
    description: str
    primary_metrics: List[str]
    units: Dict[str, str]
    data_sources: List[str]
    sample_questions: List[str]
    default_recommendations: List[Dict[str, Any]] = field(default_factory=list)

DOMAINS: Dict[str, DomainDefinition] = {
    "energy": DomainDefinition(
        domain_id="energy",
        display_name="Electricity & Energy Demand",
        description="Real-time electricity consumption, HVAC setback monitoring, peak demand forecasting, and SHAP driver attribution.",
        primary_metrics=["electricity_kwh", "hvac_power_kw", "peak_demand_kwh", "power_factor"],
        units={"electricity_kwh": "kWh", "hvac_power_kw": "kW", "peak_demand_kwh": "kWh", "power_factor": "pf"},
        data_sources=["Modbus Smart Meters", "CT Sensor Gateways", "CatBoost ML Model"],
        sample_questions=[
            "Why is energy consumption high?",
            "What is our current electricity demand?",
            "Show me the energy forecast for the next 4 hours.",
            "Which building has the highest energy intensity?"
        ],
        default_recommendations=[
            {
                "title": "Reset HVAC Thermostat Setpoint Schedule",
                "action": "Adjust Block B HVAC setback to 24.5°C during 13:00-16:00 window.",
                "expected_saving_inr": 14200.0,
                "co2_impact_kg": 150.0,
                "effort": "LOW"
            }
        ]
    ),
    "water": DomainDefinition(
        domain_id="water",
        display_name="Water Flow & Leakage Risk",
        description="Main inlet water volume, greywater recycling recovery, and abnormal overnight flow leak detection.",
        primary_metrics=["water_consumption_liters", "flow_rate_lpm", "recycled_water_kl", "leak_risk_score"],
        units={"water_consumption_liters": "L", "flow_rate_lpm": "L/min", "recycled_water_kl": "kL", "leak_risk_score": "index"},
        data_sources=["Ultrasonic Flow Sensors", "STP Greywater Meters"],
        sample_questions=[
            "What is our water consumption today?",
            "Are there any water leaks detected?",
            "How much water did we recycle this week?"
        ],
        default_recommendations=[
            {
                "title": "Inspect Block A Main Riser for Pipe Seepage",
                "action": "Dispatch plumbing team to verify 4.2 L/min overnight baseline flow rate.",
                "expected_saving_inr": 3800.0,
                "co2_impact_kg": 25.0,
                "effort": "LOW"
            }
        ]
    ),
    "waste": DomainDefinition(
        domain_id="waste",
        display_name="Smart Waste & Bin Overflow",
        description="Smart waste bin fill percentage monitoring, overflow risk prediction, and dynamic sanitation collection routing.",
        primary_metrics=["fill_level_percent", "fill_rate_pct_hr", "bins_near_capacity", "waste_diverted_kg"],
        units={"fill_level_percent": "%", "fill_rate_pct_hr": "%/hr", "bins_near_capacity": "count", "waste_diverted_kg": "kg"},
        data_sources=["Optical Time-of-Flight Sensors", "Cafeteria Smart Bins"],
        sample_questions=[
            "Which waste bins are approaching overflow?",
            "What is the waste diversion rate?",
            "When should the next cafeteria bin pick-up happen?"
        ],
        default_recommendations=[
            {
                "title": "Dispatch Early Waste Pickup for Cafeteria Bin #01",
                "action": "Route sanitation crew to empty Bin #01 before 14:00 lunch rush.",
                "expected_saving_inr": 1200.0,
                "co2_impact_kg": 10.0,
                "effort": "LOW"
            }
        ]
    ),
    "air_quality": DomainDefinition(
        domain_id="air_quality",
        display_name="Air Quality & Environmental Telemetry",
        description="Indoor & outdoor Air Quality Index (AQI), PM2.5, PM10, temperature, and relative humidity monitoring.",
        primary_metrics=["aqi", "pm2_5", "pm10", "co2_ppm", "temperature_c", "humidity_pct"],
        units={"aqi": "AQI", "pm2_5": "µg/m³", "pm10": "µg/m³", "co2_ppm": "ppm", "temperature_c": "°C", "humidity_pct": "%"},
        data_sources=["Laser Dust Sensors", "NDIR CO2 Sensors"],
        sample_questions=[
            "What is the current AQI across campus?",
            "Is air quality safe near Academic Block A?",
            "What are the PM2.5 levels today?"
        ],
        default_recommendations=[
            {
                "title": "Increase AHU Fresh Air Intake Rate in Academic Block A",
                "action": "Ramp up ventilation rate to clear 110 PM2.5 indoor concentration.",
                "expected_saving_inr": 800.0,
                "co2_impact_kg": 5.0,
                "effort": "LOW"
            }
        ]
    ),
    "traffic": DomainDefinition(
        domain_id="traffic",
        display_name="Gate Traffic & Entry Congestion",
        description="Main gate vehicle counts, peak entry window analytics, and gate congestion risk scoring.",
        primary_metrics=["vehicle_count", "peak_entry_rate", "congestion_index", "wait_time_sec"],
        units={"vehicle_count": "vehicles/hr", "peak_entry_rate": "v/min", "congestion_index": "score", "wait_time_sec": "sec"},
        data_sources=["ANPR Camera Gateways", "Inductive Loop Sensors"],
        sample_questions=[
            "How heavy is gate traffic right now?",
            "Which entry gate is most congested?",
            "What is the peak entry traffic time?"
        ],
        default_recommendations=[
            {
                "title": "Open Auxiliary Gate 02 During Morning Peak Window",
                "action": "Divert staff vehicles to Gate 02 between 08:30 and 09:30 AM.",
                "expected_saving_inr": 2500.0,
                "co2_impact_kg": 45.0,
                "effort": "MEDIUM"
            }
        ]
    ),
    "parking": DomainDefinition(
        domain_id="parking",
        display_name="Parking Zone Occupancy",
        description="Real-time parking space availability, zone occupancy percentage, and peak occupancy forecasting.",
        primary_metrics=["occupancy_percent", "available_spaces", "occupied_spaces", "ev_charging_usage"],
        units={"occupancy_percent": "%", "available_spaces": "bays", "occupied_spaces": "bays", "ev_charging_usage": "%"},
        data_sources=["Ground Ultrasonic Parking Sensors", "EV Charger Telemetry"],
        sample_questions=[
            "Are there parking spaces available in Lot B?",
            "What is the current parking occupancy rate?",
            "How many EV chargers are in use?"
        ],
        default_recommendations=[
            {
                "title": "Reallocate Overflow Parking to Zone C",
                "action": "Update digital signage to guide incoming vehicles to Zone C.",
                "expected_saving_inr": 900.0,
                "co2_impact_kg": 15.0,
                "effort": "LOW"
            }
        ]
    ),
    "equipment": DomainDefinition(
        domain_id="equipment",
        display_name="Asset Health & Predictive Maintenance",
        description="Chiller vibration, transformer temperature, pump pressure, and machine learning failure risk scoring.",
        primary_metrics=["vibration_mms", "bearing_temp_c", "health_score", "failure_risk_pct"],
        units={"vibration_mms": "mm/s", "bearing_temp_c": "°C", "health_score": "/100", "failure_risk_pct": "%"},
        data_sources=["Piezoelectric Vibration Sensors", "Thermal Cameras"],
        sample_questions=[
            "Which equipment has high maintenance risk?",
            "What is the vibration reading for Chiller 01?",
            "Are any HVAC pumps showing abnormal health scores?"
        ],
        default_recommendations=[
            {
                "title": "Schedule Preventive Lubrication on Chiller 01",
                "action": "Service drive bearing displaying 3.8 mm/s vibration anomaly.",
                "expected_saving_inr": 6400.0,
                "co2_impact_kg": 80.0,
                "effort": "MEDIUM"
            }
        ]
    ),
    "safety": DomainDefinition(
        domain_id="safety",
        display_name="Campus Safety & Incident Tracking",
        description="Observed safety incident logs, emergency egress monitoring, and physical hazard risk indicators.",
        primary_metrics=["incident_count", "open_hazards", "egress_clearance_score", "safety_index"],
        units={"incident_count": "events", "open_hazards": "count", "egress_clearance_score": "%", "safety_index": "/100"},
        data_sources=["Safety Officer Audits", "BMS Alarm Panel"],
        sample_questions=[
            "Are there any open safety hazards?",
            "What is our campus safety score?",
            "Show safety incident distribution."
        ],
        default_recommendations=[
            {
                "title": "Clear Egress Obstruction near Science Block B Door 2",
                "action": "Dispatch facilities team to remove temporary storage pallets from emergency exit.",
                "expected_saving_inr": 0.0,
                "co2_impact_kg": 0.0,
                "effort": "LOW"
            }
        ]
    ),
    "emissions": DomainDefinition(
        domain_id="emissions",
        display_name="Scope 1 & 2 Carbon Footprint",
        description="Grid electricity, diesel generator, and vehicle carbon accounting using configured emission factors.",
        primary_metrics=["daily_co2_kg", "monthly_co2_tons", "scope_1_kg", "scope_2_kg", "renewable_offset_pct"],
        units={"daily_co2_kg": "kg CO2e", "monthly_co2_tons": "Tons CO2e", "scope_1_kg": "kg CO2e", "scope_2_kg": "kg CO2e", "renewable_offset_pct": "%"},
        data_sources=["Centralized GHG Accounting Engine", "Rooftop Solar Meter"],
        sample_questions=[
            "What is our carbon footprint this month?",
            "How much CO2 did rooftop solar offset?",
            "What is the breakdown of Scope 1 vs Scope 2 emissions?"
        ],
        default_recommendations=[
            {
                "title": "Maximize Rooftop Solar Generation Yield",
                "action": "Clean 150 kWp solar PV panels to boost renewable offset by 8.5%.",
                "expected_saving_inr": 18500.0,
                "co2_impact_kg": 450.0,
                "effort": "LOW"
            }
        ]
    ),
    "sustainability": DomainDefinition(
        domain_id="sustainability",
        display_name="ESG & Composite Sustainability Scorecard",
        description="Composite 0-100 sustainability index combining energy efficiency, water recovery, waste diversion, carbon footprint, and UN SDG alignment.",
        primary_metrics=["composite_score", "grade_tier", "energy_subscore", "water_subscore", "waste_subscore"],
        units={"composite_score": "/100", "grade_tier": "tier", "energy_subscore": "/100", "water_subscore": "/100", "waste_subscore": "/100"},
        data_sources=["EstateIQ Sustainability Calculator", "UN SDG Index"],
        sample_questions=[
            "What is our overall sustainability score?",
            "How do we compare against UN SDG targets?",
            "What is our ESG performance tier?"
        ],
        default_recommendations=[
            {
                "title": "Target Gold-to-Platinum ESG Rating Upgrade",
                "action": "Execute top 3 high-confidence AI energy and water saving rules.",
                "expected_saving_inr": 24400.0,
                "co2_impact_kg": 680.0,
                "effort": "MEDIUM"
            }
        ]
    )
}

DOMAIN_REGISTRY = DOMAINS

def get_domain_info(domain_id: str) -> Optional[DomainDefinition]:
    return DOMAINS.get(domain_id.lower())

def list_all_domains() -> List[Dict[str, Any]]:
    return [
        {
            "id": d.domain_id,
            "name": d.display_name,
            "description": d.description,
            "metrics": d.primary_metrics,
            "sample_questions": d.sample_questions
        }
        for d in DOMAINS.values()
    ]
