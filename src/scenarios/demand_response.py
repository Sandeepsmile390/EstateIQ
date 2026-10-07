"""
Demand Response & Flexible Load Identification Engine (src/scenarios/demand_response.py).
Identifies shiftable electrical loads (HVAC setback, thermal storage, pumping, non-critical equipment)
during peak tariff hours to reduce peak demand charges without impacting occupant comfort.
"""

from typing import Dict, Any, List

class DemandResponseEngine:
    def __init__(self, peak_demand_tariff_inr_kw: float = 450.0):
        self.demand_tariff = peak_demand_tariff_inr_kw

    def evaluate_flexible_loads(
        self,
        current_peak_kw: float = 585.0,
        hvac_load_kw: float = 240.0,
        water_heating_kw: float = 45.0,
        pumping_load_kw: float = 30.0,
        non_critical_equipment_kw: float = 35.0
    ) -> Dict[str, Any]:
        """Identifies flexible loads and projects potential peak demand reduction impact."""
        # Calculate max shiftable load percentages per sub-system
        flexible_hvac_kw = hvac_load_kw * 0.20           # 20% HVAC setback
        flexible_water_heating_kw = water_heating_kw * 0.60 # 60% load shift
        flexible_pumping_kw = pumping_load_kw * 0.50       # 50% load shift to off-peak
        flexible_equipment_kw = non_critical_equipment_kw * 0.30

        total_shiftable_kw = flexible_hvac_kw + flexible_water_heating_kw + flexible_pumping_kw + flexible_equipment_kw
        optimized_peak_kw = current_peak_kw - total_shiftable_kw
        monthly_demand_savings_inr = total_shiftable_kw * self.demand_tariff

        return {
            "current_peak_demand_kw": round(current_peak_kw, 1),
            "optimized_peak_demand_kw": round(optimized_peak_kw, 1),
            "total_shiftable_load_kw": round(total_shiftable_kw, 1),
            "monthly_demand_charge_savings_inr": round(monthly_demand_savings_inr, 2),
            "annual_demand_charge_savings_inr": round(monthly_demand_savings_inr * 12.0, 2),
            "flexible_load_breakdown": {
                "hvac_setback_kw": round(flexible_hvac_kw, 1),
                "water_heating_shift_kw": round(flexible_water_heating_kw, 1),
                "pumping_shift_kw": round(flexible_pumping_kw, 1),
                "non_critical_equipment_kw": round(flexible_equipment_kw, 1)
            },
            "human_approval_required": True,
            "disclaimer": "Demand response recommendations require authorized human approval before execution.",
            "provenance": "SIMULATED"
        }
