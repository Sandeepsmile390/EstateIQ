"""
Groq AI Service Configuration Module (src/ai/config.py).
Reads configuration settings from environment variables with dynamic reload support.
Does NOT expose raw secrets in logs or responses.
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Ensure fresh environment configuration
load_dotenv(override=True)


class GroqAIConfig:
    """Dynamic configuration parameters for Groq AI Service."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        max_retries: Optional[int] = None,
        enabled: Optional[bool] = None,
        mode: Optional[str] = None,
        prompt_version: str = "estateiq-copilot-v1"
    ):
        self._explicit_api_key = api_key
        self._explicit_model = model
        self._explicit_base_url = base_url
        self._explicit_timeout_seconds = timeout_seconds
        self._explicit_max_retries = max_retries
        self._explicit_enabled = enabled
        self._explicit_mode = mode
        self.prompt_version = prompt_version

    @property
    def api_key(self) -> str:
        if self._explicit_api_key is not None:
            return self._explicit_api_key.strip().strip('"').strip("'")
        load_dotenv(override=True)
        raw = os.getenv("GROQ_API_KEY", "")
        return raw.strip().strip('"').strip("'")

    @property
    def model(self) -> str:
        if self._explicit_model is not None:
            return self._explicit_model
        load_dotenv(override=True)
        return os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b").strip()

    @property
    def base_url(self) -> str:
        if self._explicit_base_url is not None:
            return self._explicit_base_url
        return os.getenv("GROQ_BASE_URL", "https://api.groq.com").strip()

    @property
    def timeout_seconds(self) -> int:
        if self._explicit_timeout_seconds is not None:
            return self._explicit_timeout_seconds
        try:
            return int(os.getenv("GROQ_TIMEOUT_SECONDS", "30"))
        except (ValueError, TypeError):
            return 30

    @property
    def max_retries(self) -> int:
        if self._explicit_max_retries is not None:
            return self._explicit_max_retries
        try:
            return int(os.getenv("GROQ_MAX_RETRIES", "2"))
        except (ValueError, TypeError):
            return 2

    @property
    def enabled(self) -> bool:
        if self._explicit_enabled is not None:
            return self._explicit_enabled
        return os.getenv("GROQ_ENABLED", "true").lower() in ["true", "1", "yes"]

    @property
    def mode(self) -> str:
        if self._explicit_mode is not None:
            return self._explicit_mode
        return os.getenv("ESTATEIQ_MODE", "development").lower()

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.enabled)

    @property
    def is_production(self) -> bool:
        return self.mode == "production"


def get_ai_config() -> GroqAIConfig:
    load_dotenv(override=True)
    return GroqAIConfig()


DEFAULT_AI_CONFIG = GroqAIConfig()
