# 🌐 EstateIQ REST API Documentation

Comprehensive REST API reference for **EstateIQ Sustainable Facility & Estate Intelligence Platform**.

- Base URL: `http://localhost:8000`  
- Interactive Swagger UI: `http://localhost:8000/docs`  
- ReDoc UI: `http://localhost:8000/redoc`  
- Standalone Resource Simulator API: `http://localhost:8503/docs`  
- Standalone IoT Simulator API: `http://localhost:8502/docs`  

---

## 📡 API Endpoints Overview

### 1. Core Facility, Telemetry & Anomaly Endpoints
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :---: |
| `GET` | `/health` or `/api/v1/health` | Service health status and timestamp | No |
| `GET` | `/api/v1/facility/summary` | Summary of facility metadata and building counts | No |
| `GET` | `/api/v1/energy/history` | Historical sensor energy readings | No |
| `POST` | `/predict/energy` or `/api/v1/energy` | Predicts hourly electricity consumption (kWh) with provenance | No |
| `GET` | `/api/v1/energy/forecast` | Short-term energy forecasting horizons (1h, 4h, 24h) | No |
| `GET` | `/api/v1/energy/anomalies` | Active energy anomaly alerts & baseline deviations | No |
| `GET` | `/api/v1/water` | Water consumption summary & provenance badge | No |
| `POST` | `/anomaly/water` or `/api/v1/water/anomaly` | Detects abnormal water usage flow patterns | No |
| `POST` | `/predict/waste` or `/api/v1/waste` | Predicts 2-hour bin overflow probability & risk level | No |
| `GET` | `/api/v1/waste/summary` | Waste bin monitoring summary | No |
| `GET` | `/api/v1/air` | Campus air quality index (AQI) telemetry | No |
| `GET` | `/api/v1/traffic` | Campus gate traffic entry rate & speed | No |
| `GET` | `/api/v1/parking` | Parking zone occupancy rates & capacity | No |
| `GET` | `/api/v1/equipment` | Asset predictive health & vibration telemetry | No |
| `GET` | `/api/v1/safety` | Recorded safety incidents | No |
| `GET` | `/api/v1/alerts` | Platform operational priority alerts (Priority 1/2/3) | No |
| `GET` | `/api/v1/decisions/{id}` | **11-Step Grounded Decision Trace Audit Ledger** | No |
| `POST` | `/recommendations` or `/api/v1/recommendations` | Generates 7-part operational action plan | No |
| `POST` | `/api/v1/recommendations/apply` | Records simulated operational rule execution | **Yes (`action_execute`)** |
| `POST` | `/scenario` or `/api/v1/simulation` | Runs model-driven What-If scenario simulations | No |
| `GET` | `/models` or `/api/v1/models` | List registered ML models and validation metrics | No |
| `GET` | `/api/v1/data-quality` | **Data Completeness, Sensor Health & Provenance Report** | No |
| `GET` | `/api/v1/sustainability` | Configurable transparent Sustainability Health Score | No |

### 2. Edge IoT Telemetry, Device Registry & Gateway Endpoints
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :---: |
| `POST` | `/api/v1/iot/telemetry` | **Canonical Ingestion Endpoint:** Ingests real-time JSON envelope from ESP32 gateway or simulator | Gateway Key |
| `POST` | `/api/v1/iot/telemetry/batch` | Ingests offline buffered batch of telemetry envelopes | Gateway Key |
| `GET` | `/api/v1/iot/telemetry/stream` | **Real-Time Telemetry Stream:** Returns recent packets with verified provenance across all devices | No |
| `GET` | `/api/v1/iot/devices` | Lists registered physical and virtual IoT devices, last readings, and health status | No |
| `GET` | `/api/v1/iot/devices/{device_id}` | Detailed telemetry and configuration for a specific device | No |
| `GET` | `/api/v1/iot/devices/{device_id}/telemetry/latest` | Returns latest sample and source provenance badge | No |
| `GET` | `/api/v1/iot/devices/{device_id}/telemetry/history` | Historical rolling telemetry for a specific device | No |
| `POST` | `/api/v1/iot/devices/{device_id}/disable` | Temporarily disables a reporting device | Yes |
| `GET` | `/api/v1/iot/simulators` | Lists registered simulator instances | No |
| `POST` | `/api/v1/iot/pair` | Validates one-time single-use pairing code for simulator enrollment | No |
| `POST` | `/api/v1/iot/simulators/register` | Registers simulator instance and issues auth token | No |
| `POST` | `/api/v1/iot/simulators/{instance_id}/heartbeat` | Records simulator connection heartbeat | No |
| `POST` | `/api/v1/iot/simulators/{instance_id}/revoke` | Revokes simulator credentials | Yes |

