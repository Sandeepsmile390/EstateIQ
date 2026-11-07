"""
Integrated Elite Algorithm Pipeline Wrapper (elite_algo/pipeline.py).
Reuses EstateIQ's proprietary EstateIQ-DIF, contextual baseline engine, specialist ML models,
SHAP explainability, and priority decision engines to run unified facility intelligence.
"""

import os
import sys
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add main project root to sys.path to ensure src imports resolve
PACKAGE_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = PACKAGE_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.intelligence.dif_engine import EstateIQDIF
from src.intelligence.config import DIFConfig
from src.intelligence.seasonal_baseline import SeasonalBaselineModel
from src.intelligence.types import EventData, DecisionResult

class EliteAlgorithmPipeline:
    """Unified Pipeline Wrapper executing EstateIQ's Elite Decision Intelligence Engine."""

    def __init__(self, config: Optional[DIFConfig] = None,
                 baseline_model: Optional[SeasonalBaselineModel] = None):
        self.dif_engine = EstateIQDIF(config=config, baseline_model=baseline_model)

    def process_telemetry_event(
        self,
        facility_id: str = "FAC_GEC_CAMPUS",
        building_id: str = "Block B Hostel",
        timestamp: Optional[datetime.datetime] = None,
        actual_kwh: float = 145.2,
        occupancy: int = 140,
        temperature_c: float = 32.0,
        hvac_load_kw: float = 58.0,
        water_flow_lmin: float = 50.0,
        air_aqi: float = 110.0,
        interval_hours: float = 0.25
    ) -> Dict[str, Any]:
        """
        Executes the current Elite-DIF decision path. Trained-model inference,
        SHAP attribution, and validated action recommendations are not wired in.
        """
        ts = timestamp or datetime.datetime.now()
        ts_str = ts.strftime("%Y-%m-%d %H:%M:%S")
        evt_id = f"EVT_{int(ts.timestamp()*1000)}"

        event = EventData(
            event_id=evt_id,
            facility_id=facility_id,
            building_id=building_id,
            timestamp=ts_str,
            actual_kwh=actual_kwh,
            hour=ts.hour,
            day_of_week=ts.weekday(),
            occupancy=occupancy,
            temperature=temperature_c,
            hvac_load=hvac_load_kw,
            interval_hours=interval_hours
        )

        # Run primary DIF Decision Intelligence engine
        decision: DecisionResult = self.dif_engine.analyze(event)

        # Formulate structured decision dictionary
        return {
            "event_id": f"EVT_{int(ts.timestamp()*1000)}",
            "facility_id": facility_id,
            "building_id": building_id,
            "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "telemetry": {
                "actual_kwh": round(actual_kwh, 2),
                "occupancy": occupancy,
                "temperature_c": round(temperature_c, 1),
                "hvac_load_kw": round(hvac_load_kw, 1),
                "water_flow_lmin": round(water_flow_lmin, 1),
                "air_aqi": round(air_aqi, 1)
            },
            "contextual_baseline": {
                "expected_kwh": round(decision.contextual.expected_kwh, 2),
                "residual_kwh": round(decision.contextual.residual_kwh, 2),
                "relative_deviation_pct": round(decision.contextual.relative_deviation_pct, 1),
                "scale_kwh": round(decision.contextual.std_dev, 3),
                "source": decision.contextual.baseline_source,
                "training_observations": decision.contextual.baseline_observations,
                "operating_rules_triggered": decision.contextual.active_rules
            },
            "anomaly": {
                "anomaly_level": decision.anomaly.anomaly_level.value,
                "anomaly_score": round(decision.anomaly.anomaly_score, 4),
                "evidence_support_pct": round(decision.anomaly.evidence_support_pct, 1),
                "model_agreement_pct": round(decision.anomaly.model_agreement_pct, 1),
                "evidence_points": decision.anomaly.evidence
            },
            "confidence": {
                "confidence_percent": round(decision.confidence.confidence_pct, 1),
                "confidence_level": decision.confidence.confidence_level,
                "gate_passed": decision.confidence.gate_passed
            },
            "business_impact": {
                "surge_kwh": round(decision.impact.surge_kwh, 2),
                "hourly_cost_inr": round(decision.impact.hourly_avoidable_cost_inr, 2),
                "annual_cost_of_inaction_inr": round(decision.impact.annual_cost_of_inaction_inr, 2),
                "daily_co2_surge_kg": round(decision.impact.daily_co2_surge_kg, 2)
            },
            "decision_priority": {
                "decision_score": round(decision.decision_score, 1),
                "priority": decision.priority.value,
                "execution_path": decision.execution_path.value
            },
            "shap_attribution": decision.shap_attribution,
            "recommendations": [
                {
                    "action_id": r.action_id,
                    "title": r.title,
                    "expected_cost_saving_inr": round(r.expected_cost_saving_inr, 2),
                    "effort": r.effort
                }
                for r in decision.recommendations
            ]
        }

GLOBAL_ELITE_PIPELINE = EliteAlgorithmPipeline()
