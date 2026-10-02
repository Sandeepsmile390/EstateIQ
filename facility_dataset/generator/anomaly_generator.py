"""
Anomaly Generator.
Reads config/anomalies.json scenarios and injects realistic anomalies into generated datasets.
Appends anomaly_flag (0 or 1) and anomaly_type (e.g., 'hvac_fault', 'power_spike', 'after_hours_usage') columns.

CRITICAL MANDATE: Ground truth anomaly labels exist ONLY for evaluation and must NEVER be used as model input features.
"""

import numpy as np
import pandas as pd
from generator.config import RAW_DATA_DIR, load_json_config, logger

def inject_anomalies():
    logger.info("Injecting Realistic Anomaly Scenarios & Ground-Truth Labels...")
    
    anom_cfg = load_json_config("anomalies.json")
    scenarios = anom_cfg.get("scenarios", [])
    
    # 1. Energy Anomalies
    energy_path = RAW_DATA_DIR / "energy_readings.csv"
    if energy_path.exists():
        df_e = pd.read_csv(energy_path)
        df_e["timestamp"] = pd.to_datetime(df_e["timestamp"])
        df_e["anomaly_flag"] = 0
        df_e["anomaly_type"] = "normal"
        
        for sc in scenarios:
            if sc["module"] == "energy":
                bld = sc["affected_entity"]
                t_start = pd.to_datetime(sc["start_time"]).tz_localize("Asia/Kolkata")
                t_end = t_start + pd.Timedelta(hours=sc["duration_hours"])
                mult = sc["multiplier"]
                anom_name = sc["anomaly_type"]
                
                mask = (df_e["building_id"] == bld) & (df_e["timestamp"] >= t_start) & (df_e["timestamp"] <= t_end)
                df_e.loc[mask, "electricity_kwh"] = np.round(df_e.loc[mask, "electricity_kwh"] * mult, 2)
                df_e.loc[mask, "hvac_kwh"] = np.round(df_e.loc[mask, "hvac_kwh"] * mult, 2)
                df_e.loc[mask, "anomaly_flag"] = 1
                df_e.loc[mask, "anomaly_type"] = anom_name
                
        df_e.to_csv(energy_path, index=False)
        logger.info("Energy anomalies injected successfully.")
        
    # 2. Water Anomalies
    water_path = RAW_DATA_DIR / "water_readings.csv"
    if water_path.exists():
        df_w = pd.read_csv(water_path)
        df_w["timestamp"] = pd.to_datetime(df_w["timestamp"])
        df_w["anomaly_flag"] = 0
        df_w["anomaly_type"] = "normal"
        
        for sc in scenarios:
            if sc["module"] == "water":
                bld = sc["affected_entity"]
                t_start = pd.to_datetime(sc["start_time"]).tz_localize("Asia/Kolkata")
                t_end = t_start + pd.Timedelta(hours=sc["duration_hours"])
                mult = sc["multiplier"]
                
                mask = (df_w["building_id"] == bld) & (df_w["timestamp"] >= t_start) & (df_w["timestamp"] <= t_end)
                df_w.loc[mask, "water_consumption_liters"] = np.round(df_w.loc[mask, "water_consumption_liters"] * mult, 2)
                df_w.loc[mask, "water_flow_rate_lpm"] = np.round(df_w.loc[mask, "water_flow_rate_lpm"] * mult, 2)
                df_w.loc[mask, "anomaly_flag"] = 1
                df_w.loc[mask, "anomaly_type"] = "possible_abnormal_consumption"
                
        df_w.to_csv(water_path, index=False)
        logger.info("Water anomalies injected successfully.")
        
    # 3. Equipment Anomalies
    eq_path = RAW_DATA_DIR / "equipment_sensor_readings.csv"
    if eq_path.exists():
        df_eq = pd.read_csv(eq_path)
        df_eq["timestamp"] = pd.to_datetime(df_eq["timestamp"])
        df_eq["anomaly_flag"] = 0
        df_eq["anomaly_type"] = "normal"
        
        for sc in scenarios:
            if sc["module"] == "equipment":
                ast = sc["affected_entity"]
                t_start = pd.to_datetime(sc["start_time"]).tz_localize("Asia/Kolkata")
                t_end = t_start + pd.Timedelta(hours=sc["duration_hours"])
                mult = sc["multiplier"]
                
                mask = (df_eq["asset_id"] == ast) & (df_eq["timestamp"] >= t_start) & (df_eq["timestamp"] <= t_end)
                df_eq.loc[mask, "vibration_mm_s"] = np.round(df_eq.loc[mask, "vibration_mm_s"] * mult, 2)
                df_eq.loc[mask, "temperature_c"] = np.round(df_eq.loc[mask, "temperature_c"] + 25.0, 2)
                df_eq.loc[mask, "anomaly_flag"] = 1
                df_eq.loc[mask, "anomaly_type"] = sc["anomaly_type"]
                
        df_eq.to_csv(eq_path, index=False)
        logger.info("Equipment anomalies injected successfully.")

if __name__ == "__main__":
    inject_anomalies()
