"""
EstateIQ Security Architecture Package.
Provides centralized AES-256-GCM encryption, Key Management, Argon2id password hashing,
secret redaction, and startup security health checks.
"""

from src.security.crypto import AES256GCMCipher, CryptographicError
from src.security.key_manager import KeyManager, KeyProvider, EnvironmentKeyProvider, KMSKeyProvider
from src.security.encryption_service import EncryptionService, get_encryption_service
from src.security.password import PasswordService, get_password_service, hash_password, verify_password
from src.security.secrets import redact_secrets, get_secret, mask_sensitive_string
from src.security.security_config import SecurityConfig, validate_security_configuration, get_security_status

__all__ = [
    "AES256GCMCipher",
    "CryptographicError",
    "KeyManager",
    "KeyProvider",
    "EnvironmentKeyProvider",
    "KMSKeyProvider",
    "EncryptionService",
    "get_encryption_service",
    "PasswordService",
    "get_password_service",
    "hash_password",
    "verify_password",
    "redact_secrets",
    "get_secret",
    "mask_sensitive_string",
    "SecurityConfig",
    "validate_security_configuration",
    "get_security_status"
]
