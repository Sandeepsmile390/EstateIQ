"""
Data Requirement Planner (src/ai/data_planner.py).
Maps intent classification to required data retrieval plans, backend service calls,
and evidence aggregation.
"""

from typing import Dict, Any, List, Optional
from src.ai.query_router import IntentCategory, QueryRouteResult
from src.ai.backend_services import EstateIQBackendServices

class DataRequirementPlanner:
    """Plans and executes dynamic backend data retrieval tailored to query intent."""

    def __init__(self):
        self.backend = EstateIQBackendServices()

    def plan_and_fetch(self, route: QueryRouteResult, user_query: str) -> Dict[str, Any]:
        intent = route.intent
        bld = route.target_building

        # 1. System Capabilities
        if intent == IntentCategory.SYSTEM_CAPABILITY:
            return {
                "intent": intent.value,
                "data_type": "SYSTEM_CAPABILITIES",
                "capabilities": self.backend.get_system_capabilities(),
                "query_meta": {"is_analytical": False, "requires_telemetry": False}
            }

        # 2. Project Explanation
        if intent == IntentCategory.PROJECT_EXPLANATION:
            return {
                "intent": intent.value,
                "data_type": "PROJECT_KNOWLEDGE",
                "knowledge": self.backend.get_project_knowledge(),
                "query_meta": {"is_analytical": False, "requires_telemetry": False}
            }

        # 3. Priority Action ("What should I fix first?")
        if intent in [IntentCategory.PRIORITY_ACTION, IntentCategory.RECOMMENDATION]:
            opportunities = self.backend.get_top_opportunities()
            energy_sum = self.backend.get_energy_summary(bld)
            return {
                "intent": intent.value,
                "data_type": "RECOMMENDATIONS_TRIAGE",
                "top_opportunity": opportunities[0],
                "all_opportunities": opportunities,
                "energy_context": energy_sum,
                "query_meta": {"is_analytical": True, "requires_telemetry": True}
            }

        # 4. What-If Simulation
        if intent == IntentCategory.WHAT_IF:
            sim_res = self.backend.run_what_if_scenario(setback_percent=20.0)
            return {
                "intent": intent.value,
                "data_type": "WHAT_IF_SCENARIO",
                "simulation": sim_res,
                "query_meta": {"is_analytical": True, "requires_telemetry": True}
            }

        # 5. Executive Overview / Multi-Domain
        if intent == IntentCategory.FACILITY_OVERVIEW or route.is_multi_domain:
            return {
                "intent": intent.value,
                "data_type": "FACILITY_EXECUTIVE_OVERVIEW",
                "overview": self.backend.get_facility_overview(bld),
                "top_opportunities": self.backend.get_top_opportunities(),
                "query_meta": {"is_analytical": True, "requires_telemetry": True}
            }

        # 6. Domain Specific Retrieval
        if intent in [IntentCategory.WATER]:
            return {
                "intent": intent.value,
                "data_type": "WATER_FLOW_AUDIT",
                "water": self.backend.get_water_summary(bld),
                "query_meta": {"is_analytical": True, "requires_telemetry": True}
            }

        if intent in [IntentCategory.WASTE]:
            return {
                "intent": intent.value,
                "data_type": "WASTE_MANAGEMENT_AUDIT",
                "waste": self.backend.get_waste_summary(),
                "query_meta": {"is_analytical": True, "requires_telemetry": True}
            }

        if intent in [IntentCategory.AIR_QUALITY]:
            return {
                "intent": intent.value,
                "data_type": "AIR_QUALITY_AUDIT",
                "air_quality": self.backend.get_air_quality_summary(),
                "query_meta": {"is_analytical": True, "requires_telemetry": True}
            }

        if intent in [IntentCategory.TRAFFIC]:
            return {
                "intent": intent.value,
                "data_type": "TRAFFIC_ENTRY_AUDIT",
                "traffic": self.backend.get_traffic_summary(),
                "query_meta": {"is_analytical": True, "requires_telemetry": True}
            }

        if intent in [IntentCategory.PARKING]:
            return {
                "intent": intent.value,
                "data_type": "PARKING_OCCUPANCY_AUDIT",
                "parking": self.backend.get_parking_summary(),
                "query_meta": {"is_analytical": True, "requires_telemetry": True}
            }

        if intent in [IntentCategory.EQUIPMENT, IntentCategory.ASSETS]:
            return {
                "intent": intent.value,
                "data_type": "EQUIPMENT_HEALTH_AUDIT",
                "equipment": self.backend.get_equipment_summary(),
                "query_meta": {"is_analytical": True, "requires_telemetry": True}
            }

        if intent in [IntentCategory.SAFETY]:
            return {
                "intent": intent.value,
                "data_type": "SAFETY_INCIDENT_AUDIT",
                "safety": self.backend.get_safety_summary(),
                "query_meta": {"is_analytical": True, "requires_telemetry": True}
            }

        if intent in [IntentCategory.EMISSIONS]:
            return {
                "intent": intent.value,
                "data_type": "CARBON_EMISSIONS_AUDIT",
                "emissions": self.backend.get_emissions_summary(),
                "query_meta": {"is_analytical": True, "requires_telemetry": True}
            }

        if intent in [IntentCategory.SUSTAINABILITY]:
            return {
                "intent": intent.value,
                "data_type": "SUSTAINABILITY_SCORECARD",
                "sustainability": self.backend.get_sustainability_score(),
                "query_meta": {"is_analytical": True, "requires_telemetry": True}
            }

        if intent in [IntentCategory.DATASET]:
            return {
                "intent": intent.value,
                "data_type": "DATASET_METADATA",
                "dataset": self.backend.get_dataset_metadata(),
                "query_meta": {"is_analytical": False, "requires_telemetry": True}
            }

        # Default: Energy & Anomaly Audit
        return {
            "intent": intent.value,
            "data_type": "ENERGY_ANOMALY_AUDIT",
            "energy": self.backend.get_energy_summary(bld),
            "query_meta": {"is_analytical": True, "requires_telemetry": True}
        }
