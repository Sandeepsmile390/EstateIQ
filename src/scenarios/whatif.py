"""
What-If Scenario Simulation Engine.
Allows administrators to simulate operational parameter changes (HVAC schedule, operating hours, equipment load)
and compare base predictions against simulated predictions.

IMPORTANT: Results are explicitly labeled as modelled scenarios and do NOT represent guaranteed real-world savings.
"""

from typing import Dict, Any
import numpy as np
import pandas as pd

WHATIF_DISCLAIMER = "Simulated results represent computational model estimations based on modified inputs and do not constitute guaranteed physical savings."

class WhatIfScenarioEngine:
    def __init__(self, trained_model: Any, feature_cols: list):
        self.model = trained_model
        self.feature_cols = feature_cols

    def run_scenario(self, current_input_df: pd.DataFrame, modifications: Dict[str, float]) -> Dict[str, Any]:
        """
        Runs model against original and modified inputs.
        modifications example: {"hvac_load": 0.85, "occupancy": 0.90} (multiply by factor)
        """
        base_df = current_input_df.copy()
        
        # Original Prediction
        X_base = base_df[self.feature_cols].fillna(0)
        base_preds = float(np.mean(self.model.predict(X_base)))
        
        # Modified Scenario DataFrame
        sim_df = base_df.copy()
        for col, factor in modifications.items():
            if col in sim_df.columns:
                sim_df[col] = sim_df[col] * factor
                
        X_sim = sim_df[self.feature_cols].fillna(0)
        sim_preds = float(np.mean(self.model.predict(X_sim)))
        
        diff = sim_preds - base_preds
        pct_change = (diff / (base_preds + 1e-5)) * 100.0
        
        return {
            "current_scenario_prediction": round(base_preds, 2),
            "simulated_scenario_prediction": round(sim_preds, 2),
            "absolute_difference": round(diff, 2),
            "percentage_change": round(pct_change, 2),
            "modifications_applied": modifications,
            "disclaimer": WHATIF_DISCLAIMER
        }
