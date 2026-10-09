# EstateIQ Enterprise Security Architecture & Cryptography Specification

## 1. Executive Overview

**EstateIQ** is an enterprise-grade, AI-powered sustainable facility and estate decision intelligence platform. Due to the critical infrastructure nature of smart campus management—spanning electrical grid transformers, diesel generators, water distribution networks, building automation systems, and user identity credentials—EstateIQ enforces a robust **Defense-in-Depth** security model.

Application-level data encryption at rest is implemented exclusively using **AES-256-GCM** (Galois/Counter Mode), providing authenticated encryption with confidentiality, integrity, and tamper detection. User passwords are stored using one-way **Argon2id** password hashing. All alternative or legacy fallback security algorithms (such as PBKDF2 or unauthenticated key fallbacks) have been completely removed from the codebase.

---

## 2. Threat Model

The EstateIQ Security Architecture addresses seventeen primary threat vectors ($T1 - T17$):

| Threat ID | Threat Category & Scenario | Attack Surface | Existing Protection | Implementation Protection | Residual Risk |
|---|---|---|---|---|---|
| **T1** | **Database Compromise** (SQL/NoSQL data extraction) | Database disk / volume | Database user authentication | **AES-256-GCM** application-level encryption for sensitive columns & user profiles | Memory dump attacks on active application server process |
| **T2** | **Stolen Database Backup** (Unencrypted offsite snapshot leak) | Backup storage / S3 buckets | File permissions | **AES-256-GCM** versioned envelopes ensure backup values remain unreadable ciphertext | Compromise of master KMS key |
| **T3** | **API Credential Leakage** (Exposed integration tokens) | Environment variables / API endpoints | Environment variables | Centralized `secrets.py` secret provider + automated log redaction | Hardcoding keys in uncommitted local dev files |
| **T4** | **Unauthorized Facility Access** (Cross-tenant data peek) | `/api/v1/*` endpoints | Role checks | **Facility-Level ABAC** (`require_facility_access`) enforcing strict tenant isolation | Super admin credential theft |
| **T5** | **Object-Level Authorization Failure** (Bypassing route guards) | Deep REST resources | Static role lists | Centralized server-side **RBAC Permission Matrix** evaluated per request | Misconfigured role permission assignment |
| **T6** | **IoT Device Compromise** (Spoofed sensor hardware) | ESP32 gateway / Modbus RS-485 | WiFi WPA2 | Authenticated MQTT telemetry ingestion + device sequence counters + TLS | Physical hardware tampering on field meters |
| **T7** | **Edge Device Compromise** (Local edge cache theft) | Edge SQLite database | File permissions | Restricted filesystem permissions + AES-256-GCM local encrypted cache | Physical extraction of unencrypted flash memory |
| **T8** | **Network Interception** (Man-in-the-Middle) | Transit network / HTTP | None | Mandatory **TLS 1.3** + HSTS (`Strict-Transport-Security`) headers | User ignoring self-signed certificate warnings |
| **T9** | **Secret Leakage in Logs** (Passwords/tokens in log files) | Server stdout / audit logs | Raw logging | **Automated Secret Redaction** (`redact_secrets`) scrubbing passwords, JWTs, API keys | Unformatted standard print statements in third-party libs |
| **T10** | **Frontend Secret Exposure** (Leaked keys in client JS) | Browser DOM / LocalStorage | Client code | **Strict Server-Side Secret Management**; zero encryption keys sent to client | XSS extracting non-secret user JWT from memory |
| **T11** | **Token Theft / Replay** (Stolen JWT bearer tokens) | HTTP Headers | Session expiration | Cryptographically signed HMAC-SHA256 JWTs with 8-hour expiry + Revocation blacklist | Token theft from compromised client browser |
| **T12** | **Replay Attacks** (Duplicate telemetry payloads) | IoT ingestion route | None | Sequence numbers + timestamp freshness validation | Replay within narrow time window |
| **T13** | **Malicious Ciphertext Modification** (Tampering) | Encrypted storage rows | None | **AES-256-GCM 128-bit Authentication Tag** verification; invalid tag fails decryption | Denial of Service via corrupted ciphertext payload |
| **T14** | **Insider Access** (Unauthorized DB admin reading data) | Database query interface | DB Access Control | **Application-Level AES-256-GCM** ensures DB admins see only ciphertext | Application server process compromise |
| **T15** | **Supply-Chain Dependency Compromise** | Python PyPI packages | Package pinning | Audited standard libraries (`cryptography`, `argon2-cffi`); manual crypto prohibited | Zero-day vulnerability in underlying C extensions |
| **T16** | **Ransomware / Storage Compromise** | Storage filesystem | Backups | Immutable versioned backup snapshots + encrypted data | Complete infrastructure destruction |
| **T17** | **AI Prompt / Data Leakage** (Exposing PII to external AI) | Groq API integration | Server calls | **Prompt Sanitization & Evidence Redaction** before sending queries to Groq | Sub-syllabic inference from aggregated metrics |

---

## 3. Data Classification Model

EstateIQ enforces a four-tier data classification hierarchy:

```
[LEVEL 0: PUBLIC] ----> Public UI, documentation, general facility metadata (No App Encryption)
[LEVEL 1: INTERNAL] ---> Operational metrics, general configs, ML metadata (Storage Encryption)
[LEVEL 2: CONFIDENTIAL] -> Telemetry details, maintenance work orders (AES-256-GCM Encryption)
[LEVEL 3: HIGHLY SENSITIVE] -> Passwords (Argon2id), API Keys, Master Keys (KMS / AES-256-GCM + AAD)
```

