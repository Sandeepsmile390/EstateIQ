"""
EstateIQ-DIF Master Algorithm Implementation (src/intelligence/dif_engine.py).
Dynamic Intelligence Fusion Engine with Adaptive Execution (Path A, Path B, Path C).
"""

import time
import uuid
import math
from datetime import datetime
import copy
import pandas as pd
from typing import Dict, Any, List, Optional

from src.intelligence.config import DIFConfig
from src.intelligence.types import (
    EventData, QualityResult, ContextualResult, PredictionResult,
    AnomalyResult, ConfidenceResult, ImpactResult, RiskResult,
    OpportunityResult, RecommendationCandidate, DecisionResult,
    ExecutionPath, AnomalyLevel, PriorityLevel
)
from src.data_quality.quality_score import DataQualityEngine
from src.intelligence.context_filter import EstateIQContextFilter
from src.intelligence.adaptive_ensemble import EstateIQAdaptiveEnsemble
from src.intelligence.anomaly_consensus import EstateIQAnomalyConsensus
from src.intelligence.confidence_engine import EstateIQConfidenceIntelligence
from src.intelligence.business_impact import IntelligenceBusinessImpactEngine
from src.intelligence.decision_engine import EstateIQDecisionEngine
from src.intelligence.complexity_monitor import ComplexityMonitor
from src.intelligence.seasonal_baseline import SeasonalBaselineModel

