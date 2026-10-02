"""
Air Quality Generator.
Produces 15-minute air_quality_readings.csv across 7 campus locations over 180 days.
Columns: timestamp, location_id, pm25, pm10, no2, so2, co, o3, aqi, temperature_c, humidity_percent, wind_speed_kmph, air_quality_category.
Correlated with local traffic, wind speed, rainfall, and ambient weather.
"""

import numpy as np
import pandas as pd
from generator.config import RAW_DATA_DIR, load_json_config, logger

def calculate_cpcb_aqi(pm25: float) -> tuple:
    """Calculates Indian CPCB AQI sub-index proxy for PM2.5 and maps category."""
    if pm25 <= 30:
        aqi = pm25 * (50 / 30)
        cat = "Good"
    elif pm25 <= 60:
        aqi = 50 + (pm25 - 30) * (50 / 30)
        cat = "Satisfactory"
    elif pm25 <= 90:
        aqi = 100 + (pm25 - 60) * (100 / 30)
        cat = "Moderate"
    elif pm25 <= 120:
        aqi = 200 + (pm25 - 90) * (100 / 30)
        cat = "Poor"
    elif pm25 <= 250:
        aqi = 300 + (pm25 - 120) * (100 / 130)
        cat = "Very Poor"
    else:
        aqi = 400 + (pm25 - 250) * (100 / 130)
        cat = "Severe"
    return round(aqi, 1), cat

def generate_air_quality(df_weather: pd.DataFrame = None) -> pd.DataFrame:
    logger.info("Generating 15-minute Air Quality Readings (air_quality_readings.csv)...")
    
    if df_weather is None:
        df_weather = pd.read_csv(RAW_DATA_DIR / "weather_readings.csv")
        df_weather["timestamp"] = pd.to_datetime(df_weather["timestamp"])
        
    cfg = load_json_config("facility_config.json")
    locations = cfg["locations"]
    
    records = []
    
    for row in df_weather.itertuples():
        hr = row.timestamp.hour + row.timestamp.minute / 60.0
        wind = row.wind_speed_kmph
        rain = row.rainfall_mm
        temp = row.temperature_c
        hum = row.humidity_percent
        
        # Traffic rush hour multiplier (08:00-10:00 & 16:30-18:30)
        is_rush = (8.0 <= hr <= 10.0) or (16.5 <= hr <= 18.5)
        traffic_factor = 1.6 if is_rush else 0.8
        
        for loc in locations:
            loc_id = loc["location_id"]
            
            # Locations near gate/parking have higher vehicle emissions
            if "GATE" in loc_id or "PARK" in loc_id:
                loc_mult = 1.4
            elif "ACADEMIC" in loc_id:
                loc_mult = 1.0
            else:
                loc_mult = 0.7
                
            # PM2.5 calculation formula with wind dispersion & rain wash-out
            base_pm25 = 35.0 * loc_mult * traffic_factor - (wind * 0.8) - (rain * 4.0) + np.random.normal(0, 3.0)
            pm25 = round(max(5.0, min(350.0, base_pm25)), 2)
            pm10 = round(max(pm25 * 1.3, pm25 * 1.65 + np.random.normal(0, 2.0)), 2)
            
            no2 = round(max(2.0, 15.0 * loc_mult * traffic_factor + np.random.normal(0, 1.5)), 2)
            so2 = round(max(1.0, 8.0 * loc_mult + np.random.normal(0, 1.0)), 2)
            co = round(max(0.1, 0.6 * loc_mult * traffic_factor + np.random.normal(0, 0.05)), 2)
            o3 = round(max(5.0, 25.0 + (temp * 0.4) - (wind * 0.3) + np.random.normal(0, 2.0)), 2)
            
            aqi_val, cat = calculate_cpcb_aqi(pm25)
            
            records.append({
                "timestamp": row.timestamp,
                "location_id": loc_id,
                "pm25": pm25,
                "pm10": pm10,
                "no2": no2,
                "so2": so2,
                "co": co,
                "o3": o3,
                "aqi": aqi_val,
                "temperature_c": temp,
                "humidity_percent": hum,
                "wind_speed_kmph": wind,
                "air_quality_category": cat
            })
            
    df_air = pd.DataFrame(records)
    df_air.to_csv(RAW_DATA_DIR / "air_quality_readings.csv", index=False)
    logger.info("Air Quality readings generated successfully (%d rows).", len(df_air))
    return df_air

if __name__ == "__main__":
    generate_air_quality()
