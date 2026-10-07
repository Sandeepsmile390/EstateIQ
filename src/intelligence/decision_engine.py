"""
EstateIQ Decision Intelligence — EDI (src/intelligence/decision_engine.py).
Final decision layer synthesizing evidence into decision scores and priority classifications.
"""

from typing import Dict, Any
from src.intelligence.config import DIFConfig, DEFAULT_DIF_CONFIG
from src.intelligence.types import (
    ContextualResult, AnomalyResult, ConfidenceResult, ImpactResult,
    RiskResult, PriorityLevel
)

class EstateIQDecisionEngine:
    """EDI: Final decision score and priority classifier."""

    def __init__(self, config: DIFConfig = DEFAULT_DIF_CONFIG):
        self.config = config

    def evaluate(
        self,
        contextual: ContextualResult,
        anomaly: AnomalyResult,
        confidence: ConfidenceResult,
        impact: ImpactResult,
        risk: RiskResult,
        opportunity_score: float = 65.0
    ) -> Dict[str, Any]:
        # Normalize impact score (0 to 100) based on annual cost of inaction
        impact_score = min(100.0, (impact.annual_cost_of_inaction_inr / 500000.0) * 100.0)
        forecast_dev_score = min(100.0, max(0.0, abs(contextual.relative_deviation_pct) * 2.0))

        # Weighted Decision Score
        raw_decision_score = (
            self.config.weight_contextual_score * contextual.contextual_score +
            self.config.weight_anomaly_score * anomaly.anomaly_score +
            self.config.weight_forecast_deviation * forecast_dev_score +
            self.config.weight_business_impact * impact_score +
            self.config.weight_risk_score * risk.risk_score +
            self.config.weight_opportunity_score * opportunity_score
        )

        decision_score = round(raw_decision_score, 1)

        # Priority Classification
        if decision_score >= 75.0 and confidence.confidence_pct >= self.config.high_confidence_gate:
            priority = PriorityLevel.P1_CRITICAL
            next_step = "Immediate Automated BMS Setpoint Adjustment & Work Order Dispatch"
        elif decision_score >= 55.0:
            priority = PriorityLevel.P2_HIGH
            next_step = "Operations Technician Inspection Required"
        elif decision_score >= 35.0:
            priority = PriorityLevel.P3_MEDIUM
            next_step = "Schedule Routine HVAC Maintenance Review"
        else:
            priority = PriorityLevel.P4_LOW
            next_step = "Nominal Monitoring — No Action Required"

        return {
            "decision_score": decision_score,
            "priority": priority,
            "recommended_next_step": next_step,
            "provenance": "EDI_DECISION_ENGINE"
        }
