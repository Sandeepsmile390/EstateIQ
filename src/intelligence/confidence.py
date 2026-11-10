"""
EstateIQ Confidence Engine (src/intelligence/confidence.py).
Calculates deterministic, transparent decision confidence scores (0–100%) combining:
Model Consensus + Data Quality + Historical Volume + Sensor Reliability + Prediction Error.
"""

from typing import Dict, Any, Optional

class ConfidenceEngine:
    """Calculates multi-source confidence scores for predictions, anomalies, and decisions."""
    
    def calculate_decision_confidence(
        self,
        model_consensus_score: Optional[float] = None, # 0-1
        data_quality_score: Optional[float] = None,     # 0-100
        sensor_reliability_score: Optional[float] = None, # 0-100
        historical_days_available: Optional[int] = None,
        prediction_error_pct: Optional[float] = None,     # MAPE %
        feature_completeness_pct: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Formulation:
        Confidence = (0.35 * Consensus) + (0.25 * DataQuality) + (0.15 * SensorReliability) +
                     (0.15 * HistoricalVolume) + (0.10 * ErrorPenalty)
        """
        evidence = {}
        if model_consensus_score is not None:
            evidence["model_consensus_factor"] = (0.35, max(0.0, min(100.0, model_consensus_score * 100.0)))
        if data_quality_score is not None:
            evidence["data_quality_factor"] = (0.25, max(0.0, min(100.0, data_quality_score)))
        if sensor_reliability_score is not None:
            evidence["sensor_reliability_factor"] = (0.15, max(0.0, min(100.0, sensor_reliability_score)))
        if historical_days_available is not None:
            # Historical volume score (max out at 90 observed days).
            evidence["historical_volume_factor"] = (0.15, min(100.0, max(0, historical_days_available) / 90.0 * 100.0))
        if prediction_error_pct is not None:
            evidence["error_bound_factor"] = (0.10, max(0.0, min(100.0, 100.0 - prediction_error_pct * 2.5)))
        if feature_completeness_pct is not None:
            evidence["feature_completeness_factor"] = (0.10, max(0.0, min(100.0, feature_completeness_pct)))

        available_weight = sum(weight for weight, _ in evidence.values())
        overall_confidence_pct = round(
            sum(weight * value for weight, value in evidence.values()) / available_weight, 1
        ) if available_weight else 0.0
        norm_consensus = evidence.get("model_consensus_factor", (0.0, 0.0))[1]
        norm_dq = evidence.get("data_quality_factor", (0.0, 0.0))[1]
        norm_sr = evidence.get("sensor_reliability_factor", (0.0, 0.0))[1]
        norm_hist = evidence.get("historical_volume_factor", (0.0, 0.0))[1]
        norm_err = evidence.get("error_bound_factor", (0.0, 0.0))[1]

        overall_confidence_ratio = round(overall_confidence_pct / 100.0, 2)
        
        is_high_confidence = bool(evidence) and overall_confidence_pct >= 75.0
        is_sufficient_for_action = len(evidence) >= 3 and overall_confidence_pct >= 60.0

        recommendation_warning = None
        if not is_sufficient_for_action:
            recommendation_warning = "INSUFFICIENT_CONFIDENCE: Verify telemetry before taking high-impact physical action."

        return {
            "overall_confidence_pct": overall_confidence_pct,
            "overall_confidence_ratio": overall_confidence_ratio,
            "prediction_confidence_pct": round(norm_consensus * 0.9, 1),
            "anomaly_confidence_pct": round(norm_consensus * 0.95, 1),
            "recommendation_confidence_pct": overall_confidence_pct,
            "simulation_confidence_pct": round(overall_confidence_pct * 0.9, 1),
            "is_high_confidence": is_high_confidence,
            "is_sufficient_for_action": is_sufficient_for_action,
            "confidence_warning": recommendation_warning,
            "evidence_count": len(evidence),
            "evidence_status": "SUFFICIENT" if is_sufficient_for_action else "INSUFFICIENT_EVIDENCE",
            "factors_breakdown": {
                key: round(value, 1) for key, (_, value) in evidence.items()
            },
            "provenance": "CONFIDENCE_ENGINE"
        }
