"""
Comprehensive Security Test Suite (tests/test_security.py).
Validates AES-256-GCM cryptographic primitives, envelope serialization, key rotation,
tamper detection, Argon2id password hashing, log redaction, API security, and performance.
"""

import time
import json
import os
import base64
import pytest
from typing import Dict, Any

from src.security import (
    AES256GCMCipher,
    CryptographicError,
    KeyManager,
    EnvironmentKeyProvider,
    EncryptionService,
    get_encryption_service,
    PasswordService,
    hash_password,
    verify_password,
    redact_secrets,
    get_security_status,
    validate_security_configuration
)

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


class TestSecuritySuite:

    @pytest.fixture(autouse=True)
    def setup_env(self):
        self.enc_service = EncryptionService()
        self.pass_service = PasswordService()

    def test_01_encrypt_decrypt_roundtrip(self):
        plaintext = "Confidential Facility Maintenance Order #9842"
        envelope = self.enc_service.encrypt(plaintext)
        assert self.enc_service.is_encrypted(envelope)
        decrypted = self.enc_service.decrypt(envelope)
        assert decrypted == plaintext

    def test_02_empty_and_unicode_input(self):
        unicode_text = "EstateIQ Campus Security ⚡ Smart Grid 智能电网 100% Secure"
        envelope = self.enc_service.encrypt(unicode_text)
        assert self.enc_service.decrypt(envelope) == unicode_text

        with pytest.raises(CryptographicError):
            self.enc_service.encrypt(None)

    def test_03_large_payload_and_binary_data(self):
        large_bytes = os.urandom(1024 * 500)  # 500 KB binary payload
        env_dict = self.enc_service.encrypt_bytes(large_bytes, context="backup_bin_01")
        decrypted_bytes = self.enc_service.decrypt_bytes(env_dict, context="backup_bin_01")
        assert decrypted_bytes == large_bytes

    def test_04_wrong_key_decryption(self):
        # Generate envelope with key-v1
        envelope = self.enc_service.encrypt("Secret Data")

        # Manually alter key provider to simulate wrong key
        bad_key_provider = EnvironmentKeyProvider()
        bad_key_provider.add_key("estateiq-key-v1", os.urandom(32))
        bad_service = EncryptionService(key_manager=KeyManager(provider=bad_key_provider))

        with pytest.raises(CryptographicError):
            bad_service.decrypt(envelope)

    def test_05_tamper_detection_modified_ciphertext(self):
        """Mandatory tamper detection test: altering raw ciphertext bytes MUST cause decryption failure."""
        envelope = self.enc_service.encrypt("Tamper Proof Payload")
        parts = envelope.split(":")
        raw_ct = bytearray(base64.b64decode(parts[3]))
        raw_ct[0] ^= 0xFF  # Flip bits in first byte of raw ciphertext
        tampered_ct = base64.b64encode(raw_ct).decode('utf-8')
        tampered_envelope = f"{parts[0]}:{parts[1]}:{parts[2]}:{tampered_ct}:{parts[4]}"

        with pytest.raises(CryptographicError) as exc_info:
            self.enc_service.decrypt(tampered_envelope)
        assert "authentication failed" in str(exc_info.value).lower() or "decryption failed" in str(exc_info.value).lower()

    def test_06_tamper_detection_modified_aad(self):
        """AAD mismatch MUST result in tag verification failure."""
        aad_context = "facility:FAC_GEC_01:device:METER_01"
        envelope = self.enc_service.encrypt("Sensitive Device Log", context=aad_context)

        # Decrypt with matching AAD -> PASS
        assert self.enc_service.decrypt(envelope, context=aad_context) == "Sensitive Device Log"

        # Decrypt with altered AAD -> FAIL
        wrong_context = "facility:FAC_GEC_02:device:METER_01"
        with pytest.raises(CryptographicError):
            self.enc_service.decrypt(envelope, context=wrong_context)

    def test_07_key_versioning_and_rotation(self):
        km = KeyManager()
        km.provider.add_key("estateiq-key-v1", os.urandom(32), set_active=False)
        km.provider.add_key("estateiq-key-v2", os.urandom(32), set_active=True)

        service = EncryptionService(key_manager=km)

        # Encrypt with v1 explicitly
        v1_env = service.encrypt("Old Record Payload", key_id="estateiq-key-v1")
        assert "estateiq-key-v1" in v1_env

        # Decrypt v1 record using v1 key -> PASS
        decrypted_old = service.decrypt(v1_env)
        assert decrypted_old == "Old Record Payload"

        # Rotate key to active v2
        v2_env = service.rotate_key(v1_env)
        assert "estateiq-key-v2" in v2_env
        assert service.decrypt(v2_env) == "Old Record Payload"

    def test_08_nonce_uniqueness(self):
        """Verifies that encrypting the exact same plaintext produces unique nonces & ciphertexts."""
        p = "Static Telemetry Payload"
        env1 = self.enc_service.encrypt(p)
        env2 = self.enc_service.encrypt(p)
        assert env1 != env2
        assert env1.split(":")[2] != env2.split(":")[2]  # Nonces differ

    def test_09_argon2id_password_hashing(self):
        raw_pass = "SuperSecurePass@2026!"
        h1 = hash_password(raw_pass)
        assert h1.startswith("$argon2id$")

        is_valid, needs_rehash = verify_password(raw_pass, h1)
        assert is_valid is True
        assert needs_rehash is False

        is_wrong, _ = verify_password("WrongPass123", h1)
        assert is_wrong is False

    def test_10_strict_argon2id_rejection_of_legacy_hashes(self):
        """Verifies non-Argon2id hash formats (legacy PBKDF2/plain) are strictly rejected."""
        legacy_pbkdf2_hash = "salt1234:9b8f2d5e6a"
        ps = PasswordService()
        valid, _ = ps.verify_password("Admin@123456", legacy_pbkdf2_hash)
        assert valid is False

    def test_11_secret_redaction(self):
        sensitive_data = {
            "username": "admin",
            "password": "SuperSecretPassword123!",
            "api_key": "gsk_dummy_test_key_for_redaction_unit_test_12345",
            "metadata": {
                "jwt": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.sig",
                "normal_field": "public_val"
            }
        }
        redacted = redact_secrets(sensitive_data)
        assert redacted["password"] == "[REDACTED]"
        assert redacted["api_key"] == "[REDACTED]"
        assert "[REDACTED" in redacted["metadata"]["jwt"]
        assert redacted["metadata"]["normal_field"] == "public_val"

    def test_12_security_api_endpoints(self):
        # 1. Admin status endpoint
        res = client.get("/api/v1/admin/security/status")
        assert res.status_code == 200
        data = res.json()
        assert data["encryption"] == "AES-256-GCM"
        assert data["password_hashing"] == "Argon2id"
        assert "key_version" in data

        # 2. Admin Encrypt endpoint
        enc_res = client.post("/api/v1/admin/security/encrypt", json={"plaintext": "API Protected Data", "context": "facility:FAC_01"})
        assert enc_res.status_code == 200
        env = enc_res.json()["envelope"]

        # 3. Admin Decrypt endpoint
        dec_res = client.post("/api/v1/admin/security/decrypt", json={"envelope": env, "context": "facility:FAC_01"})
        assert dec_res.status_code == 200
        assert dec_res.json()["plaintext"] == "API Protected Data"

    def test_13_performance_benchmark(self):
        """Measures AES-256-GCM throughput across 1KB, 10KB, 100KB, and 1MB payloads."""
        sizes = [1024, 10 * 1024, 100 * 1024, 1024 * 1024]
        results = {}

        for sz in sizes:
            payload_bytes = os.urandom(sz)
            t0 = time.perf_counter()
            env_dict = self.enc_service.encrypt_bytes(payload_bytes)
            t_enc = (time.perf_counter() - t0) * 1000

            t0 = time.perf_counter()
            dec_bytes = self.enc_service.decrypt_bytes(env_dict)
            t_dec = (time.perf_counter() - t0) * 1000

            assert dec_bytes == payload_bytes
            results[f"{sz // 1024}KB"] = {"encrypt_ms": round(t_enc, 3), "decrypt_ms": round(t_dec, 3)}

        print("\n=== AES-256-GCM PERFORMANCE BENCHMARK ===")
        for k, v in results.items():
            print(f"Payload Size: {k:6s} | Encrypt: {v['encrypt_ms']:6.3f} ms | Decrypt: {v['decrypt_ms']:6.3f} ms")
        print("==========================================")
