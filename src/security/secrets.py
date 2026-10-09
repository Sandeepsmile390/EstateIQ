"""
Secret Management & Log Redaction Subsystem (src/security/secrets.py).
Scrubs sensitive data (passwords, tokens, API keys, AES keys, authorization headers)
from logs, audit trails, error tracebacks, and external AI prompts.
"""

import re
import os
from typing import Any, Dict, List, Union, Optional

# Sensitive keyword patterns for dictionary keys and string values
SENSITIVE_KEY_PATTERNS = re.compile(
    r'(password|passwd|secret|api_key|apikey|auth_token|jwt|token|bearer|access_token|refresh_token|private_key|master_key|aes_key|groq_api_key|aws_access_key|connection_string|database_url)',
    re.IGNORECASE
)

# Sensitive value pattern matchers (e.g. Bearer eyJ..., gsk_..., AWS keys)
SENSITIVE_VALUE_PATTERNS = [
    (re.compile(r'Bearer\s+[A-Za-z0-9\-\._~\+\/]+=*', re.IGNORECASE), "Bearer [REDACTED_TOKEN]"),
    (re.compile(r'gsk_[A-Za-z0-9]{30,}', re.IGNORECASE), "[REDACTED_GROQ_KEY]"),
    (re.compile(r'v1:estateiq-key-[^:\s]+:[^:\s]+:[^:\s]+:[^:\s]+'), "[REDACTED_ENCRYPTED_ENVELOPE]"),
    (re.compile(r'AKIA[0-9A-Z]{16}'), "[REDACTED_AWS_KEY_ID]")
]

REDACTED_PLACEHOLDER = "[REDACTED]"


def mask_sensitive_string(val: str, visible_suffix_len: int = 4) -> str:
    """Masks string showing only last N characters."""
    if not val or not isinstance(val, str):
        return REDACTED_PLACEHOLDER
    if len(val) <= visible_suffix_len:
        return "*" * len(val)
    return "*" * (len(val) - visible_suffix_len) + val[-visible_suffix_len:]


def redact_secrets(data: Any) -> Any:
    """
    Recursively scrubs sensitive keys and string patterns from data structures.

    Args:
        data: Primitive, dict, or list data structure

    Returns:
        Sanitized deep copy of data structure
    """
    if isinstance(data, dict):
        sanitized = {}
        for k, v in data.items():
            if isinstance(k, str) and SENSITIVE_KEY_PATTERNS.search(k):
                sanitized[k] = REDACTED_PLACEHOLDER
            else:
                sanitized[k] = redact_secrets(v)
        return sanitized
    elif isinstance(data, list):
        return [redact_secrets(item) for item in data]
    elif isinstance(data, str):
        s = data
        for pattern, replacement in SENSITIVE_VALUE_PATTERNS:
            s = pattern.sub(replacement, s)
        return s
    return data


def get_secret(env_var_name: str, default: Optional[str] = None, required_in_prod: bool = True) -> str:
    """
    Safely retrieves secret environment variable.
    Enforces that required secrets exist in production environment.
    """
    val = os.environ.get(env_var_name)
    if val:
        return val.strip()
    
    mode = os.environ.get("ESTATEIQ_MODE", "development").lower()
    if mode == "production" and required_in_prod:
        raise ValueError(
            f"CRITICAL SECURITY CONFIGURATION FAILURE: Required production secret '{env_var_name}' is not set!"
        )
    
    return default or ""
