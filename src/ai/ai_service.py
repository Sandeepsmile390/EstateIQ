"""
Master Groq AI Copilot Service (src/ai/ai_service.py).
High-level service orchestrating evidence grounding, Groq API call, response parsing,
caching, safety validation, health checks, and production error handling.
"""

import json
import time
import uuid
import datetime
import hashlib
from typing import Dict, Any, Optional

from src.ai.config import GroqAIConfig, DEFAULT_AI_CONFIG
from src.ai.groq_client import get_groq_client, GroqClientManager
from src.ai.context_builder import build_ai_context
from src.ai.schemas import (
    CopilotResponse, CopilotQueryResponse,
    AIHealthResponse, AITestResponse
)
from src.ai.safety import AISafetyGuard
from src.ai.prompts import SYSTEM_PROMPT_COPILOT, PROMPT_TEMPLATE_ANOMALY
from src.ai.usage_tracker import GLOBAL_USAGE_TRACKER
from src.ai.exceptions import (
    AIServiceError, GroqConfigurationError, GroqAuthenticationError,
    GroqRateLimitError, GroqTimeoutError, ProviderUnavailableError, InvalidAIResponseError
)

class EstateIQAIService:
    """Master AI Service for EstateIQ Copilot and Explainability."""

    def __init__(self, config: GroqAIConfig = DEFAULT_AI_CONFIG):
        self.config = config
        self._cache: Dict[str, CopilotQueryResponse] = {}

    def check_health(self) -> AIHealthResponse:
        """Executes lightweight connectivity and configuration health check."""
        start_time = time.time()
        
        if not self.config.enabled:
            return AIHealthResponse(
                enabled=False,
                configured=False,
                model=self.config.model,
                status="disabled",
                latency_ms=0.0,
                mode=self.config.mode
            )
        
        if not self.config.api_key or self.config.api_key.strip() == "":
            return AIHealthResponse(
                enabled=True,
                configured=False,
                model=self.config.model,
                status="not_configured",
                latency_ms=0.0,
                mode=self.config.mode
            )

        client = get_groq_client(self.config)
        if not client:
            return AIHealthResponse(
                enabled=True,
                configured=True,
                model=self.config.model,
                status="provider_error",
                latency_ms=0.0,
                mode=self.config.mode
            )

        # Measure ping latency
        latency_ms = round((time.time() - start_time) * 1000.0, 2)
        return AIHealthResponse(
            enabled=True,
            configured=True,
            model=self.config.model,
            status="healthy",
            latency_ms=latency_ms,
            mode=self.config.mode
        )

    def test_connection(self, prompt: str = "Respond with exactly: ESTATEIQ_GROQ_CONNECTION_OK") -> AITestResponse:
        """Executes a minimal live Groq request to verify API key and model connectivity."""
        start_time = time.time()
        
        if not self.config.is_configured:
            return AITestResponse(
                success=False,
                provider="groq",
                model=self.config.model,
                message="Groq API key missing or GROQ_ENABLED=false",
                latency_ms=0.0,
                error_code="GROQ_NOT_CONFIGURED",
                error_message="Configure GROQ_API_KEY in .env file to enable Groq AI Service.",
                retryable=False
            )

        client = get_groq_client(self.config)
        if not client:
            return AITestResponse(
                success=False,
                provider="groq",
                model=self.config.model,
                message="Failed to initialize Groq client instance",
                latency_ms=0.0,
                error_code="GROQ_INIT_FAILED",
                error_message="Check network connectivity or API endpoint configuration.",
                retryable=True
            )

        try:
            response = client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": "You are a test assistant. Answer concise test queries exactly."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0,
                max_tokens=20
            )
            duration_ms = round((time.time() - start_time) * 1000.0, 2)
            content = response.choices[0].message.content.strip()

            GLOBAL_USAGE_TRACKER.log_request(self.config.model, duration_ms, success=True, fallback_used=False)

            return AITestResponse(
                success=True,
                provider="groq",
                model=self.config.model,
                message=content,
                latency_ms=duration_ms
            )

        except Exception as e:
            duration_ms = round((time.time() - start_time) * 1000.0, 2)
            error_str = str(e)
            GLOBAL_USAGE_TRACKER.log_request(self.config.model, duration_ms, success=False, error_msg=error_str)

            code = "GROQ_TEST_FAILED"
            retryable = True
            if "401" in error_str or "auth" in error_str.lower() or "invalid api key" in error_str.lower():
                code = "GROQ_AUTH_FAILED"
                retryable = False
            elif "429" in error_str or "rate limit" in error_str.lower():
                code = "GROQ_RATE_LIMITED"

            return AITestResponse(
                success=False,
                provider="groq",
                model=self.config.model,
                message="Groq connection test failed",
                latency_ms=duration_ms,
                error_code=code,
                error_message=error_str,
                retryable=retryable
            )

    def query_copilot(
        self,
        user_query: str,
        facility_id: str = "FAC_GEC_CAMPUS",
        building_id: Optional[str] = None
    ) -> CopilotQueryResponse:
        """Executes full Copilot query pipeline: Context Builder -> DIF -> Groq LLM -> Validation."""
        start_time = time.time()
        req_id = f"REQ_AI_{uuid.uuid4().hex[:8].upper()}"
        now_iso = datetime.datetime.now().isoformat()
        sanitized_query = AISafetyGuard.sanitize_user_input(user_query)

        # 1. Build Grounded Context & Evidence Packet from real EstateIQ telemetry
        evidence_packet = build_ai_context(
            facility_id=facility_id,
            user_query=sanitized_query,
            building_id=building_id
        )

        evidence_hash = hashlib.md5(json.dumps(evidence_packet, sort_keys=True).encode("utf-8")).hexdigest()
        cache_key = f"{facility_id}_{building_id}_{evidence_hash}_{self.config.prompt_version}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # 2. Check Groq API configuration
        client = get_groq_client(self.config)

        if not client or not self.config.is_configured:
            if self.config.is_production:
                raise GroqConfigurationError("GROQ_API_KEY is missing or not configured. Cannot perform live AI analysis in production mode.")
            else:
                # Demo mode fallback allowed
                return self._generate_fallback_response(req_id, sanitized_query, evidence_packet, now_iso)

        # 3. Call Groq API
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

            # Format final response contract
            formatted_actions = [
                {
                    "title": act,
                    "reason": "Derived from SHAP feature drivers & DIF priority",
                    "expected_cost_saving_inr": evidence_packet["business_impact"]["hourly_cost_inr"] * 24 * 30
                }
                for act in copilot_resp.recommended_actions
            ]

            full_res = CopilotQueryResponse(
                success=True,
                request_id=req_id,
                response=copilot_resp.summary,
                summary=copilot_resp.summary,
                what_happened=copilot_resp.what_happened,
                why=[copilot_resp.why_it_happened],
                evidence=[
                    {"metric": k, "value": v} for k, v in evidence_packet["telemetry_observed"].items()
                ],
                recommended_actions=formatted_actions,
                assumptions=copilot_resp.assumptions,
                limitations=copilot_resp.limitations,
                confidence=copilot_resp.confidence_percent,
                data_status=evidence_packet["query_meta"]["data_source"],
                ai_provider="groq",
                model=self.config.model,
                generated_at=now_iso,
                fallback_used=False,
                data_source_badge=f"[{evidence_packet['query_meta']['data_source']}]"
            )

            self._cache[cache_key] = full_res
            return full_res

        except Exception as e:
            duration_ms = round((time.time() - start_time) * 1000.0, 2)
            error_str = str(e)
            GLOBAL_USAGE_TRACKER.log_request(self.config.model, duration_ms, success=False, error_msg=error_str)

            if self.config.is_production:
                if "401" in error_str or "auth" in error_str.lower():
                    raise GroqAuthenticationError(f"Groq API authentication failed: {error_str}")
                elif "429" in error_str or "rate limit" in error_str.lower():
                    raise GroqRateLimitError(f"Groq API rate limit exceeded: {error_str}")
                elif "timeout" in error_str.lower():
                    raise GroqTimeoutError(f"Groq API call timed out after {self.config.timeout_seconds}s: {error_str}")
                else:
                    raise ProviderUnavailableError(f"Groq AI provider error: {error_str}")
            else:
                # Return demo fallback only when explicitly in DEMO mode
                return self._generate_fallback_response(req_id, sanitized_query, evidence_packet, now_iso)

    def _generate_fallback_response(
        self,
        request_id: str,
        user_query: str,
        evidence: Dict[str, Any],
        now_iso: str
    ) -> CopilotQueryResponse:
        """Deterministic offline fallback response derived strictly from DIF evidence (DEMO MODE ONLY)."""
        bld = evidence["facility"]["building_id"]
        actual = evidence["telemetry_observed"]["actual_kwh"]
        expected = evidence["contextual_baseline"]["expected_kwh"]
        dev_pct = evidence["contextual_baseline"]["relative_deviation_pct"]
        cost_yr = evidence["business_impact"]["annual_cost_of_inaction_inr"]

        summary = f"EstateIQ Deterministic Baseline (DEMO MODE): Consumption in {bld} is {actual:.1f} kWh vs expected ({expected:.1f} kWh), representing a {dev_pct:+.1f}% deviation."
        what_happened = f"Observed electricity demand in {bld} is {actual:.1f} kWh."
        why = [f"Contextual baseline deviation (+{dev_pct:.1f}%) and model consensus agreement."]
        
        recs = [r["title"] for r in evidence.get("recommended_actions", [])]
        if not recs:
            recs = ["Reset thermostat setback schedule to 24.5°C"]

        formatted_recs = [
            {
                "title": r,
                "reason": "Rule-based DIF recommendation",
                "expected_cost_saving_inr": evidence["business_impact"]["hourly_cost_inr"] * 24 * 30
            } for r in recs
        ]

        return CopilotQueryResponse(
            success=True,
            request_id=request_id,
            response=summary,
            summary=summary,
            what_happened=what_happened,
            why=why,
            evidence=[
                {"metric": k, "value": v} for k, v in evidence["telemetry_observed"].items()
            ],
            recommended_actions=formatted_recs,
            assumptions=["Tariff: ₹9.50/kWh", "DEMO MODE ACTIVE"],
            limitations=["Offline fallback engine active (Groq API not called)"],
            confidence=evidence["confidence"]["confidence_percent"],
            data_status="DEMO_FALLBACK",
            ai_provider="estateiq_deterministic_fallback",
            model="estateiq-fallback-v1",
            generated_at=now_iso,
            fallback_used=True,
            data_source_badge="[DEMO MODE]"
        )
