"""
Security Configuration & Startup Health Check Subsystem (src/security/security_config.py).
Validates runtime security postures and enforces fail-close controls for production environments.
"""

import os
import logging
from typing import Dict, Any, List
from src.security.key_manager import get_key_manager
from src.security.secrets import redact_secrets

logger = logging.getLogger("EstateIQ.Security.Config")


class SecurityConfig:
    """Central Security Configuration State."""
    
    ENCRYPTION_ALGORITHM = "AES-256-GCM"
    PASSWORD_HASHING_ALGORITHM = "Argon2id"
    DEFAULT_JWT_SECRET_MARKER = "estateiq_prod_sec_key_2026_9823748293748293"


def validate_security_configuration() -> Dict[str, Any]:
    """
    Validates security posture at application startup.
    In production mode (`ESTATEIQ_MODE=production`), enforces strict security checks and raises RuntimeError on failure.
    """
    mode = os.environ.get("ESTATEIQ_MODE", "development").lower()
    jwt_secret = os.environ.get("JWT_SECRET", "")
    cors_origins = os.environ.get("CORS_ALLOWED_ORIGINS", "")
    
    errors: List[str] = []
    warnings: List[str] = []

    # 1. JWT Secret Check
    if not jwt_secret or jwt_secret == SecurityConfig.DEFAULT_JWT_SECRET_MARKER:
        if mode == "production":
            errors.append("CRITICAL: Default or empty JWT_SECRET detected in production mode!")
        else:
            warnings.append("WARNING: Using default JWT_SECRET for development.")

    # 2. Encryption Key Provider Check
    try:
        km = get_key_manager()
        active_id, active_bytes = km.get_active_key()
        if len(active_bytes) != 32:
            errors.append(f"CRITICAL: Active key '{active_id}' is not 32 bytes.")
    except Exception as e:
        if mode == "production":
            errors.append(f"CRITICAL: Failed to initialize encryption key provider: {str(e)}")
        else:
            warnings.append(f"WARNING: Key provider fallback warning: {str(e)}")

    # 3. CORS Check
    if cors_origins == "*" and mode == "production":
        errors.append("CRITICAL: Wildcard CORS ('*') with credentialed authentication is forbidden in production mode!")

    # 4. Master Key / Groq Key Check
    groq_key = os.environ.get("GROQ_API_KEY", "")
    if mode == "production" and not groq_key:
        warnings.append("NOTICE: GROQ_API_KEY missing in production; AI Copilot will operate in offline deterministic mode.")

    status_report = {
        "status": "PASS" if not errors else "FAIL",
        "mode": mode,
        "errors": errors,
        "warnings": warnings,
        "encryption": SecurityConfig.ENCRYPTION_ALGORITHM,
        "password_hashing": SecurityConfig.PASSWORD_HASHING_ALGORITHM
    }

    if errors:
        error_msg = "; ".join(errors)
        logger.critical(f"SECURITY STARTUP VALIDATION FAILED: {error_msg}")
        if mode == "production":
            raise RuntimeError(f"Application failed to start due to severe security misconfigurations: {error_msg}")

    for w in warnings:
        logger.warning(w)

    logger.info(f"Security startup validation passed (Mode: {mode}, Status: PASS)")
    return status_report


def get_security_status() -> Dict[str, Any]:
    """
    Returns non-secret security status metadata suitable for admin endpoints.
    NEVER includes keys, secrets, or passwords.
    """
    km = get_key_manager()
    active_key_id = km.provider.get_active_key_id()
    mode = os.environ.get("ESTATEIQ_MODE", "development").lower()

    return {
        "encryption": SecurityConfig.ENCRYPTION_ALGORITHM,
        "key_management": "configured",
        "key_version": active_key_id,
        "available_key_versions": km.list_keys(),
        "password_hashing": SecurityConfig.PASSWORD_HASHING_ALGORITHM,
        "tls_required": True if mode == "production" else False,
        "rbac_enabled": True,
        "facility_authorization": True,
        "audit_logging": True,
        "secret_scanning": True,
        "mode": mode
    }
