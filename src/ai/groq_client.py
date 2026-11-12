"""
Singleton Groq Client Module (src/ai/groq_client.py).
Provides a single, thread-safe reusable Groq client using environment settings.
Automatically refreshes if the underlying API key or configuration changes in .env.
Does NOT expose client instances to frontend JavaScript or raw API keys in logs.
"""

import logging
from typing import Optional, Dict, Any
from groq import Groq
from src.ai.config import GroqAIConfig, DEFAULT_AI_CONFIG

logger = logging.getLogger(__name__)


class GroqClientManager:
    """Singleton Manager for Groq API client connection with automatic key rotation."""

    _instance: Optional["GroqClientManager"] = None
    _client: Optional[Groq] = None
    _last_key: Optional[str] = None
    _last_base_url: Optional[str] = None

    def __new__(cls, config: GroqAIConfig = DEFAULT_AI_CONFIG):
        if cls._instance is None:
            cls._instance = super(GroqClientManager, cls).__new__(cls)
            cls._instance.config = config
            cls._instance._init_client()
        else:
            cls._instance.config = config
            current_key = config.api_key if config.is_configured else None
            current_base = config.base_url
            if cls._instance._client is None or cls._instance._last_key != current_key or cls._instance._last_base_url != current_base:
                cls._instance._init_client()
        return cls._instance

    def _init_client(self):
        if self.config.is_configured:
            try:
                clean_key = self.config.api_key.strip().strip('"').strip("'")
                client_kwargs = {
                    "api_key": clean_key,
                    "timeout": self.config.timeout_seconds,
                    "max_retries": self.config.max_retries
                }
                # Groq Python SDK v0.18+ uses base_url="https://api.groq.com"
                if self.config.base_url:
                    base_clean = self.config.base_url.rstrip("/")
                    if base_clean.endswith("/openai/v1"):
                        base_clean = base_clean[:-10]
                    client_kwargs["base_url"] = base_clean

                self._client = Groq(**client_kwargs)
                self._last_key = clean_key
                self._last_base_url = self.config.base_url
                logger.info("Groq API client initialized successfully with model %s", self.config.model)
            except Exception as e:
                logger.warning("Failed to initialize Groq API client: %s", str(e))
                self._client = None
                self._last_key = None
        else:
            logger.info("Groq API key missing or GROQ_ENABLED=false. AI service operating in Fallback mode.")
            self._client = None
            self._last_key = None

    def reset(self):
        """Forces client re-instantiation on next call."""
        self._client = None
        self._last_key = None
        self._init_client()

    @property
    def client(self) -> Optional[Groq]:
        # Check if the key changed dynamically
        current_key = self.config.api_key if self.config.is_configured else None
        if self._client is None or self._last_key != current_key:
            self._init_client()
        return self._client

    @property
    def is_available(self) -> bool:
        return self.client is not None


def get_groq_client(config: GroqAIConfig = DEFAULT_AI_CONFIG) -> Optional[Groq]:
    """Helper function to return the singleton Groq client instance."""
    manager = GroqClientManager(config)
    return manager.client
