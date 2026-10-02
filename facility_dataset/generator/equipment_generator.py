"""
Equipment / Asset Generator.
Produces 15-minute equipment_sensor_readings.csv for 35 campus assets over 180 days.
Produces maintenance_events.csv recording scheduled & corrective servicing.
Columns: timestamp, asset_id, temperature_c, vibration_mm_s, pressure_bar, current_amp, voltage_v,
         operating_hours, load_percent, efficiency_percent, maintenance_required, maintenance_risk_score.
"""

import numpy as np
import pandas as pd
from generator.config import RAW_DATA_DIR, get_master_timestamps, logger

def generate_equipment() -> pd.DataFrame:
    logger.info("Generating 15-minute Equipment Sensor Readings (equipment_sensor_readings.csv)...")
    
    df_assets = pd.read_csv(RAW_DATA_DIR / "assets.csv")
    timestamps = get_master_timestamps()
    n_ts = len(timestamps)
    
    all_readings = []
    maint_events = []
    
    for asset in df_assets.itertuples():
        ast_id = asset.asset_id
        category = asset.category
        rated_power = asset.rated_power_kw
        
        runtime_accum = float((2026 - asset.installation_year) * 1200.0)
        
        temp_base = 45.0 if "Chiller" in category else (55.0 if "Transformer" in category else 40.0)
        vib_base = 1.1 if "Pump" in category else 0.8
        
        for t_idx in range(n_ts):
            ts = timestamps[t_idx]
            hr = ts.hour + ts.minute / 60.0
            
            # Asset load pattern
            if 7.0 <= hr <= 20.0:
                load_pct = np.clip(0.65 + np.random.normal(0, 0.15), 0.20, 0.95)
                runtime_accum += 0.25
            else:
                load_pct = np.clip(0.15 + np.random.normal(0, 0.05), 0.05, 0.30)
                runtime_accum += 0.05
                
            # Physical Wear Effect based on accumulated runtime hours
            wear_factor = (runtime_accum % 2000.0) / 2000.0  # Resets every 2000 hours after service
            
            # Sensor physics
            temp = temp_base + (load_pct * 30.0) + (wear_factor * 12.0) + np.random.normal(0, 1.2)
            vib = vib_base + (load_pct * 1.8) + (wear_factor * 2.2) + np.random.normal(0, 0.15)
            pressure = 4.5 + (load_pct * 2.0) + np.random.normal(0, 0.1)
            
            voltage = 415.0 + np.random.normal(0, 3.5)  # 3-Phase 415V Indian grid standard
            current = (load_pct * rated_power * 1000.0) / (1.732 * voltage * 0.88)
            current = max(0.5, current + np.random.normal(0, 0.5))
            
            eff_pct = max(50.0, min(98.0, 92.0 - (wear_factor * 15.0) - (load_pct * 5.0) + np.random.normal(0, 0.5)))
            
            # Risk score (0.0 to 1.0)
            risk_score = min(1.0, max(0.0, (wear_factor * 0.6) + ((vib - vib_base) / 4.0) * 0.4))
            risk_score = round(risk_score, 4)
            maint_req = 1 if risk_score >= 0.75 else 0
            
            # Service event trigger
            if maint_req and np.random.rand() < 0.02:
                maint_events.append({
                    "event_id": f"MNT_{ast_id}_{t_idx}",
                    "timestamp": ts,
                    "asset_id": ast_id,
                    "maintenance_type": "PREDICTIVE_SERVICING",
                    "description": f"Serviced {asset.asset_name} due to elevated vibration ({round(vib,2)} mm/s) & risk score ({risk_score})"
                })
                runtime_accum = max(100.0, runtime_accum - 1800.0)  # Reset wear
                
            all_readings.append({
                "timestamp": ts,
                "asset_id": ast_id,
                "temperature_c": round(temp, 2),
                "vibration_mm_s": round(vib, 2),
                "pressure_bar": round(pressure, 2),
                "current_amp": round(current, 2),
                "voltage_v": round(voltage, 2),
                "operating_hours": round(runtime_accum, 1),
                "load_percent": round(load_pct * 100.0, 1),
                "efficiency_percent": round(eff_pct, 1),
                "maintenance_required": maint_req,
                "maintenance_risk_score": risk_score
            })
            
    df_readings = pd.DataFrame(all_readings)
    df_readings.to_csv(RAW_DATA_DIR / "equipment_sensor_readings.csv", index=False)
    
    df_maint = pd.DataFrame(maint_events)
    df_maint.to_csv(RAW_DATA_DIR / "maintenance_events.csv", index=False)
    
    logger.info("Equipment sensor readings generated successfully (%d rows, %d maintenance events).", len(df_readings), len(df_maint))
    return df_readings

if __name__ == "__main__":
    generate_equipment()
