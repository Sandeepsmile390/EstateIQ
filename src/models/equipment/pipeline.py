"""
Equipment / Asset Utilization Training Pipeline.
Handles predictive maintenance risk indicator classification and equipment utilization rate prediction.
IMPORTANT: Uses non-definitive wording 'maintenance-risk indicator' instead of claiming definite equipment failure.
"""

import os
import pandas as pd
from src.features.engineering import extract_time_features, prepare_feature_matrix
from src.evaluation.validation import chronological_split
from src.models.selector import ModelSelectionEngine
from src.data.quality import DataQualityChecker

EQUIPMENT_DISCLAIMER = "Outputs represent a maintenance-risk indicator to prioritize inspection, not a guarantee of physical failure."

def train_equipment_module(data_path: str = "data/synthetic/equipment.csv", models_dir: str = "models"):
    if not os.path.exists(data_path):
        from src.data.generator import generate_equipment_data
        df = generate_equipment_data(60)
    else:
        df = pd.read_csv(data_path)
        
    checker = DataQualityChecker(df)
    q_res = checker.evaluate_quality_score(numeric_cols=["vibration", "temperature", "power_consumption"])
    print(f"[Equipment Pipeline] Data Quality Score: {q_res['data_quality_score']} ({q_res['quality_rating']})")
    
    # High risk indicator target: high vibration or high temp
    df["maintenance_risk_flag"] = ((df["vibration"] > 3.0) | (df["temperature"] > 70.0)).astype(int)
    
    df_feat = extract_time_features(df)
    train_df, val_df, test_df = chronological_split(df_feat, train_ratio=0.7, val_ratio=0.15)
    
    drop_cols = ["timestamp", "facility_id", "equipment_id", "equipment_type", "is_synthetic"]
    X_train, y_train = prepare_feature_matrix(train_df, target_col="maintenance_risk_flag", drop_cols=drop_cols)
    X_val, y_val = prepare_feature_matrix(val_df, target_col="maintenance_risk_flag", drop_cols=drop_cols)
    
    engine = ModelSelectionEngine(task_name="equipment_maintenance_risk", task_type="classification", output_dir=models_dir)
    model, metadata = engine.select_and_save(X_train, y_train, X_val, y_val)
    metadata["disclaimer"] = EQUIPMENT_DISCLAIMER
    
    return model, metadata, engine.comparison_table

if __name__ == "__main__":
    train_equipment_module()
