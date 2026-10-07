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
        model_consensus_score: float = 0.85, # 0-1
        data_quality_score: float = 94.0,     # 0-100
        sensor_reliability_score: float = 90.0, # 0-100
        historical_days_available: int = 365,
        prediction_error_pct: float = 5.2,     # MAPE %
        feature_completeness_pct: float = 98.0
    ) -> Dict[str, Any]:
        """
        Formulation:
        Confidence = (0.35 * Consensus) + (0.25 * DataQuality) + (0.15 * SensorReliability) +
                     (0.15 * HistoricalVolume) + (0.10 * ErrorPenalty)
        """
        norm_consensus = model_consensus_score * 100.0
        norm_dq = data_quality_score
        norm_sr = sensor_reliability_score
        
        # Historical volume score (max out at 90 days = 100%)
        norm_hist = min(100.0, (historical_days_available / 90.0) * 100.0)
        
        # Error penalty (lower MAPE = higher confidence)
        norm_err = max(0.0, 100.0 - (prediction_error_pct * 2.5))

        overall_confidence_pct = round(
            (0.35 * norm_consensus) +
            (0.25 * norm_dq) +
            (0.15 * norm_sr) +
            (0.15 * norm_hist) +
            (0.10 * norm_err),
            1
        )

        overall_confidence_ratio = round(overall_confidence_pct / 100.0, 2)
        
        is_high_confidence = overall_confidence_pct >= 75.0
        is_sufficient_for_action = overall_confidence_pct >= 60.0

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
            "factors_breakdown": {
                "model_consensus_factor": round(norm_consensus, 1),
                "data_quality_factor": round(norm_dq, 1),
                "sensor_reliability_factor": round(norm_sr, 1),
                "historical_volume_factor": round(norm_hist, 1),
                "error_bound_factor": round(norm_err, 1)
            },
            "provenance": "CONFIDENCE_ENGINE"
        }
