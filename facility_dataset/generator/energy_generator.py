"""
Energy Generator.
Produces 15-minute energy_readings.csv for all 10 buildings over 180 days.
Columns: timestamp, building_id, electricity_kwh, hvac_kwh, lighting_kwh, equipment_kwh, other_kwh,
         peak_load_kw, power_factor, renewable_generation_kwh, grid_import_kwh, energy_intensity_kwh_per_sqft.

Domain Physics Formula:
  electricity_kwh = base_load + occupancy_effect + hvac_effect(temp) + lighting_effect + equipment_effect + noise
"""

import numpy as np
import pandas as pd
from generator.config import RAW_DATA_DIR, load_json_config, logger

def generate_energy(df_weather: pd.DataFrame = None, df_occupancy: pd.DataFrame = None) -> pd.DataFrame:
    logger.info("Generating 15-minute Energy Readings (energy_readings.csv)...")
    
    if df_weather is None:
        df_weather = pd.read_csv(RAW_DATA_DIR / "weather_readings.csv")
        df_weather["timestamp"] = pd.to_datetime(df_weather["timestamp"])
        
    if df_occupancy is None:
        df_occupancy = pd.read_csv(RAW_DATA_DIR / "occupancy_readings.csv")
        df_occupancy["timestamp"] = pd.to_datetime(df_occupancy["timestamp"])
        
    cfg = load_json_config("facility_config.json")
    bld_map = {b["building_id"]: b for b in cfg["buildings"]}
    
    # Merge weather and occupancy to enforce domain physics relations
    df_merged = pd.merge(df_occupancy, df_weather, on="timestamp", how="left")
    
    records = []
    
    for row in df_merged.itertuples():
        bld_info = bld_map[row.building_id]
        area = bld_info["area_sqft"]
        hvac_type = bld_info["hvac_type"]
        
        occ = row.occupancy_count
        temp = row.temperature_c
        solar = row.solar_radiation_w_m2
        hr = row.timestamp.hour + row.timestamp.minute / 60.0
        
        # 1. Sub-meter calculation (kW for 15-min interval -> kWh = kW * 0.25)
        base_load_kw = (area / 1000.0) * 0.4  # Base standby power
        
        # HVAC load depends strongly on temperature above 22°C and occupancy
        hvac_mult = 1.6 if "Chiller" in hvac_type else (1.2 if "VRF" in hvac_type else 0.4)
        hvac_kw = max(0.5, (max(0.0, temp - 20.0) * 1.8 * hvac_mult + occ * 0.08))
        if hvac_type == "Natural_Ventilation":
            hvac_kw = 0.5 + occ * 0.01  # Ceiling fans only
            
        # Lighting load depends on time of day & inverse of solar
        lighting_kw = max(0.2, (area / 1000.0) * (0.8 if (hr < 7 or hr > 18) else 0.2) + occ * 0.03)
        
        # Equipment load depends on building type & occupancy
        equip_kw = max(0.5, (area / 1000.0) * 0.5 + occ * 0.12)
        other_kw = base_load_kw + np.random.normal(0.5, 0.1)
        
        # Total kW load
        total_kw = hvac_kw + lighting_kw + equip_kw + other_kw + np.random.normal(0, 1.0)
        total_kw = max(2.0, total_kw)
        
        # Convert to 15-min kWh (kW * 0.25 hours)
        electricity_kwh = round(total_kw * 0.25, 3)
        hvac_kwh = round(hvac_kw * 0.25, 3)
        lighting_kwh = round(lighting_kw * 0.25, 3)
        equipment_kwh = round(equip_kw * 0.25, 3)
        other_kwh = round(other_kw * 0.25, 3)
        
        peak_load_kw = round(total_kw * np.random.uniform(1.05, 1.15), 2)
        power_factor = round(np.clip(0.95 - (hvac_kw / (total_kw + 1e-5)) * 0.08 + np.random.normal(0, 0.01), 0.85, 0.99), 3)
        
        # Rooftop Solar Generation on Academic A and CSE Block
        if row.building_id in ["BLD001", "BLD003"]:
            renewable_gen_kwh = round((solar / 1000.0) * 40.0 * 0.25, 3)  # 40 kW solar array
        else:
            renewable_gen_kwh = 0.0
            
        grid_import_kwh = round(max(0.0, electricity_kwh - renewable_gen_kwh), 3)
        intensity_kwh_per_sqft = round(electricity_kwh / area, 6)
        
        records.append({
            "timestamp": row.timestamp,
            "building_id": row.building_id,
            "electricity_kwh": electricity_kwh,
            "hvac_kwh": hvac_kwh,
            "lighting_kwh": lighting_kwh,
            "equipment_kwh": equipment_kwh,
            "other_kwh": other_kwh,
            "peak_load_kw": peak_load_kw,
            "power_factor": power_factor,
            "renewable_generation_kwh": renewable_gen_kwh,
            "grid_import_kwh": grid_import_kwh,
            "energy_intensity_kwh_per_sqft": intensity_kwh_per_sqft
        })
        
    df_energy = pd.DataFrame(records)
    df_energy.to_csv(RAW_DATA_DIR / "energy_readings.csv", index=False)
    logger.info("Energy readings generated successfully (%d rows).", len(df_energy))
    return df_energy

if __name__ == "__main__":
    generate_energy()
