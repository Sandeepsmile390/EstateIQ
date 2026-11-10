"""
EstateIQ Intelligence Fusion Engine (src/intelligence/fusion_engine.py).
Core decision-intelligence layer orchestrating and contextualizing multiple analytical models,
data quality metrics, confidence estimates, SHAP attributions, financial impacts, and safety gates.
"""

import uuid
from typing import Dict, Any, List, Optional
import pandas as pd

from src.data_quality.quality_score import DataQualityEngine
from src.intelligence.facility_fingerprint import FacilityFingerprintEngine
from src.intelligence.contextual_baseline import ContextualBaselineEngine
from src.intelligence.model_consensus import ModelConsensusEngine
from src.intelligence.confidence import ConfidenceEngine
from src.intelligence.scoring import IntelligenceScoringEngine
from src.intelligence.business_impact import IntelligenceBusinessImpactEngine
from src.intelligence.opportunity_engine import OpportunityEngine
from src.intelligence.safety_gate import AISafetyGate

class EstateIQIntelligenceFusionEngine:
    """Master Intelligence Fusion Engine orchestrating closed-loop decision intelligence."""
    
    def __init__(self):
        self.quality_engine = DataQualityEngine()
        self.fingerprint_engine = FacilityFingerprintEngine()
        self.baseline_engine = ContextualBaselineEngine()
        self.consensus_engine = ModelConsensusEngine()
        self.confidence_engine = ConfidenceEngine()
        self.scoring_engine = IntelligenceScoringEngine()
        self.impact_engine = IntelligenceBusinessImpactEngine()
        self.opportunity_engine = OpportunityEngine()
        self.safety_gate = AISafetyGate()

    def run_fusion_analysis(
        self,
        df_telemetry: pd.DataFrame,
        building_id: str = "Block B Hostel",
        actual_kwh: float = 145.2,
        hour: int = 14,
        day_of_week: int = 2,
        occupancy: int = 140,
        temperature: float = 31.5,
        hvac_load: float = 75.0,
        alert_id: str = "ALT_01"
    ) -> Dict[str, Any]:
        """Executes complete Intelligence Fusion Analysis loop."""
        
        trace_id = f"TRC_FUSION_{uuid.uuid4().hex[:8].upper()}"

        # 1. Data Quality Engine Check
        dq_res = self.quality_engine.evaluate_telemetry(df_telemetry)
        dq_score = dq_res["overall_data_quality_score"]

        # 2. Facility Fingerprint & Contextual Baseline
        base_info = self.baseline_engine.compute_expected_baseline(
            building_id=building_id,
            hour=hour,
            day_of_week=day_of_week,
            occupancy=occupancy,
            temperature=temperature,
            hvac_load=hvac_load
        )
        expected_kwh = base_info["expected_kwh"]

        dev_res = self.baseline_engine.evaluate_telemetry_deviation(actual_kwh, base_info)

        # 3. Model Consensus Engine
        # Only provide model outputs that were actually computed for this request.
        # The former fixed XGBoost/IsolationForest/Prophet values were not predictions.
        consensus_res = self.consensus_engine.evaluate_consensus(
            contextual_anomaly_flag=dev_res["is_contextual_anomaly"]
        )

        if "event_timestamp" in df_telemetry.columns or "timestamp" in df_telemetry.columns:
            timestamp_col = "event_timestamp" if "event_timestamp" in df_telemetry.columns else "timestamp"
            observed_times = pd.to_datetime(df_telemetry[timestamp_col], errors="coerce", utc=True).dropna()
            historical_days = max(0, int((observed_times.max() - observed_times.min()).total_seconds() // 86400)) if not observed_times.empty else 0
        else:
            historical_days = 0
        feature_completeness = float(df_telemetry.notna().mean().mean() * 100.0) if not df_telemetry.empty else 0.0

        # 4. Confidence Engine
        conf_res = self.confidence_engine.calculate_decision_confidence(
            model_consensus_score=consensus_res["model_consensus_score"],
            data_quality_score=dq_score,
            sensor_reliability_score=dq_res["sensor_reliability_score"],
            historical_days_available=historical_days,
            prediction_error_pct=None,
            feature_completeness_pct=feature_completeness
        )

        # 5. Multi-Dimension Scoring Engine
        scores_res = self.scoring_engine.compute_all_scores(
            anomaly_z_score=dev_res["z_score_deviation"],
            actual_kwh=actual_kwh,
            expected_kwh=expected_kwh,
            data_quality_score=dq_score,
            confidence_pct=conf_res["overall_confidence_pct"],
            model_consensus_score=consensus_res["model_consensus_score"] or 0.0
        )

        # 6. Business Impact & Cost of Inaction Engine
        impact_res = self.impact_engine.calculate_surge_impact(
            actual_kwh=actual_kwh,
            expected_kwh=expected_kwh
        )

        # 7. Opportunity Engine
        opportunities = self.opportunity_engine.discover_opportunities(
            building_id=building_id,
            actual_kwh=actual_kwh,
            expected_kwh=expected_kwh,
            confidence_pct=conf_res["overall_confidence_pct"]
        )

        # 8. AI Safety Gate & Human-in-the-Loop Check
        safety_res = self.safety_gate.evaluate_safety_gate(
            data_quality_score=dq_score,
            confidence_pct=conf_res["overall_confidence_pct"],
            model_consensus_score=consensus_res["model_consensus_score"],
            priority_score=scores_res["priority_score"]
        )

        # Grounded SHAP Attribution Evidence (derived from actual models)
        # SHAP values must come from a fitted model explanation, never fixed demo numbers.
        shap_evidence = []

        # Why / Why Not Explanation Logic
        why_explanation = (
            f"Actual electricity consumption in {building_id} ({actual_kwh} kWh) exceeded contextual baseline ({expected_kwh} kWh) by +{dev_res['percentage_deviation_pct']}%. "
            f"Contextual baseline evidence reports {'anomalous' if dev_res['is_contextual_anomaly'] else 'within range'} behavior. "
            f"Independent model consensus is {consensus_res['consensus_status'].lower()}; SHAP attribution is unavailable unless a fitted explainer ran for this request."
        )

        return {
            "trace_id": trace_id,
            "building_id": building_id,
            "actual_kwh": actual_kwh,
            "expected_kwh": expected_kwh,
            "baseline_info": base_info,
            "deviation_info": dev_res,
            "data_quality": dq_res,
            "model_consensus": consensus_res,
            "confidence": conf_res,
            "scores": scores_res,
            "business_impact": impact_res,
            "opportunities": opportunities,
            "safety_gate": safety_res,
            "shap_attribution": shap_evidence,
            "shap_attribution_status": "UNAVAILABLE_NO_MODEL_EXPLANATION",
            "why_explanation": why_explanation,
            "provenance": "ESTATEIQ_INTELLIGENCE_FUSION_ENGINE"
        }
