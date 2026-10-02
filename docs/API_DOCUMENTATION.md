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
| `GET` | `/api/v1/safety` | Recorded safety incidents (Sparse sample notice) | No |
| `GET` | `/api/v1/alerts` | Platform operational priority alerts (Priority 1/2/3) | No |
| `GET` | `/api/v1/decisions/{id}` | **11-Step Grounded Decision Trace Audit Ledger** | No |
| `POST` | `/recommendations` or `/api/v1/recommendations` | Generates 7-part operational action plan | No |
| `POST` | `/api/v1/recommendations/apply` | Records simulated operational rule execution | **Yes (`action_execute`)** |
| `POST` | `/scenario` or `/api/v1/simulation` | Runs model-driven What-If scenario simulations | No |
| `GET` | `/models` or `/api/v1/models` | List registered ML models and validation metrics | No |
| `GET` | `/api/v1/data-quality` | **Data Completeness, Sensor Health & Provenance Report** | No |
| `GET` | `/api/v1/sustainability` | Configurable transparent Sustainability Health Score | No |
| `POST` | `/api/v1/ai/chat` | AI Co-Pilot chat query with grounded context & fallback | No |
| `POST` | `/api/v1/auth/login` | Prototype RBAC login endpoint (Admin, Engineer, Auditor, Viewer) | No |
| `GET` | `/api/v1/auth/me` | Current user session metadata | No |
| `POST` | `/api/v1/subscription/upgrade` | SaaS subscription tier upgrade endpoint | **Yes (`subscription_upgrade`)** |

---

## 💻 Sample Requests & Responses

### 1. Decision Trace Audit Endpoint
`GET /api/v1/decisions/ALT_01`

**Response**:
```json
{
  "trace_id": "TRC_ALT_01",
  "alert_id": "ALT_01",
  "building": "Block B Hostel",
  "provenance_badge": "[SYNTHETIC IoT DATA]",
  "step_1_observed": {
    "metric": "Electricity Consumption",
    "value": 145.2,
    "unit": "kWh",
    "timestamp": "2026-10-02T18:00:00"
  },
  "step_2_baseline": {
    "expected_value": 78.0,
    "formula": "f(building, hour, occupancy, temp, HVAC)",
    "unit": "kWh"
  },
  "step_3_deviation": {
    "absolute_deviation": 67.2,
    "percentage_deviation": "+86.1%",
    "is_abnormal": true
  },
  "step_4_ml_prediction": {
    "1h_forecast": 152.5,
    "4h_forecast": 162.6,
    "24h_forecast": 2940.0,
    "confidence_interval": "±8.4%",
    "algorithm": "CatBoostRegressor"
  },
  "step_5_anomaly": {
    "is_anomaly": true,
    "anomaly_score": 0.88,
    "severity": "HIGH",
    "disclaimer": "Potential abnormal operational pattern detected. Physical inspection may be required."
  },
  "step_6_shap": {
    "feature_contributions": [
      {"feature": "HVAC Load", "impact": "+42%"},
      {"feature": "Occupancy Rate", "impact": "+18%"},
      {"feature": "Ambient Temperature", "impact": "+11%"}
    ],
    "disclaimer": "SHAP values explain model behavior. They do not prove physical causation."
  },
  "step_7_priority": {
    "priority_rank": "Priority 1 (URGENT)",
    "priority_score": 8.8,
    "action_complexity": "MEDIUM"
  },
  "step_8_recommendation": {
    "action_title": "HVAC Thermostat Setpoint Reset",
    "detailed_recommendation": "Reset thermostat setpoint schedule to 24.5°C in Block B Hostel."
  },
  "step_9_assumptions": [
    "Occupancy sensors report current building headcounts.",
    "Ambient temperature sensors reflect local microclimate."
  ],
  "step_10_whatif_impact": {
    "simulated_action": "Reduce HVAC load by 20%",
    "target_demand_kwh": 121.5,
    "hourly_kwh_reduction": 23.7,
    "monthly_inr_savings": 142800,
    "monthly_co2_reduction_tons": 16.4
  },
  "step_11_action_record": {
    "status": "PENDING_ADMIN_DISPATCH"
  }
}
```

---

### 2. Data Quality Center Endpoint
`GET /api/v1/data-quality`

**Response**:
```json
{
  "overall_quality_score": 96.5,
  "completeness": {
    "energy_data": "98.2%",
    "water_data": "96.5%",
    "waste_data": "97.0%",
    "occupancy_data": "94.1%",
    "weather_data": "99.8%",
    "air_quality": "95.4%"
  },
  "sensor_health": {
    "total_sensors": 245,
    "online": 238,
    "degraded": 5,
    "offline": 2
  },
  "data_provenance_summary": {
    "observed_sensors": "0% (Simulated Target)",
    "synthetic_iot_stream": "100% Active Feeds",
    "ml_forecasts": "Active CatBoost / XGBoost Pipelines"
  }
}
```
