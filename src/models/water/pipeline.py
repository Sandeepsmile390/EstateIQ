"""
Water Module Training Pipeline.
Handles Water consumption forecasting and leak-risk detection.
"""

import os
import pandas as pd
from src.features.engineering import extract_time_features, prepare_feature_matrix, add_lag_and_rolling_features
from src.evaluation.validation import chronological_split
from src.models.selector import ModelSelectionEngine
from src.data.quality import DataQualityChecker

DISCLAIMER_TEXT = "Potential abnormal water-use pattern detected. Physical inspection may be required."

def train_water_module(data_path: str = "data/synthetic/water.csv", models_dir: str = "models"):
    if not os.path.exists(data_path):
        from src.data.generator import generate_water_data
        df = generate_water_data(60)
    else:
        df = pd.read_csv(data_path)
        
    checker = DataQualityChecker(df)
    q_res = checker.evaluate_quality_score(numeric_cols=["water_usage_liters", "flow_rate"])
    print(f"[Water Pipeline] Data Quality Score: {q_res['data_quality_score']} ({q_res['quality_rating']})")
    
    df_feat = extract_time_features(df)
    df_feat = add_lag_and_rolling_features(df_feat, group_col="building_id", target_col="water_usage_liters", lags=[1, 24], windows=[3])
    
    train_df, val_df, test_df = chronological_split(df_feat, train_ratio=0.7, val_ratio=0.15)
    
    drop_cols = ["timestamp", "facility_id", "building_id", "is_synthetic"]
    X_train, y_train = prepare_feature_matrix(train_df, target_col="water_usage_liters", drop_cols=drop_cols)
    X_val, y_val = prepare_feature_matrix(val_df, target_col="water_usage_liters", drop_cols=drop_cols)
    
    engine = ModelSelectionEngine(task_name="water_usage_forecasting", task_type="regression", output_dir=models_dir)
    model, metadata = engine.select_and_save(X_train, y_train, X_val, y_val)
    metadata["disclaimer"] = DISCLAIMER_TEXT
    
    return model, metadata, engine.comparison_table

if __name__ == "__main__":
    train_water_module()
