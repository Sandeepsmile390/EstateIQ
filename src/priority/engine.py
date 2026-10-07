"""
Facility Priority Engine (src/priority/engine.py).
Ranks operational incidents and alerts based on:
Priority Score = Severity × Probability × Impact × Urgency.
Resource Effort / Complexity is computed and reported as a separate dimension to avoid artificially inflating priority for complex tasks.
"""

from typing import Dict, Any

class FacilityPriorityEngine:
    def __init__(self, weights: Dict[str, float] = None):
        # Default priority weights (sum to 1.0)
        self.weights = weights if weights else {
            "severity": 0.35,
            "probability": 0.30,
            "impact": 0.20,
            "urgency": 0.15
        }

    def compute_priority(
        self,
        severity_score: float,       # 0.0 to 1.0
        probability_score: float,    # 0.0 to 1.0
        impact_score: float,         # 0.0 to 1.0
        urgency_score: float,        # 0.0 to 1.0
        complexity_score: float = 0.5 # 0.0 (Low effort) to 1.0 (High effort)
    ) -> Dict[str, Any]:
        """Calculates transparent composite score and assigns Priority Band & Complexity Level."""
        priority_score = (
            severity_score * self.weights["severity"] +
            probability_score * self.weights["probability"] +
            impact_score * self.weights["impact"] +
            urgency_score * self.weights["urgency"]
        )
        priority_score = round(priority_score, 4)
        
        if priority_score >= 0.70:
            priority_level = "Priority 1 (URGENT)"
            priority_badge = "URGENT"
        elif priority_score >= 0.40:
            priority_level = "Priority 2 (MODERATE)"
            priority_badge = "MODERATE"
        else:
            priority_level = "Priority 3 (LOW)"
            priority_badge = "LOW"
            
        # Complexity classification (kept separate from priority)
        if complexity_score >= 0.75:
            complexity_level = "HIGH (Specialized Contractor / BMS Integration)"
        elif complexity_score >= 0.40:
            complexity_level = "MEDIUM (Facilities Staff Servicing)"
        else:
            complexity_level = "LOW (Single-Click Automation / Setpoint Adjustment)"
            
        return {
            "priority_level": priority_level,
            "priority_badge": priority_badge,
            "composite_priority_score": priority_score,
            "complexity_level": complexity_level,
            "complexity_score": round(complexity_score, 2),
            "scoring_breakdown": {
                "severity_contrib": round(severity_score * self.weights["severity"], 4),
                "probability_contrib": round(probability_score * self.weights["probability"], 4),
                "impact_contrib": round(impact_score * self.weights["impact"], 4),
                "urgency_contrib": round(urgency_score * self.weights["urgency"], 4)
            },
            "weights_used": self.weights
        }
