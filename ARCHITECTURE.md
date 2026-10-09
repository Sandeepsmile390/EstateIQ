# 🏛️ EstateIQ-DIF v2.0 — Comprehensive System Architecture Specification

This document provides an exhaustive, multi-dimensional architectural reference for **EstateIQ-DIF v2.0 (Facility Decision Intelligence Engine)**. It covers all 10 architectural layers powering the platform—from physical IoT edge hardware to AI meta-reasoning, cloud LLMs, and closed-loop outcome verification.

---

## 📑 Table of Architectural Views

1. [System & Structural Architecture](#1-system--structural-architecture)
2. [Data & Telemetry Ingestion Architecture](#2-data--telemetry-ingestion-architecture)
3. [Machine Learning & Time-Series Forecasting Architecture](#3-machine-learning--time-series-forecasting-architecture)
4. [EstateIQ-DIF v2.0 Decision Meta-Engine Architecture](#4-estateiq-dif-v20-decision-meta-engine-architecture)
5. [Grounded GenAI & LLM Copilot Architecture](#5-grounded-genai--llm-copilot-architecture)
6. [Backend Microservices & Unified Service Layer Architecture](#6-backend-microservices--unified-service-layer-architecture)
7. [Frontend & Presentation UI Architecture](#7-frontend--presentation-ui-architecture)
8. [Security & Role-Based Access Control (RBAC) Architecture](#8-security--role-based-access-control-rbac-architecture)
9. [IoT Edge Gateway & Hardware Prototype Architecture](#9-iot-edge-gateway--hardware-prototype-architecture)
10. [Closed-Loop Action & Outcome Verification Architecture](#10-closed-loop-action--outcome-verification-architecture)

---

## 1. System & Structural Architecture

The EstateIQ platform follows a layered, micro-service ready architecture built around a **Unified Service Layer** (`src/services/`). This ensures that both the FastAPI REST microservices and the Streamlit analytical cockpit share a single source of calculation truth.

```text
 ┌───────────────────────────────────────────────────────────────────────────────────────────────────┐
 │                                   1. PHYSICAL & SIMULATED EDGE                                    │
 │   ESP32 Edge Microcontrollers (MQTT)  •  IoT Real-Time Simulator  •  365-Day Digital Twin Dataset   │
 └─────────────────────────────────────────────────┬─────────────────────────────────────────────────┘
                                                   │ (15-Minute Telemetry Streams)
                                                   ▼
 ┌───────────────────────────────────────────────────────────────────────────────────────────────────┐
 │                                2. INGESTION & DATA QUALITY LAYER                                 │
 │   Pydantic Schema Validation   •   Data Quality Score (0-100)   •   Provenance Badges [REAL/SIM]   │
 └─────────────────────────────────────────────────┬─────────────────────────────────────────────────┘
                                                   │
                                                   ▼
 ┌───────────────────────────────────────────────────────────────────────────────────────────────────┐
 │                               3. CONTEXTUAL BASELINE & FEATURE ENGINE                             │
 │   Thermal Sensitivity Models   •   Schedule Multipliers   •   COLD_START Fallback (<14 Days)      │
 └─────────────────────────────────────────────────┬─────────────────────────────────────────────────┘
                                                   │ (Expected Baseline + Dynamic Normal Bounds)
                                                   ▼
 ┌───────────────────────────────────────────────────────────────────────────────────────────────────┐
 │                               4. SPECIALIST MACHINE LEARNING ENSEMBLE                             │
 │   XGBoost Regressor  •  LightGBM  •  CatBoost  •  Prophet  •  Isolation Forest  •  SHAP Explainer  │
 └─────────────────────────────────────────────────┬─────────────────────────────────────────────────┘
                                                   │ (Predictions + SHAP Feature Drivers)
                                                   ▼
 ┌───────────────────────────────────────────────────────────────────────────────────────────────────┐
 │                             5. ESTATEIQ-DIF v2.0 DECISION META-ENGINE                             │
 │   Early Exit Filter  •  AWEHA Adaptive Ensemble  •  Multi-Signal Fusion  •  Temporal Persistence │
 │   Model Consensus    •  Independent Confidence   •  Cost of Inaction    •  Utility Ranker         │
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
 │  OpenAPI Specs (/docs)   •   JWT 4-Tier RBAC      │ │  Translucent Glassmorphic Tabs  •  ₹ Cards    │
 │  Liquid Glass Web App (web/index.html)            │ │  Folium GIS Maps  •  Plotly Interactive Charts │
 └─────────────────────────┬─────────────────────────┘ └─────────────────────────┬─────────────────────┘
                           │                                                     │
                           └───────────────────────────┬─────────────────────────┘
                                                       │
                                                       ▼
 ┌───────────────────────────────────────────────────────────────────────────────────────────────────┐
 │                                    8. GROUNDED GROQ AI COPILOT                                    │
 │   Groq Cloud LPU (llama-3.3-70b-versatile)   •   JSON Evidence Grounding   •   Offline Fallback   │
 └─────────────────────────────────────────────────┬─────────────────────────────────────────────────┘
                                                   │
                                                   ▼
 ┌───────────────────────────────────────────────────────────────────────────────────────────────────┐
 │                                   9. HUMAN-IN-THE-LOOP ACTION CENTER                              │
 │   Work Order State Machine   •   What-If Scenario Sandbox   •   Constrained HVAC Optimization     │
 └─────────────────────────────────────────────────┬─────────────────────────────────────────────────┘
                                                   │ (MQTT Control Relay Signals)
                                                   ▼
 ┌───────────────────────────────────────────────────────────────────────────────────────────────────┐
 │                              10. CLOSED-LOOP OUTCOME VERIFICATION                                 │
 │   Pre/Post Telemetry Snapshot   •   4-Tier Classification   •   Closed-Loop Model Weight Feedback │
 └───────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Data & Telemetry Ingestion Architecture

### Data Sources & Resolution
* **Temporal Resolution**: Aligned 15-minute intervals (96 intervals per 24-hour cycle; 35,040 intervals per 365-day annual cycle).
* **Domain Tables**: 19 multi-module domain datasets (Energy, Water, Waste, Air Quality, Traffic, Parking, Equipment Utilization, Safety Incidents, Carbon Emissions).
* **Annotated Ground Truth**: Historical telemetry (`facility_dataset/`) contains explicit ground-truth anomaly annotations (`anomaly_flag`, `anomaly_type`, `severity`) used strictly for off-line backtesting and precision/recall evaluation.

### Data Provenance Engine (`src/data/`)
Every metric rendered in the application carries an unforgeable **Data Provenance Badge**:
1. `[REAL SENSOR]` — Physical hardware telemetry ingested from ESP32 microcontrollers over MQTT.
2. `[SIMULATED SENSOR]` — Real-time synthesized payload mimicking live edge hardware behavior.
3. `[SYNTHETIC DATA]` — Canonical 365-day benchmark dataset generated under physics constraints.
4. `[MODEL PREDICTION]` — Inference output generated by trained ML regressors (XGBoost/Prophet).
5. `[AI INTERPRETATION]` — Executive natural-language summary generated by Groq AI grounded in JSON evidence.
6. `[VERIFIED RESULT]` — Empirically measured before-vs-after post-intervention savings.

---

## 3. Machine Learning & Time-Series Forecasting Architecture

### Chronological Data Splitting & Leakage Prevention
To prevent lookahead bias in time-series validation:
* **Train / Val / Test Split**: Strict chronological 70% Train / 15% Validation / 15% Test split.
* **Lag Feature Matrices**: 15-minute lag features (`lag_1`, `lag_4`, `lag_96`) and rolling window statistics (`rolling_mean_4`) are derived strictly from historical intervals.

### Model Hierarchy & Adapters (`src/models/forecasting.py`)
```text
Naive Baseline ──► Moving Average (24h) ──► Prophet Time-Series ──► XGBoost / LightGBM / CatBoost
```
* **Naive Baseline**: Historical mean and previous observation benchmark.
* **Moving Average (24h)**: 24-hour rolling window moving average adapter.
* **Prophet Adapter**: Captures daily and weekly seasonalities with holiday components.
* **XGBoost & LightGBM**: Gradient-boosted decision trees for structured feature matrices.
* **CatBoost**: Categorical-aware regressor modeling complex building operational modes.

### Explainable AI (XAI) Engine (`src/explainability/`)
Integrated `SHAP (SHapley Additive exPlanations)` TreeExplainer computes exact feature attributions ($\Delta\text{kWh}$) for every prediction, identifying key drivers (e.g. HVAC load +42%, Ambient Temperature +11%, Occupancy +18%).

---

## 4. EstateIQ-DIF v2.0 Decision Meta-Engine Architecture

EstateIQ-DIF (`src/intelligence/dif_engine.py`) is the core meta-reasoning algorithm that orchestrates specialist model outputs:

```text
       Raw Telemetry Event Data + Context
                       │
                       ▼
    ┌──────────────────────────────────────┐
    │ 1. Early Exit Filter (ECF)           │ ──► [Nominal Reading (<10% dev)] ──► PATH A: FAST EXIT (0.02ms)
    └──────────────────┬───────────────────┘
                       │ [Deviation >= 10%]
                       ▼
    ┌──────────────────────────────────────┐
    │ 2. Contextual Baseline & Cold Start  │ ──► Dynamic Bounds (±18%, expanded 1.8x if COLD_START)
    └──────────────────┬───────────────────┘
                       │
                       ▼
    ┌──────────────────────────────────────┐
    │ 3. AWEHA Adaptive Ensemble (EAE)     │ ──► Error-Weighted Forecast: w_i = rel_i / Σrel_i
    └──────────────────┬───────────────────┘
                       │
                       ▼
    ┌──────────────────────────────────────┐
    │ 4. Multi-Signal Fusion (EAC)         │ ──► Residual Z-Score + IF + LOF + Physics Rules (PF < 0.82)
    └──────────────────┬───────────────────┘
                       │
                       ▼
    ┌──────────────────────────────────────┐
    │ 5. Temporal Persistence Window (EPT) │ ──► Multi-interval sustained vs single transient spike
    └──────────────────┬───────────────────┘
                       │
                       ▼
    ┌──────────────────────────────────────┐
    │ 6. Model Consensus & Confidence (ECI)│ ──► Consensus voting % & Confidence Score ∈ [0, 100]%
    └──────────────────┬───────────────────┘
                       │
                       ▼
    ┌──────────────────────────────────────┐
    │ 7. Business Impact & Inaction (EBI)  │ ──► ₹ Tariff loss, CO2e, 7-Day & 30-Day Cost of Inaction
    └──────────────────┬───────────────────┘
                       │
                       ▼
    ┌──────────────────────────────────────┐
    │ 8. Next Best Action Utility Ranker   │ ──► Multi-attribute ranking + "Why / Why NOT" Rationale
    └──────────────────────────────────────┘
```

### Key Mathematical Formulations
1. **Adaptive Reliability Weighting**:
   $$\text{reliability}_i = \frac{1}{\text{RMSE}_i + 1e-4}, \quad w_i = \frac{\text{reliability}_i}{\sum_j \text{reliability}_j}$$
2. **Independent Confidence Score**:
   $$\text{Confidence} = (0.25 \cdot \text{DQ}) + (0.25 \cdot \text{Consensus}) + (0.20 \cdot \text{History}) + (0.15 \cdot \text{Completeness}) + (0.15 \cdot \text{Reliability})$$

---

## 5. Grounded GenAI & LLM Copilot Architecture

### Anti-Hallucination Evidence Grounding Pipeline (`src/ai/`)
Groq AI Cloud (`llama-3.3-70b-versatile`) acts strictly as an explanation and natural-language synthesis layer **ABOVE** the quantitative decision engine:

```text
User Question ──► AIContextBuilder ──► DIF v2.0 Engine ──► JSON Evidence Packet ──► Groq AI ──► Pydantic Validation
```

### JSON Evidence Packet Contract
```json
{
  "building_id": "Block B Hostel",
  "actual_kwh": 145.2,
  "expected_kwh": 78.0,
  "anomaly_score": 88.0,
  "confidence_pct": 87.5,
  "shap_drivers": [{"feature": "HVAC Load", "impact_percent": "+42%"}],
  "hourly_cost_inaction_inr": 638.40,
  "cost_30day_inaction_inr": 459648.00,
  "recommended_action": "Automated HVAC Thermostat Reset to 24.5°C"
}
```

### Offline Fallback Engine (`src/ai/ai_service.py`)
If `GROQ_API_KEY` is absent or network connectivity drops, the system seamlessly routes through a local, deterministic rule-based template engine (`OFFLINE AI INSIGHT ENGINE`), guaranteeing 100% demo uptime.

---

## 6. Backend Microservices & Unified Service Layer Architecture

### Service Layer Contracts (`src/services/`)
To decouple business logic from API controllers and presentation templates:
1. **`FacilityService`**: Campus overview metrics, building fingerprints, Folium GIS map generation.
2. **`EnergyService`**: Demand forecasting, contextual baselines, SHAP feature attributions, financial waste impact.
3. **`SimulationService`**: What-If scenario execution (thermostat setback, solar PV addition, tariff shifts).

### REST API Endpoints (`api/main.py`)
* `GET /health` — Service health & diagnostic status.
* `POST /api/v1/intelligence/analyze` — Executes full EstateIQ-DIF v2.0 decision pipeline.
* `POST /api/v1/energy/forecast` — Returns multi-model forecasting predictions.
* `POST /api/v1/ai/copilot` — Interrogates grounded Groq AI Copilot.

---

## 7. Frontend & Presentation UI Architecture

### Dual Presentation Layer Architecture
1. **Streamlit Analytical Dashboard (`app.py`)**:
   - Power BI-style command center for facility engineers and executives.
   - Customized CSS with translucent light/glassmorphism tabs (`st.tabs`), Indian Rupees (₹) currency formatting, and dynamic KPI cards.
   - Embedded Plotly Express time-series charts and Folium GIS campus maps.
2. **Liquid Glass Web App (`web/index.html`)**:
   - Lightweight HTML5 / Vanilla CSS / JavaScript interface with frosted glass surfaces, SVG icons, and responsive tab navigation.

---

## 8. Security & Role-Based Access Control (RBAC) Architecture

### 4-Tier Security Persona Matrix (`src/auth/security.py`)
| Role Persona | Target User | System Permissions |
| :--- | :--- | :--- |
| `FACILITY_ADMIN` | Campus Director / Chief Engineer | Full operational access, configuration, thermostat setpoint overrides, model retraining. |
| `OPERATIONS_TECH` | Maintenance Technician | View active work orders, inspect asset vibration telemetry, update work order status. |
| `SUSTAINABILITY_OFFICER` | ESG Officer | View Scope 1 & 2 carbon accounting, ESG scorecards, UN SDG compliance metrics. |
| `CAMPUS_VIEWER` | Student / Campus Public | Read-only access to public energy dashboards and GIS maps. Unrestricted tab inspection. |

* **Stateless Tokens**: Argon2id password hashing and JSON Web Tokens (JWT) with server-side claims enforcement on action endpoints.

---

## 9. IoT Edge Gateway & Hardware Prototype Architecture

### Physical Sensing Hardware (`hardware/esp32/firmware/main.ino`)
* **Microcontroller**: ESP32 running modular C++ Arduino firmware.
* **Sensing Array**:
  - Current Transformer (SCT-013) — Non-invasive current measurement (0-100A).
  - Voltage Module (ZMPT101B) — AC mains voltage monitoring.
  - Temperature & Humidity (DHT22) — Ambient environmental readings.
* **Connectivity**: Wi-Fi client publishing JSON payloads over MQTT (`estateiq/telemetry/#`) to Paho-MQTT broker subscriber (`src/data/mqtt_consumer.py`).

---

## 10. Closed-Loop Action & Outcome Verification Architecture

### Work Order State Machine (`src/decisions/work_orders.py`)
```text
NEW ──► ASSIGNED ──► APPROVED (Human-in-the-Loop) ──► COMPLETED ──► VERIFIED
```

### 4-Tier Outcome Verification Classification (`src/intelligence/outcome_verification.py`)
Post-action telemetry window (e.g., 60 minutes) is compared against pre-action baseline to classify outcomes:
1. `VERIFIED_SUCCESS`: $\text{kWh}$ reduction $\ge 10\%$, expected savings achieved ($\text{weight adjustment } +0.05$).
2. `PARTIAL_SUCCESS`: $\text{kWh}$ reduction $> 0\%$, but $< 10\%$ ($\text{weight adjustment } +0.01$).
3. `NO_IMPACT`: $\text{kWh}$ reduction within baseline noise threshold ($\text{weight adjustment } -0.02$).
4. `DEGRADATION`: Consumption increased post-intervention ($\text{weight adjustment } -0.10$).

* **Closed-Loop Feedback**: Recommendation utility weights are dynamically updated based on verified real-world outcomes.
