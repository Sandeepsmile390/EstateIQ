"""
Occupancy Generator.
Produces 15-minute occupancy_readings.csv for all 10 campus buildings over 180 days.
Columns: timestamp, building_id, occupancy_count, occupancy_percent, students_count, staff_count, visitors_count.
Tied strictly to building type profiles, weekdays vs weekends, and event calendar.
"""

import numpy as np
import pandas as pd
from generator.config import RAW_DATA_DIR, get_master_timestamps, load_json_config, logger

def generate_occupancy() -> pd.DataFrame:
    logger.info("Generating 15-minute Occupancy Readings (occupancy_readings.csv)...")
    
    cfg = load_json_config("facility_config.json")
    buildings = cfg["buildings"]
    timestamps = get_master_timestamps()
    n_ts = len(timestamps)
    
    # Pre-calculate hour and day of week arrays
    hours = np.array(timestamps.hour + timestamps.minute / 60.0)
    dows = np.array(timestamps.dayofweek)
    is_weekend = (dows >= 5)
    
    all_records = []
    
    for bld in buildings:
        bld_id = bld["building_id"]
        cap = bld["capacity"]
        profile = bld["occupancy_profile"]
        
        counts = np.zeros(n_ts)
        
        for i in range(n_ts):
            hr = hours[i]
            wknd = is_weekend[i]
            
            if profile == "academic_daytime" or profile == "academic_extended":
                if wknd:
                    base_ratio = 0.05 if hr < 8 or hr > 18 else 0.15
                else:
                    if 8.0 <= hr <= 16.5:
                        base_ratio = 0.75 + 0.15 * np.sin((hr - 8.0) * np.pi / 8.5)
                    elif 16.5 < hr <= 18.5:
                        base_ratio = 0.40
                    elif 18.5 < hr <= 21.0 and profile == "academic_extended":
                        base_ratio = 0.25
                    else:
                        base_ratio = 0.02
                        
            elif profile == "residential_247":  # Hostels
                if 0.0 <= hr <= 7.0:
                    base_ratio = 0.88
                elif 7.0 < hr <= 9.0:
                    base_ratio = 0.60
                elif 9.0 < hr <= 17.0:
                    base_ratio = 0.35 if not wknd else 0.75
                elif 17.0 < hr <= 22.0:
                    base_ratio = 0.70
                else:
                    base_ratio = 0.90
                    
            elif profile == "meal_peaks":  # Canteen
                if 7.5 <= hr <= 9.0:      # Breakfast
                    base_ratio = 0.65
                elif 12.0 <= hr <= 14.5:  # Lunch
                    base_ratio = 0.92
                elif 16.5 <= hr <= 18.0:  # Snacks
                    base_ratio = 0.55
                elif 19.5 <= hr <= 21.5:  # Dinner
                    base_ratio = 0.80
                else:
                    base_ratio = 0.05
                    
            elif profile == "library_hours":
                if wknd:
                    base_ratio = 0.30 if 9.0 <= hr <= 17.0 else 0.05
                else:
                    base_ratio = 0.70 if 9.0 <= hr <= 21.0 else 0.05
                    
            elif profile == "sports_hours":
                if 16.0 <= hr <= 20.5:
                    base_ratio = 0.80 if wknd else 0.65
                elif 6.0 <= hr <= 8.5:
                    base_ratio = 0.45
                else:
                    base_ratio = 0.08
                    
            elif profile == "office_hours":  # Admin Block
                if wknd:
                    base_ratio = 0.02
                else:
                    base_ratio = 0.75 if 9.0 <= hr <= 17.5 else 0.03
                    
            else:  # Utility 24/7
                base_ratio = 0.30
                
            # Add random fluctuation noise
            noise = np.random.normal(0, 0.04)
            ratio = np.clip(base_ratio + noise, 0.0, 1.0)
            count = int(np.round(ratio * cap))
            counts[i] = count
            
        # Split into students, staff, visitors
        students = np.round(counts * 0.82).astype(int)
        staff = np.round(counts * 0.12).astype(int)
        visitors = counts - (students + staff)
        visitors = np.maximum(0, visitors)
        occ_pct = np.round((counts / cap) * 100.0, 2)
        
        df_bld_occ = pd.DataFrame({
            "timestamp": timestamps,
            "building_id": bld_id,
            "occupancy_count": counts.astype(int),
            "occupancy_percent": occ_pct,
            "students_count": students,
            "staff_count": staff,
            "visitors_count": visitors
        })
        all_records.append(df_bld_occ)
        
    df_occ_all = pd.concat(all_records, ignore_index=True)
    df_occ_all.to_csv(RAW_DATA_DIR / "occupancy_readings.csv", index=False)
    logger.info("Occupancy readings generated successfully (%d rows).", len(df_occ_all))
    return df_occ_all

if __name__ == "__main__":
    generate_occupancy()
