"""
Transformer & Diesel Generator (DG) Intelligence Module (src/monitoring/transformer_dg.py).
Provides telemetry tracking, overload detection, efficiency analysis, and operational recommendations
for campus transformers and standby diesel generators.
"""

from typing import Dict, Any, List
import pandas as pd
import numpy as np

class TransformerDGMonitor:
    def __init__(self):
        # Default campus electrical equipment specifications
        self.transformer_capacity_kva = 750.0  # 750 kVA Main Transformer
        self.rated_power_factor = 0.92
        self.transformer_capacity_kw = self.transformer_capacity_kva * self.rated_power_factor
        self.dg_capacity_kva = 500.0          # 500 kVA Generator

    def get_transformer_status(self, current_load_kw: float = 585.0, voltage_v: float = 415.0) -> Dict[str, Any]:
        """Evaluates transformer loading percentage, thermal risk, and power factor."""
        loading_pct = (current_load_kw / self.transformer_capacity_kw) * 100.0
        loading_pct = round(loading_pct, 1)

        # Thermal estimation based on loading curve
        estimated_temp_c = round(35.0 + (loading_pct / 100.0)**2 * 45.0, 1)

        if loading_pct >= 90.0:
            status = "CRITICAL_OVERLOAD_RISK"
            alert_msg = f"Transformer operating at {loading_pct}% capacity. Thermal rise imminent."
        elif loading_pct >= 75.0:
            status = "HIGH_LOAD"
            alert_msg = f"Transformer operating at {loading_pct}% capacity. Monitor peak hours."
        else:
            status = "NORMAL"
            alert_msg = f"Transformer operating smoothly at {loading_pct}% capacity."

        return {
            "transformer_id": "XFMR_MAIN_01",
            "rated_capacity_kva": self.transformer_capacity_kva,
            "rated_capacity_kw": round(self.transformer_capacity_kw, 1),
            "current_load_kw": round(current_load_kw, 1),
            "loading_percent": loading_pct,
            "estimated_temperature_c": estimated_temp_c,
            "voltage_v": voltage_v,
            "power_factor": self.rated_power_factor,
            "status": status,
            "alert_message": alert_msg,
            "provenance": "DERIVED"
        }

    def get_dg_status(
        self,
        is_running: bool = False,
        runtime_hours_today: float = 1.5,
        fuel_level_pct: float = 82.0,
        current_output_kw: float = 0.0
    ) -> Dict[str, Any]:
        """Evaluates Standby Diesel Generator operating status, fuel reserve, and efficiency."""
        fuel_tank_capacity_l = 1000.0
        fuel_remaining_l = (fuel_level_pct / 100.0) * fuel_tank_capacity_l
        
        # DG Diesel consumption: ~0.28 L/kWh
        hourly_fuel_burn_l = (current_output_kw * 0.28) if is_running else 0.0
        
        return {
            "dg_id": "DG_STANDBY_01",
            "rated_capacity_kva": self.dg_capacity_kva,
            "is_running": is_running,
            "current_output_kw": current_output_kw,
            "runtime_hours_today": runtime_hours_today,
            "fuel_level_percent": fuel_level_pct,
            "fuel_remaining_liters": round(fuel_remaining_l, 1),
            "hourly_fuel_burn_liters": round(hourly_fuel_burn_l, 1),
            "efficiency_kwh_per_liter": 3.57 if is_running else 0.0,
            "status": "RUNNING" if is_running else "STANDBY",
            "provenance": "DERIVED"
        }
