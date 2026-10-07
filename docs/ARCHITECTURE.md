# 🏛️ EstateIQ System Architecture

Comprehensive architecture reference for **EstateIQ — Sustainable Facility and Estate Intelligence Platform for India**.

---

## 📐 Target System Architecture

```text
                         ESTATEIQ
                            │
        ┌───────────────────┼──────────────────┐
        │                   │                  │
       DATA                AI/ML            UI
        │                   │                  │
        ▼                   ▼                  ▼
    IoT Simulator       sklearn            Streamlit
    MQTT Consumer       Prophet             Dashboard
    Pandas              XGBoost             Folium GIS
    NumPy               LightGBM            Plotly
                        CatBoost
                        SHAP
        │                   │                  │
        └───────────────────┼──────────────────┘
                            ▼
                    Unified Services
                  (`src/services/`)
                            │
        ┌───────────────────┴───────────────────┐
        ▼                                       ▼
  FastAPI REST Server                   Streamlit Dashboard
  (`api/main.py`)                       (`app.py`)
        │                                       │
        └───────────────────┬───────────────────┘
                            ▼
                     GenAI Decision
                      Trace Engine
                            │
                            ▼
                     Action Center &
                       Verification
```

---

## 🧩 Unified Service Layer (`src/services/`)

To eliminate duplicate business logic between the REST API and Streamlit presentation layers, **EstateIQ** routes all operational computations through a unified Service Layer:

1. **`FacilityService` (`src/services/facility_service.py`)**:
   - Manages campus overview metrics, building baseline expectations, and Folium GIS map generation.
2. **`EnergyService` (`src/services/energy_service.py`)**:
   - Manages energy demand forecasting, contextual thermal baselines, SHAP feature attributions, and financial surge impact calculations.
3. **`SimulationService` (`src/services/simulation_service.py`)**:
   - Executes What-If scenario simulations (HVAC setback, solar PV addition, tariff rate shifts) and returns predicted kWh, ₹ cost savings, and CO₂e carbon reduction.

```text
FastAPI Endpoints  ─────┐
                        ├───► Unified Services ───► Core AI / ML / Repositories
Streamlit Dashboard ────┘
```

---

## 🛠️ Technology Stack & Selection Justification (Teacher & Examiner Reference)

| Technology | Role | Justification / Problem Statement Alignment |
|---|---|---|
| **Python 3.11+** | Primary Language | Recommended by problem statement; standard for data science and AI. |
| **Pandas & NumPy** | Data Engineering | Time-series 15-minute interval aggregation, feature engineering, and data cleaning. |
| **Scikit-learn** | Machine Learning | Standard baseline regressors, classifiers, IsolationForest, and LOF anomaly detection. |
| **Prophet** | Forecasting Baseline | Problem-statement-recommended time-series forecasting library modeling multi-seasonality. |
| **XGBoost, LightGBM, CatBoost** | Advanced Tabular ML | Gradient boosted decision trees optimized for structured non-linear facility telemetry. |
| **SHAP** | Explainable AI (XAI) | Game-theoretic local feature attribution scores (+42% HVAC, +18% Occupancy). |
| **Streamlit** | Analytical Dashboard | Primary data-science presentation layer recommended by problem statement for Power BI-style UIs. |
| **FastAPI & Uvicorn** | Backend Microservices | High-performance REST API service layer with OpenAPI specs and JWT authorization. |
| **GeoPandas & Folium** | Geospatial GIS Maps | OpenStreetMap rendering & spatial asset coordinate mapping across campus blocks. |
| **IoT Simulator & paho-mqtt** | Hardware Telemetry | 365-day 15-min synthetic generator (`facility_dataset/generator/`) + MQTT broker consumer interface. |
| **Grounded GenAI Engine** | Decision Support | JSON-grounded 7-part explanation engine with `OFFLINE AI INSIGHT ENGINE` fallback. |

---

## 🔒 Security & Role-Based Access Control (RBAC)

- **4-Tier Security Personas**:
  - `FACILITY_ADMIN`: Full operational, configuration, and model management access.
  - `OPERATIONS_TECH`: Maintenance work orders, asset vibration telemetry, and thermostat overrides.
  - `SUSTAINABILITY_OFFICER`: ESG sustainability scorecards, Scope 1 & 2 carbon accounting, UN SDG compliance.
  - `CAMPUS_VIEWER`: Read-only access to executive KPI cards and GIS maps.
- **Server-Side Authorization**: Enforced on all action endpoints (`/api/v1/recommendations/apply`, `/api/v1/subscription/upgrade`) via JWT dependencies in `src/auth/security.py`.