### 3. Interactive IoT Simulator Controller Endpoints (Port 8000)
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :---: |
| `GET` | `/api/v1/iot-simulator/status` | Returns simulation clock, sensor values, and active preset | No |
| `POST` | `/api/v1/iot-simulator/control` | Control simulation (`start`, `pause`, `resume`, `stop`, `step`, `reset`) | No |
| `POST` | `/api/v1/iot-simulator/scenario` | Apply scenario preset (`Normal`, `High HVAC`, `Water Leak`, etc.) | No |
| `POST` | `/api/v1/iot-simulator/sensors` | Override specific sensor slider values | No |
| `GET` | `/api/v1/iot-simulator/stream` | Rolling stream log of generated simulator samples | No |
| `POST` | `/api/v1/iot-simulator/evaluate` | Runs DIF anomaly consensus and SHAP attribution on live simulator state | No |

### 4. Standalone Multi-Utility Resource Simulator Endpoints (Port 8503)
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :---: |
| `GET` | `/health` | Standalone health status (`{"status": "ok", "port": 8503}`) | No |
| `GET` | `/api/status` | Complete state of all 4 utilities (Electricity, Water, Air, Waste) | No |
| `POST` | `/api/start` | Start simulation for all or single utility (`?utility=electricity`) | No |
| `POST` | `/api/pause` | Toggle pause/resume state | No |
| `POST` | `/api/stop` | Stop simulation | No |
| `POST` | `/api/step` | Advance simulation by one step | No |
| `POST` | `/api/reset` | Reset counters or restore default baseline values | No |
| `POST` | `/api/scenario` | Select utility scenario preset | No |
| `POST` | `/api/config/baseline` | Adjust baseline active load, water flow, occupants, or waste rate | No |
| `POST` | `/api/config/interval` | Adjust reporting frequency in seconds | No |
| `GET` | `/api/stream` | Rolling 30-sample history for live Chart.js visualization | No |

### 5. AI Co-Pilot & Security Endpoints
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :---: |
| `POST` | `/api/v1/ai/copilot` | **Grounded Groq AI Copilot query endpoint** with Evidence Packet | No |
| `POST` | `/api/v1/ai/chat` | AI Copilot query endpoint alias | No |
| `GET` | `/api/v1/ai/health` | AI service latency, availability, and provider status | No |
| `POST` | `/api/v1/ai/test` | Executes minimal live ping test to Groq API gateway | No |
| `POST` | `/api/v1/auth/login` | RBAC authentication endpoint issuing scoped JWT | No |
| `GET` | `/api/v1/auth/me` | Current user profile and role permissions | Yes |
| `POST` | `/api/v1/subscription/upgrade` | SaaS subscription tier upgrade | Yes |

---

## 💻 Sample Requests & Responses

### 1. Ingest Canonical Telemetry Envelope
`POST /api/v1/iot/telemetry`

