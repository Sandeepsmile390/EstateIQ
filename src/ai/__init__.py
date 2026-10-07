"""
EstateIQ Groq AI Service Package (src/ai/__init__.py).
Exports GroqClientManager, EstateIQAIService, CopilotResponse, and AIUsageTracker.
"""

from src.ai.config import GroqAIConfig, DEFAULT_AI_CONFIG
from src.ai.groq_client import GroqClientManager, get_groq_client
from src.ai.schemas import (
    CopilotResponse, CopilotQueryRequest, CopilotQueryResponse,
    AIHealthResponse, AITestRequest, AITestResponse,
    AnomalyExplanationResponse, WhatIfInterpretationResponse
)
from src.ai.context_builder import AIContextBuilder, build_ai_context
from src.ai.safety import AISafetyGuard
from src.ai.grounding import AIEvidenceBuilder
from src.ai.usage_tracker import GLOBAL_USAGE_TRACKER, AIUsageTracker
from src.ai.ai_service import EstateIQAIService
from src.ai.exceptions import (
    AIServiceError, GroqConfigurationError, GroqAuthenticationError,
    GroqRateLimitError, GroqTimeoutError, ProviderUnavailableError, InvalidAIResponseError
)

__all__ = [
    "GroqAIConfig",
    "DEFAULT_AI_CONFIG",
    "GroqClientManager",
    "get_groq_client",
    "CopilotResponse",
    "CopilotQueryRequest",
    "CopilotQueryResponse",
    "AIHealthResponse",
    "AITestRequest",
    "AITestResponse",
    "AnomalyExplanationResponse",
    "WhatIfInterpretationResponse",
    "AIContextBuilder",
    "build_ai_context",
    "AISafetyGuard",
    "AIEvidenceBuilder",
    "GLOBAL_USAGE_TRACKER",
    "AIUsageTracker",
    "EstateIQAIService",
    "AIServiceError",
    "GroqConfigurationError",
    "GroqAuthenticationError",
    "GroqRateLimitError",
    "GroqTimeoutError",
    "ProviderUnavailableError",
    "InvalidAIResponseError"
]
