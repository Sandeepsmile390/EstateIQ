"""
Energy Module Training Pipeline.
Handles Energy consumption prediction, short-term forecasting, and efficiency analysis.
"""

import os
import pandas as pd
from src.features.engineering import extract_time_features, prepare_feature_matrix, add_lag_and_rolling_features
from src.evaluation.validation import chronological_split
from src.models.selector import ModelSelectionEngine
from src.data.quality import DataQualityChecker

def train_energy_module(data_path: str = "data/synthetic/energy.csv", models_dir: str = "models"):
    """Runs complete end-to-end training and model selection for Energy module."""
    if not os.path.exists(data_path):
        from src.data.generator import generate_energy_data
        df = generate_energy_data(60)
    else:
        df = pd.read_csv(data_path)
        
    # Data Quality Validation
    checker = DataQualityChecker(df)
    q_res = checker.evaluate_quality_score(numeric_cols=["energy_kwh", "temperature", "hvac_load"])
    print(f"[Energy Pipeline] Data Quality Score: {q_res['data_quality_score']} ({q_res['quality_rating']})")
    
    # Feature Engineering
    df_feat = extract_time_features(df)
    df_feat = add_lag_and_rolling_features(df_feat, group_col="building_id", target_col="energy_kwh", lags=[1, 24], windows=[6])
    
    # Split
    train_df, val_df, test_df = chronological_split(df_feat, train_ratio=0.7, val_ratio=0.15)
    
    drop_cols = ["timestamp", "facility_id", "building_id", "is_synthetic"]
    X_train, y_train = prepare_feature_matrix(train_df, target_col="energy_kwh", drop_cols=drop_cols)
    X_val, y_val = prepare_feature_matrix(val_df, target_col="energy_kwh", drop_cols=drop_cols)
    
    # Execute Model Selection Engine
    engine = ModelSelectionEngine(task_name="energy_kwh_prediction", task_type="regression", output_dir=models_dir)
    model, metadata = engine.select_and_save(X_train, y_train, X_val, y_val)
    
    return model, metadata, engine.comparison_table

if __name__ == "__main__":
    train_energy_module()
