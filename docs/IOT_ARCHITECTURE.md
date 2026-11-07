# EstateIQ Edge & IoT Architecture Specification

This document details the edge telemetry acquisition, transport, device registry, buffering, and ingestion architecture for the **EstateIQ Facility Decision Intelligence Platform**.

---

## 1. Physical & Simulated Data Flow Architecture

```text
 ┌────────────────────────────────────────────────────────┐
 │            PHYSICAL SENSING LAYER                      │
 │  Eastron SDM630 Modbus RTU (Active Energy, Power, PF)  │
 │  YF-S201 Hall Turbine Water Meter (Pulse Counter)      │
 │  4-20 mA Pressure Transmitter (150 Ohm Shunt Loop)     │
 └──────────────────────────┬─────────────────────────────┘
                            │ (Isolated Serial / Discrete Pulses)
                            ▼
 ┌────────────────────────────────────────────────────────┐
 │            ESP32 PHYSICAL EDGE GATEWAY                 │
 │  Device ID: ESP32_EDGE_GATEWAY_01                      │
 │  Mornsun TD301D485H Galvanically Isolated Transceiver  │
 │  NTP Time Synchronization & Monotonic Sequence Counter │
 │  Dual Transport: Direct HTTP REST or Authenticated MQTT│
 └──────────────────────────┬─────────────────────────────┘
                            │
                            │ (HTTP POST or MQTT)
                            ▼
 ┌────────────────────────────────────────────────────────┐
 │           ESTATEIQ INGESTION LAYER (FastAPI)           │
 │  Endpoint: POST /api/v1/iot/telemetry                  │
 │  Headers: X-Gateway-Key / X-API-Key                    │
 │  Schema Validation & Sanitization                      │
 │  Provenance Tagging: [REAL SENSOR] vs [SIMULATED DATA] │
 └──────────────────────────┬─────────────────────────────┘
                            │
                            ├──────────────────────────┐
                            ▼                          ▼
 ┌──────────────────────────────────────┐   ┌─────────────────────────────────────┐
 │       CENTRAL DEVICE REGISTRY        │   │    REAL-TIME SSE STREAM SERVICE     │
 │  src/registry/device_registry.py     │   │  GET /api/v1/iot/telemetry/stream   │
 │  Heartbeat tracking & health states  │   │  Push updates to Liquid Glass Web UI│
 └──────────────────┬───────────────────┘   └─────────────────────────────────────┘
                    │
                    ▼
 ┌────────────────────────────────────────────────────────┐
 │           ESTATEIQ-DIF v2.0 DECISION ENGINE            │
 │  Seasonal Median-MAD Baseline  •  Domain Physics Rules │
 │  Score Fusion  •  Temporal Persistence Window          │
 └────────────────────────────────────────────────────────┘
```

---

## 2. Ingestion Endpoints Specification

All incoming telemetry is ingested through canonical REST endpoints defined in `api/canonical_routes.py` and `api/main.py`:

| Canonical Endpoint | Method | Role & Description |
|---|---|---|
| `POST /api/v1/iot/telemetry` | `POST` | Ingests a single telemetry packet or array batch. Supports both physical hardware and simulated sources. |
| `GET /api/v1/iot/telemetry/stream` | `GET` | Server-Sent Events (SSE) live stream delivering newly ingested readings to connected dashboards without polling. |
| `GET /api/v1/iot/telemetry/recent` | `GET` | Fetches recent telemetry readings filtered by `device_id` or `building_id`. |
| `GET /api/v1/iot/devices` | `GET` | Returns list of registered devices, health status (`ONLINE`, `STREAMING`, `STALE`, `OFFLINE`), and last sample. |
| `POST /api/v1/iot/devices/register` | `POST` | Registers or updates device profile metadata in the central registry. |
| `POST /api/v1/iot/simulators/pair` | `POST` | Single-use pairing code exchange for LAN simulator discovery. |
| `POST /api/v1/iot/simulators/{instance_id}/heartbeat`| `POST` | Dispatches operational heartbeat from edge nodes. |

