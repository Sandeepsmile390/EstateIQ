"""
Anomaly Detection Module for Sustainable Facility Engine.
Uses Isolation Forest and Local Outlier Factor to detect un-supervised sensor anomalies.
Returns anomaly_status, anomaly_score, severity, location, and factual deviation explanations.
"""

from typing import Dict, Any, List
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor

class AnomalyDetectorEngine:
    def __init__(self, method: str = "isolation_forest", contamination: float = 0.05):
        self.method = method
        self.contamination = contamination
        self.model = None

    def fit_detect(self, df: pd.DataFrame, feature_cols: List[str]) -> pd.DataFrame:
        """Fits anomaly detector and returns DataFrame with anomaly scores and statuses."""
        df_res = df.copy()
        X = df_res[feature_cols].fillna(0).values
        
        if self.method == "isolation_forest":
            self.model = IsolationForest(contamination=self.contamination, random_state=42)
            preds = self.model.fit_predict(X)
            scores = -self.model.score_samples(X)  # Higher score = more anomalous
        else:
            self.model = LocalOutlierFactor(n_neighbors=20, contamination=self.contamination, novelty=False)
            preds = self.model.fit_predict(X)
            scores = -self.model.negative_outlier_factor_
            
        df_res["is_anomaly"] = (preds == -1).astype(int)
        # Normalize score between 0.0 and 1.0
        score_min, score_max = scores.min(), scores.max()
        denom = (score_max - score_min) if (score_max - score_min) > 1e-5 else 1.0
        df_res["anomaly_score"] = np.round((scores - score_min) / denom, 4)
        
        df_res["severity"] = df_res["anomaly_score"].apply(
            lambda s: "HIGH" if s > 0.75 else ("MEDIUM" if s > 0.50 else "LOW")
        )
        return df_res

    def generate_anomaly_explanation(self, row: pd.Series, feature_cols: List[str], feature_means: Dict[str, float]) -> str:
        """Generates factual, non-definitive explanation based on observed deviations from baseline mean."""
        deviations = []
        for col in feature_cols:
            if col in row and col in feature_means:
                val = row[col]
                mean_val = feature_means[col]
                pct_diff = ((val - mean_val) / (mean_val + 1e-5)) * 100.0
                if abs(pct_diff) > 30.0:
                    direction = "substantially above" if pct_diff > 0 else "substantially below"
                    deviations.append(f"{col} ({val}) is {direction} recent baseline mean ({round(mean_val, 2)}).")
                    
        if deviations:
            return "Potential abnormal pattern observed: " + "; ".join(deviations) + " Physical inspection may be required."
        return "Minor parameter fluctuation detected relative to historical baseline."
