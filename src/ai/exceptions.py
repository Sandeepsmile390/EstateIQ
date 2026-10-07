"""
AI Service Exceptions Module (src/ai/exceptions.py).
Defines custom, structured exception types for Groq API integration and AI decision support.
"""

class AIServiceError(Exception):
    """Base exception for all AI Service failures."""
    def __init__(self, message: str, error_code: str = "AI_SERVICE_ERROR", status_code: int = 500, retryable: bool = False):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.retryable = retryable

class GroqConfigurationError(AIServiceError):
    """Raised when Groq API key or model is missing/invalidly configured."""
    def __init__(self, message: str = "Groq API key or model is not configured."):
        super().__init__(message, error_code="GROQ_NOT_CONFIGURED", status_code=400, retryable=False)

class GroqAuthenticationError(AIServiceError):
    """Raised when Groq API authentication fails (HTTP 401)."""
    def __init__(self, message: str = "Groq authentication failed. Check configured GROQ_API_KEY."):
        super().__init__(message, error_code="GROQ_AUTH_FAILED", status_code=401, retryable=False)

class GroqRateLimitError(AIServiceError):
    """Raised when Groq API rate limit is reached (HTTP 429)."""
    def __init__(self, message: str = "Groq API rate limit reached. Please retry shortly."):
        super().__init__(message, error_code="GROQ_RATE_LIMITED", status_code=429, retryable=True)

class GroqTimeoutError(AIServiceError):
    """Raised when Groq API request times out."""
    def __init__(self, message: str = "Groq API request timed out."):
        super().__init__(message, error_code="GROQ_TIMEOUT", status_code=504, retryable=True)

class ProviderUnavailableError(AIServiceError):
    """Raised when Groq provider returns HTTP 500/502/503."""
    def __init__(self, message: str = "AI provider is temporarily unavailable."):
        super().__init__(message, error_code="PROVIDER_UNAVAILABLE", status_code=503, retryable=True)

class InvalidAIResponseError(AIServiceError):
    """Raised when Groq output fails Pydantic schema validation."""
    def __init__(self, message: str = "AI output did not match expected structured schema."):
        super().__init__(message, error_code="INVALID_AI_SCHEMA", status_code=422, retryable=True)
