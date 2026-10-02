# 🌱 EstateIQ — Sustainable Facility and Estate Intelligence Platform for India

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Dashboard-Streamlit-FF4B4B.svg)](https://streamlit.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**EstateIQ** is an explainable, AI-powered decision-support platform designed for institutional and government facilities across India (Engineering Colleges, Universities, Hospitals, Corporate Tech Parks, Municipal Zones, Industrial Estates, and PSUs).

Repository: [https://github.com/Sandeepsmile390/EstateIQ](https://github.com/Sandeepsmile390/EstateIQ)

---

## 💡 Problem & Core Vision

Managing large institutional facilities in India involves complex, interrelated challenges across **electricity consumption, water usage, waste management, air quality, traffic flow, parking, asset utilization, emissions, and climate resilience**.

Traditional Building Management Systems (BMS) act as passive monitors—they show *what* happened, but fail to explain *why* or *what action administrators should take next*.

**EstateIQ** solves this by establishing a complete operational intelligence loop:

```text
DATA ──► MONITOR ──► ANALYZE ──► DETECT ──► PREDICT ──► EXPLAIN ──► RECOMMEND ──► SIMULATE ──► DECIDE
```

1. **WHAT IS HAPPENING?** ── Real-time multi-module IoT telemetry monitoring & Data Provenance badges (`[SYNTHETIC IoT DATA]`, `[OBSERVED]`, `[ML FORECAST]`, `[SIMULATED]`).
2. **WHAT IS ABNORMAL?** ── Unsupervised AI Anomaly Detection & Contextual Baseline Deviations (+86.1% Surge).
3. **WHAT WILL HAPPEN NEXT?** ── Multi-horizon forecasting (15m, 1h, 4h, 24h, 7d, 1m, 1y).
4. **WHY IS IT HAPPENING?** ── SHAP TreeExplainer quantifying local feature impact (+42% HVAC load, +18% Occupancy, +11% Temp).
5. **WHAT SHOULD WE DO?** ── Grounded 7-Part Action Recommendations & Single-click Rule Execution.
6. **WHAT HAPPENS IF WE TAKE ACTION?** ── Interactive 4-Slider What-If Scenario Simulator with 24-hr demand comparison curve.
7. **WHAT EVIDENCE SUPPORTS THIS?** ── 11-Step Grounded Decision Trace Audit Ledger.

---

## 📐 System Architecture

```text
                    ┌─────────────────────────┐
                    │      DATA SOURCES       │
                    │ Smart Meters / Sensors  │
                    │ Synthetic IoT Simulator  │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │   DATA REPOSITORY       │
                    │ (DataRepository & DB)   │
                    └────────────┬────────────┘
                                 │
             ┌───────────────────┼───────────────────┐
             ▼                   ▼                   ▼
       FORECASTING         ANOMALY ENGINE       ML MODELS
             │                   │                   │
             └───────────────────┼───────────────────┘
                                 ▼
                    ┌─────────────────────────┐
                    │   SHAP EXPLAINABILITY   │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │ 11-STEP DECISION TRACE  │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │ RECOMMENDATION ENGINE   │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │   WHAT-IF SIMULATOR     │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │ FASTAPI & LIQUID GLASS  │
                    └─────────────────────────┘
```

---

## 🔬 Core Differentiators & Features

1. **11-Step Decision Trace Audit Ledger (`/api/v1/decisions/{id}`)**:
   - Provides an unalterable audit trail for every operational recommendation:
     1. Observed Sensor Data
     2. Contextual Baseline
     3. Operational Deviation (+86.1%)
     4. ML Model Forecast (1h, 24h)
     5. Anomaly Detection Score
     6. SHAP Feature Attribution (+42% HVAC)
     7. Priority Score & Action Complexity
     8. Grounded AI Action Recommendation
     9. System Assumptions & Disclaimers
     10. What-If Simulated Intervention Impact
     11. Recorded Simulated Execution

2. **Data Provenance System**:
   - Explicitly tags every displayed metric as `[OBSERVED]`, `[PREDICTED]`, `[SIMULATED]`, or `[SYNTHETIC IoT DATA]` to prevent misleading administrators.

3. **Data Quality & Sensor Health Center (`/api/v1/data-quality`)**:
   - Monitors sensor health (238 online, 5 degraded, 2 offline), missing value imputation rates, and data completeness percentages.

4. **Multi-Horizon Time Controls**:
   - Interactive time horizon buttons (**`15 Min` \| `1 Hour` \| `24 Hours` \| `7 Days` \| `1 Month` \| `1 Year`**) across Energy, Water, Waste, Mobility, Air Quality, and Equipment health.

5. **Role-Based Access Control (RBAC)**:
   - 4-Tier Security: **RS Administrator**, **Alex Chen (Operations Engineer)**, **Dr. Priya Sharma (ESG Auditor)**, **Sam Taylor (Campus Stakeholder)**.

---

## 🛠️ Quick Start & Complete Execution Guide (Start-to-Finish)

Follow this complete step-by-step pipeline to set up the environment, generate synthetic campus telemetry, train all ML models, and launch the EstateIQ application.

### Step 1: Environment Setup & Dependencies
```bash
# Clone repository & enter project directory
git clone https://github.com/Sandeepsmile390/EstateIQ.git
cd EstateIQ

# Install required Python dependencies
pip install -r requirements.txt
```

### Step 2: Generate 365-Day Digital Twin Dataset
Generate synthetic IoT campus telemetry (weather, occupancy, energy, water, waste, air quality, traffic, parking, equipment, safety, emissions, and ground-truth anomaly injections):
```bash
python -m facility_dataset.generator.main
```

### Step 3: Train & Register All 9 ML Pipeline Modules
Train and register all 9 multi-model ML pipelines (CatBoost, Random Forest, Isolation Forest, XGBoost, LinearRegression):
```bash
python train_all_modules.py
```

### Step 4: Launch Main Web Application (FastAPI + Liquid Glass UI)
Launch the primary REST API service and production web interface:
```bash
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```
Open **`http://localhost:8000/`** in your browser to access the complete EstateIQ Liquid Glass Dashboard.

### Step 5: (Optional) Run Streamlit Analytics Dashboard
Launch the secondary Streamlit operational dashboard:
```bash
streamlit run app.py --server.port 8501
```
Open **`http://localhost:8501/`** in your browser.

### Step 6: Execute Automated Test Suite
Run the full test suite (34/34 passing tests covering models, API endpoints, decision trace, and MongoDB database connector):
```bash
python -m unittest discover tests
```

---

## 📚 Complete Documentation Suite

All detailed system specs and guides are organized under the [`docs/`](docs/) directory:

| Document | Description |
|---|---|
| 📐 [**Architecture Guide**](docs/ARCHITECTURE.md) | Technical stack, components, state management & design system |
| 🤖 [**AI Pipeline**](docs/AI_PIPELINE.md) | 11-step Decision Trace engine, SHAP & Co-Pilot NLP architecture |
| 📊 [**ML Pipeline**](docs/ML_PIPELINE.md) | Multi-model ML training, CatBoost, Random Forest & Isolation Forest |
| 🌐 [**API Documentation**](docs/API_DOCUMENTATION.md) | FastAPI REST endpoints specification & MongoDB connector schemas |
| 📖 [**Data Dictionary**](docs/DATA_DICTIONARY.md) | Telemetry features, MongoDB schemas, and Data Provenance badges |
| 🎮 [**Demo Guide**](docs/DEMO_GUIDE.md) | Step-by-step hackathon demonstration walkthrough & scenarios |
| 📋 [**Acceptance Specification**](ACCEPTANCE_SPECIFICATION.md) | Verified phase gates (0–10), 17 product requirements & scorecard |
| 📑 [**Final Implementation Report**](docs/FINAL_IMPLEMENTATION_REPORT.md) | Executive summary, technical audit, and verification metrics |
| ⚠️ [**Known Limitations**](docs/KNOWN_LIMITATIONS.md) | Simulated IoT telemetry, model estimate bounds, and disclaimers |

---

## 📜 License
Licensed under the [MIT License](LICENSE).
