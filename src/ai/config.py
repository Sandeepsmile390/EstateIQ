"""
Groq AI Service Configuration Module (src/ai/config.py).
Reads configuration settings from environment variables without exposing secrets.
"""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class GroqAIConfig:
    """Configuration parameters for Groq AI Service."""

    api_key: str = os.getenv("GROQ_API_KEY", "")
    model: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    base_url: str = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    timeout_seconds: int = int(os.getenv("GROQ_TIMEOUT_SECONDS", "30"))
    max_retries: int = int(os.getenv("GROQ_MAX_RETRIES", "2"))
    enabled: bool = os.getenv("GROQ_ENABLED", "true").lower() in ["true", "1", "yes"]
    prompt_version: str = "estateiq-copilot-v1"

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.enabled)

DEFAULT_AI_CONFIG = GroqAIConfig()
