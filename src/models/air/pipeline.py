"""
Air Quality Module Training Pipeline.
Handles PM2.5 prediction, short-term AQI forecasting, pollution anomaly detection, and hotspot analysis.
"""

import os
import pandas as pd
from src.features.engineering import extract_time_features, prepare_feature_matrix
from src.evaluation.validation import chronological_split
from src.models.selector import ModelSelectionEngine
from src.data.quality import DataQualityChecker

AIR_DISCLAIMER = "Outputs represent environmental decision-support indicators, not official regulatory or health measurements."

def train_air_module(data_path: str = "data/synthetic/air_quality.csv", models_dir: str = "models"):
    if not os.path.exists(data_path):
        from src.data.generator import generate_air_quality_data
        df = generate_air_quality_data(60)
    else:
        df = pd.read_csv(data_path)
        
    checker = DataQualityChecker(df)
    q_res = checker.evaluate_quality_score(numeric_cols=["PM2_5", "PM10", "AQI"])
    print(f"[Air Pipeline] Data Quality Score: {q_res['data_quality_score']} ({q_res['quality_rating']})")
    
    df_feat = extract_time_features(df)
    train_df, val_df, test_df = chronological_split(df_feat, train_ratio=0.7, val_ratio=0.15)
    
    drop_cols = ["timestamp", "facility_id", "location", "is_synthetic", "AQI"]
    X_train, y_train = prepare_feature_matrix(train_df, target_col="PM2_5", drop_cols=drop_cols)
    X_val, y_val = prepare_feature_matrix(val_df, target_col="PM2_5", drop_cols=drop_cols)
    
    engine = ModelSelectionEngine(task_name="air_pm25_prediction", task_type="regression", output_dir=models_dir)
    model, metadata = engine.select_and_save(X_train, y_train, X_val, y_val)
    metadata["disclaimer"] = AIR_DISCLAIMER
    
    return model, metadata, engine.comparison_table

if __name__ == "__main__":
    train_air_module()
