# 🌐 EstateIQ REST API Documentation

Comprehensive REST API reference for **EstateIQ Sustainable Facility & Estate Intelligence Platform**.

Base URL: `http://localhost:8000`  
Interactive Swagger UI: `http://localhost:8000/docs`  
ReDoc UI: `http://localhost:8000/redoc`  

---

## 📡 API Endpoints Overview

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
| `POST` | `/api/v1/ai/copilot` | **Grounded Groq AI Copilot decision query endpoint** | No |
| `POST` | `/api/v1/ai/chat` | AI Copilot query endpoint alias | No |
| `GET` | `/api/v1/ai/health` | **AI Service availability, latency, and status health check** | No |
| `POST` | `/api/v1/ai/test` | **Executes minimal live ping test to Groq API gateway** | No |
| `POST` | `/api/v1/auth/login` | Prototype RBAC login endpoint | No |
| `GET` | `/api/v1/auth/me` | Current user session metadata | No |
| `POST` | `/api/v1/subscription/upgrade` | SaaS subscription tier upgrade endpoint | **Yes (`subscription_upgrade`)** |

---

## 💻 Sample Requests & Responses

### 1. AI Copilot Query Endpoint
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
  "assumptions": ["Tariff: ₹9.50/kWh", "CEA Emission Factor: 0.82 kg CO2e/kWh"],
  "limitations": ["Model prediction based on 15-min interval IoT stream"],
  "confidence": 92.5,
  "data_status": "SIMULATED IoT",
  "ai_provider": "groq",
  "model": "llama-3.3-70b-versatile",
  "generated_at": "2026-10-07T13:55:00Z",
  "fallback_used": false,
  "data_source_badge": "[SIMULATED IoT]"
}
```

---

### 2. AI Health Endpoint
`GET /api/v1/ai/health`

**Response**:
```json
{
  "enabled": true,
  "provider": "groq",
  "configured": true,
  "model": "llama-3.3-70b-versatile",
  "status": "healthy",
  "latency_ms": 12.5,
  "mode": "production"
}
```

---

### 3. AI Live Connection Test Endpoint
`POST /api/v1/ai/test`

**Request**:
```json
{
  "prompt": "Respond with exactly: ESTATEIQ_GROQ_CONNECTION_OK"
}
```

**Response**:
```json
{
  "success": true,
  "provider": "groq",
  "model": "llama-3.3-70b-versatile",
  "message": "ESTATEIQ_GROQ_CONNECTION_OK",
  "latency_ms": 284.5
}
```
