"""
Campus Event Generator.
Produces events.csv containing scheduled campus activities (exams, sports week, placement drives, holidays).
Events dynamically modulate occupancy, traffic, waste, and energy demand.
"""

import pandas as pd
import numpy as np
from generator.config import RAW_DATA_DIR, START_TIME, END_TIME, logger

def generate_events() -> pd.DataFrame:
    logger.info("Generating Campus Events Schedule (events.csv)...")
    
    events = []
    
    # 1. Mid-Term Examination (March 10 - March 20, 2026)
    events.append({
        "event_id": "EVT_EXAM_MID",
        "event_type": "exam_day",
        "start_time": "2026-03-10 08:00:00",
        "end_time": "2026-03-20 18:00:00",
        "affected_locations": "Academic_Zone,Library",
        "occupancy_multiplier": 1.45,
        "energy_multiplier": 1.25,
        "traffic_multiplier": 1.30,
        "description": "Mid-Semester Examinations (High Library & Classroom Usage)"
    })
    
    # 2. Annual Sports Fest (February 12 - February 15, 2026)
    events.append({
        "event_id": "EVT_SPORTS_ANNUAL",
        "event_type": "sports_event",
        "start_time": "2026-02-12 09:00:00",
        "end_time": "2026-02-15 21:00:00",
        "affected_locations": "Sports_Complex,Canteen,Hostels",
        "occupancy_multiplier": 1.60,
        "energy_multiplier": 1.35,
        "traffic_multiplier": 1.50,
        "description": "Inter-College Sports Championship"
    })
    
    # 3. Campus Placement Drive (April 05 - April 08, 2026)
    events.append({
        "event_id": "EVT_PLACEMENT_DRIVE",
        "event_type": "placement_drive",
        "start_time": "2026-04-05 08:00:00",
        "end_time": "2026-04-08 20:00:00",
        "affected_locations": "Admin_Block,CSE_Block",
        "occupancy_multiplier": 1.30,
        "energy_multiplier": 1.40,
        "traffic_multiplier": 1.40,
        "description": "National Corporate Campus Hiring Drive"
    })
    
    # 4. Summer Heatwave Period (May 18 - May 24, 2026)
    events.append({
        "event_id": "EVT_HEATWAVE_SUMMER",
        "event_type": "extreme_heat_day",
        "start_time": "2026-05-18 00:00:00",
        "end_time": "2026-05-24 23:59:00",
        "affected_locations": "All_Campus",
        "occupancy_multiplier": 0.80,
        "energy_multiplier": 1.70,  # Extreme HVAC demand
        "traffic_multiplier": 0.70,
        "description": "Severe Summer Heatwave (High Cooling Load)"
    })
    
    # 5. Monsoon Downpour Event (June 15 - June 17, 2026)
    events.append({
        "event_id": "EVT_MONSOON_HEAVY",
        "event_type": "rainy_day",
        "start_time": "2026-06-15 00:00:00",
        "end_time": "2026-06-17 23:59:00",
        "affected_locations": "Outdoor_Roads,Parking",
        "occupancy_multiplier": 0.75,
        "energy_multiplier": 1.10,
        "traffic_multiplier": 0.50,  # Low outdoor movement
        "description": "Heavy Monsoon Rainstorm"
    })

    df_events = pd.DataFrame(events)
    df_events.to_csv(RAW_DATA_DIR / "events.csv", index=False)
    logger.info("Events Schedule generated successfully.")
    return df_events

if __name__ == "__main__":
    generate_events()
