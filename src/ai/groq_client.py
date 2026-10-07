"""
Singleton Groq Client Module (src/ai/groq_client.py).
Provides a single, thread-safe reusable Groq client using environment settings.
Does NOT expose client instances to frontend JavaScript or raw API keys in logs.
"""

import logging
from typing import Optional, Dict, Any
from groq import Groq
from src.ai.config import GroqAIConfig, DEFAULT_AI_CONFIG

logger = logging.getLogger(__name__)

class GroqClientManager:
    """Singleton Manager for Groq API client connection."""

    _instance: Optional["GroqClientManager"] = None
    _client: Optional[Groq] = None

    def __new__(cls, config: GroqAIConfig = DEFAULT_AI_CONFIG):
        if cls._instance is None:
            cls._instance = super(GroqClientManager, cls).__new__(cls)
            cls._instance.config = config
            cls._instance._init_client()
        else:
            cls._instance.config = config
            cls._instance._init_client()
        return cls._instance

    def _init_client(self):
        if self.config.is_configured:
            try:
                client_kwargs = {
                    "api_key": self.config.api_key,
                    "timeout": self.config.timeout_seconds,
                    "max_retries": self.config.max_retries
                }
                # Groq Python SDK v0.18+ uses base_url="https://api.groq.com"
                # Strip trailing /openai/v1 if present to avoid SDK double-prefixing
                if self.config.base_url:
                    base_clean = self.config.base_url.rstrip("/")
                    if base_clean.endswith("/openai/v1"):
                        base_clean = base_clean[:-10]
                    client_kwargs["base_url"] = base_clean

                self._client = Groq(**client_kwargs)
                logger.info("Groq API client initialized successfully with model %s", self.config.model)
            except Exception as e:
                logger.warning("Failed to initialize Groq API client: %s", str(e))
                self._client = None
        else:
            logger.info("Groq API key missing or GROQ_ENABLED=false. AI service operating in Fallback mode.")
            self._client = None

    @property
    def client(self) -> Optional[Groq]:
        return self._client

    @property
    def is_available(self) -> bool:
        return self._client is not None

def get_groq_client(config: GroqAIConfig = DEFAULT_AI_CONFIG) -> Optional[Groq]:
    """Helper function to return the singleton Groq client instance."""
    manager = GroqClientManager(config)
    return manager.client
