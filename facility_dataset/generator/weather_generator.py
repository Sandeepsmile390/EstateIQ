"""
Weather Generator.
Produces 15-minute weather_readings.csv covering Jan-June 2026 (Pune/Western India seasonal trends).
Columns: timestamp, temperature_c, humidity_percent, rainfall_mm, wind_speed_kmph, solar_radiation_w_m2, cloud_cover_percent, pressure_hpa.
"""

import numpy as np
import pandas as pd
from generator.config import RAW_DATA_DIR, get_master_timestamps, logger

def generate_weather() -> pd.DataFrame:
    logger.info("Generating 15-minute Weather Readings (weather_readings.csv)...")
    
    timestamps = get_master_timestamps()
    n = len(timestamps)
    
    # Time factors as numpy arrays
    hours = np.array(timestamps.hour + timestamps.minute / 60.0)
    day_of_year = np.array(timestamps.dayofyear)
    
    # 1. Temperature: Seasonal warming from Jan (22°C avg) to May (36°C avg) + Diurnal cycle
    seasonal_temp_base = 22.0 + (day_of_year / 180.0) * 14.0  # Rises from 22°C to 36°C
    diurnal_temp = 7.5 * np.sin((hours - 8.0) * np.pi / 12.0)  # Peak around 14:00
    temp_noise = np.random.normal(0, 0.8, size=n)
    temperature_c = np.round(np.clip(seasonal_temp_base + diurnal_temp + temp_noise, 12.0, 44.0), 2)
    
    # 2. Solar Radiation: 0 at night (before 06:00 & after 19:00), peaks around noon (~900 W/m2)
    solar_base = np.maximum(0.0, np.sin((hours - 6.0) * np.pi / 13.0))
    # Night mask
    night_mask = (hours < 6.2) | (hours > 18.8)
    solar_base[night_mask] = 0.0
    solar_radiation = np.round(np.maximum(0.0, solar_base * 920.0 + np.random.normal(0, 15.0, size=n)), 2)
    solar_radiation[night_mask] = 0.0
    
    # 3. Cloud Cover: 10-30% Jan-April, 60-90% June Monsoon
    cloud_base = 15.0 + np.maximum(0.0, (day_of_year - 140) / 40.0) * 60.0
    cloud_cover = np.round(np.clip(cloud_base + np.random.normal(0, 8.0, size=n), 0.0, 100.0), 1)
    
    # Cloud attenuation on solar
    solar_radiation = np.round(solar_radiation * (1.0 - cloud_cover / 150.0), 2)
    solar_radiation = np.maximum(0.0, solar_radiation)
    solar_radiation[night_mask] = 0.0
    
    # 4. Humidity: Inverse of temperature + higher in monsoon
    humidity_base = 80.0 - (temperature_c - 20.0) * 2.2 + (cloud_cover * 0.3)
    humidity_percent = np.round(np.clip(humidity_base + np.random.normal(0, 3.0, size=n), 15.0, 98.0), 1)
    
    # 5. Rainfall: Sparse in Jan-May, heavy in June monsoon (Day 155+)
    rainfall = np.zeros(n)
    monsoon_mask = (day_of_year >= 155) & (cloud_cover > 70)
    rain_probability = np.where(monsoon_mask, 0.25, 0.002)
    rain_events = np.random.rand(n) < rain_probability
    rainfall[rain_events] = np.random.exponential(scale=4.5, size=np.sum(rain_events))
    rainfall = np.round(rainfall, 2)
    
    # 6. Wind Speed (km/h) & Pressure (hPa)
    wind_speed = np.round(np.clip(4.0 + (temperature_c / 10.0) + np.random.normal(0, 2.0, size=n), 0.5, 45.0), 1)
    pressure = np.round(1013.25 - (temperature_c * 0.4) + np.random.normal(0, 1.2, size=n), 1)
    
    df_weather = pd.DataFrame({
        "timestamp": timestamps,
        "temperature_c": temperature_c,
        "humidity_percent": humidity_percent,
        "rainfall_mm": rainfall,
        "wind_speed_kmph": wind_speed,
        "solar_radiation_w_m2": solar_radiation,
        "cloud_cover_percent": cloud_cover,
        "pressure_hpa": pressure
    })
    
    df_weather.to_csv(RAW_DATA_DIR / "weather_readings.csv", index=False)
    logger.info("Weather readings generated successfully (%d rows).", len(df_weather))
    return df_weather

if __name__ == "__main__":
    generate_weather()
