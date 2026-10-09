"""
EstateIQ Business Impact & Cost of Inaction Engine (src/intelligence/business_impact.py).
Translates operational deviations into monetary (₹ INR / $ USD), carbon (CO2e),
and peak demand impact metrics. Calculates Cost of Inaction if issues remain unaddressed.
"""

from typing import Dict, Any, Optional

class IntelligenceBusinessImpactEngine:
    """Calculates financial impact, carbon footprint, and Cost of Inaction."""
    
    def __init__(
        self,
        grid_tariff_inr_kwh: float = 9.50,
        peak_demand_tariff_inr_kw: float = 450.0,
        grid_emission_factor_kg_kwh: float = 0.82,
        inr_to_usd_rate: float = 0.012
    ):
        self.tariff = grid_tariff_inr_kwh
        self.peak_tariff = peak_demand_tariff_inr_kw
        self.co2_factor = grid_emission_factor_kg_kwh
        self.inr_to_usd = inr_to_usd_rate

    def calculate_surge_impact(
        self,
        actual_kwh: float,
        expected_kwh: float,
        duration_hours: float = 1.0
    ) -> Dict[str, Any]:
        """Calculates monetary surge impact and Cost of Inaction."""
        residual_kwh = max(0.0, actual_kwh - expected_kwh)
        
        hourly_cost_inr = round(residual_kwh * self.tariff, 2)
        daily_cost_inr = round(hourly_cost_inr * 24.0, 2)
        monthly_cost_inr = round(daily_cost_inr * 30.0, 2)
        annual_cost_inr = round(monthly_cost_inr * 12.0, 2)

        # Carbon Emissions
        hourly_co2_kg = round(residual_kwh * self.co2_factor, 2)
        annual_co2_tons = round((residual_kwh * 24 * 365 * self.co2_factor) / 1000.0, 2)

        # Cost of Inaction Breakdown
        weekly_cost_inr = round(daily_cost_inr * 7.0, 2)
        cost_of_inaction = {
            "daily_cost_inaction_inr": daily_cost_inr,
            "cost_7day_inaction_inr": weekly_cost_inr,
            "cost_30day_inaction_inr": monthly_cost_inr,
            "monthly_cost_inaction_inr": monthly_cost_inr,
            "annualized_cost_inaction_inr": annual_cost_inr,
            "annualized_cost_inaction_usd": round(annual_cost_inr * self.inr_to_usd, 2),
            "disclaimer": "Cost of Inaction represents model-derived estimate if operational deviation continues unaddressed."
        }

        return {
            "residual_surge_kwh": round(residual_kwh, 2),
            "hourly_cost_impact_inr": hourly_cost_inr,
            "hourly_co2_impact_kg": hourly_co2_kg,
            "annual_co2_impact_tons": annual_co2_tons,
            "cost_of_inaction": cost_of_inaction,
            "tariff_applied_inr_kwh": self.tariff,
            "provenance": "BUSINESS_IMPACT_ENGINE"
        }
