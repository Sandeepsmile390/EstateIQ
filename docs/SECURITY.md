# 🔒 EstateIQ Security & Governance Architecture

## Overview

EstateIQ implements an enterprise-grade, multi-tenant security architecture designed for institutional facility intelligence platforms in India. All authentication, role-based access control (RBAC), attribute-based facility scoping (ABAC), and security headers are enforced server-side via FastAPI dependencies.

---

## 1. Authentication Engine

- **Password Storage**: Uses PBKDF2-HMAC-SHA256 with 100,000 iterations and 16-byte random salts. Plaintext passwords are never stored.
- **Session Tokens**: Uses HMAC-SHA256 JWT access tokens with 8-hour expiration.
- **Token Revocation**: Maintains an active revoked token blacklist in memory for secure logout.
- **Endpoints**:
  - `POST /api/v1/auth/login`: Authenticates email & password, returns JWT token.
  - `GET /api/v1/auth/me`: Returns active authenticated user identity.
  - `POST /api/v1/auth/logout`: Revokes active access token.

---

## 2. Server-Side RBAC & ABAC

No security decision relies on frontend JavaScript. The frontend hides controls for UX convenience; the backend enforces strict authorization.

### Enterprise Roles
1. `SUPER_ADMIN`: System-wide full administration.
2. `FACILITY_ADMIN`: Facility-level management, energy, water, waste, air, assets, alerts, recommendations, actions, reports, users.
3. `OPERATIONS_ENGINEER`: Operational telemetry, energy forecasting, alerts management, action execution, simulation.
4. `ESG_AUDITOR`: Read-only operational views, sustainability index, carbon footprint audit, compliance exports.
5. `MANAGEMENT_VIEWER`: Executive KPI dashboards, high-level business impact reports.

### ABAC Scoping
All requests validate facility object ownership (`facility_id`). Cross-facility access attempts return HTTP 403 Forbidden.

---

## 3. Security Headers & Input Bounds

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- `Referrer-Policy: strict-origin-when-cross-origin`
- Typed Pydantic request models enforce strict numeric bounds on input parameters (temperature, occupancy, HVAC load, pagination max 500).
