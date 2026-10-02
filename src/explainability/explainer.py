"""
Explainable AI (XAI) Module using SHAP.
Extracts local feature attributions for any trained model prediction.

IMPORTANT: SHAP feature contributions represent model attributions and do NOT prove direct physical causation.
"""

from typing import Dict, Any, List
import numpy as np
import pandas as pd
import shap

SHAP_DISCLAIMER = "SHAP attributions indicate how features influenced the model prediction, not definitive physical causation."

class ModelExplainer:
    def __init__(self, model: Any, background_data: pd.DataFrame = None):
        self.model = model
        self.background_data = background_data
        self.explainer = None
        
        # Initialize appropriate SHAP explainer
        try:
            self.explainer = shap.TreeExplainer(self.model)
        except Exception:
            try:
                if background_data is not None:
                    self.explainer = shap.KernelExplainer(self.model.predict, background_data.iloc[:50])
                else:
                    self.explainer = shap.Explainer(self.model)
            except Exception:
                self.explainer = None

    def explain_prediction(self, sample_df: pd.DataFrame, top_k: int = 5) -> Dict[str, Any]:
        """Calculates SHAP values for a single input instance."""
        if sample_df.ndim == 1:
            sample_df = pd.DataFrame([sample_df])
            
        feature_names = list(sample_df.columns)
        
        if self.explainer is not None:
            try:
                shap_values = self.explainer.shap_values(sample_df)
                if isinstance(shap_values, list):
                    vals = np.abs(shap_values[1][0]) if len(shap_values) > 1 else np.abs(shap_values[0][0])
                    raw_vals = shap_values[1][0] if len(shap_values) > 1 else shap_values[0][0]
                elif hasattr(shap_values, "values"):
                    vals = np.abs(shap_values.values[0])
                    raw_vals = shap_values.values[0]
                else:
                    vals = np.abs(shap_values[0])
                    raw_vals = shap_values[0]
                    
                contribs = []
                for name, val, raw_v in zip(feature_names, vals, raw_vals):
                    contribs.append({"feature": name, "abs_impact": float(val), "shap_value": float(raw_v)})
                    
                contribs.sort(key=lambda x: x["abs_impact"], reverse=True)
                top_features = contribs[:top_k]
            except Exception as e:
                top_features = [{"feature": col, "abs_impact": 0.0, "shap_value": 0.0} for col in feature_names[:top_k]]
        else:
            top_features = [{"feature": col, "abs_impact": 0.0, "shap_value": 0.0} for col in feature_names[:top_k]]
            
        return {
            "top_contributing_features": top_features,
            "important_feature_names": [f["feature"] for f in top_features],
            "disclaimer": SHAP_DISCLAIMER
        }
