"""
EstateIQ Decision Memory & Feedback Store (src/decisions/decision_memory.py).
Persists operational decisions, human approvals/rejections, rejection reasons,
and closed-loop post-action verification outcomes for continuous calibration.
"""

import time
import uuid
from typing import Dict, Any, List, Optional

class DecisionMemoryStore:
    """In-memory & persistent store for decision lifecycle events."""
    
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DecisionMemoryStore, cls).__new__(cls)
            cls._instance.decisions = {}
            cls._instance.action_history = []
        return cls._instance

    def record_decision(self, decision_data: Dict[str, Any]) -> str:
        """Stores decision record and returns unique decision ID."""
        d_id = decision_data.get("decision_id", f"DEC_{uuid.uuid4().hex[:8].upper()}")
        decision_data["decision_id"] = d_id
        decision_data["recorded_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        decision_data["status"] = decision_data.get("status", "RECOMMENDED")
        self.decisions[d_id] = decision_data
        return d_id

    def update_human_feedback(
        self,
        decision_id: str,
        user: str,
        action_status: str, # "APPROVED", "REJECTED", "POSTPONED"
        rejection_reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Records human-in-the-loop approval or rejection feedback."""
        if decision_id not in self.decisions:
            # Create default record if missing
            self.decisions[decision_id] = {
                "decision_id": decision_id,
                "recorded_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }
        
        d = self.decisions[decision_id]
        d["status"] = action_status
        d["approved_by"] = user
        d["action_timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
        if rejection_reason:
            d["rejection_reason"] = rejection_reason

        self.action_history.append({
            "decision_id": decision_id,
            "user": user,
            "status": action_status,
            "timestamp": d["action_timestamp"]
        })
        return d

    def get_decision(self, decision_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves decision record by ID."""
        return self.decisions.get(decision_id)

    def list_recent_decisions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Returns recent decision records."""
        return list(self.decisions.values())[-limit:]
