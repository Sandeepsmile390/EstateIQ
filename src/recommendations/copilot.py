"""
Tool-Based AI Copilot Engine (src/recommendations/copilot.py).
Wrapper delegating to EstateIQAIService to execute verified internal DIF tools
and formulate grounded evidence-backed responses for facility management queries.
"""

from typing import Dict, Any
from src.ai.ai_service import EstateIQAIService

class AICopilotEngine:
    """Legacy wrapper for EstateIQAIService enforcing grounded DIF execution."""

    def __init__(self):
        self.ai_service = EstateIQAIService()

    def process_query(self, user_query: str, building_id: str = "Block B Hostel") -> Dict[str, Any]:
        """Processes user query by invoking master AI service with evidence context building."""
        res = self.ai_service.query_copilot(
            user_query=user_query,
            building_id=building_id
        )

        return {
            "mode": f"Groq AI ({res.model})" if not res.fallback_used else "OFFLINE DETERMINISTIC FALLBACK",
            "query": user_query,
            "response": res.response,
            "answer": res.response,
            "summary": res.summary,
            "what_happened": res.what_happened,
            "why": res.why,
            "evidence": res.evidence,
            "recommended_actions": res.recommended_actions,
            "confidence": res.confidence / 100.0 if res.confidence > 1.0 else res.confidence,
            "fallback_used": res.fallback_used,
            "data_source_badge": res.data_source_badge,
            "assumptions": res.assumptions,
            "limitations": res.limitations
        }
