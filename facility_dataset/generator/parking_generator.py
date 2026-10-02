"""
Parking Generator.
Produces 15-minute parking_readings.csv across 4 parking zones over 180 days.
Zones: North Parking, South Parking, Visitor Parking, Hostel Parking.
Columns: timestamp, parking_zone_id, total_spaces, occupied_spaces, occupancy_percent,
         available_spaces, turnover_rate, parking_status.
"""

import numpy as np
import pandas as pd
from generator.config import RAW_DATA_DIR, logger

def generate_parking(df_traffic: pd.DataFrame = None) -> pd.DataFrame:
    logger.info("Generating 15-minute Parking Readings (parking_readings.csv)...")
    
    if df_traffic is None:
        df_traffic = pd.read_csv(RAW_DATA_DIR / "traffic_readings.csv")
        df_traffic["timestamp"] = pd.to_datetime(df_traffic["timestamp"])
        
    zones = [
        ("ZON_PARK_NORTH", "North Parking", 350),
        ("ZON_PARK_SOUTH", "South Parking", 250),
        ("ZON_PARK_VISITOR", "Visitor Parking", 100),
        ("ZON_PARK_HOSTEL", "Hostel Parking", 200)
    ]
    
    # Pre-aggregate Main Gate vehicle counts as parking arrival proxy
    main_gate_df = df_traffic[df_traffic["location_id"] == "Main_Gate"].sort_values(by="timestamp").reset_index(drop=True)
    
    records = []
    
    for zone_id, z_name, total_cap in zones:
        curr_occ = int(total_cap * 0.15)
        
        for row in main_gate_df.itertuples():
            ts = row.timestamp
            hr = ts.hour + ts.minute / 60.0
            dow = ts.dayofweek
            wknd = (dow >= 5)
            v_flow = row.vehicle_count
            
            if "NORTH" in zone_id or "VISITOR" in zone_id:  # Academic & Admin parking
                if wknd:
                    target_ratio = 0.10
                else:
                    if 8.0 <= hr <= 10.5:
                        target_ratio = 0.85
                    elif 10.5 < hr <= 16.5:
                        target_ratio = 0.75
                    elif 16.5 < hr <= 18.5:
                        target_ratio = 0.30
                    else:
                        target_ratio = 0.08
            else:  # Hostel & South parking
                if 0.0 <= hr <= 7.0:
                    target_ratio = 0.80
                elif 7.0 < hr <= 17.0:
                    target_ratio = 0.35 if not wknd else 0.70
                else:
                    target_ratio = 0.85
                    
            target_occ = int(np.round(target_ratio * total_cap + np.random.normal(0, 5)))
            target_occ = max(0, min(total_cap, target_occ))
            
            # Smooth transition
            curr_occ = int(np.round(0.8 * curr_occ + 0.2 * target_occ))
            curr_occ = max(0, min(total_cap, curr_occ))
            
            avail = total_cap - curr_occ
            occ_pct = round((curr_occ / total_cap) * 100.0, 2)
            turnover = round(max(0.1, (v_flow / 50.0) + np.random.normal(0, 0.2)), 2)
            
            if occ_pct >= 90.0:
                status = "FULL"
            elif occ_pct >= 70.0:
                status = "LIMITED"
            else:
                status = "AVAILABLE"
                
            records.append({
                "timestamp": ts,
                "parking_zone_id": zone_id,
                "total_spaces": total_cap,
                "occupied_spaces": curr_occ,
                "occupancy_percent": occ_pct,
                "available_spaces": avail,
                "turnover_rate": turnover,
                "parking_status": status
            })
            
    df_parking = pd.DataFrame(records)
    df_parking.to_csv(RAW_DATA_DIR / "parking_readings.csv", index=False)
    logger.info("Parking readings generated successfully (%d rows).", len(df_parking))
    return df_parking

if __name__ == "__main__":
    generate_parking()
