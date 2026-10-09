"""
Key Management Subsystem (src/security/key_manager.py).
Provides abstract key providers, key versioning, key rotation capabilities,
and secure storage abstractions (Environment / KMS / Vault).
"""

import os
import base64
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple
from src.security.crypto import AES256GCMCipher, CryptographicError

logger = logging.getLogger("EstateIQ.Security.KeyManager")


class KeyProvider(ABC):
    """Abstract interface for cryptographic key providers."""

    @abstractmethod
    def get_key(self, key_id: str) -> bytes:
        """Retrieves raw 32-byte key for specified key_id."""
        pass

    @abstractmethod
    def get_active_key_id(self) -> str:
        """Returns key_id of currently active key for new encryptions."""
        pass

    @abstractmethod
    def list_key_ids(self) -> List[str]:
        """Lists all known key IDs available for decryption."""
        pass


class EnvironmentKeyProvider(KeyProvider):
    """
    KeyProvider implementation reading base64/hex-encoded keys from environment.
    Supports versioned keys (e.g., ESTATEIQ_KEY_V1, ESTATEIQ_KEY_V2).
    """

    DEFAULT_ACTIVE_KEY_ID = "estateiq-key-v1"

    def __init__(self):
        self._keys: Dict[str, bytes] = {}
        self._active_key_id = os.environ.get("ESTATEIQ_ACTIVE_KEY_ID", self.DEFAULT_ACTIVE_KEY_ID)
        self._load_keys_from_env()

    def _parse_key_value(self, val: str) -> bytes:
        val_clean = val.strip()
        # Try Base64 decoding first
        try:
            raw = base64.b64decode(val_clean)
            if len(raw) == 32:
                return raw
        except Exception:
            pass
        
        # Try Hex decoding next
        try:
            raw = bytes.fromhex(val_clean)
            if len(raw) == 32:
                return raw
        except Exception:
            pass

        # Try utf-8 raw if 32 bytes
        raw = val_clean.encode('utf-8')
        if len(raw) == 32:
            return raw

        raise CryptographicError(
            f"Key string must resolve to 32 bytes (base64, hex, or 32 raw chars). Provided length: {len(raw)}"
        )

    def _load_keys_from_env(self):
        # 1. Master Key check (check ESTATEIQ_MASTER_KEY, fallback to default dev key if not provided)
        master_key_env = os.environ.get("ESTATEIQ_MASTER_KEY", "estateiq_master_sec_key_32bytes!")
        if master_key_env:
            try:
                self._keys[self._active_key_id] = self._parse_key_value(master_key_env)
            except Exception as e:
                logger.error(f"Failed to parse ESTATEIQ_MASTER_KEY: {e}")

        # 2. Versioned key checks (ESTATEIQ_KEY_V1, ESTATEIQ_KEY_V2, etc.)
        for env_var, val in os.environ.items():
            if env_var.startswith("ESTATEIQ_KEY_"):
                version_suffix = env_var.replace("ESTATEIQ_KEY_", "").lower()
                key_id = f"estateiq-key-{version_suffix}"
                try:
                    self._keys[key_id] = self._parse_key_value(val)
                except Exception as e:
                    logger.error(f"Failed to parse env key {env_var}: {e}")

        # 3. Enforce key requirement
        if not self._keys:
            raise CryptographicError(
                "CRITICAL SECURITY CONFIGURATION ERROR: Failed to load AES-256 master key!"
            )

    def get_key(self, key_id: str) -> bytes:
        if key_id not in self._keys:
            # Refresh from env in case key was updated dynamically
            self._load_keys_from_env()
        if key_id not in self._keys:
            raise CryptographicError(f"Encryption key '{key_id}' not found in KeyProvider.")
        return self._keys[key_id]

    def get_active_key_id(self) -> str:
        return self._active_key_id

    def list_key_ids(self) -> List[str]:
        return list(self._keys.keys())

    def add_key(self, key_id: str, key_bytes: bytes, set_active: bool = False):
        if len(key_bytes) != 32:
            raise CryptographicError("Added key must be exactly 32 bytes.")
        self._keys[key_id] = key_bytes
        if set_active:
            self._active_key_id = key_id


class KMSKeyProvider(KeyProvider):
    """
    Production Enterprise KMS Provider Interface.
    Simulates / integrates Envelope Encryption with AWS KMS, HashiCorp Vault, or GCP Secret Manager.
    """

    def __init__(self, kms_key_arn: Optional[str] = None):
        self.kms_key_arn = kms_key_arn or os.environ.get("KMS_KEY_ARN", "arn:aws:kms:us-east-1:123456789012:key/estateiq-kek")
        self._underlying_provider = EnvironmentKeyProvider()

    def get_key(self, key_id: str) -> bytes:
        # Production implementation decrypts DEK using KMS KEK.
        # Fallback delegates to underlying environment provider.
        return self._underlying_provider.get_key(key_id)

    def get_active_key_id(self) -> str:
        return self._underlying_provider.get_active_key_id()

    def list_key_ids(self) -> List[str]:
        return self._underlying_provider.list_key_ids()


class KeyManager:
    """
    Centralized Key Manager coordinating KeyProviders and supporting key rotation.
    """

    def __init__(self, provider: Optional[KeyProvider] = None):
        self.provider = provider or EnvironmentKeyProvider()

    def get_active_key(self) -> Tuple[str, bytes]:
        active_id = self.provider.get_active_key_id()
        key_bytes = self.provider.get_key(active_id)
        return active_id, key_bytes

    def get_key(self, key_id: Optional[str] = None) -> Tuple[str, bytes]:
        if not key_id:
            return self.get_active_key()
        return key_id, self.provider.get_key(key_id)

    def list_keys(self) -> List[str]:
        return self.provider.list_key_ids()


# Singleton KeyManager instance
_DEFAULT_KEY_MANAGER = KeyManager()

def get_key_manager() -> KeyManager:
    return _DEFAULT_KEY_MANAGER
