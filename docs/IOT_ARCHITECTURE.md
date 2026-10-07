# EstateIQ Edge & IoT Architecture Specification

---

## 1. PHYSICAL TO AI DATA FLOW

```text
PHYSICAL METERS (Grid / Transformer / Sub-meter)
                   │
                RS-485 Modbus RTU
                   │
           ESP32 EDGE GATEWAY
                   │
             WiFi / MQTT Broker
                   │
       ESTATEIQ INGESTION SERVICE (FastAPI)
                   │
         DATA QUALITY & FINGERPRINT
                   │
           SPECIALIST ML ENGINES
                   │
            ESTATEIQ-DIF ENGINE
                   │
             GROQ AI COPILOT
```

---

## 2. INGESTION & DEVICE REGISTRY

The EstateIQ backend provides an ingestion service under `/api/v1/ingestion/*`:

| Endpoint | Method | Description |
|---|---|---|
| `POST /api/v1/ingestion/telemetry` | `POST` | Ingests real-time 15-second / 15-minute telemetry JSON payload |
| `POST /api/v1/ingestion/batch` | `POST` | Ingests offline buffered telemetry batch |
| `GET /api/v1/devices` | `GET` | Returns list of registered hardware meters and sensor nodes |
| `GET /api/v1/devices/{device_id}/health` | `GET` | Returns device health status (ONLINE, DEGRADED, STALE, OFFLINE, ERROR) |

---

## 3. OFFLINE EDGE BUFFERING

If network connectivity is interrupted:
1. ESP32 / Industrial Gateway buffers telemetry to SPIFFS / EEPROM / local queue.
2. When MQTT connection is restored, the gateway pushes buffered readings via `/api/v1/ingestion/batch`.
3. Zero telemetry loss during intermittent network outages.

---

## 4. HARDWARE SIMULATOR

For software demonstration and testing without physical hardware, run:

```bash
python scripts/iot_simulator.py
```

Supports `NORMAL`, `ANOMALY`, and `OFFLINE` simulation modes.
