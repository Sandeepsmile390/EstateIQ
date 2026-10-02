"""
Waste Management Generator.
Produces waste_bins.csv, waste_collection_events.csv, and 15-minute bin fill readings over 180 days.
Columns: timestamp, bin_id, location_id, waste_type, capacity_liters, fill_level_percent, estimated_waste_kg,
         temperature_c, odor_risk_score, overflow_risk, collection_required, overflow_event,
         overflow_within_2h, overflow_within_4h.
"""

import numpy as np
import pandas as pd
from generator.config import RAW_DATA_DIR, get_master_timestamps, load_json_config, logger

def generate_waste(df_occupancy: pd.DataFrame = None) -> pd.DataFrame:
    logger.info("Generating Waste Bins, Collection Events, and Fill Readings...")
    
    cfg = load_json_config("facility_config.json")
    locations = cfg["locations"]
    timestamps = get_master_timestamps()
    n_ts = len(timestamps)
    
    # 1. Define 32 Waste Bins across campus
    waste_types = ["Wet_Organic", "Dry_Recyclable", "Hazardous_EWaste", "General_Waste"]
    bins = []
    bin_idx = 1
    for loc in locations:
        loc_id = loc["location_id"]
        for w_type in waste_types:
            cap = 240 if "Organic" in w_type or "General" in w_type else 120
            bins.append({
                "bin_id": f"BIN_{bin_idx:02d}",
                "location_id": loc_id,
                "waste_type": w_type,
                "capacity_liters": cap
            })
            bin_idx += 1
            
    df_bins = pd.DataFrame(bins)
    df_bins.to_csv(RAW_DATA_DIR / "waste_bins.csv", index=False)
    
    # Merge location occupancy proxy
    if df_occupancy is None:
        df_occupancy = pd.read_csv(RAW_DATA_DIR / "occupancy_readings.csv")
        df_occupancy["timestamp"] = pd.to_datetime(df_occupancy["timestamp"])
        
    avg_occ_df = df_occupancy.groupby("timestamp")["occupancy_count"].mean().reset_index()
    
    # Generate continuous fill dynamics for each bin
    all_bin_dfs = []
    collections = []
    
    for bin_info in bins:
        b_id = bin_info["bin_id"]
        loc_id = bin_info["location_id"]
        w_type = bin_info["waste_type"]
        cap = bin_info["capacity_liters"]
        
        # Fill rate depends on bin location and type
        fill_rate_mult = 1.8 if "CANTEEN" in loc_id else (1.2 if "ACADEMIC" in loc_id else 0.8)
        if "Organic" in w_type:
            fill_rate_mult *= 1.4
            
        current_fill = float(np.random.uniform(10.0, 35.0))
        fill_levels = np.zeros(n_ts)
        collection_flags = np.zeros(n_ts, dtype=int)
        overflow_events = np.zeros(n_ts, dtype=int)
        
        for t_idx in range(n_ts):
            ts = timestamps[t_idx]
            hr = ts.hour + ts.minute / 60.0
            occ_val = avg_occ_df.iloc[t_idx]["occupancy_count"]
            
            # Collection schedule: Routine empty at 06:00 and 18:00 if fill > 50%
            is_scheduled_collection = (hr in [6.0, 18.0]) and (current_fill >= 50.0)
            is_emergency_collection = (current_fill >= 92.0)
            
            if is_scheduled_collection or is_emergency_collection:
                collections.append({
                    "collection_id": f"COL_{b_id}_{t_idx}",
                    "timestamp": ts,
                    "bin_id": b_id,
                    "location_id": loc_id,
                    "fill_level_before": round(current_fill, 2),
                    "collection_type": "EMERGENCY" if is_emergency_collection else "SCHEDULED"
                })
                current_fill = float(np.random.uniform(2.0, 8.0))
                collection_flags[t_idx] = 1
            else:
                # Accumulate waste based on occupancy
                inc = (occ_val / 500.0) * fill_rate_mult * np.random.uniform(0.1, 0.4)
                current_fill = min(100.0, current_fill + inc)
                
            fill_levels[t_idx] = current_fill
            if current_fill >= 95.0:
                overflow_events[t_idx] = 1
                
        # Calculate Future Targets without leakage:
        # overflow_within_2h = 1 if max fill in next 8 steps (2 hrs) >= 95.0
        # overflow_within_4h = 1 if max fill in next 16 steps (4 hrs) >= 95.0
        s_fill = pd.Series(fill_levels)
        target_2h = (s_fill.iloc[::-1].rolling(window=8, min_periods=1).max().iloc[::-1] >= 95.0).astype(int).values
        target_4h = (s_fill.iloc[::-1].rolling(window=16, min_periods=1).max().iloc[::-1] >= 95.0).astype(int).values
        
        est_kg = np.round((fill_levels / 100.0) * cap * (0.35 if "Organic" in w_type else 0.15), 2)
        odor_score = np.round(np.clip((fill_levels / 100.0) * (1.5 if "Organic" in w_type else 0.6) * 10.0, 0.0, 10.0), 1)
        overflow_risk = np.round(np.clip(fill_levels / 100.0, 0.0, 1.0), 2)
        coll_req = (fill_levels >= 80.0).astype(int)
        
        df_single_bin = pd.DataFrame({
            "timestamp": timestamps,
            "bin_id": b_id,
            "location_id": loc_id,
            "waste_type": w_type,
            "capacity_liters": cap,
            "fill_level_percent": np.round(fill_levels, 2),
            "estimated_waste_kg": est_kg,
            "temperature_c": 28.5,
            "odor_risk_score": odor_score,
            "overflow_risk": overflow_risk,
            "collection_required": coll_req,
            "overflow_event": overflow_events,
            "overflow_within_2h": target_2h,
            "overflow_within_4h": target_4h
        })
        all_bin_dfs.append(df_single_bin)
        
    df_waste_all = pd.concat(all_bin_dfs, ignore_index=True)
    df_waste_all.to_csv(RAW_DATA_DIR / "waste_readings.csv", index=False)
    
    df_colls = pd.DataFrame(collections)
    df_colls.to_csv(RAW_DATA_DIR / "waste_collection_events.csv", index=False)
    
    logger.info("Waste readings generated successfully (%d rows, %d collection events).", len(df_waste_all), len(df_colls))
    return df_waste_all

if __name__ == "__main__":
    generate_waste()
