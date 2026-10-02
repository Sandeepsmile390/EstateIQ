"""
Facility Priority Engine.
Ranks operational incidents and alerts into Priority 1, Priority 2, or Priority 3 based on transparent, configurable scoring weights.
"""

from typing import Dict, Any

class FacilityPriorityEngine:
    def __init__(self, weights: Dict[str, float] = None):
        # Default scoring weights (sum to 1.0)
        self.weights = weights if weights else {
            "severity": 0.30,
            "probability": 0.25,
            "impact": 0.20,
            "urgency": 0.15,
            "resource_effort": 0.10
        }

    def compute_priority(
        self,
        severity_score: float,       # 0.0 to 1.0 (e.g. HIGH=1.0, MED=0.5, LOW=0.2)
        probability_score: float,    # 0.0 to 1.0 (raw ML probability)
        impact_score: float,         # 0.0 to 1.0 (criticality of zone)
        urgency_score: float,        # 0.0 to 1.0 (time sensitivity)
        resource_effort_score: float # 0.0 to 1.0 (ease of fix)
    ) -> Dict[str, Any]:
        """Calculates transparent composite score and assigns Priority Band."""
        total_score = (
            severity_score * self.weights["severity"] +
            probability_score * self.weights["probability"] +
            impact_score * self.weights["impact"] +
            urgency_score * self.weights["urgency"] +
            resource_effort_score * self.weights["resource_effort"]
        )
        total_score = round(total_score, 4)
        
        if total_score >= 0.70:
            priority = "Priority 1 (URGENT - Immediate Action Required)"
        elif total_score >= 0.40:
            priority = "Priority 2 (MODERATE - Scheduled Maintenance)"
        else:
            priority = "Priority 3 (LOW - Routine Monitoring)"
            
        return {
            "priority_level": priority,
            "composite_priority_score": total_score,
            "scoring_breakdown": {
                "severity_contrib": round(severity_score * self.weights["severity"], 4),
                "probability_contrib": round(probability_score * self.weights["probability"], 4),
                "impact_contrib": round(impact_score * self.weights["impact"], 4),
                "urgency_contrib": round(urgency_score * self.weights["urgency"], 4),
                "resource_effort_contrib": round(resource_effort_score * self.weights["resource_effort"], 4)
            },
            "weights_used": self.weights
        }

if __name__ == "__main__":
    engine = FacilityPriorityEngine()
    res = engine.compute_priority(1.0, 0.85, 0.8, 0.9, 0.5)
    print("[Priority Engine Test] Output:", res)
