# 🛡️ EstateIQ Enterprise RBAC & Permission Matrix

## Overview

EstateIQ employs a centralized, server-side Permission Matrix defined in `src/auth/security.py`. Every protected REST endpoint declares its required permission using the `require_permission(perm)` FastAPI dependency.

---

## Permission Matrix

| Permission | SUPER_ADMIN | FACILITY_ADMIN | OPERATIONS_ENGINEER | ESG_AUDITOR | MANAGEMENT_VIEWER |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `facility.read` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `facility.manage` | ✅ | ✅ | ❌ | ❌ | ❌ |
| `energy.read` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `energy.predict` | ✅ | ✅ | ✅ | ❌ | ❌ |
| `energy.configure` | ✅ | ✅ | ❌ | ❌ | ❌ |
| `water.read` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `waste.read` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `air.read` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `mobility.read` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `assets.read` | ✅ | ✅ | ✅ | ✅ | ❌ |
| `alerts.read` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `alerts.manage` | ✅ | ✅ | ✅ | ❌ | ❌ |
| `recommendations.read` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `recommendations.approve` | ✅ | ✅ | ❌ | ❌ | ❌ |
| `recommendations.execute` | ✅ | ✅ | ✅ | ❌ | ❌ |
| `simulation.read` | ✅ | ✅ | ✅ | ✅ | ❌ |
| `simulation.run` | ✅ | ✅ | ✅ | ❌ | ❌ |
| `models.read` | ✅ | ✅ | ✅ | ❌ | ❌ |
| `models.manage` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `reports.read` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `reports.export` | ✅ | ✅ | ❌ | ✅ | ❌ |
| `audit.read` | ✅ | ✅ | ❌ | ✅ | ❌ |
| `users.read` | ✅ | ✅ | ❌ | ❌ | ❌ |
| `users.manage` | ✅ | ❌ | ❌ | ❌ | ❌ |
