"""
Parking Module Training Pipeline.
Handles Parking Occupancy Forecasting and Peak-Period Prediction.
"""

import os
import pandas as pd
from src.features.engineering import extract_time_features, prepare_feature_matrix
from src.evaluation.validation import chronological_split
from src.models.selector import ModelSelectionEngine
from src.data.quality import DataQualityChecker

def train_parking_module(data_path: str = "data/synthetic/parking.csv", models_dir: str = "models"):
    if not os.path.exists(data_path):
        from src.data.generator import generate_parking_data
        df = generate_parking_data(60)
    else:
        df = pd.read_csv(data_path)
        
    checker = DataQualityChecker(df)
    q_res = checker.evaluate_quality_score(numeric_cols=["occupancy_rate", "occupied_spaces"])
    print(f"[Parking Pipeline] Data Quality Score: {q_res['data_quality_score']} ({q_res['quality_rating']})")
    
    df_feat = extract_time_features(df)
    train_df, val_df, test_df = chronological_split(df_feat, train_ratio=0.7, val_ratio=0.15)
    
    drop_cols = ["timestamp", "parking_zone", "is_synthetic", "occupied_spaces"]
    X_train, y_train = prepare_feature_matrix(train_df, target_col="occupancy_rate", drop_cols=drop_cols)
    X_val, y_val = prepare_feature_matrix(val_df, target_col="occupancy_rate", drop_cols=drop_cols)
    
    engine = ModelSelectionEngine(task_name="parking_occupancy_forecasting", task_type="regression", output_dir=models_dir)
    model, metadata = engine.select_and_save(X_train, y_train, X_val, y_val)
    
    return model, metadata, engine.comparison_table

if __name__ == "__main__":
    train_parking_module()
