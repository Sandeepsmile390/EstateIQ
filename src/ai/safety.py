"""
AI Safety & Injection Defense Module (src/ai/safety.py).
Defends against prompt injection attacks and validates LLM outputs.
"""

import re
from typing import Dict, Any, List

class AISafetyGuard:
    """Sanitizes inputs to prevent prompt injection and validates AI outputs."""

    INJECTION_PATTERNS = [
        r"ignore\s+previous\s+instructions",
        r"ignore\s+all\s+prior\s+prompts",
        r"system\s+prompt",
        r"you\s+are\s+now\s+a",
        r"bypass\s+safety",
        r"forget\s+everything"
    ]

    @classmethod
    def sanitize_user_input(cls, user_text: str) -> str:
        """Sanitizes user input string to prevent prompt injection attacks."""
        if not user_text:
            return ""

        sanitized = user_text.strip()
        for pattern in cls.INJECTION_PATTERNS:
            sanitized = re.sub(pattern, "[FILTERED_INSTRUCTION]", sanitized, flags=re.IGNORECASE)

        # Limit string length to 500 characters
        return sanitized[:500]

    @classmethod
    def validate_ai_output(cls, output_dict: Dict[str, Any], backend_evidence: Dict[str, Any]) -> Dict[str, Any]:
        """Validates AI response ensuring numeric metrics do NOT override backend truth."""
        # Enforce backend metrics as authoritative
        if "actual_energy_kwh" in backend_evidence:
            output_dict["actual_energy_kwh"] = backend_evidence["actual_energy_kwh"]
        if "confidence" in backend_evidence and isinstance(backend_evidence["confidence"], dict):
            output_dict["confidence_percent"] = backend_evidence["confidence"].get("confidence_percent", 87.5)

        return output_dict
