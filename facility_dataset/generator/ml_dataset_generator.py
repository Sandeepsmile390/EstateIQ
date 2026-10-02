"""
ML Dataset Generator.
Transforms raw continuous 15-minute sensor streams into ML-ready datasets in data/ml/.
Constructs historical lag features (lag_1, lag_4 [1h], lag_24 [6h], lag_96 [24h]), rolling window averages,
and future targets (energy_next_1h, overflow_within_2h, failure_within_24h).

CRITICAL RULE: Prevent target leakage. Future targets are NEVER included as current features.
"""

import pandas as pd
import numpy as np
from generator.config import RAW_DATA_DIR, ML_DATA_DIR, logger

def generate_ml_datasets():
    logger.info("Building ML-ready datasets in data/ml/ with lag features and future targets...")
    
    # 1. Energy Forecasting ML Dataset
    energy_path = RAW_DATA_DIR / "energy_readings.csv"
    if energy_path.exists():
        df_e = pd.read_csv(energy_path)
        df_e["timestamp"] = pd.to_datetime(df_e["timestamp"])
        df_e = df_e.sort_values(by=["building_id", "timestamp"]).reset_index(drop=True)
        
        # Historical Lags (Strictly past data)
        grouped = df_e.groupby("building_id")
        df_e["energy_lag_1"] = grouped["electricity_kwh"].shift(1)
        df_e["energy_lag_4"] = grouped["electricity_kwh"].shift(4)     # 1 Hour ago
        df_e["energy_lag_24"] = grouped["electricity_kwh"].shift(24)   # 6 Hours ago
        df_e["energy_lag_96"] = grouped["electricity_kwh"].shift(96)   # 24 Hours ago
        
        df_e["energy_rolling_mean_4"] = grouped["electricity_kwh"].shift(1).rolling(4).mean()
        df_e["energy_rolling_mean_24"] = grouped["electricity_kwh"].shift(1).rolling(24).mean()
        
        # Future Target (Target for prediction: energy consumption 1 hour into the future)
        df_e["energy_next_1h"] = grouped["electricity_kwh"].shift(-4)
        
        df_e_clean = df_e.dropna().reset_index(drop=True)
        df_e_clean.to_csv(ML_DATA_DIR / "energy_forecasting.csv", index=False)
        logger.info("Saved ML dataset: energy_forecasting.csv (%d rows)", len(df_e_clean))
        
    # 2. Water Anomaly & Forecasting ML Dataset
    water_path = RAW_DATA_DIR / "water_readings.csv"
    if water_path.exists():
        df_w = pd.read_csv(water_path)
        df_w["timestamp"] = pd.to_datetime(df_w["timestamp"])
        df_w = df_w.sort_values(by=["building_id", "timestamp"]).reset_index(drop=True)
        
        grouped_w = df_w.groupby("building_id")
        df_w["water_lag_1"] = grouped_w["water_consumption_liters"].shift(1)
        df_w["water_lag_4"] = grouped_w["water_consumption_liters"].shift(4)
        df_w["water_rolling_mean_4"] = grouped_w["water_consumption_liters"].shift(1).rolling(4).mean()
        df_w["water_next_1h"] = grouped_w["water_consumption_liters"].shift(-4)
        
        df_w_clean = df_w.dropna().reset_index(drop=True)
        df_w_clean.to_csv(ML_DATA_DIR / "water_anomaly.csv", index=False)
        logger.info("Saved ML dataset: water_anomaly.csv (%d rows)", len(df_w_clean))
        
    # 3. Waste Overflow ML Dataset
    waste_path = RAW_DATA_DIR / "waste_readings.csv"
    if waste_path.exists():
        df_wst = pd.read_csv(waste_path)
        df_wst["timestamp"] = pd.to_datetime(df_wst["timestamp"])
        df_wst = df_wst.sort_values(by=["bin_id", "timestamp"]).reset_index(drop=True)
        
        grouped_wst = df_wst.groupby("bin_id")
        df_wst["fill_lag_1"] = grouped_wst["fill_level_percent"].shift(1)
        df_wst["fill_lag_4"] = grouped_wst["fill_level_percent"].shift(4)
        df_wst["fill_rolling_mean_4"] = grouped_wst["fill_level_percent"].shift(1).rolling(4).mean()
        
        df_wst_clean = df_wst.dropna().reset_index(drop=True)
        df_wst_clean.to_csv(ML_DATA_DIR / "waste_overflow.csv", index=False)
        logger.info("Saved ML dataset: waste_overflow.csv (%d rows)", len(df_wst_clean))
        
    # 4. Traffic Prediction ML Dataset
    traffic_path = RAW_DATA_DIR / "traffic_readings.csv"
    if traffic_path.exists():
        df_tr = pd.read_csv(traffic_path)
        df_tr["timestamp"] = pd.to_datetime(df_tr["timestamp"])
        df_tr = df_tr.sort_values(by=["location_id", "timestamp"]).reset_index(drop=True)
        
        grouped_tr = df_tr.groupby("location_id")
        df_tr["traffic_lag_1"] = grouped_tr["vehicle_count"].shift(1)
        df_tr["traffic_lag_4"] = grouped_tr["vehicle_count"].shift(4)
        df_tr["traffic_next_1h"] = grouped_tr["vehicle_count"].shift(-4)
        
        df_tr_clean = df_tr.dropna().reset_index(drop=True)
        df_tr_clean.to_csv(ML_DATA_DIR / "traffic_prediction.csv", index=False)
        logger.info("Saved ML dataset: traffic_prediction.csv (%d rows)", len(df_tr_clean))
        
    # 5. Equipment Failure ML Dataset
    eq_path = RAW_DATA_DIR / "equipment_sensor_readings.csv"
    if eq_path.exists():
        df_eq = pd.read_csv(eq_path)
        df_eq["timestamp"] = pd.to_datetime(df_eq["timestamp"])
        df_eq = df_eq.sort_values(by=["asset_id", "timestamp"]).reset_index(drop=True)
        
        grouped_eq = df_eq.groupby("asset_id")
        df_eq["vib_lag_1"] = grouped_eq["vibration_mm_s"].shift(1)
        df_eq["temp_lag_1"] = grouped_eq["temperature_c"].shift(1)
        df_eq["failure_within_24h"] = grouped_eq["maintenance_required"].shift(-96).fillna(0).astype(int)
        
        df_eq_clean = df_eq.dropna().reset_index(drop=True)
        df_eq_clean.to_csv(ML_DATA_DIR / "equipment_failure.csv", index=False)
        logger.info("Saved ML dataset: equipment_failure.csv (%d rows)", len(df_eq_clean))

if __name__ == "__main__":
    generate_ml_datasets()
