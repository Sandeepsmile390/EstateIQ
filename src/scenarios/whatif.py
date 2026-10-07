"""
What-If Scenario Simulation Engine.
Allows administrators to simulate operational parameter changes (HVAC schedule, operating hours, equipment load)
and compare base predictions against simulated predictions.

IMPORTANT: Results are explicitly labeled as modelled scenarios and do NOT represent guaranteed real-world savings.
"""

from typing import Dict, Any, Optional
import numpy as np
import pandas as pd

WHATIF_DISCLAIMER = "Simulated results represent computational model estimations based on modified inputs and do not constitute guaranteed physical savings."

class WhatIfScenarioEngine:
    def __init__(self, trained_model: Optional[Any] = None, feature_cols: Optional[list] = None):
        self.model = trained_model
        self.feature_cols = feature_cols or []

    def simulate_hvac_setback(
        self,
        baseline_kwh: float = 145.2,
        setback_percent: float = 20.0,
        tariff_rate_inr: float = 9.50
    ) -> Dict[str, Any]:
        """Simulates HVAC setback schedule impact on demand and cost."""
        factor = (100.0 - setback_percent) / 100.0
        simulated_kwh = max(10.0, baseline_kwh * factor)
        saved_kwh_hr = baseline_kwh - simulated_kwh
        monthly_saving_kwh = saved_kwh_hr * 24 * 30
        monthly_saving_inr = monthly_saving_kwh * tariff_rate_inr
        annual_saving_inr = monthly_saving_inr * 12
        co2_saved_kg_mo = monthly_saving_kwh * 0.82

        return {
            "scenario_name": f"HVAC Setback ({setback_percent:.0f}% Load Reduction)",
            "baseline_kwh": round(baseline_kwh, 2),
            "simulated_kwh": round(simulated_kwh, 2),
            "hourly_kwh_saved": round(saved_kwh_hr, 2),
            "monthly_cost_saving_inr": round(monthly_saving_inr, 2),
            "annual_cost_saving_inr": round(annual_saving_inr, 2),
            "monthly_co2_reduced_kg": round(co2_saved_kg_mo, 2),
            "disclaimer": WHATIF_DISCLAIMER,
            "provenance": "[SIMULATED SCENARIO]"
        }

    def run_scenario(self, current_input_df: pd.DataFrame, modifications: Dict[str, float]) -> Dict[str, Any]:
        """
        Runs model against original and modified inputs.
        modifications example: {"hvac_load": 0.85, "occupancy": 0.90} (multiply by factor)
        """
        if not self.model or not self.feature_cols:
            base_kwh = float(current_input_df.get("actual_kwh", [145.2])[0]) if "actual_kwh" in current_input_df.columns else 145.2
            factor = modifications.get("hvac_load", 0.80)
            return self.simulate_hvac_setback(baseline_kwh=base_kwh, setback_percent=(1.0 - factor) * 100.0)

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
