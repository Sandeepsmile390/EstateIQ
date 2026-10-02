"""
Emissions Generator.
Produces 15-minute emissions.csv over 180 days based on electricity, generator diesel, and traffic.
Columns: timestamp, source_type, energy_consumption, emission_factor, estimated_co2_kg, calculation_method.
Uses configurable factors from config/emission_factors.json.
"""

import numpy as np
import pandas as pd
from generator.config import RAW_DATA_DIR, load_json_config, logger

def generate_emissions(df_energy: pd.DataFrame = None, df_traffic: pd.DataFrame = None) -> pd.DataFrame:
    logger.info("Generating 15-minute Emissions Records (emissions.csv)...")
    
    factors_cfg = load_json_config("emission_factors.json")
    factors = factors_cfg["emission_factors"]
    
    grid_factor = factors["grid_electricity_kg_co2_per_kwh"]
    diesel_factor = factors["diesel_generator_kg_co2_per_liter"]
    car_factor = factors["car_transport_kg_co2_per_km"]
    
    if df_energy is None:
        df_energy = pd.read_csv(RAW_DATA_DIR / "energy_readings.csv")
        df_energy["timestamp"] = pd.to_datetime(df_energy["timestamp"])
        
    if df_traffic is None:
        df_traffic = pd.read_csv(RAW_DATA_DIR / "traffic_readings.csv")
        df_traffic["timestamp"] = pd.to_datetime(df_traffic["timestamp"])
        
    # Aggregate campus energy per 15-min timestamp
    energy_agg = df_energy.groupby("timestamp")["grid_import_kwh"].sum().reset_index()
    traffic_agg = df_traffic.groupby("timestamp")["vehicle_count"].sum().reset_index()
    
    df_merged = pd.merge(energy_agg, traffic_agg, on="timestamp", how="inner")
    
    records = []
    
    for row in df_merged.itertuples():
        ts = row.timestamp
        grid_kwh = row.grid_import_kwh
        v_count = row.vehicle_count
        
        # 1. Grid Electricity Emissions
        grid_co2 = round(grid_kwh * grid_factor, 3)
        records.append({
            "timestamp": ts,
            "source_type": "grid_electricity",
            "energy_consumption": round(grid_kwh, 2),
            "emission_factor": grid_factor,
            "estimated_co2_kg": grid_co2,
            "calculation_method": "CEA_Grid_Factor_Factorization"
        })
        
        # 2. Backup Diesel Generator (Occasional grid outage runs ~5% of time)
        diesel_liters = round(np.random.uniform(2.0, 10.0), 2) if np.random.rand() < 0.05 else 0.0
        if diesel_liters > 0:
            dg_co2 = round(diesel_liters * diesel_factor, 3)
            records.append({
                "timestamp": ts,
                "source_type": "diesel_generator",
                "energy_consumption": diesel_liters,
                "emission_factor": diesel_factor,
                "estimated_co2_kg": dg_co2,
                "calculation_method": "Fuel_Volume_Factorization"
            })
            
        # 3. Vehicle Transport Emissions (assuming average 2.5 km campus loop per vehicle)
        v_km = v_count * 2.5
        v_co2 = round(v_km * car_factor, 3)
        records.append({
            "timestamp": ts,
            "source_type": "vehicle_transport",
            "energy_consumption": round(v_km, 2),
            "emission_factor": car_factor,
            "estimated_co2_kg": v_co2,
            "calculation_method": "VMT_Emission_Factorization"
        })
        
    df_emissions = pd.DataFrame(records)
    df_emissions.to_csv(RAW_DATA_DIR / "emissions.csv", index=False)
    logger.info("Emissions records generated successfully (%d rows).", len(df_emissions))
    return df_emissions

if __name__ == "__main__":
    generate_emissions()
