"""
Emissions Module Training Pipeline.
Handles GHG Emission Forecasting and Conversion Factor Modeling.

DOCUMENTED EMISSION CONVERSION FACTORS (CEA India & IPCC Guidelines):
1. Grid Electricity: 0.82 kg CO2e / kWh (Baseline Indian Central Electricity Authority Grid Factor)
2. Diesel Generator Fuel: 2.68 kg CO2e / Liter
3. Fleet Vehicle Travel: 0.14 kg CO2e / vehicle-km
"""

import os
import pandas as pd
from src.features.engineering import extract_time_features, prepare_feature_matrix
from src.evaluation.validation import chronological_split
from src.models.selector import ModelSelectionEngine
from src.data.quality import DataQualityChecker

EMISSIONS_DISCLAIMER = "Emissions are estimated using standard conversion factors (CEA Grid & IPCC). Outputs are not official regulatory carbon audit measurements."

GRID_EMISSION_FACTOR = 0.82    # kg CO2e / kWh
DIESEL_EMISSION_FACTOR = 2.68  # kg CO2e / Liter
VEHICLE_EMISSION_FACTOR = 0.14 # kg CO2e / km

def train_emissions_module(data_path: str = "data/synthetic/emissions.csv", models_dir: str = "models"):
    if not os.path.exists(data_path):
        from src.data.generator import generate_emissions_data
        df = generate_emissions_data(60)
    else:
        df = pd.read_csv(data_path)
        
    checker = DataQualityChecker(df)
    q_res = checker.evaluate_quality_score(numeric_cols=["emission_estimate", "energy_consumption", "fuel_consumption"])
    print(f"[Emissions Pipeline] Data Quality Score: {q_res['data_quality_score']} ({q_res['quality_rating']})")
    
    df_feat = extract_time_features(df)
    train_df, val_df, test_df = chronological_split(df_feat, train_ratio=0.7, val_ratio=0.15)
    
    drop_cols = ["timestamp", "facility_id", "is_synthetic"]
    X_train, y_train = prepare_feature_matrix(train_df, target_col="emission_estimate", drop_cols=drop_cols)
    X_val, y_val = prepare_feature_matrix(val_df, target_col="emission_estimate", drop_cols=drop_cols)
    
    engine = ModelSelectionEngine(task_name="emissions_forecasting", task_type="regression", output_dir=models_dir)
    model, metadata = engine.select_and_save(X_train, y_train, X_val, y_val)
    metadata["conversion_factors"] = {
        "grid_electricity_kg_co2_per_kwh": GRID_EMISSION_FACTOR,
        "diesel_fuel_kg_co2_per_liter": DIESEL_EMISSION_FACTOR,
        "vehicle_kg_co2_per_km": VEHICLE_EMISSION_FACTOR
    }
    metadata["disclaimer"] = EMISSIONS_DISCLAIMER
    
    return model, metadata, engine.comparison_table

if __name__ == "__main__":
    train_emissions_module()
