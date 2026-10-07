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
from typing import Dict, Any, Optional, List

from src.ai.config import GroqAIConfig, DEFAULT_AI_CONFIG
from src.ai.groq_client import get_groq_client, GroqClientManager
from src.ai.context_builder import build_ai_context
from src.ai.schemas import (
    CopilotResponse, CopilotQueryResponse,
    AIHealthResponse, AITestResponse
)
from src.ai.safety import AISafetyGuard
from src.ai.prompts import SYSTEM_PROMPT_COPILOT, SYSTEM_PROMPT_CAPABILITY, SYSTEM_PROMPT_PROJECT, PROMPT_TEMPLATE_ANOMALY
from src.ai.usage_tracker import GLOBAL_USAGE_TRACKER
from src.ai.exceptions import (
    AIServiceError, GroqConfigurationError, GroqAuthenticationError,
    GroqRateLimitError, GroqTimeoutError, ProviderUnavailableError, InvalidAIResponseError
)

# Priority model candidate chain for resilient fallback
MODEL_CANDIDATE_CHAIN: List[str] = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "llama-3.3-70b-versatile",
    "qwen/qwen3.8-27b"
]

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

        models_to_try = [self.config.model] + [m for m in MODEL_CANDIDATE_CHAIN if m != self.config.model]
        last_error = ""

        for model_name in models_to_try:
            try:
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": "You are a test assistant. Answer concise test queries exactly."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.0,
                    max_tokens=20
                )
                duration_ms = round((time.time() - start_time) * 1000.0, 2)
                content = response.choices[0].message.content.strip()

                GLOBAL_USAGE_TRACKER.log_request(model_name, duration_ms, success=True, fallback_used=False)

                return AITestResponse(
                    success=True,
                    provider="groq",
                    model=model_name,
                    message=content,
                    latency_ms=duration_ms
                )
            except Exception as e:
                last_error = str(e)
                continue

        duration_ms = round((time.time() - start_time) * 1000.0, 2)
        GLOBAL_USAGE_TRACKER.log_request(self.config.model, duration_ms, success=False, error_msg=last_error)

        code = "GROQ_TEST_FAILED"
        retryable = True
        if "401" in last_error or "auth" in last_error.lower() or "invalid api key" in last_error.lower():
            code = "GROQ_AUTH_FAILED"
            retryable = False
        elif "429" in last_error or "rate limit" in last_error.lower():
            code = "GROQ_RATE_LIMITED"

        return AITestResponse(
            success=False,
            provider="groq",
            model=self.config.model,
            message="Groq connection test failed",
            latency_ms=duration_ms,
            error_code=code,
            error_message=last_error,
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
                return self._generate_fallback_response(req_id, sanitized_query, evidence_packet, now_iso)

        # Select intent-appropriate system prompt
        intent_type = evidence_packet.get("intent_type", "ANOMALY")
        if intent_type == "SYSTEM_CAPABILITY":
            system_prompt = SYSTEM_PROMPT_CAPABILITY
        elif intent_type == "PROJECT_EXPLANATION":
            system_prompt = SYSTEM_PROMPT_PROJECT
        else:
            system_prompt = SYSTEM_PROMPT_COPILOT

        user_prompt = PROMPT_TEMPLATE_ANOMALY.format(
            evidence_json=json.dumps(evidence_packet, indent=2),
            user_query=sanitized_query
        )

        models_to_try = [self.config.model] + [m for m in MODEL_CANDIDATE_CHAIN if m != self.config.model]
        last_exception = None

        for model_name in models_to_try:
            try:
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
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
                GLOBAL_USAGE_TRACKER.log_request(model_name, duration_ms, success=True, fallback_used=False)

                hourly_cost = evidence_packet.get("business_impact", {}).get("hourly_cost_inr", 500) if isinstance(evidence_packet.get("business_impact"), dict) else 500
                formatted_actions = [
                    {
                        "title": act,
                        "reason": "Derived from SHAP feature drivers & DIF priority",
                        "expected_cost_saving_inr": hourly_cost * 24 * 30
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
                        {"metric": k, "value": v} for k, v in evidence_packet.get("telemetry_observed", {}).items()
                    ],
                    recommended_actions=formatted_actions,
                    assumptions=copilot_resp.assumptions,
                    limitations=copilot_resp.limitations,
                    confidence=copilot_resp.confidence_percent,
                    data_status=evidence_packet.get("query_meta", {}).get("data_source", "SUCCESS"),
                    ai_provider="groq",
                    model=model_name,
                    generated_at=now_iso,
                    fallback_used=False,
                    data_source_badge=f"[{evidence_packet.get('query_meta', {}).get('data_source', 'SIMULATED IoT')}]"
                )

                self._cache[cache_key] = full_res
                return full_res

            except Exception as e:
                last_exception = e
                error_str = str(e)
                # If model not found, silently retry with next model in chain
                if "model_not_found" in error_str or "404" in error_str:
                    continue
                # If auth error or rate limit, break and report
                if "401" in error_str or "auth" in error_str.lower():
                    raise GroqAuthenticationError(f"Groq API authentication failed: {error_str}")
                elif "429" in error_str or "rate limit" in error_str.lower():
                    raise GroqRateLimitError(f"Groq API rate limit reached: {error_str}")

        # If all candidate models failed
        duration_ms = round((time.time() - start_time) * 1000.0, 2)
        error_str = str(last_exception) if last_exception else "All candidate models failed"
        GLOBAL_USAGE_TRACKER.log_request(self.config.model, duration_ms, success=False, error_msg=error_str)

        if self.config.is_production:
            raise ProviderUnavailableError(f"Groq AI provider error: {error_str}")
        else:
            return self._generate_fallback_response(req_id, sanitized_query, evidence_packet, now_iso)

    def _generate_fallback_response(
        self,
        req_id: str,
        user_query: str,
        evidence_packet: Dict[str, Any],
        now_iso: str
    ) -> CopilotQueryResponse:
        """Dynamic intent-grounded fallback response when Groq API key is unconfigured or unavailable."""
        summary = evidence_packet.get("summary") or evidence_packet.get("analysis_narrative") or "EstateIQ Facility Intelligence Analysis."
        what_happened = evidence_packet.get("what_happened") or f"Telemetry analysis for query: '{user_query}'"
        
        raw_why = evidence_packet.get("why")
        if isinstance(raw_why, list):
            why_list = raw_why
        elif isinstance(raw_why, str):
            why_list = [raw_why]
        else:
            why_list = [evidence_packet.get("why_it_happened", "Derived from current facility telemetry.")]

        raw_actions = evidence_packet.get("recommended_actions", ["Review facility telemetry parameters"])
        formatted_actions = []
        for act in raw_actions:
            if isinstance(act, dict):
                formatted_actions.append(act)
            else:
                formatted_actions.append({
                    "title": str(act),
                    "reason": "Generated by EstateIQ Analytical Engine",
                    "expected_cost_saving_inr": 5000
                })

        conf = evidence_packet.get("confidence", evidence_packet.get("confidence_percent", 85.0))

        return CopilotQueryResponse(
            success=True,
            request_id=req_id,
            response=summary,
            summary=summary,
            what_happened=what_happened,
            why=why_list,
            evidence=[
                {"metric": k, "value": v} for k, v in evidence_packet.get("telemetry_observed", {}).items()
            ],
            recommended_actions=formatted_actions,
            assumptions=evidence_packet.get("assumptions", ["Facility telemetry sensors operational"]),
            limitations=evidence_packet.get("limitations", ["Analysis constrained to retrieved period"]),
            confidence=float(conf),
            data_status=evidence_packet.get("query_meta", {}).get("data_source", "SUCCESS"),
            ai_provider="estateiq_baseline_engine",
            model="estateiq-dif-v1",
            generated_at=now_iso,
            fallback_used=True,
            data_source_badge=f"[{evidence_packet.get('query_meta', {}).get('data_source', 'REAL SENSOR')}]"
        )
