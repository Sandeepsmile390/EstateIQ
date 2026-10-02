"""
Water Generator.
Produces 15-minute water_readings.csv for all 10 buildings over 180 days.
Columns: timestamp, building_id, water_consumption_liters, water_flow_rate_lpm, water_pressure_bar,
         tank_level_percent, recycled_water_liters, municipal_water_liters, water_intensity_l_per_person.
"""

import numpy as np
import pandas as pd
from generator.config import RAW_DATA_DIR, load_json_config, logger

def generate_water(df_occupancy: pd.DataFrame = None) -> pd.DataFrame:
    logger.info("Generating 15-minute Water Readings (water_readings.csv)...")
    
    if df_occupancy is None:
        df_occupancy = pd.read_csv(RAW_DATA_DIR / "occupancy_readings.csv")
        df_occupancy["timestamp"] = pd.to_datetime(df_occupancy["timestamp"])
        
    cfg = load_json_config("facility_config.json")
    bld_map = {b["building_id"]: b for b in cfg["buildings"]}
    
    records = []
    
    for row in df_occupancy.itertuples():
        bld_info = bld_map[row.building_id]
        profile = bld_info["occupancy_profile"]
        occ = row.occupancy_count
        hr = row.timestamp.hour + row.timestamp.minute / 60.0
        
        # Per capita 15-min liters multiplier by building type
        if "residential" in profile:    # Hostels
            per_person_lpm = 0.45
            base_flow = 8.0
        elif "meal" in profile:        # Canteen
            per_person_lpm = 0.65
            base_flow = 12.0
        elif "academic" in profile:    # Classrooms
            per_person_lpm = 0.15
            base_flow = 3.0
        else:                          # Admin/Library
            per_person_lpm = 0.10
            base_flow = 2.0
            
        # Flow rate in Liters Per Minute (LPM)
        flow_lpm = max(0.5, base_flow + occ * per_person_lpm + np.random.normal(0, 1.0))
        # 15-minute total water consumption in Liters (LPM * 15 minutes)
        water_liters = round(flow_lpm * 15.0, 2)
        
        # Water pressure (bar) fluctuates slightly with flow demand
        pressure_bar = round(np.clip(3.5 - (flow_lpm / 80.0) + np.random.normal(0, 0.05), 1.8, 4.2), 2)
        
        # Overhead tank level calculation (0-100%)
        # Refills during 04:00-06:00 and 16:00-18:00
        is_refill = (4.0 <= hr <= 6.0) or (16.0 <= hr <= 18.0)
        tank_base = 85.0 if is_refill else (70.0 - (hr % 6) * 4.0)
        tank_level = round(np.clip(tank_base + np.random.normal(0, 2.0), 20.0, 100.0), 1)
        
        # Recycled greywater usage (Hostels & Canteen use STP recycled water for flushing)
        if "residential" in profile or "meal" in profile:
            recycled_liters = round(water_liters * 0.30, 2)
        else:
            recycled_liters = 0.0
            
        municipal_liters = round(max(0.0, water_liters - recycled_liters), 2)
        intensity_l_per_person = round(water_liters / max(1, occ), 2)
        
        records.append({
            "timestamp": row.timestamp,
            "building_id": row.building_id,
            "water_consumption_liters": water_liters,
            "water_flow_rate_lpm": round(flow_lpm, 2),
            "water_pressure_bar": pressure_bar,
            "tank_level_percent": tank_level,
            "recycled_water_liters": recycled_liters,
            "municipal_water_liters": municipal_liters,
            "water_intensity_l_per_person": intensity_l_per_person
        })
        
    df_water = pd.DataFrame(records)
    df_water.to_csv(RAW_DATA_DIR / "water_readings.csv", index=False)
    logger.info("Water readings generated successfully (%d rows).", len(df_water))
    return df_water

if __name__ == "__main__":
    generate_water()