class EstateIQDIF:
    """Master EstateIQ-DIF Dynamic Intelligence Fusion Algorithm."""

    def __init__(
        self,
        config: DIFConfig = None,
        baseline_model: Optional[Any] = None,
        sensor_health_engine: Optional[Any] = None,
        anomaly_threshold: Optional[float] = None,
    ):
        self.config = copy.copy(config) if config else DIFConfig()
        if anomaly_threshold is not None:
            self.config.anomaly_score_threshold = float(anomaly_threshold)
        self.quality_engine = DataQualityEngine()
        self.baseline_model = baseline_model
        self.sensor_health_engine = sensor_health_engine
        self.context_filter = EstateIQContextFilter(self.config)
        self.adaptive_ensemble = EstateIQAdaptiveEnsemble(self.config)
        self.anomaly_consensus = EstateIQAnomalyConsensus(self.config)
        self.confidence_engine = EstateIQConfidenceIntelligence(self.config)
        self.business_impact = IntelligenceBusinessImpactEngine(self.config.default_tariff_inr_kwh, grid_emission_factor_kg_kwh=self.config.default_emission_factor_kg_kwh)
        self.decision_engine = EstateIQDecisionEngine(self.config)
        self.monitor = ComplexityMonitor()

    def analyze(
        self,
        event: EventData,
        df_telemetry: pd.DataFrame = None
    ) -> DecisionResult:
        start_time = time.perf_counter()
        trace_id = f"TRC_DIF_{uuid.uuid4().hex[:8].upper()}"

        # 1. Data Quality Evaluation
        if df_telemetry is not None and not df_telemetry.empty:
            dq_res = self.quality_engine.evaluate_telemetry(df_telemetry)
            quality = QualityResult(
                overall_quality_score=dq_res["overall_data_quality_score"],
                completeness=dq_res["data_completeness_pct"],
                freshness=dq_res["data_freshness_pct"],
                consistency=dq_res["data_consistency_pct"],
                sensor_reliability=dq_res["sensor_reliability_score"],
                is_insufficient=dq_res["overall_data_quality_score"] < self.config.min_data_quality_score
            )
        else:
            quality = self._evaluate_event_quality(event)

        if quality.is_insufficient:
            return self._insufficient_data_result(event, trace_id, quality)

        # 2. ECF — EstateIQ Context Filter (Early Exit Check)
        contextual = self.context_filter.evaluate(event, self.baseline_model)

        # PATH A — FAST PATH (Early Exit for Normal Telemetry)
        if contextual.early_exit:
            self.anomaly_consensus.record_normal(event)
            duration_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
            self.monitor.record_execution("PATH_A_FAST", early_exit=True, shap_executed=False, duration_ms=duration_ms)
            return self._fast_path_result(event, trace_id, quality, contextual)

        # 3. Determine Execution Path (Path B vs Path C)
        z_score = abs(contextual.residual_kwh) / max(contextual.std_dev, self.config.epsilon)
        is_critical = (
            abs(contextual.relative_deviation_pct) > self.config.critical_deviation_threshold_pct
            or z_score >= self.config.critical_zscore_threshold
        )
        path = ExecutionPath.CRITICAL_PATH if is_critical else ExecutionPath.INTELLIGENCE_PATH

        # 4. EAE — Adaptive Ensemble (Run Champion + Challengers if critical/low confidence)
        prediction = self.adaptive_ensemble.predict(event, contextual, run_challengers=(path == ExecutionPath.CRITICAL_PATH))

        # 5. EAC — Anomaly Consensus
        anomaly = self.anomaly_consensus.evaluate(event, contextual, prediction)

        # 6. ECI — Confidence Intelligence
        confidence = self.confidence_engine.calculate(quality, anomaly)

        # 7. EBI — Business Impact & Cost of Inaction
        impact_raw = self.business_impact.calculate_surge_impact(
            event.actual_kwh, contextual.expected_kwh, duration_hours=event.interval_hours
        )
        coi = impact_raw["cost_of_inaction"]
        impact = ImpactResult(
            surge_kwh=impact_raw["residual_surge_kwh"],
            hourly_avoidable_cost_inr=impact_raw["hourly_cost_impact_inr"],
            daily_avoidable_cost_inr=coi["daily_cost_inaction_inr"],
            annual_cost_of_inaction_inr=coi["annualized_cost_inaction_inr"],
            daily_co2_surge_kg=round(impact_raw["hourly_co2_impact_kg"] * 24.0, 2),
            annual_co2_surge_tons=impact_raw["annual_co2_impact_tons"]
        )

        # 8. Operational Risk Engine
        risk_score = round(min(100.0, (anomaly.anomaly_score * 0.6) + (impact.annual_cost_of_inaction_inr / 10000.0)), 1)
        risk = RiskResult(
            risk_score=risk_score,
            risk_level="HIGH" if risk_score >= 70.0 else ("MEDIUM" if risk_score >= 40.0 else "LOW"),
            risk_factors=anomaly.evidence
        )

        # 9. Opportunity Engine
        # No action catalog or measured savings model is currently connected.
        opportunities = []

        # 10. EDI — Decision Engine
        dec_info = self.decision_engine.evaluate(contextual, anomaly, confidence, impact, risk)

        # No model-backed feature attribution is available; rule evidence is returned above.
        shap_attribution = []
        models_skipped = ["trained ensemble", "Isolation Forest", "LOF", "SHAP", "validated action catalog"]

        duration_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
        self.monitor.record_execution(path.value, early_exit=False, shap_executed=len(shap_attribution) > 0, duration_ms=duration_ms)

        return DecisionResult(
            event_id=event.event_id,
            trace_id=trace_id,
            execution_path=path,
            quality=quality,
            contextual=contextual,
            prediction=prediction,
            anomaly=anomaly,
            confidence=confidence,
            impact=impact,
            risk=risk,
            opportunities=opportunities,
            decision_score=dec_info["decision_score"],
            priority=dec_info["priority"],
            recommendations=[],
            shap_attribution=shap_attribution,
            models_skipped=models_skipped,
        )

    def _fast_path_result(self, event: EventData, trace_id: str, quality: QualityResult, contextual: ContextualResult) -> DecisionResult:
        anomaly = AnomalyResult(anomaly_score=0.0, anomaly_level=AnomalyLevel.NORMAL, evidence=["No configured contextual or domain rule exceeded its trigger"], model_agreement_pct=0.0)
        confidence = self.confidence_engine.calculate(quality, anomaly)
        impact = ImpactResult(surge_kwh=0.0, hourly_avoidable_cost_inr=0.0, daily_avoidable_cost_inr=0.0, annual_cost_of_inaction_inr=0.0, daily_co2_surge_kg=0.0, annual_co2_surge_tons=0.0)
        risk = RiskResult(risk_score=0.0, risk_level="LOW", risk_factors=[])

        return DecisionResult(
            event_id=event.event_id, trace_id=trace_id, execution_path=ExecutionPath.FAST_PATH,
            quality=quality, contextual=contextual, prediction=None, anomaly=anomaly,
            confidence=confidence, impact=impact, risk=risk, opportunities=[],
            decision_score=0.0, priority=PriorityLevel.P4_LOW, recommendations=[],
            models_skipped=["trained ensemble", "Isolation Forest", "LOF", "SHAP"]
        )

    @staticmethod
    def _evaluate_event_quality(event: EventData) -> QualityResult:
        """Conservative single-record quality check when no telemetry window is supplied."""
        try:
            numeric_values = (event.actual_kwh, event.occupancy, event.temperature, event.hvac_load, event.interval_hours)
            finite = all(math.isfinite(float(value)) for value in numeric_values)
            ranges_valid = (
                event.actual_kwh >= 0 and event.occupancy >= 0
                and -10 <= event.temperature <= 60 and event.hvac_load >= 0
                and 0 < event.interval_hours <= 24
                and 0 <= event.hour <= 23 and 0 <= event.day_of_week <= 6
            )
        except (TypeError, ValueError):
            finite = ranges_valid = False
        try:
            datetime.fromisoformat(event.timestamp.replace("Z", "+00:00"))
            timestamp_valid = True
        except (TypeError, ValueError, AttributeError):
            timestamp_valid = False
        valid = finite and ranges_valid and timestamp_valid
        if not valid:
            return QualityResult(0.0, 0.0, 0.0, 0.0, 0.0, is_insufficient=True)
        # A single event cannot establish freshness or historical sensor health.
        return QualityResult(82.5, 100.0, 50.0, 100.0, 50.0, is_insufficient=False)

    def _insufficient_data_result(self, event: EventData, trace_id: str, quality: QualityResult) -> DecisionResult:
        contextual = ContextualResult(expected_kwh=0.0, std_dev=0.0, residual_kwh=0.0, relative_deviation_pct=0.0, contextual_score=0.0, early_exit=False, early_exit_reason="Insufficient Data Quality")
        anomaly = AnomalyResult(anomaly_score=0.0, anomaly_level=AnomalyLevel.NORMAL, evidence=["Insufficient Data Quality"], model_agreement_pct=0.0)
        confidence = ConfidenceResult(confidence_pct=30.0, confidence_level="LOW", gate_passed=False)
        impact = ImpactResult(surge_kwh=0.0, hourly_avoidable_cost_inr=0.0, daily_avoidable_cost_inr=0.0, annual_cost_of_inaction_inr=0.0, daily_co2_surge_kg=0.0, annual_co2_surge_tons=0.0)
        risk = RiskResult(risk_score=0.0, risk_level="LOW", risk_factors=["Insufficient sensor data quality"])

        return DecisionResult(
            event_id=event.event_id, trace_id=trace_id, execution_path=ExecutionPath.FAST_PATH,
            quality=quality, contextual=contextual, prediction=None, anomaly=anomaly,
            confidence=confidence, impact=impact, risk=risk, opportunities=[],
            decision_score=0.0, priority=PriorityLevel.P4_LOW, recommendations=[]
        )
