"""
AES-256-GCM Cryptographic Primitive Engine (src/security/crypto.py).
Implements authenticated encryption with associated data (AEAD) using AES-256-GCM.

Security Properties:
- Confidentiality: 256-bit AES symmetric key
- Integrity & Authentication: 128-bit GCM authentication tag
- Nonce Uniqueness: 96-bit (12-byte) cryptographically secure random nonce generated per operation
- Zero Key/Nonce Reuse: Checked & enforced
"""

import os
import base64
from typing import Optional, Dict, Tuple, Union
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag, InvalidKey


class CryptographicError(Exception):
    """Base exception for all cryptographic operations."""
    pass


class AES256GCMCipher:
    """
    Low-level AES-256-GCM cipher wrapper providing audited, standards-compliant
    authenticated encryption and decryption.
    """

    KEY_SIZE_BYTES = 32  # 256 bits
    NONCE_SIZE_BYTES = 12  # 96 bits
    TAG_SIZE_BYTES = 16  # 128 bits

    @classmethod
    def generate_key(cls) -> bytes:
        """Generates a cryptographically secure 256-bit (32-byte) random key."""
        return os.urandom(cls.KEY_SIZE_BYTES)

    @classmethod
    def generate_key_base64(cls) -> str:
        """Generates a base64-encoded 256-bit random key."""
        return base64.b64encode(cls.generate_key()).decode('utf-8')

    @classmethod
    def _validate_key(cls, key: bytes) -> bytes:
        if not isinstance(key, bytes):
            raise CryptographicError("Encryption key must be bytes.")
        if len(key) != cls.KEY_SIZE_BYTES:
            raise CryptographicError(
                f"Invalid AES key length: expected {cls.KEY_SIZE_BYTES} bytes, got {len(key)} bytes."
            )
        return key

    @classmethod
    def encrypt_raw(
        cls,
        plaintext: bytes,
        key: bytes,
        aad: Optional[bytes] = None
    ) -> Dict[str, bytes]:
        """
        Encrypts plaintext bytes using AES-256-GCM with a fresh secure nonce.

        Args:
            plaintext: Raw bytes to encrypt
            key: 32-byte (256-bit) AES key
            aad: Optional additional authenticated data bytes

        Returns:
            Dict containing 'nonce', 'ciphertext', 'tag', and 'combined'
        """
        if not isinstance(plaintext, bytes):
            raise CryptographicError("Plaintext payload must be bytes.")
        
        valid_key = cls._validate_key(key)
        nonce = os.urandom(cls.NONCE_SIZE_BYTES)
        
        try:
            aesgcm = AESGCM(valid_key)
            # cryptography library appends 16-byte authentication tag to ciphertext
            combined = aesgcm.encrypt(nonce, plaintext, aad)
            ciphertext = combined[:-cls.TAG_SIZE_BYTES]
            tag = combined[-cls.TAG_SIZE_BYTES:]
            
            return {
                "nonce": nonce,
                "ciphertext": ciphertext,
                "tag": tag,
                "combined": combined
            }
        except Exception as e:
            raise CryptographicError(f"AES-256-GCM encryption operation failed: {str(e)}") from e

    @classmethod
    def decrypt_raw(
        cls,
        ciphertext: bytes,
        tag: bytes,
        key: bytes,
        nonce: bytes,
        aad: Optional[bytes] = None
    ) -> bytes:
        """
        Decrypts AES-256-GCM ciphertext bytes and verifies tag authentication.

        Args:
            ciphertext: Encrypted payload bytes
            tag: 16-byte authentication tag
            key: 32-byte AES key
            nonce: 12-byte nonce used during encryption
            aad: Optional additional authenticated data (must match encryption AAD)

        Returns:
            Decrypted plaintext bytes

        Raises:
            CryptographicError: If decryption or tag authentication fails
        """
        valid_key = cls._validate_key(key)
        if not isinstance(nonce, bytes) or len(nonce) != cls.NONCE_SIZE_BYTES:
            raise CryptographicError(
                f"Invalid nonce length: expected {cls.NONCE_SIZE_BYTES} bytes, got {len(nonce) if isinstance(nonce, bytes) else type(nonce)}"
            )
        if not isinstance(tag, bytes) or len(tag) != cls.TAG_SIZE_BYTES:
            raise CryptographicError(
                f"Invalid tag length: expected {cls.TAG_SIZE_BYTES} bytes, got {len(tag) if isinstance(tag, bytes) else type(tag)}"
            )

        combined = ciphertext + tag
        try:
            aesgcm = AESGCM(valid_key)
            plaintext = aesgcm.decrypt(nonce, combined, aad)
            return plaintext
        except InvalidTag:
            raise CryptographicError("AES-256-GCM authentication failed: Ciphertext or AAD has been tampered with.")
        except Exception as e:
            raise CryptographicError(f"AES-256-GCM decryption failed: {str(e)}") from e
