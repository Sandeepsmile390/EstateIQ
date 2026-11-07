# EstateIQ Automated Test Suite

This directory contains the automated test suite verifying correctness, data provenance, physical hardware integration, simulation accuracy, and role-based security for the **EstateIQ Facility Decision Intelligence Platform**.

---

## 🧪 Test Suite Inventory

| Test Module | Coverage & Verification Focus | Test Count / Status |
|---|---|---|
| [`test_final_round_acceptance.py`](test_final_round_acceptance.py) | **Phase 0–10 Acceptance Specification**: Seed data, 14 zones, 4 injected anomalies, 24-hr forecast, What-If simulator, work order audit trail, RBAC, offline resilience. | ✅ **143 / 143 Passing** |
| [`test_hardware_integration.py`](test_hardware_integration.py) | **Physical ESP32 Gateway Integration**: Modbus RTU metrology, YF-S201 turbine pulse counter, 150 Ω shunt 4-20mA loop, dual HTTP/MQTT transport, registry auto-provisioning, SSE streaming, provenance badging. | ✅ **12 / 12 Passing** |
| [`test_resource_simulator.py`](test_resource_simulator.py) | **Standalone Resource Simulator**: Multi-utility physics models, monotonic totalizers (energy kWh, water L), EPA AQI derivation, standalone offline mode, canonical ingestion. | ✅ **8 / 8 Passing** |
| [`test_canonical_telemetry.py`](test_canonical_telemetry.py) | **Canonical Telemetry Validation**: Pydantic schema validation, provenance tagging (`[REAL SENSOR]` vs `[SIMULATED DATA]`), boundary checks, missing field rejections. | ✅ Passing |
| [`test_security.py`](test_security.py) | **4-Tier RBAC & Security**: JWT token validation, role hierarchy, admin-only route blocking with `403 Forbidden`, API key authentication. | ✅ Passing |
| [`test_ai_copilot_universal.py`](test_ai_copilot_universal.py) | **Grounded AI Copilot**: Grounded JSON Evidence Packet validation, LLM hallucination prevention, deterministic offline rule fallback. | ✅ Passing |
| [`test_dataset_synchronization.py`](test_dataset_synchronization.py) | **Dataset Integrity**: Verification of campus building profiles, hourly readings, and deterministic seeds. | ✅ Passing |
| [`test_work_orders_and_notifications.py`](test_work_orders_and_notifications.py) | **Closed-Loop Action Tracking**: State transitions (`OPEN` ➔ `ACKNOWLEDGED` ➔ `ASSIGNED` ➔ `COMPLETED`), operator notes, immutable audit logs. | ✅ Passing |
| [`test_anomaly.py`](test_anomaly.py) | **Anomaly Consensus**: Multi-signal fusion, contextual score, and physics rule firing. | ✅ Passing |
| [`test_forecasting.py`](test_forecasting.py) | **Forecasting Adapters**: Seasonal-naive benchmark and rolling moving average adapters. | ✅ Passing |

---

## 🚀 Running the Tests

### 1. Final Round Acceptance Test Suite (143 Tests)
```bash
python -m pytest tests/test_final_round_acceptance.py -v
```

### 2. Physical ESP32 Hardware Integration Test Suite (12 Tests)
```bash
python -m pytest tests/test_hardware_integration.py -v
```

### 3. Standalone Resource Simulator Test Suite (8 Tests)
```bash
python -m pytest tests/test_resource_simulator.py -v
```

### 4. Canonical Telemetry & Schema Tests
```bash
python -m pytest tests/test_canonical_telemetry.py -v
```

### 5. Run All Tests
```bash
python -m pytest tests/
```

---

## ⚠️ Sandbox & Socket Isolation Note

When executing tests in restricted sandbox environments where in-process TCP socket binding is restricted:
- Use unit-level function calls and direct API method invocations (as demonstrated in `test_hardware_integration.py` and `test_resource_simulator.py`).
- Do not instantiate background persistent HTTP socket servers in interactive test runs.
