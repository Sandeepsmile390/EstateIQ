"""
AI Context Builder (src/ai/context_builder.py).
Fetches real EstateIQ telemetry, runs baseline calculations, DIF analysis, SHAP driver extraction,
and What-If scenario simulation to build authoritative grounded evidence packets for AI reasoning.
"""

import datetime
from typing import Dict, Any, Optional, List
from src.data.repository import DataRepository, ProvenanceType
from src.intelligence.dif_engine import EstateIQDIF
from src.intelligence.types import EventData, DecisionResult
from src.scenarios.whatif import WhatIfScenarioEngine

class AIContextBuilder:
    """Master Context Builder for EstateIQ AI Copilot grounding."""

    def __init__(self):
        self.repo = DataRepository()
        self.dif_engine = EstateIQDIF()
        self.whatif_engine = WhatIfScenarioEngine()

    def build_ai_context(
        self,
        facility_id: str = "FAC_GEC_CAMPUS",
        user_query: str = "",
        building_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Gathers real EstateIQ facility telemetry and runs DIF engine to produce grounded evidence."""

        query_lower = user_query.lower()
        target_building = building_id or self._extract_building_id(query_lower)

        # 1. Fetch latest energy telemetry from database repository
        latest_energy = self.repo.get_latest_energy(building_id=target_building)
        
        actual_kwh = float(latest_energy.get("energy_kwh", 145.2))
        temperature = float(latest_energy.get("temperature", 32.0))
        occupancy = int(latest_energy.get("occupancy", 140))
        hvac_load = float(latest_energy.get("hvac_power_kw", 58.0))
        timestamp = str(latest_energy.get("timestamp", datetime.datetime.now().isoformat()))
        prov_type = str(latest_energy.get("provenance", "SIMULATED_IoT"))

        now = datetime.datetime.now()
        event = EventData(
            event_id=f"EVT_CTX_{now.strftime('%Y%m%d%H%M%S')}",
            facility_id=facility_id,
            building_id=target_building,
            timestamp=timestamp,
            actual_kwh=actual_kwh,
            hour=now.hour,
            day_of_week=now.weekday(),
            occupancy=occupancy,
            temperature=temperature,
            hvac_load=hvac_load
        )

        # 2. Run DIF analysis engine
        decision: DecisionResult = self.dif_engine.analyze(event)

        # 3. Determine query category
        category = self._classify_query_category(query_lower)

        # 4. Assemble Grounded Evidence Packet
        evidence = {
            "query_meta": {
                "user_query": user_query,
                "category": category,
                "facility_id": facility_id,
                "building_id": target_building,
                "analyzed_at": now.strftime("%Y-%m-%d %H:%M:%S"),
                "data_through": timestamp,
                "data_source": "SIMULATED IoT" if "SIMULATED" in prov_type.upper() else "REAL SENSOR"
            },
            "facility": {
                "facility_id": facility_id,
                "building_id": target_building,
                "timestamp": timestamp
            },
            "data_quality": {
                "quality_score": decision.quality.overall_quality_score,
                "sensor_reliability": decision.quality.sensor_reliability,
                "is_insufficient": decision.quality.is_insufficient
            },
            "telemetry_observed": {
                "actual_kwh": round(event.actual_kwh, 2),
                "occupancy": event.occupancy,
                "temperature_c": round(event.temperature, 1),
                "hvac_load_kw": round(event.hvac_load, 1)
            },
            "contextual_baseline": {
                "expected_kwh": round(decision.contextual.expected_kwh, 2),
                "residual_kwh": round(decision.contextual.residual_kwh, 2),
                "relative_deviation_pct": round(decision.contextual.relative_deviation_pct, 1)
            },
            "anomaly_evidence": {
                "anomaly_score": round(decision.anomaly.anomaly_score, 3),
                "anomaly_level": decision.anomaly.anomaly_level.value,
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
                "daily_co2_surge_kg": round(decision.impact.daily_co2_surge_kg, 2),
                "annual_co2_surge_tons": round(decision.impact.annual_co2_surge_tons, 2)
            },
            "decision_intelligence": {
                "decision_score": round(decision.decision_score, 1),
                "priority": decision.priority.value,
                "execution_path": decision.execution_path.value
            },
            "shap_attribution": decision.shap_attribution,
            "recommended_actions": [
                {
                    "action_id": r.action_id,
                    "title": r.title,
                    "expected_cost_saving_inr": round(r.expected_cost_saving_inr, 2),
                    "effort": r.effort
                }
                for r in decision.recommendations
            ]
        }

        # 5. If query relates to What-If simulation, execute scenario engine
        if category == "what_if_simulation":
            sim_res = self.whatif_engine.simulate_hvac_setback(
                baseline_kwh=actual_kwh,
                setback_percent=20.0,
                tariff_rate_inr=9.50
            )
            evidence["what_if_scenario"] = sim_res

        return evidence

    def _extract_building_id(self, query_lower: str) -> str:
        """Extract target building ID from query text or return default."""
        if "block b" in query_lower or "hostel b" in query_lower:
            return "Block B Hostel"
        elif "hostel a" in query_lower:
            return "Hostel A"
        elif "cafeteria" in query_lower:
            return "Central Cafeteria"
        elif "admin" in query_lower:
            return "Admin Block"
        return "Block B Hostel"

    def _classify_query_category(self, query_lower: str) -> str:
        """Classify user query into operational categories."""
        if any(w in query_lower for w in ["what if", "simulate", "reduce", "setback", "solar", "curtail"]):
            return "what_if_simulation"
        elif any(w in query_lower for w in ["energy", "kwh", "surge", "anomaly", "electricity", "power", "high"]):
            return "energy_anomaly_analysis"
        elif any(w in query_lower for w in ["waste", "bin", "overflow", "cafeteria"]):
            return "waste_management_audit"
        elif any(w in query_lower for w in ["water", "leak", "pipe", "flow"]):
            return "water_flow_audit"
        elif any(w in query_lower for w in ["chiller", "vibration", "equipment", "maintenance", "ahu"]):
            return "equipment_health_audit"
        elif any(w in query_lower for w in ["carbon", "scope", "emission", "esg", "co2"]):
            return "carbon_sustainability_audit"
        elif any(w in query_lower for w in ["recommend", "action", "do", "fix", "mitigate"]):
            return "recommendation_triage"
        return "general_facility_overview"

build_ai_context = AIContextBuilder().build_ai_context
