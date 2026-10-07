# 🌱 EstateIQ — Sustainable Facility and Estate Intelligence Platform for India

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Dashboard-Streamlit-FF4B4B.svg)](https://streamlit.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**EstateIQ** is an AI-powered facility decision intelligence platform that combines specialized machine-learning models with contextual facility intelligence, confidence estimation, business-impact analysis, simulation, and outcome verification to turn facility data into measurable operational decisions.

Repository: [https://github.com/Sandeepsmile390/EstateIQ](https://github.com/Sandeepsmile390/EstateIQ)

---

## 🧠 EstateIQ-DIF — Dynamic Intelligence Fusion Algorithm

The proprietary decision-intelligence layer in EstateIQ is **EstateIQ-DIF** (Dynamic Intelligence Fusion Algorithm), which operates directly **ABOVE** specialized machine-learning models (XGBoost, LightGBM, CatBoost, Random Forest, Prophet, Isolation Forest, LOF, SHAP):

```text
                  EstateIQ-DIF
                       │
        ┌──────────────┼──────────────┐
        ↓              ↓              ↓
       ECF            EAE            EAC
   Context Filter   Adaptive       Anomaly
                    Ensemble      Consensus
        │              │              │
        └──────────────┼──────────────┘
                       ↓
                      ECI
                  Confidence
                       ↓
                      EBI
                Business Impact
                       ↓
                  Risk/Opportunity
                       ↓
                      EDI
              Decision Intelligence
                       ↓
             Recommendation Ranker
                       ↓
                   What-If
                       ↓
                  Verification
                       ↓
                  Calibration
```

- **ECF (EstateIQ Context Filter)**: Fast first-stage screening providing $O(1)$ early exit for nominal readings ($<10\%$ deviation).
- **EAE (EstateIQ Adaptive Ensemble)**: Champion (LightGBM) / Challenger (XGBoost, CatBoost, Prophet) model selection architecture.
- **EAC (EstateIQ Anomaly Consensus)**: Normalized multi-detector signal fusion across contextual residual, Isolation Forest, LOF, and domain rules ($0–100$).
- **ECI (EstateIQ Confidence Intelligence)**: Deterministic multi-source confidence calculation ($0–100\%$).
- **EBI (EstateIQ Business Impact)**: Calculates surge kWh, hourly/daily cost (₹), annual Cost of Inaction (₹/year), and $\text{CO}_2\text{e}$ emissions.
- **EDI (EstateIQ Decision Intelligence)**: Weighted decision score and priority classifier (`P1_CRITICAL`, `P2_HIGH`, `P3_MEDIUM`, `P4_LOW`).

---

## 💡 Problem Statement & Technology Alignment

**EstateIQ** is engineered in direct alignment with the **Sustainable Facility and Estate Intelligence Dashboard for India** problem statement requirements:

```text
                    ESTATEIQ ARCHITECTURE
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
      DATA                    AI/ML                 UI
        │                      │                      │
        ▼                      ▼                      ▼
    Pandas                  sklearn               Streamlit /
    NumPy                   Prophet               Power BI-style UI
    IoT Simulator           XGBoost               Folium Maps
    MQTT Gateway            LightGBM              Plotly
                            CatBoost
                            SHAP
        │                      │                      │
        └──────────────────────┼──────────────────────┘
                               ▼
                        FastAPI Services
                               │
                ┌──────────────┼──────────────┐
                ▼              ▼              ▼
          Recommendations   What-If       Business Impact
                │              │              │
                └──────────────┼──────────────┘
                               ▼
                             GenAI
                               │
                               ▼
                         Action Center
                               │
                               ▼
                          Verification
```

### Why Each Technology Was Chosen (Teacher & Examiner Justification)

- **Python 3.11+**: Primary runtime recommended by the problem statement, supported by a mature data science and ML ecosystem.
- **Pandas & NumPy**: Core data manipulation frameworks for 15-minute time-series telemetry aggregation, feature engineering, and data cleaning.
- **Scikit-learn**: Industry standard for linear regression, random forest, gradient boosting, and IsolationForest/LOF anomaly detection.
- **Prophet**: Recommended forecasting framework for modeling multi-seasonality campus time-series trends alongside moving average and gradient boosting models.
- **XGBoost, LightGBM, CatBoost**: Non-linear gradient boosted decision trees for structured facility tabular data.
- **SHAP (SHapley Additive exPlanations)**: Grounded game-theoretic explainable AI (XAI) feature attribution scores (+42% HVAC, +18% Occupancy).
- **Streamlit**: Primary data-science & analytical presentation layer directly recommended by the problem statement for Power BI-style dashboards.
- **FastAPI & Uvicorn**: High-performance RESTful API microservice backend layer with Pydantic validation, CORS enforcement, and JWT RBAC authentication.
- **Folium, GeoPandas & OpenStreetMap**: Geospatial GIS library stack for interactive campus asset maps and spatial intelligence.
- **IoT Simulator & MQTT Readiness**: 365-day 15-minute interval synthetic IoT telemetry generator (`facility_dataset/generator/`) with `paho-mqtt` hardware consumer interface.
- **Grounded GenAI Engine**: Natural language insight generation grounded strictly in structured JSON evidence, featuring an `OFFLINE AI INSIGHT ENGINE` fallback.

---

## 💡 Operational Intelligence Loop

```text
OBSERVE ──► UNDERSTAND ──► DETECT ──► PREDICT ──► EXPLAIN ──► PRIORITIZE ──► SIMULATE ──► APPROVE ──► ACT ──► VERIFY
```

1. **OBSERVE**: Real-time multi-module IoT telemetry monitoring & Data Provenance badges (`[SYNTHETIC IoT DATA]`, `[OBSERVED]`, `[ML FORECAST]`, `[SIMULATED]`).
2. **UNDERSTAND**: Contextual Baseline Engine establishing thermal & schedule expectations.
3. **DETECT**: Unsupervised AI Anomaly Detection & Contextual Baseline Deviations (+86.1% Surge).
4. **PREDICT**: Multi-horizon forecasting (Prophet, XGBoost, Moving Average) across 15m, 1h, 4h, 24h, 7d, 1m, 1y.
5. **EXPLAIN**: SHAP TreeExplainer quantifying local feature impact (+42% HVAC load, +18% Occupancy, +11% Temp).
6. **PRIORITIZE**: Facility Priority Engine calculating urgency scores and action complexity.
7. **SIMULATE**: Interactive What-If Scenario Simulator with 24-hr demand comparison curve.
8. **APPROVE & ACT**: 7-Part Action Recommendations & Single-click Rule Execution.
9. **VERIFY & MEASURE IMPACT**: 11-Step Grounded Decision Trace Audit Ledger & ₹ financial savings calculation.

---

## 🛠️ Quick Start & Execution Guide

### Step 1: Environment Setup
```bash
git clone https://github.com/Sandeepsmile390/EstateIQ.git
cd EstateIQ
pip install -r requirements.txt
```

### Step 2: Generate 365-Day Digital Twin Dataset
```bash
python -m facility_dataset.generator.main
```

### Step 3: Train & Register All ML Models
```bash
python train_all_modules.py
```

### Step 4: Launch FastAPI Backend Server
```bash
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```
Open **`http://localhost:8000/`** for the Liquid Glass Web Dashboard.

### Step 5: Launch Streamlit Data Science Dashboard
```bash
streamlit run app.py --server.port 8501
```
Open **`http://localhost:8501/`** for the Streamlit Power BI-style Dashboard.

### Step 6: Execute Automated Test Suite
```bash
python -m unittest discover tests
```

---

## 📚 Complete Documentation Suite

| Document | Description |
|---|---|
| 🧠 [**EstateIQ-DIF Specification**](docs/ESTATEIQ_DIF_ALGORITHM.md) | Authoritative 44-point algorithm architecture specification & complexity analysis |
| 📋 [**Tech Stack Alignment**](docs/TECH_STACK_ALIGNMENT.md) | Problem Statement Technology Audit Matrix & Verification Status |
| 📐 [**Architecture Guide**](docs/ARCHITECTURE.md) | Technical stack, components, unified service layer & design system |
| 🤖 [**AI Pipeline**](docs/AI_PIPELINE.md) | 11-step Decision Trace engine, SHAP & Co-Pilot NLP architecture |
| 📊 [**ML Pipeline**](docs/ML_PIPELINE.md) | Multi-model ML training, Prophet, CatBoost, Random Forest & Isolation Forest |
| 🌐 [**API Documentation**](docs/API_DOCUMENTATION.md) | FastAPI REST endpoints specification & MongoDB connector schemas |
| 📖 [**Data Dictionary**](docs/DATA_DICTIONARY.md) | Telemetry features, MongoDB schemas, and Data Provenance badges |
| 🎮 [**Demo Guide**](docs/DEMO_GUIDE.md) | Step-by-step hackathon demonstration walkthrough & scenarios |
| 📋 [**Acceptance Specification**](docs/ACCEPTANCE_SPECIFICATION.md) | Verified phase gates (0–10), 17 product requirements & scorecard |

---

## 📜 License
Licensed under the [MIT License](LICENSE).
