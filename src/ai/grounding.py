"""
AI Grounding & Context Builder (src/ai/grounding.py).
Constructs structured evidence packets from EstateIQ-DIF backend logic to ground LLM reasoning.
"""

from typing import Dict, Any, List
from src.intelligence.dif_engine import EstateIQDIF
from src.intelligence.types import EventData, DecisionResult

class AIEvidenceBuilder:
    """Constructs verifiable JSON evidence packets for Groq AI prompting."""

    @classmethod
    def build_evidence_packet(
        self,
        event: EventData,
        decision: DecisionResult
    ) -> Dict[str, Any]:
        """Builds a structured evidence dictionary containing strictly backend-verified facts."""
        return {
            "facility": {
                "facility_id": event.facility_id,
                "building_id": event.building_id,
                "timestamp": event.timestamp
            },
            "data_quality": {
                "quality_score": decision.quality.overall_quality_score,
                "sensor_reliability": decision.quality.sensor_reliability,
                "is_insufficient": decision.quality.is_insufficient
            },
            "telemetry_observed": {
                "actual_kwh": event.actual_kwh,
                "occupancy": event.occupancy,
                "temperature_c": event.temperature,
                "hvac_load_kw": event.hvac_load
            },
            "contextual_baseline": {
                "expected_kwh": decision.contextual.expected_kwh,
                "residual_kwh": decision.contextual.residual_kwh,
                "relative_deviation_pct": decision.contextual.relative_deviation_pct
            },
            "anomaly_evidence": {
                "anomaly_score": decision.anomaly.anomaly_score,
                "anomaly_level": decision.anomaly.anomaly_level.value,
                "evidence_points": decision.anomaly.evidence,
                "model_agreement_pct": decision.anomaly.model_agreement_pct
            },
            "confidence": {
                "confidence_percent": decision.confidence.confidence_pct,
                "confidence_level": decision.confidence.confidence_level,
                "gate_passed": decision.confidence.gate_passed
            },
            "business_impact": {
                "surge_kwh": decision.impact.surge_kwh,
                "hourly_cost_inr": decision.impact.hourly_avoidable_cost_inr,
                "annual_cost_of_inaction_inr": decision.impact.annual_cost_of_inaction_inr,
                "daily_co2_surge_kg": decision.impact.daily_co2_surge_kg,
                "annual_co2_surge_tons": decision.impact.annual_co2_surge_tons
            },
            "decision_intelligence": {
                "decision_score": decision.decision_score,
                "priority": decision.priority.value,
                "execution_path": decision.execution_path.value
            },
            "shap_attribution": decision.shap_attribution,
            "recommended_actions": [
                {
                    "action_id": r.action_id,
                    "title": r.title,
                    "expected_cost_saving_inr": r.expected_cost_saving_inr,
                    "effort": r.effort
                }
                for r in decision.recommendations
            ],
            "provenance": "ESTATEIQ_DIF_GROUNDED_EVIDENCE"
        }
