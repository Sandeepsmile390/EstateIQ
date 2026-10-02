"""
Basic Model Monitoring Module.
Tracks prediction distribution, detects input feature drift against training baselines, and flags retraining requirements.
"""

from typing import Dict, Any, List
import numpy as np
import pandas as pd

class ModelMonitor:
    def __init__(self, baseline_means: Dict[str, float], baseline_stds: Dict[str, float]):
        self.baseline_means = baseline_means
        self.baseline_stds = baseline_stds

    def evaluate_input_drift(self, current_df: pd.DataFrame, threshold_std_shift: float = 2.0) -> Dict[str, Any]:
        """Detects if incoming feature means shift by more than N standard deviations from baseline."""
        drifted_features = []
        feature_shifts = {}
        
        for col, base_mean in self.baseline_means.items():
            if col in current_df.columns:
                curr_mean = float(current_df[col].mean())
                base_std = self.baseline_stds.get(col, 1.0)
                shift = abs(curr_mean - base_mean) / (base_std + 1e-5)
                feature_shifts[col] = round(shift, 2)
                if shift >= threshold_std_shift:
                    drifted_features.append(col)
                    
        retrain_recommended = len(drifted_features) > 0
        
        return {
            "retrain_recommended": retrain_recommended,
            "drifted_features_count": len(drifted_features),
            "drifted_features": drifted_features,
            "std_shifts": feature_shifts,
            "alert": "WARNING: Feature drift detected. Model retraining recommended." if retrain_recommended else "Input distributions within normal bounds."
        }
