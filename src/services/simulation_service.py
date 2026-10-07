"""
Unified Simulation Service (src/services/simulation_service.py).
Executes What-If scenario simulations across energy, HVAC, temperature, and occupancy.
Calculates predicted consumption, ₹ cost savings, and CO₂e carbon reduction.
"""

from typing import Dict, Any

class SimulationService:
    def __init__(self, tariff_per_kwh: float = 9.50, co2_kg_per_kwh: float = 0.82):
        self.tariff = tariff_per_kwh
        self.co2_factor = co2_kg_per_kwh

    def run_hvac_scenario(
        self,
        baseline_kwh: float = 145.2,
        hvac_reduction_percent: float = 20.0
    ) -> Dict[str, Any]:
        """Simulates HVAC setpoint optimization scenario."""
        savings_ratio = (hvac_reduction_percent / 100.0) * 0.80
        simulated_kwh = round(baseline_kwh * (1.0 - savings_ratio), 2)
        saved_kwh_hourly = round(baseline_kwh - simulated_kwh, 2)
        
        saved_inr_monthly = round(saved_kwh_hourly * 24 * 30 * self.tariff, 2)
        saved_co2_tons_annual = round((saved_kwh_hourly * 24 * 365 * self.co2_factor) / 1000.0, 2)

        return {
            "intervention": f"Reduce HVAC load by {hvac_reduction_percent}%",
            "baseline_kwh": baseline_kwh,
            "simulated_kwh": simulated_kwh,
            "hourly_kwh_savings": saved_kwh_hourly,
            "monthly_savings_inr": saved_inr_monthly,
            "monthly_savings_usd": round(saved_inr_monthly / 82.0, 2),
            "annual_co2_reduction_tons": saved_co2_tons_annual,
            "status": "SIMULATED_MODEL_ESTIMATE",
            "provenance": "WHAT_IF_ML_SIMULATOR"
        }
