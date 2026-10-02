# 🌐 FastAPI REST API Documentation

Comprehensive REST API reference for **Facility Intelligence AI**.

Base URL: `http://localhost:8000`  
Interactive Swagger UI: `http://localhost:8000/docs`  
ReDoc UI: `http://localhost:8000/redoc`  

---

## 📡 API Endpoints Overview

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` or `/api/v1/health` | Service health status and timestamp |
| `GET` | `/api/v1/facility/summary` | Summary of facility metadata and building counts |
| `POST` | `/predict/energy` or `/api/v1/energy` | Predicts hourly electricity consumption (kWh) |
| `GET` | `/api/v1/energy/forecast` | Short-term energy forecasting horizons (1h, 4h, 24h) |
| `GET` | `/api/v1/energy/anomalies` | Active energy anomaly alerts |
| `GET` | `/api/v1/water` | Water consumption summary & non-definitive leak disclaimer |
| `POST` | `/anomaly/water` or `/api/v1/water/anomaly` | Detects abnormal water usage flow patterns |
| `POST` | `/predict/waste` or `/api/v1/waste` | Predicts 2-hour bin overflow probability & risk level |
| `GET` | `/api/v1/waste/summary` | Waste bin monitoring summary |
| `GET` | `/api/v1/air` | Air quality indicators & Indian CPCB AQI proxy |
| `GET` | `/api/v1/traffic` | Gate traffic counts & vehicle fleet mix |
| `GET` | `/api/v1/parking` | Parking zone occupancy rates & capacity |
| `GET` | `/api/v1/equipment` | 35 campus assets maintenance-risk indicators |
| `GET` | `/api/v1/alerts` | Platform operational priority alerts (Priority 1/2/3) |
| `POST` | `/recommendations` or `/api/v1/recommendations` | Generates 7-part operational action plan |
| `POST` | `/scenario` or `/api/v1/simulation` | Runs What-If scenario simulations |
| `GET` | `/models` or `/api/v1/models` | List registered ML models and validation metrics |
| `POST` | `/api/v1/ai/chat` | AI Facility Assistant chat query with fallback |

---

## 💻 Sample Requests & Responses

### 1. Energy Prediction Endpoint
`POST /api/v1/energy`

**Request Payload**:
```json
{
  "temperature": 32.0,
  "humidity": 55.0,
  "occupancy": 150,
  "hvac_load": 55.0,
  "lighting_load": 15.0,
  "equipment_load": 25.0,
  "previous_energy_kwh": 125.0,
  "hour": 14,
  "day_of_week": 2
}
```

**Response**:
```json
{
  "task": "energy_kwh_prediction",
  "predicted_energy_kwh": 142.5,
  "algorithm": "Linear Regression",
  "unit": "kWh"
}
```

---

### 2. Waste Bin Overflow Prediction Endpoint
`POST /api/v1/waste`

**Request Payload**:
```json
{
  "fill_level": 82.0,
  "fill_rate": 5.0,
  "temperature": 30.0,
  "occupancy": 200,
  "day_of_week": 3,
  "hour": 16,
  "collection_time": 0
}
```

**Response**:
```json
{
  "task": "waste_overflow_2hr",
  "overflow_probability": 0.8845,
  "risk_level": "HIGH",
  "algorithm": "Logistic Regression",
  "note": "Probabilities represent estimated risk levels, not physical certainty."
}
```

---

### 3. AI Facility Assistant Chat Endpoint
`POST /api/v1/ai/chat`

**Request Payload**:
```json
{
  "user_query": "Why is energy consumption high in Block B Hostel?"
}
```

**Response**:
```json
{
  "mode": "Rule-Based Offline Fallback Engine (Active)",
  "query": "Why is energy consumption high in Block B Hostel?",
  "response": "Block B Hostel is experiencing elevated energy consumption (145 kWh vs 78 kWh baseline), primarily attributed to HVAC load and temperature features. Recommend inspecting thermostat controls.",
  "validated_context": true
}
```
