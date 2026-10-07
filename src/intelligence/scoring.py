"""
EstateIQ Scoring Architecture (src/intelligence/scoring.py).
Computes distinct normalized score dimensions (0.0-1.0):
Anomaly Score, Risk Score, Business Impact Score, Opportunity Score, Priority Score, Confidence Score,
and composite EstateIQ Decision Score (0-100).
"""

from typing import Dict, Any

class IntelligenceScoringEngine:
    """Computes distinct score dimensions without mixing confidence and severity."""
    
    def compute_all_scores(
        self,
        anomaly_z_score: float = 2.8,
        actual_kwh: float = 145.2,
        expected_kwh: float = 78.0,
        data_quality_score: float = 94.0,
        confidence_pct: float = 87.0,
        model_consensus_score: float = 0.85
    ) -> Dict[str, Any]:
        """Calculates normalized score vector."""
        
        # 1. Anomaly Score (0.0 - 1.0)
        anomaly_score = round(min(1.0, max(0.0, (anomaly_z_score / 4.0))), 2)

        # 2. Business Impact Score (0.0 - 1.0 based on residual surge kWh)
        surge_kwh = max(0.0, actual_kwh - expected_kwh)
        impact_score = round(min(1.0, max(0.0, surge_kwh / 100.0)), 2)

        # 3. Risk Score (0.0 - 1.0 based on severity and equipment stress)
        risk_score = round(min(1.0, (anomaly_score * 0.6) + (impact_score * 0.4)), 2)

        # 4. Opportunity Score (0.0 - 1.0)
        opportunity_score = round(min(1.0, (impact_score * 0.7) + ((confidence_pct / 100.0) * 0.3)), 2)

        # 5. Priority Score (0.0 - 1.0): High Impact + High Anomaly + High Urgency
        priority_score = round(min(1.0, (impact_score * 0.45) + (anomaly_score * 0.35) + (risk_score * 0.20)), 2)

        # 6. Confidence Score (0.0 - 1.0)
        confidence_score = round(confidence_pct / 100.0, 2)

        # 7. EstateIQ Composite Decision Score (0 - 100)
        decision_score = round(
            (priority_score * 40.0) +
            (confidence_score * 35.0) +
            (impact_score * 25.0),
            1
        )

        return {
            "anomaly_score": anomaly_score,
            "risk_score": risk_score,
            "business_impact_score": impact_score,
            "opportunity_score": opportunity_score,
            "priority_score": priority_score,
            "confidence_score": confidence_score,
            "estateiq_decision_score": decision_score,
            "priority_level": "P1_CRITICAL" if priority_score >= 0.75 else ("P2_WARNING" if priority_score >= 0.50 else "P3_NOTICE"),
            "provenance": "INTELLIGENCE_SCORING_ENGINE"
        }
