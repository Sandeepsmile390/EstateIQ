"""
Traffic Generator.
Produces 15-minute traffic_readings.csv across 6 campus gate/road locations over 180 days.
Locations: Main Gate, North Gate, South Gate, Academic Road, Hostel Road, Canteen Road.
Columns: timestamp, location_id, vehicle_count, average_speed_kmph, congestion_level,
         heavy_vehicle_count, two_wheeler_count, car_count, bus_count.
"""

import numpy as np
import pandas as pd
from generator.config import RAW_DATA_DIR, load_json_config, logger

def generate_traffic(df_weather: pd.DataFrame = None, df_occupancy: pd.DataFrame = None) -> pd.DataFrame:
    logger.info("Generating 15-minute Traffic Readings (traffic_readings.csv)...")
    
    if df_weather is None:
        df_weather = pd.read_csv(RAW_DATA_DIR / "weather_readings.csv")
        df_weather["timestamp"] = pd.to_datetime(df_weather["timestamp"])
        
    locations = ["Main_Gate", "North_Gate", "South_Gate", "Academic_Road", "Hostel_Road", "Canteen_Road"]
    
    records = []
    
    for row in df_weather.itertuples():
        ts = row.timestamp
        hr = ts.hour + ts.minute / 60.0
        dow = ts.dayofweek
        wknd = (dow >= 5)
        rain = row.rainfall_mm
        
        for loc_id in locations:
            # Base vehicle count per 15-min interval
            if "Main_Gate" in loc_id or "Academic" in loc_id:
                if wknd:
                    v_base = 15.0 if (9.0 <= hr <= 17.0) else 5.0
                else:
                    if 8.0 <= hr <= 10.0:        # Morning Inflow Rush
                        v_base = 110.0
                    elif 16.5 <= hr <= 18.5:    # Evening Outflow Rush
                        v_base = 95.0
                    elif 10.0 < hr < 16.5:
                        v_base = 35.0
                    else:
                        v_base = 8.0
            else:
                v_base = 25.0 if (8.0 <= hr <= 19.0) else 4.0
                
            v_count = int(max(0, np.round(v_base + np.random.normal(0, v_base * 0.15))))
            
            # Fleet mix (Indian Campus: 65% 2-Wheelers, 25% Cars, 5% Buses/Shuttles, 5% Heavy/Utility)
            two_wheelers = int(np.round(v_count * 0.65))
            cars = int(np.round(v_count * 0.25))
            buses = int(np.round(v_count * 0.05))
            heavy = max(0, v_count - (two_wheelers + cars + buses))
            
            # Average speed drops with higher vehicle count and rain
            base_speed = 35.0 if "Road" in loc_id else 20.0
            speed = max(5.0, base_speed - (v_count * 0.15) - (rain * 2.5) + np.random.normal(0, 1.5))
            speed = round(speed, 1)
            
            # Congestion Level mapping: Low, Moderate, High, Severe
            if v_count < 30:
                c_level = "Low"
            elif v_count < 75:
                c_level = "Moderate"
            elif v_count < 110:
                c_level = "High"
            else:
                c_level = "Severe"
                
            records.append({
                "timestamp": ts,
                "location_id": loc_id,
                "vehicle_count": v_count,
                "average_speed_kmph": speed,
                "congestion_level": c_level,
                "heavy_vehicle_count": heavy,
                "two_wheeler_count": two_wheelers,
                "car_count": cars,
                "bus_count": buses
            })
            
    df_traffic = pd.DataFrame(records)
    df_traffic.to_csv(RAW_DATA_DIR / "traffic_readings.csv", index=False)
    logger.info("Traffic readings generated successfully (%d rows).", len(df_traffic))
    return df_traffic

if __name__ == "__main__":
    generate_traffic()
