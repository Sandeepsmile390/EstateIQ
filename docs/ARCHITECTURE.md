# 🏛️ EstateIQ-DIF v2.0 — System Architecture Guide

> **Note:** For the complete, exhaustive 10-layer architectural specification, see [ARCHITECTURE.md](../ARCHITECTURE.md) in the project root.

---

## 1. Architectural Overview & Component Stack

EstateIQ is structured as a decoupled, microservice-ready decision intelligence platform with unified calculations and multiple presentation clients:

```text
 ┌───────────────────────────────────────────────────────────────────────────────────────────────────┐
 │                                   1. PHYSICAL & SIMULATED EDGE                                    │
 │   ESP32 Edge Gateway (Modbus/Pulse)  •  IoT Simulator (Port 8502)  •  Resource Simulator (Port 8503)│
 └─────────────────────────────────────────────────┬─────────────────────────────────────────────────┘
                                                   │ (HTTP POST / MQTT Canonical JSON Stream)
                                                   ▼
 ┌───────────────────────────────────────────────────────────────────────────────────────────────────┐
 │                                2. INGESTION & DATA QUALITY LAYER                                  │
 │   FastAPI Ingestion (/api/v1/iot/telemetry)  •  Pydantic Validation  •  Data Quality Score (0-100)│
 │   Device Registry Engine  •  Provenance Badges: [REAL SENSOR] vs [SIMULATED DATA]                │
 └─────────────────────────────────────────────────┬─────────────────────────────────────────────────┘
                                                   │
                                                   ▼
 ┌───────────────────────────────────────────────────────────────────────────────────────────────────┐
 │                               3. CONTEXTUAL BASELINE & FEATURE ENGINE                             │
 │   Seasonal Median-MAD Profiles  •  Thermal Sensitivity Models  •  Schedule & Occupancy Multipliers│
 └─────────────────────────────────────────────────┬─────────────────────────────────────────────────┘
                                                   │ (Expected Baseline + Dynamic Bounds)
                                                   ▼
 ┌───────────────────────────────────────────────────────────────────────────────────────────────────┐
 │                               4. SPECIALIST MACHINE LEARNING ENSEMBLE                             │
 │   XGBoost Regressor  •  LightGBM  •  CatBoost  •  Prophet  •  Isolation Forest  •  SHAP Explainer  │
 └─────────────────────────────────────────────────┬─────────────────────────────────────────────────┘
                                                   │ (Predictions + Local SHAP Attributions)
                                                   ▼
 ┌───────────────────────────────────────────────────────────────────────────────────────────────────┐
 │                             5. ESTATEIQ-DIF v2.0 DECISION META-ENGINE                             │
 │   Early Exit Filter  •  Multi-Signal Fusion  •  Temporal Persistence Window (Sliding Queue)      │
 │   Model Consensus  •  Independent Confidence Engine (0-100)  •  Cost of Inaction (₹9.50/kWh)      │
 └─────────────────────────────────────────────────┬─────────────────────────────────────────────────┘
                                                   │ (Structured JSON Evidence Packet)
                                                   ▼
 ┌───────────────────────────────────────────────────────────────────────────────────────────────────┐
 │                                    6. UNIFIED SERVICE LAYER                                       │
 │           FacilityService           •         EnergyService         •        SimulationService        │
 └─────────────────────────┬─────────────────────────────────────────────────────┬───────────────────┘
                           │                                                     │
                           ▼                                                     ▼
 ┌───────────────────────────────────────────────────┐ ┌───────────────────────────────────────────────┐
 │          7A. FASTAPI REST BACKEND SERVER          │ │       7B. STREAMLIT COMMAND CENTER DASHBOARD  │
 │  Port 8000 (OpenAPI /docs)                        │ │  Port 8501                                    │
 │  SSE Stream: /api/v1/iot/telemetry/stream         │ │  Glassmorphic UI, Plotly Charts, GIS Map      │
 │  Liquid Glass Web Client (web/index.html)         │ │  What-If Scenario Simulator, Audit Logs       │
 └───────────────────────────────────────────────────┘ └───────────────────────────────────────────────┘
```

---

## 2. Telemetry Ingestion Services

EstateIQ ingests telemetry through three distinct channels, all standardized to canonical Pydantic schemas:

1. **Physical Hardware Gateway (`ESP32_EDGE_GATEWAY_01`)**:
   - Transports: Direct HTTP REST (`POST /api/v1/iot/telemetry`) or authenticated MQTT.
   - Headers: `X-Gateway-Key` or `X-API-Key`.
   - Provenance: `source_type: "hardware"`, `is_verified_hardware: true`.
   - Display Badge: `[REAL SENSOR]` (Emerald Green).
   - Documentation: [hardware/esp32/README.md](../hardware/esp32/README.md).

2. **Standalone Multi-Utility Resource Simulator (Port `8503`)**:
   - Location: `resource-simulator-app/`.
   - Dedicated controller for Electricity (`SIM-ELEC-01`), Water (`SIM-WATER-01`), Air Quality (`SIM-AIR-01`), and Waste (`SIM-WASTE-01`).
   - Provenance: `source_type: "simulated_iot"`, `is_verified_hardware: false`.
   - Display Badge: `[SIMULATED DATA]` (Amber/Indigo).
   - Documentation: [docs/RESOURCE_SIMULATOR.md](RESOURCE_SIMULATOR.md).

3. **Standalone Multi-Device IoT Simulator (Port `8502`)**:
   - Location: `iot-simulator-app/`.
   - 12 virtual device profiles, 14 physics anomaly scenarios, pairing code discovery.
   - Documentation: [docs/IOT_SIMULATOR_ARCHITECTURE.md](IOT_SIMULATOR_ARCHITECTURE.md).

---

## 3. Real-Time Telemetry Streaming

The backend provides Server-Sent Events (SSE) for zero-polling, real-time telemetry streaming:

```http
GET /api/v1/iot/telemetry/stream HTTP/1.1
Host: localhost:8000
Accept: text/event-stream
```

Both the **Liquid Glass Web App** (`web/index.html`) and external monitoring tools subscribe to this endpoint to receive instantaneous live meter updates as soon as packets arrive from either physical or simulated sources.

---

## 4. Multi-Tier Security & RBAC

The platform enforces strict 4-tier Role-Based Access Control:

| Role | Permitted Operations |
|---|---|
| `administrator` | Full campus config, demo seed/reset, system thresholds, user role management, batch rollback. |
| `operations` | Acknowledge and assign alerts, update work order status, log completion notes. |
| `sustainability` | What-If simulations, ESG sustainability metrics, scoped CSV and printable report generation. |
| `viewer` | Read-only access to facility overviews and historical trends. |

Server-side enforcement ensures that users lacking authorization receive HTTP `403 Forbidden` rather than relying merely on UI component hiding.

---

## 5. Key Documentation Links

- Root Architecture: [ARCHITECTURE.md](../ARCHITECTURE.md)
- Technology Stack: [TECHSTACK.md](../TECHSTACK.md)
- API Specification: [docs/API_DOCUMENTATION.md](API_DOCUMENTATION.md)
- Physical Hardware Prototype: [docs/HARDWARE_PROTOTYPE.md](HARDWARE_PROTOTYPE.md)
- Resource Simulator: [docs/RESOURCE_SIMULATOR.md](RESOURCE_SIMULATOR.md)
- Master Index: [docs/README.md](README.md)
