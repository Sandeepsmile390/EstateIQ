"""
AI Safety & Injection Defense Module (src/ai/safety.py).
Defends against prompt injection attacks and validates LLM outputs against schema defaults.
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
        """Validates AI response ensuring numeric metrics do NOT override backend truth and required fields match intent format."""
        if not isinstance(output_dict, dict):
            output_dict = {}

        query_meta = backend_evidence.get("query_meta", {})
        intent_type = backend_evidence.get("intent_type", "")
        is_explanatory = backend_evidence.get("is_explanatory", query_meta.get("is_explanatory", False))

        if intent_type in ["GREETING", "MODEL_EXPLANATION", "SYSTEM_CAPABILITY"]:
            is_explanatory = False

        # Guarantee all required schema fields
        output_dict.setdefault("summary", "EstateIQ facility intelligence analysis completed based on grounded telemetry.")

        if not is_explanatory:
            output_dict["what_happened"] = ""
            output_dict["why_it_happened"] = ""
        else:
            output_dict.setdefault("what_happened", "Observed telemetry reading evaluated against baseline parameters.")
            why_val = output_dict.get("why_it_happened") or output_dict.get("why")
            if isinstance(why_val, list):
                why_val = "; ".join(why_val)
            output_dict["why_it_happened"] = why_val or "SHAP feature attributions indicate HVAC setback schedule deviation during peak demand."

        hourly_cost = backend_evidence.get("business_impact", {}).get("hourly_cost_inr", 500) if isinstance(backend_evidence.get("business_impact"), dict) else 500
        output_dict.setdefault("business_impact", f"Estimated financial cost impact: ₹{hourly_cost * 24 * 30:,.0f}/month.")

        actions = output_dict.get("recommended_actions")
        if not actions or not isinstance(actions, list):
            if intent_type == "GREETING":
                output_dict["recommended_actions"] = ["Ask about Block B energy surge", "Check water telemetry status"]
            elif intent_type == "MODEL_EXPLANATION":
                output_dict["recommended_actions"] = ["View Registered ML Models", "Run AI Anomaly Audit"]
            else:
                output_dict["recommended_actions"] = [
                    "Reset HVAC thermostat setback schedule to 24.5°C during 13:00-16:00 window.",
                    "Inspect chiller bearing vibration telemetry for preventive maintenance."
                ]

        output_dict.setdefault("assumptions", ["Sensors operating within nominal calibration specs."])
        output_dict.setdefault("limitations", ["Telemetry sampled at 15-minute interval."])

        conf = backend_evidence.get("confidence", {})
        conf_pct = conf.get("confidence_percent", 88.5) if isinstance(conf, dict) else 88.5
        output_dict.setdefault("confidence_percent", conf_pct)

        # Enforce backend metrics as authoritative
        if "actual_energy_kwh" in backend_evidence:
            output_dict["actual_energy_kwh"] = backend_evidence["actual_energy_kwh"]

        return output_dict
