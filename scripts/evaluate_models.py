"""
Model Evaluation Script.
Usage:
    python scripts/evaluate_models.py
"""

import sys
import os
import joblib
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

def evaluate_registered_models():
    models_dir = BASE_DIR / "models"
    if not models_dir.exists():
        print("Error: models directory does not exist. Run python scripts/train_models.py first.")
        return

    files = [f for f in os.listdir(models_dir) if f.endswith("_metadata.joblib")]
    if not files:
        print("No trained model metadata files found in models/.")
        return

    print("==================================================")
    print("   SUSTAINABLE FACILITY ML MODEL EVALUATION AUDIT")
    print("==================================================\n")

    records = []
    for f in files:
        meta = joblib.load(models_dir / f)
        metrics = meta.get("val_metrics", {})
        records.append({
            "Task": meta["task"],
            "Winning Algorithm": meta["selected_model"],
            "MAE": metrics.get("MAE", "N/A"),
            "RMSE": metrics.get("RMSE", "N/A"),
            "R2 / F1": metrics.get("R2", metrics.get("F1", "N/A")),
            "Precision": metrics.get("Precision", "N/A"),
            "Recall": metrics.get("Recall", "N/A")
        })

    df = pd.DataFrame(records)
    print(df.to_string(index=False))
    
    reports_dir = BASE_DIR / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    csv_path = reports_dir / "model_metrics.csv"
    json_path = reports_dir / "model_metrics.json"
    
    df.to_csv(csv_path, index=False)
    df.to_json(json_path, orient="records", indent=2)
    print(f"\nSaved metrics report to:\n - {csv_path}\n - {json_path}")
    print("Evaluation audit complete.")

if __name__ == "__main__":
    evaluate_registered_models()
