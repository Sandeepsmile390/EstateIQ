"""
Centralized Encryption Service (src/security/encryption_service.py).
High-level application encryption API supporting:
- AES-256-GCM authenticated envelope encryption
- Compact and JSON versioned storage representations
- Additional Authenticated Data (AAD) binding
- Transparent key rotation & re-encryption
- Exception safety (never exposes plaintext or key material on failure)
"""

import json
import base64
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Union
from src.security.crypto import AES256GCMCipher, CryptographicError
from src.security.key_manager import KeyManager, get_key_manager

logger = logging.getLogger("EstateIQ.Security.EncryptionService")


class EncryptionService:
    """
    High-level application-level encryption service for sensitive EstateIQ data.
    All business logic modules perform encryption strictly through this service.
    """

    ENVELOPE_VERSION = 1
    ALGORITHM_NAME = "AES-256-GCM"

    def __init__(self, key_manager: Optional[KeyManager] = None):
        self.key_manager = key_manager or get_key_manager()

    def get_key_version(self) -> str:
        """Returns active key_id version."""
        active_id, _ = self.key_manager.get_active_key()
        return active_id

    def is_encrypted(self, value: Any) -> bool:
        """
        Checks whether a value is an EstateIQ AES-256-GCM encrypted envelope.
        Supports checking compact string envelopes ('v1:kid:nonce:ct:tag') and JSON dicts.
        """
        if isinstance(value, str):
            if value.startswith("v1:"):
                parts = value.split(":")
                return len(parts) == 5
            elif value.strip().startswith("{") and "AES-256-GCM" in value:
                try:
                    parsed = json.loads(value)
                    return isinstance(parsed, dict) and parsed.get("algorithm") == self.ALGORITHM_NAME
                except Exception:
                    return False
        elif isinstance(value, dict):
            return value.get("algorithm") == self.ALGORITHM_NAME and "ciphertext" in value
        return False

    def _prepare_aad(self, context: Optional[Union[str, bytes]]) -> Optional[bytes]:
        if context is None:
            return None
        if isinstance(context, str):
            return context.encode('utf-8')
        if isinstance(context, bytes):
            return context
        return str(context).encode('utf-8')

    def encrypt(
        self,
        plaintext: str,
        context: Optional[str] = None,
        key_id: Optional[str] = None,
        format_type: str = "compact"
    ) -> str:
        """
        Encrypts a plaintext string using AES-256-GCM with optional context AAD.

        Args:
            plaintext: Plaintext string to encrypt
            context: Optional string context bound as AAD (e.g. 'facility:FAC_01:user:USR_02')
            key_id: Optional target key_id (defaults to current active key)
            format_type: Output format - 'compact' ("v1:kid:nonce:ciphertext:tag") or 'json'

        Returns:
            Encrypted envelope string
        """
        if plaintext is None:
            raise CryptographicError("Plaintext cannot be None.")
        
        target_key_id, key_bytes = self.key_manager.get_key(key_id)
        aad_bytes = self._prepare_aad(context)
        plaintext_bytes = plaintext.encode('utf-8')

        crypto_res = AES256GCMCipher.encrypt_raw(plaintext_bytes, key_bytes, aad=aad_bytes)

        nonce_b64 = base64.b64encode(crypto_res["nonce"]).decode('utf-8')
        ct_b64 = base64.b64encode(crypto_res["ciphertext"]).decode('utf-8')
        tag_b64 = base64.b64encode(crypto_res["tag"]).decode('utf-8')

        if format_type == "json":
            envelope = {
                "version": self.ENVELOPE_VERSION,
                "algorithm": self.ALGORITHM_NAME,
                "key_id": target_key_id,
                "nonce": nonce_b64,
                "ciphertext": ct_b64,
                "tag": tag_b64,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            return json.dumps(envelope)
        
        # Default compact envelope: v1:key_id:nonce_b64:ct_b64:tag_b64
        return f"v1:{target_key_id}:{nonce_b64}:{ct_b64}:{tag_b64}"

    def decrypt(self, encrypted_value: str, context: Optional[str] = None) -> str:
        """
        Decrypts an EstateIQ AES-256-GCM envelope string and validates authentication tag & AAD.

        Args:
            encrypted_value: Compact string or JSON envelope string
            context: Context string used during encryption for AAD validation

        Returns:
            Decrypted plaintext string

        Raises:
            CryptographicError: If decryption, tag, format, or AAD validation fails
        """
        if not encrypted_value or not isinstance(encrypted_value, str):
            raise CryptographicError("Encrypted value must be a non-empty string.")

        key_id = None
        nonce_b64 = None
        ct_b64 = None
        tag_b64 = None

        # Parse Envelope
        if encrypted_value.startswith("v1:"):
            parts = encrypted_value.split(":")
            if len(parts) != 5:
                raise CryptographicError("Invalid compact encrypted envelope structure.")
            _, key_id, nonce_b64, ct_b64, tag_b64 = parts
        elif encrypted_value.strip().startswith("{"):
            try:
                env = json.loads(encrypted_value)
                if env.get("version") != self.ENVELOPE_VERSION:
                    raise CryptographicError(f"Unsupported envelope version: {env.get('version')}")
                if env.get("algorithm") != self.ALGORITHM_NAME:
                    raise CryptographicError(f"Unsupported cipher algorithm: {env.get('algorithm')}")
                key_id = env["key_id"]
                nonce_b64 = env["nonce"]
                ct_b64 = env["ciphertext"]
                tag_b64 = env["tag"]
            except Exception as e:
                if isinstance(e, CryptographicError):
                    raise e
                raise CryptographicError(f"Failed to parse JSON encrypted envelope: {str(e)}") from e
        else:
            raise CryptographicError("Unrecognized encrypted envelope format.")

        try:
            nonce_bytes = base64.b64decode(nonce_b64)
            ct_bytes = base64.b64decode(ct_b64)
            tag_bytes = base64.b64decode(tag_b64)
        except Exception as e:
            raise CryptographicError(f"Failed to base64 decode envelope parameters: {str(e)}") from e

        _, key_bytes = self.key_manager.get_key(key_id)
        aad_bytes = self._prepare_aad(context)

        decrypted_bytes = AES256GCMCipher.decrypt_raw(
            ciphertext=ct_bytes,
            tag=tag_bytes,
            key=key_bytes,
            nonce=nonce_bytes,
            aad=aad_bytes
        )

        return decrypted_bytes.decode('utf-8')

    def encrypt_bytes(
        self,
        data: bytes,
        context: Optional[Union[str, bytes]] = None,
        key_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Encrypts raw binary data and returns detailed envelope dictionary."""
        if not isinstance(data, bytes):
            raise CryptographicError("Data payload must be bytes.")

        target_key_id, key_bytes = self.key_manager.get_key(key_id)
        aad_bytes = self._prepare_aad(context)

        crypto_res = AES256GCMCipher.encrypt_raw(data, key_bytes, aad=aad_bytes)

        return {
            "version": self.ENVELOPE_VERSION,
            "algorithm": self.ALGORITHM_NAME,
            "key_id": target_key_id,
            "nonce": base64.b64encode(crypto_res["nonce"]).decode('utf-8'),
            "ciphertext": base64.b64encode(crypto_res["ciphertext"]).decode('utf-8'),
            "tag": base64.b64encode(crypto_res["tag"]).decode('utf-8'),
            "created_at": datetime.now(timezone.utc).isoformat()
        }

    def decrypt_bytes(
        self,
        envelope: Union[Dict[str, Any], str],
        context: Optional[Union[str, bytes]] = None
    ) -> bytes:
        """Decrypts envelope to raw binary data bytes."""
        if isinstance(envelope, str):
            if envelope.startswith("v1:"):
                parts = envelope.split(":")
                if len(parts) != 5:
                    raise CryptographicError("Invalid compact envelope string.")
                _, key_id, nonce_b64, ct_b64, tag_b64 = parts
            else:
                parsed = json.loads(envelope)
                key_id = parsed["key_id"]
                nonce_b64 = parsed["nonce"]
                ct_b64 = parsed["ciphertext"]
                tag_b64 = parsed["tag"]
        elif isinstance(envelope, dict):
            key_id = envelope["key_id"]
            nonce_b64 = envelope["nonce"]
            ct_b64 = envelope["ciphertext"]
            tag_b64 = envelope["tag"]
        else:
            raise CryptographicError("Envelope must be string or dictionary.")

        nonce_bytes = base64.b64decode(nonce_b64)
        ct_bytes = base64.b64decode(ct_b64)
        tag_bytes = base64.b64decode(tag_b64)

        _, key_bytes = self.key_manager.get_key(key_id)
        aad_bytes = self._prepare_aad(context)

        return AES256GCMCipher.decrypt_raw(
            ciphertext=ct_bytes,
            tag=tag_bytes,
            key=key_bytes,
            nonce=nonce_bytes,
            aad=aad_bytes
        )

    def rotate_key(
        self,
        encrypted_value: str,
        context: Optional[str] = None,
        target_key_id: Optional[str] = None
    ) -> str:
        """
        Decrypts an envelope encrypted with an older key version and re-encrypts
        it using the latest active key version.

        Args:
            encrypted_value: Existing encrypted envelope
            context: Context string for AAD
            target_key_id: Target key_id (defaults to current active key)

        Returns:
            New encrypted envelope re-encrypted with target key version
        """
        plaintext = self.decrypt(encrypted_value, context=context)
        return self.encrypt(plaintext, context=context, key_id=target_key_id)


# Singleton EncryptionService instance
_DEFAULT_ENCRYPTION_SERVICE = EncryptionService()

def get_encryption_service() -> EncryptionService:
    return _DEFAULT_ENCRYPTION_SERVICE
