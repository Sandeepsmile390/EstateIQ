# 🏛️ Facility Intelligence AI Architecture

System architecture document for **Sustainable Facility and Estate Intelligence Dashboard for India**.

---

## 📐 End-to-End Intelligence Pipeline

```text
               ┌──────────────────────────┐
               │ Synthetic / IoT Data     │
               └────────────┬─────────────┘
                            │
                            ▼
               ┌──────────────────────────┐
               │ Data Engineering Layer   │ (DataRepository & facility.db)
               └────────────┬─────────────┘
                            │
                            ▼
               ┌──────────────────────────┐
               │ Feature Engineering      │ (Lags & Rolling Windows)
               └────────────┬─────────────┘
                            │
            ┌───────────────┼────────────────┐
            ▼               ▼                ▼
     Forecasting        Anomaly          Prediction
     Models             Detection        Models
            │               │                │
            └───────────────┼────────────────┘
                            │
                            ▼
                   ┌────────────────┐
                   │ SHAP / XAI     │
                   └───────┬────────┘
                           │
                           ▼
                  ┌──────────────────┐
                  │ Decision Engine  │ (Priority Engine & Alerts)
                  └────────┬─────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │ Recommendation      │ (Deterministic Rules & GenAI 7-Part)
                │ Engine              │
                └──────────┬──────────┘
                           │
            ┌──────────────┼──────────────┐
            ▼                             ▼
     What-if Simulation                GenAI / Rule Fallback
            │                             │
            └──────────────┬──────────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │ FastAPI         │ (/api/v1/ REST Endpoints)
                  └────────┬────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │ Streamlit       │ (app.py 18-Page Dashboard)
                  │ Dashboard       │
                  └─────────────────┘
```

---

## 🧩 Architectural Layers

1. **IoT Data Stream & Database Layer**:
   - `facility_dataset/facility.db`: SQLite database storing 16 normalized tables covering 180 days of 15-minute sensor feeds.
   - `src/data/repository.py`: Centralized `DataRepository` wrapping SQL queries and CSV fallbacks.

2. **ML Modeling & Selection Layer**:
   - `src/models/selector.py`: Automated 21-step model selection framework evaluating Baselines, Linear Models, Random Forest, Gradient Boosting, XGBoost, LightGBM, and CatBoost.
   - `models/`: Joblib serialized winning models and versioned metadata.

3. **Explainability & Anomaly Layer**:
   - `src/anomaly/detector.py`: Isolation Forest and Local Outlier Factor anomaly scoring.
   - `src/explainability/explainer.py`: Local feature attributions via Tree/Kernel SHAP.

4. **Recommendation & Priority Layer**:
   - `src/priority/engine.py`: Platform Operational Priority (Priority 1/2/3) combining severity, probability, impact, and urgency.
   - `src/recommendations/genai_engine.py`: Structured 7-part operational action plans.

5. **Simulation & What-If Layer**:
   - `src/scenarios/whatif.py`: Modelled operational parameter adjustments for HVAC schedules, water consumption, and renewable energy generation.

6. **Service & Presentation Layer**:
   - `api/main.py`: FastAPI server exposing `/api/v1/` endpoints.
   - `app.py`: Streamlit web dashboard providing 18 modules, interactive Folium maps, live IoT streaming simulation, and hackathon demo mode.
