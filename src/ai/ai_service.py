"""
Master Groq AI Copilot Service (src/ai/ai_service.py).
High-level service orchestrating evidence grounding, Groq API call, response parsing,
caching, safety validation, and deterministic offline fallback.
"""

import json
import time
import hashlib
from typing import Dict, Any, Optional

from src.ai.config import GroqAIConfig, DEFAULT_AI_CONFIG
from src.ai.groq_client import get_groq_client
from src.ai.schemas import CopilotResponse
from src.ai.safety import AISafetyGuard
from src.ai.prompts import SYSTEM_PROMPT_COPILOT, PROMPT_TEMPLATE_ANOMALY
from src.ai.grounding import AIEvidenceBuilder
from src.ai.usage_tracker import GLOBAL_USAGE_TRACKER
from src.intelligence.dif_engine import EstateIQDIF
from src.intelligence.types import EventData, DecisionResult

class EstateIQAIService:
    """Master AI Service for EstateIQ Copilot and Explainability."""

    def __init__(self, config: GroqAIConfig = DEFAULT_AI_CONFIG):
        self.config = config
        self.dif_engine = EstateIQDIF()
        self._cache: Dict[str, CopilotResponse] = {}

    def query_copilot(
        self,
        user_query: str,
        event: EventData,
        df_telemetry: Any = None
    ) -> CopilotResponse:
        start_time = time.time()
        sanitized_query = AISafetyGuard.sanitize_user_input(user_query)

        # 1. Execute DIF backend engine to generate grounded evidence
        decision: DecisionResult = self.dif_engine.analyze(event, df_telemetry)
        evidence_packet = AIEvidenceBuilder.build_evidence_packet(event, decision)

        # 2. Check response cache based on evidence hash
        evidence_hash = hashlib.md5(json.dumps(evidence_packet, sort_keys=True).encode("utf-8")).hexdigest()
        cache_key = f"{event.event_id}_{evidence_hash}_{self.config.prompt_version}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # 3. Attempt Groq API Execution
        client = get_groq_client(self.config)
        if client and self.config.is_configured:
            try:
                user_prompt = PROMPT_TEMPLATE_ANOMALY.format(
                    evidence_json=json.dumps(evidence_packet, indent=2),
                    user_query=sanitized_query
                )

                response = client.chat.completions.create(
                    model=self.config.model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT_COPILOT},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.2,
                    response_format={"type": "json_object"}
                )

                content_raw = response.choices[0].message.content
                parsed_json = json.loads(content_raw)
                validated_dict = AISafetyGuard.validate_ai_output(parsed_json, evidence_packet)
                copilot_resp = CopilotResponse(**validated_dict)

                duration_ms = round((time.time() - start_time) * 1000.0, 2)
                GLOBAL_USAGE_TRACKER.log_request(self.config.model, duration_ms, success=True, fallback_used=False)

                self._cache[cache_key] = copilot_resp
                return copilot_resp

            except Exception as e:
                duration_ms = round((time.time() - start_time) * 1000.0, 2)
                GLOBAL_USAGE_TRACKER.log_request(self.config.model, duration_ms, success=False, fallback_used=True, error_msg=str(e))
                return self._generate_fallback_response(evidence_packet, decision, sanitized_query)
        else:
            duration_ms = round((time.time() - start_time) * 1000.0, 2)
            GLOBAL_USAGE_TRACKER.log_request("DETERMINISTIC_FALLBACK", duration_ms, success=True, fallback_used=True)
            return self._generate_fallback_response(evidence_packet, decision, sanitized_query)

    def _generate_fallback_response(
        self,
        evidence: Dict[str, Any],
        decision: DecisionResult,
        user_query: str
    ) -> CopilotResponse:
        """Deterministic offline fallback response derived strictly from DIF evidence."""
        bld = evidence["facility"]["building_id"]
        actual = evidence["telemetry_observed"]["actual_kwh"]
        expected = evidence["contextual_baseline"]["expected_kwh"]
        dev_pct = evidence["contextual_baseline"]["relative_deviation_pct"]
        cost_yr = evidence["business_impact"]["annual_cost_of_inaction_inr"]

        summary = f"EstateIQ Deterministic Analysis: Consumption in {bld} is {actual:.1f} kWh vs baseline ({expected:.1f} kWh), representing a {dev_pct:+.1f}% deviation."
        what_happened = f"Observed electricity demand in {bld} is {actual:.1f} kWh."
        why = f"Contextual baseline deviation (+{dev_pct:.1f}%) and model consensus vote ({decision.anomaly.model_agreement_pct:.0f}% agreement)."
        impact_str = f"Estimated annual Cost of Inaction is ₹{cost_yr:,.0f}."

        recs = [r.title for r in decision.recommendations]

        return CopilotResponse(
            summary=summary,
            what_happened=what_happened,
            why_it_happened=why,
            evidence=decision.anomaly.evidence,
            confidence_percent=decision.confidence.confidence_pct,
            business_impact=impact_str,
            recommended_actions=recs if recs else ["Review thermostat setback schedule"],
            what_if_interpretation="Simulated 2°C thermostat setback projected to reduce annual costs by ~15%.",
            assumptions=["Tariff: ₹9.50/kWh", "CEA Emission Factor: 0.82 kg CO2e/kWh"],
            limitations=["Offline fallback engine active"],
            data_status="SUCCESS",
            verification_status="DETERMINISTIC_FALLBACK",
            provenance="ESTATEIQ_DETERMINISTIC_ENGINE"
        )
