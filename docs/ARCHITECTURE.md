# 🏛️ EstateIQ System Architecture

Comprehensive architecture reference for **EstateIQ — Sustainable Facility and Estate Intelligence Platform**.

---

## 📐 Target System Architecture

```text
                    ┌─────────────────────────┐
                    │      DATA SOURCES       │
                    │ Smart Meters / Sensors  │
                    │ Occupancy / Weather     │
                    │ HVAC / Water / Waste    │
                    │ Traffic / Parking       │
                    │ Equipment / Safety      │
                    │ Synthetic IoT Simulator  │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │     INGESTION LAYER     │
                    │ REST / CSV / MQTT-ready  │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │   DATA QUALITY LAYER    │
                    │ Range validation        │
                    │ Missing value impute    │
                    │ Sensor health audit     │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │    DATA REPOSITORY      │
                    │ SQLite (PostgreSQL-ready)│
                    │ Data Provenance Badges  │
                    └────────────┬────────────┘
                                 │
             ┌───────────────────┼───────────────────┐
             ▼                   ▼                   ▼
       FORECASTING         ANOMALY ENGINE       ML MODELS
       (1h, 4h, 24h, 7d)   (Isolation Forest)   (CatBoost/XGB)
             │                   │                   │
             └───────────────────┼───────────────────┘
                                 ▼
                    ┌─────────────────────────┐
                    │   SHAP EXPLAINABILITY   │
                    │   (Tree/Kernel SHAP)    │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │ 11-STEP DECISION TRACE  │
                    │ Audit Ledger (TRC_01)   │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │ RECOMMENDATION ENGINE   │
                    │ Rules + Grounded GenAI  │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │   WHAT-IF SIMULATOR     │
                    │ 4-Slider Model Engine   │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │   FASTAPI & SECURITY    │
                    │ OAuth2 / JWT / RBAC     │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │      ESTATEIQ UI        │
                    │ Liquid Glass Dashboard  │
                    └─────────────────────────┘
```

---

## 🧩 Architectural Layers & Modules

1. **Ingestion & Data Quality Layer (`src/data/quality.py` & `src/data/repository.py`)**:
   - Ingests SQLite `facility.db` (16 normalized tables, 180 days at 15-min resolution) and CSV feeds.
   - Evaluates data completeness (Energy 98.2%, Occupancy 94.1%, Weather 99.8%) and flags out-of-range sensor values.
   - Attaches Data Provenance badges (`[SYNTHETIC IoT DATA]`, `[OBSERVED]`, `[ML FORECAST]`, `[SIMULATED]`, `[DERIVED]`).

2. **Contextual Baseline & Anomaly Engine (`src/anomaly/detector.py`)**:
   - Calculates expected contextual energy baselines:
     $$\text{Expected Energy} = f(\text{building}, \text{hour}, \text{occupancy}, \text{temperature}, \text{HVAC})$$
   - Computes percentage deviation ($\text{Deviation \%}$) and Isolation Forest anomaly scores ($0.05$ to $0.99$).

3. **Machine Learning & Model Registry (`src/models/` & `models/`)**:
   - Automated 21-step model selector (`src/models/selector.py`) benchmarking Baselines, Linear Models, Random Forest, Gradient Boosting, XGBoost, and CatBoost.
   - Serialized joblib artifacts in `models/` versioned with metadata.

4. **SHAP Explainability & Decision Trace (`src/explainability/explainer.py` & `src/decisions/trace.py`)**:
   - Quantifies positive/negative feature attributions via SHAP.
   - Assembles the **11-Step Decision Trace Audit Ledger** linking observed telemetry to baseline deviation, ML prediction, anomaly score, SHAP attribution, priority rank, grounded recommendation, system assumptions, What-If simulation impact, and simulated action execution.

5. **Security & RBAC Layer (`src/auth/security.py`)**:
   - Enforces 4-tier Role-Based Access Control (**RS Administrator**, **Alex Chen - Operations Engineer**, **Dr. Priya Sharma - ESG Auditor**, **Sam Taylor - Viewer**).
   - Protects action endpoints (`/api/v1/recommendations/apply`, `/api/v1/subscription/upgrade`).

6. **Service & Presentation Layer (`api/main.py` & `web/`)**:
   - `api/main.py`: FastAPI backend REST API serving JSON endpoints and static assets.
   - `web/index.html`, `web/js/app.js`, `web/js/charts.js`, `web/css/styles.css`: Liquid Glass design system.
   - `app.py`: Streamlit operational dashboard.
