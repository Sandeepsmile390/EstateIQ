"""
Tariff-Aware Energy Intelligence & Business Impact Engine (src/scoring/business_impact.py).
Translates operational deviations, forecasts, and intervention scenarios into monetary (₹ INR / $ USD) and CO2e carbon impact metrics.
Explicitly distinguishes energy consumption savings from peak demand charge savings and DG fuel savings.
"""

from typing import Dict, Any, Optional

class BusinessImpactEngine:
    def __init__(
        self,
        grid_tariff_inr_kwh: float = 8.50,
        peak_demand_tariff_inr_kw_month: float = 450.0,
        diesel_price_inr_liter: float = 92.0,
        dg_fuel_yield_kwh_liter: float = 3.5,
        grid_emission_factor_kg_kwh: float = 0.82,
        diesel_emission_factor_kg_liter: float = 2.68,
        inr_to_usd_rate: float = 0.012
    ):
        self.grid_tariff_inr = grid_tariff_inr_kwh
        self.peak_demand_tariff_inr = peak_demand_tariff_inr_kw_month
        self.diesel_price_inr = diesel_price_inr_liter
        self.dg_yield = dg_fuel_yield_kwh_liter
        self.grid_emission_factor = grid_emission_factor_kg_kwh
        self.diesel_emission_factor = diesel_emission_factor_kg_liter
        self.inr_to_usd = inr_to_usd_rate

    def calculate_energy_impact(
        self,
        actual_kwh: float,
        expected_kwh: float,
        hours_duration: float = 1.0,
        peak_kw_reduction: float = 0.0
    ) -> Dict[str, Any]:
        """Calculates financial and environmental impact of energy deviation/intervention."""
        kwh_diff = actual_kwh - expected_kwh
        is_excess = kwh_diff > 0

        # Hourly / Annualized Cost Savings or Excess
        energy_cost_inr = abs(kwh_diff) * self.grid_tariff_inr
        monthly_kwh_diff = abs(kwh_diff) * (720.0 / max(hours_duration, 0.25))
        monthly_energy_cost_inr = monthly_kwh_diff * self.grid_tariff_inr
        annual_energy_cost_inr = monthly_energy_cost_inr * 12.0

        # Peak Demand Charge Impact
        monthly_demand_savings_inr = peak_kw_reduction * self.peak_demand_tariff_inr
        annual_demand_savings_inr = monthly_demand_savings_inr * 12.0

        total_annual_savings_inr = annual_energy_cost_inr + annual_demand_savings_inr
        total_annual_savings_usd = total_annual_savings_inr * self.inr_to_usd

        # Carbon Emissions Impact (Metric Tons CO2e)
        co2_kg_hourly = abs(kwh_diff) * self.grid_emission_factor
        co2_tons_annual = (monthly_kwh_diff * 12.0 * self.grid_emission_factor) / 1000.0

        return {
            "is_excess": is_excess,
            "kwh_difference": round(kwh_diff, 2),
            "hourly_cost_impact_inr": round(energy_cost_inr, 2),
            "monthly_projected_savings_inr": round(monthly_energy_cost_inr + monthly_demand_savings_inr, 2),
            "annual_projected_savings_inr": round(total_annual_savings_inr, 2),
            "annual_projected_savings_usd": round(total_annual_savings_usd, 2),
            "breakdown": {
                "energy_consumption_savings_inr": round(annual_energy_cost_inr, 2),
                "peak_demand_charge_savings_inr": round(annual_demand_savings_inr, 2),
                "co2_emissions_avoided_tons_yr": round(co2_tons_annual, 2)
            },
            "tariffs_applied": {
                "grid_tariff_inr_kwh": self.grid_tariff_inr,
                "peak_demand_tariff_inr_kw_month": self.peak_demand_tariff_inr,
                "grid_emission_factor_kg_kwh": self.grid_emission_factor
            },
            "confidence": 0.92,
            "currency": "INR",
            "provenance": "DERIVED"
        }

    def calculate_dg_impact(self, runtime_hours: float, load_kw: float) -> Dict[str, Any]:
        """Calculates cost and emissions of Diesel Generator operation vs Grid."""
        energy_kwh = load_kw * runtime_hours
        fuel_liters = energy_kwh / self.dg_yield
        dg_cost_inr = fuel_liters * self.diesel_price_inr
        dg_effective_rate_inr_kwh = dg_cost_inr / max(energy_kwh, 0.1)

        grid_cost_inr = energy_kwh * self.grid_tariff_inr
        excess_dg_cost_inr = dg_cost_inr - grid_cost_inr

        dg_co2_kg = fuel_liters * self.diesel_emission_factor
        grid_co2_kg = energy_kwh * self.grid_emission_factor
        excess_co2_kg = dg_co2_kg - grid_co2_kg

        return {
            "dg_runtime_hours": runtime_hours,
            "energy_generated_kwh": round(energy_kwh, 2),
            "fuel_consumed_liters": round(fuel_liters, 2),
            "total_dg_cost_inr": round(dg_cost_inr, 2),
            "effective_dg_tariff_inr_kwh": round(dg_effective_rate_inr_kwh, 2),
            "excess_cost_vs_grid_inr": round(excess_dg_cost_inr, 2),
            "dg_co2_emissions_kg": round(dg_co2_kg, 2),
            "excess_co2_vs_grid_kg": round(excess_co2_kg, 2),
            "provenance": "DERIVED"
        }