### Level 0 — Public
- **Description**: Information intended for public view or general campus displays.
- **Examples**: Public project documentation, UI styling assets, general public sustainability statistics.
- **Encryption**: Not required at application level.

### Level 1 — Internal
- **Description**: Non-sensitive operational metrics and system configuration.
- **Examples**: Aggregated daily kWh totals, model feature metadata, system status flags.
- **Encryption**: Storage/volume-level encryption recommended; application encryption optional.

### Level 2 — Confidential
- **Description**: Sensitive building operational records, maintenance details, and detailed telemetry.
- **Examples**: Building-specific consumption spikes, work order staff notes, internal equipment health logs.
- **Encryption**: Application-level **AES-256-GCM** encryption applied to sensitive text/fields.

### Level 3 — Highly Sensitive
- **Description**: Critical security credentials, user identity records, integration keys, and private facility identifiers.
- **Examples**: User passwords, JWT secrets, Groq API keys, master AES keys, user recovery profiles.
- **Encryption**:
  - **Passwords**: Strictly one-way **Argon2id** password hashing (`Argon2id(password, salt)`). Passwords are NEVER reversibly encrypted.
  - **API / Master Keys**: External Secret Manager (AWS Secrets Manager / Vault) or AES-256-GCM with context AAD binding.

---

## 4. Pure Encryption vs Hashing vs Transport Security

All alternative algorithms (PBKDF2) have been removed from the platform.

```
+-----------------------------------------------------------------------------------+
|                            STRICT ESTATEIQ CRYPTOGRAPHY                           |
+--------------------------+--------------------------+-----------------------------+
|    AES-256-GCM (AEAD)    |    Argon2id (Strict)     |          TLS 1.3            |
+--------------------------+--------------------------+-----------------------------+
| Reversible Encryption    | One-Way Password Hashing | Transport Layer Security    |
| - Confidentiality        | - Non-reversible         | - In-Transit Privacy        |
| - 128-bit Auth Tag       | - Salted & Peppered      | - HSTS Enabled              |
| - Fresh Nonce per Op     | - GPU/ASIC Resistant     | - Secure Cookies            |
+--------------------------+--------------------------+-----------------------------+
```

---

## 5. Central Cryptography Architecture

All encryption operations are centralized inside `src/security/`:

```
Application Layer (api/main.py, services)
       │
       ▼
EncryptionService (src/security/encryption_service.py)
       │
       ▼
KeyManager (src/security/key_manager.py) ──► KeyProvider (Env / KMS)
       │
       ▼
AES256GCMCipher (src/security/crypto.py) ──► cryptography.hazmat.primitives.ciphers.aead.AESGCM
```

### AES-256-GCM Specification
- **Algorithm**: `AES-256-GCM`
- **Key Length**: 256 bits (32 bytes)
- **Nonce/IV**: 96 bits (12 bytes), generated via `os.urandom(12)` cryptographically secure random generator per operation.
- **Authentication Tag**: 128 bits (16 bytes) appended to ciphertext.
- **Associated Authenticated Data (AAD)**: Context string (e.g. `facility:FAC_GEC_01:user:USR_01`) bound during encryption and validated during decryption.

### Versioned Envelope Storage Format
Compact format:
`v1:<key_id>:<base64_nonce>:<base64_ciphertext>:<base64_tag>`

JSON envelope format:
```json
{
  "version": 1,
  "algorithm": "AES-256-GCM",
  "key_id": "estateiq-key-v1",
  "nonce": "...",
  "ciphertext": "...",
  "tag": "...",
  "created_at": "2026-10-08T20:45:00Z"
}
```

---

## 6. Key Management & Rotation Strategy

### KeyProvider Abstraction
- `EnvironmentKeyProvider`: Reads base64/hex keys from environment (`ESTATEIQ_MASTER_KEY`, `ESTATEIQ_KEY_V1`, `ESTATEIQ_KEY_V2`). Requires explicit key configuration; fallback hardcoded keys removed.
- `KMSKeyProvider`: AWS KMS / HashiCorp Vault / GCP Secret Manager Envelope Encryption interface (KEK protects DEK).

### Key Rotation Workflow
1. New active key version (e.g., `estateiq-key-v2`) is registered in KeyProvider.
2. New encryptions automatically use the latest active key version.
3. Legacy records encrypted with `estateiq-key-v1` remain decryptable.
4. Background rotation job calls `EncryptionService.rotate_key(envelope)` to re-encrypt old records without downtime.

---

## 7. Password Hashing (Strict Argon2id)

User passwords are protected strictly using **Argon2id** via `argon2-cffi`:
- **Time Cost ($t$)**: 2 iterations
- **Memory Cost ($m$)**: 19,456 KiB (~19 MB)
- **Parallelism ($p$)**: 1 thread
- **Salt**: 16 bytes fresh cryptographically secure random salt

Non-Argon2id hashes (PBKDF2) are rejected upon authentication.

---

## 8. Security Status API

Administrators can inspect security configuration status via:
`GET /api/v1/admin/security/status`

Sample Response:
```json
{
  "encryption": "AES-256-GCM",
  "key_management": "configured",
  "key_version": "estateiq-key-v1",
  "available_key_versions": ["estateiq-key-v1"],
  "password_hashing": "Argon2id",
  "tls_required": false,
  "rbac_enabled": true,
  "facility_authorization": true,
  "audit_logging": true,
  "secret_scanning": true,
  "mode": "development"
}
```
