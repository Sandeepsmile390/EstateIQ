"""
Safety Incident Generator.
Produces sparse safety_incidents.csv records over 180 days (~20-30 events).
Columns: incident_id, timestamp, location_id, incident_type, severity, weather_condition,
         occupancy_level, traffic_level, response_time_minutes, resolved, description.
"""

import numpy as np
import pandas as pd
from generator.config import RAW_DATA_DIR, get_master_timestamps, load_json_config, logger

def generate_safety() -> pd.DataFrame:
    logger.info("Generating Sparse Safety Incidents (safety_incidents.csv)...")
    
    cfg = load_json_config("facility_config.json")
    locations = [loc["location_id"] for loc in cfg["locations"]]
    timestamps = get_master_timestamps()
    n_ts = len(timestamps)
    
    incident_types = [
        ("slip", "Wet floor near canteen quadrangle"),
        ("minor_injury", "Minor hand cut during lab experiment"),
        ("electrical_issue", "Short circuit in distribution box"),
        ("equipment_incident", "Belt slippage on ventilation unit"),
        ("traffic_incident", "Minor vehicle bumper scrape near Main Gate"),
        ("fire_alarm", "Transient smoke sensor trigger"),
        ("security_event", "Tailgating at vehicle entry barrier")
    ]
    
    severities = ["LOW", "MEDIUM", "HIGH"]
    weathers = ["Clear", "Rainy", "Overcast"]
    
    incidents = []
    idx = 1
    
    for t_idx in range(n_ts):
        ts = timestamps[t_idx]
        # Low probability event (~1 incident every 6-8 days)
        if np.random.rand() < 0.0015:
            loc = np.random.choice(locations)
            inc_type, desc = incident_types[np.random.choice(len(incident_types))]
            sev = np.random.choice(severities, p=[0.70, 0.22, 0.08])
            weather = "Rainy" if ts.month == 6 and np.random.rand() < 0.4 else np.random.choice(weathers, p=[0.7, 0.2, 0.1])
            resp_time = int(np.random.uniform(5, 25))
            
            incidents.append({
                "incident_id": f"INC_{idx:03d}",
                "timestamp": ts,
                "location_id": loc,
                "incident_type": inc_type,
                "severity": sev,
                "weather_condition": weather,
                "occupancy_level": np.random.randint(20, 250),
                "traffic_level": np.random.randint(10, 90),
                "response_time_minutes": resp_time,
                "resolved": 1,
                "description": desc
            })
            idx += 1
            
    df_safety = pd.DataFrame(incidents)
    df_safety.to_csv(RAW_DATA_DIR / "safety_incidents.csv", index=False)
    logger.info("Safety incidents generated successfully (%d sparse events).", len(df_safety))
    return df_safety

if __name__ == "__main__":
    generate_safety()