### Backward Compatibility Endpoints
For existing clients, backward-compatible aliases are preserved:
- `POST /api/v1/ingestion/telemetry` ➔ routes to canonical ingestion.
- `POST /api/v1/ingestion/batch` ➔ routes to canonical batch ingestion.
- `GET /api/v1/devices` ➔ routes to canonical device listing.
- `GET /api/v1/devices/{device_id}/health` ➔ returns individual device health.

---

## 3. Telemetry Sources & Provenance Segregation

EstateIQ enforces strict separation of real-world hardware measurements from simulated demo data:

| Metric Characteristic | Physical Hardware (`ESP32_EDGE_GATEWAY_01`) | Standalone Resource Simulator (Port 8503) | Standalone IoT Simulator (Port 8502) |
|---|---|---|---|
| `source_type` | `"hardware"` | `"simulated_iot"` | `"simulated_iot"` |
| `is_verified_hardware` | `true` | `false` | `false` |
| **Authentication** | `X-Gateway-Key: ESTATEIQ-GATEWAY-SECRET-KEY` | Localhost loopback / LAN | Pairing Token |
| **UI Badge** | `[REAL SENSOR]` (Emerald Green) | `[SIMULATED DATA]` (Amber/Indigo) | `[SIMULATED DATA]` |
| **Hardware Attached** | Eastron SDM630 Modbus, YF-S201 Pulse | Pure numerical physics models | 12 Virtual campus device profiles |

---

## 4. Edge Hardware & ESP32 Implementation

The physical edge gateway is powered by an ESP32 microcontroller running verified firmware:

- **Source Code**: [hardware/esp32/firmware/main.ino](../hardware/esp32/firmware/main.ino)
- **Configuration**: [hardware/esp32/firmware/config.h.example](../hardware/esp32/firmware/config.h.example)
- **Wiring & Safety Guide**: [hardware/esp32/README.md](../hardware/esp32/README.md)
- **Hardware Prototype Specs**: [docs/HARDWARE_PROTOTYPE.md](HARDWARE_PROTOTYPE.md)

### Key Edge Gateway Capabilities
1. **NTP Timestamping**: Queries local NTP servers (`pool.ntp.org`) to assign microsecond-precision UTC timestamps (`event_timestamp`).
2. **Monotonic Sequence Counter**: Increments sequence number per transmission to ensure chronological ordering and detect packet drops.
3. **Dual Transport Selection**:
   - `USE_HTTP_INGESTION`: Direct HTTP POST to `http://<server-ip>:8000/api/v1/iot/telemetry`.
   - `MQTT`: Publishes JSON packets to `estateiq/telemetry/ESP32_EDGE_GATEWAY_01`.
4. **Galvanic Isolation**: Uses Mornsun TD301D485H with integrated DC-DC converter providing 2500 VDC isolation barrier between high-voltage Modbus lines and the ESP32.

---

## 5. Simulators Suite

EstateIQ provides two dedicated, isolated simulation tools for demonstration without physical sensors:

### 1. Standalone Multi-Utility Resource Simulator (Port 8503)
- Located in `resource-simulator-app/`.
- Independent process and UI dedicated to the 4 campus utilities: Electricity, Water, Air Quality, and Waste.
- Dispatches canonical telemetry to `POST /api/v1/iot/telemetry` while preserving standalone offline operation.
- Documentation: [docs/RESOURCE_SIMULATOR.md](RESOURCE_SIMULATOR.md).

### 2. Standalone Multi-Device IoT Simulator (Port 8502)
- Located in `iot-simulator-app/`.
- Independent process simulating 12 campus device profiles with 14 physics anomaly presets.
- Includes local offline buffer (`data/buffer.json`) to queue packets during temporary network dropouts.
- Documentation: [docs/IOT_SIMULATOR_ARCHITECTURE.md](IOT_SIMULATOR_ARCHITECTURE.md).

---

## 6. Verification and Test Suite

The edge architecture is verified through automated integration tests:

```bash
# Run physical hardware gateway integration test suite (12/12 passing)
python -m pytest tests/test_hardware_integration.py -v

# Run resource simulator test suite (8/8 passing)
python -m pytest tests/test_resource_simulator.py -v
```
