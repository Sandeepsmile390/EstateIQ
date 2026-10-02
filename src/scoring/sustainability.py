"""
Transparent Facility Sustainability Score Engine.
Calculates a composite facility rating (0 to 100) across customizable indicators:
Energy, Water, Waste, Air Quality, Emissions, Equipment Utilization, Traffic Efficiency.

DISCLAIMER: This score is a facility decision-support metric and not an official government sustainability certification.
"""

from typing import Dict, Any

DEFAULT_WEIGHTS = {
    "energy": 0.20,
    "water": 0.15,
    "waste": 0.15,
    "air": 0.15,
    "emissions": 0.15,
    "equipment": 0.10,
    "traffic": 0.10
}

SUSTAINABILITY_DISCLAIMER = "This composite score is an internal decision-support benchmark and does not constitute an official regulatory or government sustainability rating."

class SustainabilityScoreCalculator:
    def __init__(self, custom_weights: Dict[str, float] = None):
        self.weights = custom_weights if custom_weights else DEFAULT_WEIGHTS.copy()
        # Normalize weights to sum to 1.0
        total_w = sum(self.weights.values())
        if total_w > 0:
            self.weights = {k: v / total_w for k, v in self.weights.items()}

    def calculate_score(
        self,
        energy_kwh: float,
        energy_target: float,
        water_liters: float,
        water_target: float,
        waste_fill_avg: float,
        aqi_val: float,
        emissions_kg: float,
        emissions_target: float,
        equipment_util_avg: float,
        traffic_congestion_pct: float
    ) -> Dict[str, Any]:
        """
        Calculates sub-scores (0 to 100) for each dimension and computes weighted composite score.
        High sub-scores mean superior performance.
        """
        # 1. Energy Score: Ratio of actual vs baseline target
        energy_ratio = min(2.0, max(0.0, energy_kwh / (energy_target + 1e-5)))
        sub_energy = max(0.0, 100.0 - (energy_ratio - 1.0) * 100.0) if energy_ratio > 1.0 else min(100.0, 100.0 + (1.0 - energy_ratio) * 50.0)
        
        # 2. Water Score
        water_ratio = min(2.0, max(0.0, water_liters / (water_target + 1e-5)))
        sub_water = max(0.0, 100.0 - (water_ratio - 1.0) * 100.0) if water_ratio > 1.0 else min(100.0, 100.0 + (1.0 - water_ratio) * 50.0)
        
        # 3. Waste Score: Based on average bin fill level
        sub_waste = max(0.0, 100.0 - waste_fill_avg)
        
        # 4. Air Quality Score: Based on AQI (0-500 scale mapped to 0-100 score)
        sub_air = max(0.0, 100.0 - (aqi_val / 3.0))
        
        # 5. Emissions Score
        em_ratio = min(2.0, max(0.0, emissions_kg / (emissions_target + 1e-5)))
        sub_emissions = max(0.0, 100.0 - (em_ratio - 1.0) * 100.0) if em_ratio > 1.0 else 100.0
        
        # 6. Equipment Score: Ideal utilization is 70-85%
        sub_equipment = min(100.0, equipment_util_avg * 100.0)
        
        # 7. Traffic Score: Inverse of congestion
        sub_traffic = max(0.0, 100.0 - traffic_congestion_pct)
        
        sub_scores = {
            "energy": round(sub_energy, 2),
            "water": round(sub_water, 2),
            "waste": round(sub_waste, 2),
            "air": round(sub_air, 2),
            "emissions": round(sub_emissions, 2),
            "equipment": round(sub_equipment, 2),
            "traffic": round(sub_traffic, 2)
        }
        
        # Weighted Total
        composite_score = sum(sub_scores[k] * self.weights.get(k, 0.0) for k in sub_scores)
        composite_score = round(max(0.0, min(100.0, composite_score)), 2)
        
        # Rating Band
        if composite_score >= 85:
            band = "PLATINUM (LEADERSHIP)"
        elif composite_score >= 70:
            band = "GOLD (EFFICIENT)"
        elif composite_score >= 50:
            band = "SILVER (MODERATE)"
        else:
            band = "BRONZE (REQUIRES ACTION)"
            
        return {
            "composite_sustainability_score": composite_score,
            "performance_band": band,
            "sub_scores": sub_scores,
            "weights_used": {k: round(v, 4) for k, v in self.weights.items()},
            "disclaimer": SUSTAINABILITY_DISCLAIMER
        }

if __name__ == "__main__":
    calc = SustainabilityScoreCalculator()
    res = calc.calculate_score(
        energy_kwh=120, energy_target=100,
        water_liters=800, water_target=1000,
        waste_fill_avg=45.0, aqi_val=85.0,
        emissions_kg=210.0, emissions_target=250.0,
        equipment_util_avg=0.75, traffic_congestion_pct=30.0
    )
    print("[Sustainability Score Test] Output:", res)
