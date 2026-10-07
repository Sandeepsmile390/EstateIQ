"""
Closed-Loop Action Center & Intervention Lifecycle Engine (src/decisions/action_center.py).
Manages authorized operational interventions through a strict state machine:
NEW -> REVIEWED -> APPROVED -> ASSIGNED -> EXECUTED -> VERIFIED.
Includes audit tracking, verification evidence recording, and physical control disclaimers.
"""

import time
import pandas as pd
from typing import Dict, Any, List, Optional
from fastapi import HTTPException, status

ACTION_STATE_FLOW = {
    "NEW": ["REVIEWED", "DISMISSED"],
    "REVIEWED": ["APPROVED", "DISMISSED"],
    "APPROVED": ["ASSIGNED", "EXECUTED"],
    "ASSIGNED": ["EXECUTED"],
    "EXECUTED": ["VERIFIED"],
    "VERIFIED": [],
    "DISMISSED": []
}

# In-memory store of actions (persisted to log/DB in production)
ACTIONS_REGISTRY: Dict[str, Dict[str, Any]] = {
    "ACT_HVAC_01": {
        "action_id": "ACT_HVAC_01",
        "recommendation_id": "REC_HVAC_01",
        "title": "HVAC Thermostat Setpoint Reset in Block B Hostel",
        "facility_id": "FAC_GEC_01",
        "building_id": "Block_B_Hostel",
        "category": "Energy Optimization",
        "status": "APPROVED",
        "created_by": "lead@estateiq.in",
        "approved_by": "admin@estateiq.in",
        "assigned_to": "alex.chen@estateiq.in",
        "expected_kwh_reduction": 18.5,
        "expected_annual_savings_inr": 1150000,
        "is_simulation_only": True,
        "disclaimer": "Simulated operational action. No physical BMS signal transmitted without hardware gateway.",
        "history": [
            {"status": "NEW", "timestamp": "2026-10-04T08:00:00", "actor": "system"},
            {"status": "REVIEWED", "timestamp": "2026-10-04T09:15:00", "actor": "alex.chen@estateiq.in"},
            {"status": "APPROVED", "timestamp": "2026-10-04T10:00:00", "actor": "admin@estateiq.in"}
        ]
    }
}

class ActionCenterEngine:
    def list_actions(self, facility_id: Optional[str] = None) -> List[Dict[str, Any]]:
        actions = list(ACTIONS_REGISTRY.values())
        if facility_id:
            actions = [a for a in actions if a.get("facility_id") == facility_id]
        return actions

    def get_action(self, action_id: str) -> Dict[str, Any]:
        if action_id not in ACTIONS_REGISTRY:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Action '{action_id}' not found.")
        return ACTIONS_REGISTRY[action_id]

    def update_action_status(
        self,
        action_id: str,
        target_status: str,
        actor: str,
        notes: str = "",
        verification_evidence: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        action = self.get_action(action_id)
        current_status = action["status"]
        allowed_next = ACTION_STATE_FLOW.get(current_status, [])

        if target_status not in allowed_next:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid state transition from '{current_status}' to '{target_status}'. Allowed transitions: {allowed_next}"
            )

        action["status"] = target_status
        history_entry = {
            "status": target_status,
            "timestamp": pd.Timestamp.now().isoformat(),
            "actor": actor,
            "notes": notes
        }
        action.setdefault("history", []).append(history_entry)

        if target_status == "EXECUTED":
            action["executed_by"] = actor
            action["executed_at"] = pd.Timestamp.now().isoformat()
            action["simulated_execution_recorded"] = True

        if target_status == "VERIFIED" and verification_evidence:
            action["verification_evidence"] = verification_evidence
            action["verified_by"] = actor
            action["verified_at"] = pd.Timestamp.now().isoformat()

        ACTIONS_REGISTRY[action_id] = action
        return action

    def create_action_from_recommendation(
        self,
        recommendation_id: str,
        building_id: str,
        facility_id: str,
        title: str,
        actor: str,
        expected_kwh_reduction: float = 15.0
    ) -> Dict[str, Any]:
        action_id = f"ACT_{int(time.time())}"
        new_action = {
            "action_id": action_id,
            "recommendation_id": recommendation_id,
            "title": title,
            "facility_id": facility_id,
            "building_id": building_id,
            "category": "Operational Intervention",
            "status": "NEW",
            "created_by": actor,
            "expected_kwh_reduction": expected_kwh_reduction,
            "is_simulation_only": True,
            "disclaimer": "Simulated operational action. No physical BMS signal transmitted without hardware gateway integration.",
            "history": [
                {"status": "NEW", "timestamp": pd.Timestamp.now().isoformat(), "actor": actor}
            ]
        }
        ACTIONS_REGISTRY[action_id] = new_action
        return new_action
