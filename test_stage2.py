"""
Stage 2 Validation Script: Model Selection Engine Test.
"""

from src.data.generator import generate_energy_data
import pandas as pd
from src.features.engineering import extract_time_features, prepare_feature_matrix
from src.evaluation.validation import chronological_split
from src.models.selector import ModelSelectionEngine

def test_energy_selection():
    df = generate_energy_data(num_days=30)
    df_feat = extract_time_features(df)
    
    train_df, val_df, test_df = chronological_split(df_feat, train_ratio=0.7, val_ratio=0.15)
    
    X_train, y_train = prepare_feature_matrix(train_df, target_col="energy_kwh", drop_cols=["timestamp", "facility_id", "building_id", "is_synthetic"])
    X_val, y_val = prepare_feature_matrix(val_df, target_col="energy_kwh", drop_cols=["timestamp", "facility_id", "building_id", "is_synthetic"])
    
    engine = ModelSelectionEngine(task_name="energy_consumption", task_type="regression")
    model, metadata = engine.select_and_save(X_train, y_train, X_val, y_val)
    
    print("\n--- Model Selection Comparison Table ---")
    df_comp = pd.DataFrame([r[1] for r in engine.comparison_table])
    print(df_comp.to_string(index=False))
    print("\n--- Final Selected Model Metadata ---")
    print("Selected Model:", metadata["selected_model"])
    print("Validation Metrics:", metadata["val_metrics"])
    print("Error Analysis:", metadata["error_analysis"])

if __name__ == "__main__":
    import pandas as pd
    test_energy_selection()
