"""
Waste Management Module Training Pipeline.
Predicts bin overflow within the next 2 hours using candidate classifiers (Logistic Regression, RF, XGBoost, LightGBM, CatBoost).
Outputs overflow_probability and risk_level (LOW, MEDIUM, HIGH).
"""

import os
import pandas as pd
import numpy as np
from src.features.engineering import extract_time_features, prepare_feature_matrix
from src.evaluation.validation import chronological_split
from src.models.selector import ModelSelectionEngine
from src.data.quality import DataQualityChecker

def categorize_waste_risk(probability: float) -> str:
    """Categorizes raw prediction probability into non-definitive risk levels."""
    if probability < 0.35:
        return "LOW"
    elif probability < 0.70:
        return "MEDIUM"
    else:
        return "HIGH"

def train_waste_module(data_path: str = "data/synthetic/waste.csv", models_dir: str = "models"):
    if not os.path.exists(data_path):
        from src.data.generator import generate_waste_data
        df = generate_waste_data(60)
    else:
        df = pd.read_csv(data_path)
        
    checker = DataQualityChecker(df)
    q_res = checker.evaluate_quality_score(numeric_cols=["fill_level", "fill_rate"])
    print(f"[Waste Pipeline] Data Quality Score: {q_res['data_quality_score']} ({q_res['quality_rating']})")
    
    df_feat = extract_time_features(df)
    train_df, val_df, test_df = chronological_split(df_feat, train_ratio=0.7, val_ratio=0.15)
    
    drop_cols = ["timestamp", "facility_id", "bin_id", "location", "is_synthetic"]
    X_train, y_train = prepare_feature_matrix(train_df, target_col="overflow", drop_cols=drop_cols)
    X_val, y_val = prepare_feature_matrix(val_df, target_col="overflow", drop_cols=drop_cols)
    
    engine = ModelSelectionEngine(task_name="waste_overflow_2hr", task_type="classification", output_dir=models_dir)
    model, metadata = engine.select_and_save(X_train, y_train, X_val, y_val)
    
    return model, metadata, engine.comparison_table

if __name__ == "__main__":
    train_waste_module()