**Request**:
```json
{
  "schema_version": "1.0",
  "message_id": "MSG_ESP32_ELEC_1731000000",
  "gateway_id": "ESP32_EDGE_GATEWAY_01",
  "device_id": "METER-BLOCK-B-001",
  "auth_token": "gw_secret_estateiq_hw_2026",
  "facility_id": "FAC_GEC_CAMPUS",
  "building_id": "Block B Hostel",
  "source_type": "real_sensor",
  "event_timestamp": "2026-11-07T14:30:00Z",
  "sent_timestamp": "2026-11-07T14:30:01Z",
  "sequence_number": 142,
  "metrics": [
    {"metric": "voltage_v", "value": 231.4, "unit": "V", "quality": "good"},
    {"metric": "current_a", "value": 64.2, "unit": "A", "quality": "good"},
    {"metric": "active_power_kw", "value": 14.85, "unit": "kW", "quality": "good"},
    {"metric": "cumulative_energy_kwh", "value": 12845.6, "unit": "kWh", "quality": "good"},
    {"metric": "power_factor", "value": 0.96, "unit": "ratio", "quality": "good"},
    {"metric": "frequency_hz", "value": 50.02, "unit": "Hz", "quality": "good"}
  ]
}
```

**Response**:
```json
{
  "success": true,
  "accepted": true,
  "message_id": "MSG_ESP32_ELEC_1731000000",
  "device_id": "METER-BLOCK-B-001",
  "source_type": "real_sensor",
  "is_verified_hardware": true,
  "data_source_badge": "[REAL SENSOR]",
  "status": "INGESTED",
  "warnings": []
}
```

---

### 2. Query Real-Time Telemetry Stream
`GET /api/v1/iot/telemetry/stream?limit=2`

**Response**:
```json
{
  "count": 2,
  "total_ingested": 1420,
  "stats": {
    "total_devices": 8,
    "online_devices": 8,
    "verified_hardware_devices": 2,
    "simulated_devices": 6
  },
  "stream": [
    {
      "message_id": "MSG_ESP32_ELEC_1731000000",
      "device_id": "METER-BLOCK-B-001",
      "building_id": "Block B Hostel",
      "source_type": "real_sensor",
      "is_verified_hardware": true,
      "data_source_badge": "[REAL SENSOR]",
      "event_timestamp": "2026-11-07T14:30:00Z",
      "metrics": {
        "active_power_kw": 14.85,
        "cumulative_energy_kwh": 12845.6,
        "voltage_v": 231.4,
        "current_a": 64.2,
        "power_factor": 0.96,
        "frequency_hz": 50.02
      },
      "status": "INGESTED"
    }
  ]
}
```

---

### 3. AI Copilot Query Endpoint
`POST /api/v1/ai/copilot`

**Request**:
```json
{
  "query": "Why is energy consumption high in Block B Hostel?",
  "facility_id": "FAC_GEC_CAMPUS",
  "building_id": "Block B Hostel"
}
```

**Response**:
```json
{
  "success": true,
  "request_id": "REQ_AI_9A8B7C",
  "response": "Electricity consumption in Block B Hostel is 145.2 kWh vs expected 78.0 kWh baseline (+86.1% deviation).",
  "summary": "Electricity consumption in Block B Hostel is 145.2 kWh vs expected 78.0 kWh baseline.",
  "what_happened": "HVAC compressor override detected during peak ambient temperature.",
  "why": [
    "Contextual baseline deviation (+86.1%) and SHAP HVAC driver attribution (+42%)."
  ],
  "evidence": [
    {"metric": "actual_kwh", "value": 145.2},
    {"metric": "occupancy", "value": 140},
    {"metric": "temperature_c", "value": 32.0}
  ],
  "recommended_actions": [
    {
      "title": "Reset thermostat setback schedule to 24.5°C",
      "reason": "Derived from SHAP feature drivers & DIF priority",
      "expected_cost_saving_inr": 11500.0
    }
  ],
  "confidence": 92.5,
  "data_status": "SIMULATED IoT",
  "ai_provider": "groq",
  "model": "llama-3.3-70b-versatile",
  "data_source_badge": "[SIMULATED IoT]"
}
```
