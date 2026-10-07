# EstateIQ — Technology Stack Alignment & Audit Matrix

## Executive Summary
This document provides a comprehensive audit of **EstateIQ** against the technology recommendations and functional expectations of the **Sustainable Facility and Estate Intelligence Dashboard for India** problem statement.

---

## Technology Stack Alignment Matrix

| Problem Statement Requirement | Current Implementation | Identified Gap | Required Change | Final Technology | Verification Strategy | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Python Ecosystem** | Python 3.11 core runtime across `api/` and `src/` | None. Python is fully integrated. | Maintain Python 3.x core architecture. | `Python 3.11+` | `python --version` & test suite | ✅ ALIGNED |
| **Data Engineering** | Pandas & NumPy in `src/data/` & `facility_dataset/` | Data pipeline needed unified service abstraction. | Standardize ingestion & feature engineering on Pandas/NumPy. | `Pandas`, `NumPy` | Automated shape & null validation tests | ✅ ALIGNED |
| **Machine Learning** | `scikit-learn` regressors, classifiers, IsolationForest | Need explicit unified model selection & baseline comparison. | Maintain `scikit-learn` algorithms for baseline and anomaly detection. | `scikit-learn` | `python -m unittest discover tests` | ✅ ALIGNED |
| **Advanced Tabular ML** | `XGBoost`, `LightGBM`, `CatBoost` in `src/models/` | Models trained independently per module. | Expose candidate comparison in Model Registry with metrics. | `XGBoost`, `LightGBM`, `CatBoost` | `train_all_modules.py` evaluation | ✅ ALIGNED |
| **Time-Series Forecasting** | ML regressors (XGBoost/LightGBM) | **Prophet** model adapter missing from forecasting candidates. | Implement `ProphetForecast` adapter alongside Naive/Moving Average/XGBoost. | `Prophet`, `scikit-learn`, `XGBoost` | Chronological backtest evaluation | 🔄 IN MIGRATION |
| **Streamlit Dashboard** | Dual Streamlit (`app.py`) & FastAPI (`api/main.py`) | Streamlit app needed full Power BI-style layout & map integration. | Enhance Streamlit app to serve as primary data science presentation layer. | `Streamlit` | `streamlit run app.py` | ✅ ALIGNED |
| **Power BI-Style UI** | Executive KPI cards, trend charts, liquid-glass CSS | Dashboard needed structured analytical flow (What, Why, Future, Impact). | Implement top KPI → trend → drilldown → anomaly → AI recommendation. | `Streamlit` + Custom CSS / Plotly | Visual audit & interactive drilldown | ✅ ALIGNED |
| **Geospatial Libraries & Maps** | Static asset location listings | Interactive map interface and geospatial data models missing. | Integrate `Folium`, `GeoPandas`, and OpenStreetMap tile renderer. | `Folium`, `GeoPandas`, `OpenStreetMap` | Map layer rendering & fallback check | 🔄 IN MIGRATION |
| **IoT Simulator & Telemetry** | 365-day 15-minute synthetic IoT generator | Explicit MQTT ingestion adapter missing for hardware readiness. | Add MQTT consumer interface (`src/data/mqtt_consumer.py`) & label simulated data. | `facility_dataset/generator`, `paho-mqtt` | Data generator & MQTT consumer tests | ✅ ALIGNED |
| **GenAI Insight Generation** | `GenAIExplanationEngine` & `AICopilotEngine` | Needed strict grounding and explicit offline fallback labeling. | Enforce JSON evidence grounding; label offline mode as `OFFLINE AI INSIGHT ENGINE`. | `GenAI Engine` + LLM API / Rule Fallback | Grounding assertion tests | ✅ ALIGNED |

---

## System Architecture

```text
                    ESTATEIQ
                       │
        ┌──────────────┼──────────────┐
        │              │              │
      DATA            AI/ML         DASHBOARD
        │              │              │
        ▼              ▼              ▼
    Pandas          sklearn       Streamlit /
    NumPy           Prophet       Power BI-style UI
    IoT             XGBoost       Folium Maps
    APIs            LightGBM
                    CatBoost
                    SHAP
        │              │              │
        └──────────────┼──────────────┘
                       ▼
                 DECISION ENGINE
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
