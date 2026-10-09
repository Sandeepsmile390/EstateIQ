# 🌱 EstateIQ-DIF v2.0 — Comprehensive Technology Stack Specification

This document details the complete production technology stack implemented in **EstateIQ-DIF v2.0 (Facility Decision Intelligence Engine)**, aligned with the **Sustainable Facility and Estate Intelligence Dashboard for India** specification.

---

## 1. 🐍 Core Programming Language & Runtime Environment
| Technology | Version / Requirement | Role & Purpose | Status |
| :--- | :--- | :--- | :--- |
| **Python** | `Python 3.11+` | Primary language powering ML models, decision intelligence engines, FastAPI backend, and analytical dashboards. | ✅ **ACTIVE** |

---

## 2. 🧠 EstateIQ-DIF v2.0 Intelligence Engine Layer (`src/intelligence/`)
| Module Component | File / Engine | Math & Technical Role | Status |
| :--- | :--- | :--- | :--- |
| **Adaptive Ensemble (EAE)** | `adaptive_ensemble.py` | AWEHA-inspired dynamic error-weighted forecasting ($w_i = \text{reliability}_i / \sum \text{reliability}_i$, $\text{reliability}_i = 1 / (\text{RMSE}_i + \epsilon)$). | ✅ **ACTIVE** |
| **Contextual Baseline (ECF)** | `contextual_baseline.py` | Thermal, schedule, and occupancy-aware dynamic normal bounds; features `COLD_START` fallback for history $< 14$ days. | ✅ **ACTIVE** |
| **Multi-Signal Anomaly Fusion (EAC)** | `anomaly_consensus.py` | Fuses residual z-scores, Isolation Forest, LOF, and Physics consistency rules (power factor $<0.82$, off-peak surges). | ✅ **ACTIVE** |
| **Temporal Anomaly Persistence** | `anomaly_consensus.py` | Sliding persistence window tracking to distinguish transient single-interval noise from sustained anomalies. | ✅ **ACTIVE** |
| **Model Consensus Engine** | `model_consensus.py` | Computes agreement/disagreement metrics based strictly on executed models. | ✅ **ACTIVE** |
| **Independent Confidence (ECI)** | `confidence_engine.py`, `confidence.py` | Deterministic score $\in [0, 100]$ evaluating Data Quality, Consensus, History Depth, Completeness, and Sensor Reliability. | ✅ **ACTIVE** |
| **Business Impact & Cost of Inaction (EBI)** | `business_impact.py` | Calculates INR (₹9.50/kWh) monetary loss, $\text{CO}_2\text{e}$ carbon footprint, and 7-day & 30-day Cost of Inaction projections. | ✅ **ACTIVE** |
| **Opportunity Discovery Engine** | `opportunity_engine.py` | Scans domain signals to rank proactive energy reduction and peak load shifting opportunities. | ✅ **ACTIVE** |
| **Decision Intelligence (EDI)** | `decision_engine.py` | Synthesizes multi-dimension scores into priority levels (`P1_CRITICAL` to `P4_LOW`) and operational next steps. | ✅ **ACTIVE** |
| **Recommendation Ranker** | `recommendation_ranker.py` | Multi-attribute utility function ranking candidate actions by benefit, sustainability, risk, effort, and confidence. | ✅ **ACTIVE** |
| **Why / Why Not Intelligence** | `dif_engine.py` | Generates factual evidence for recommended actions and explicit rationale for rejected alternative actions. | ✅ **ACTIVE** |
| **What-If Simulation Engine** | `src/scenarios/whatif.py` | Simulates operational parameter modifications (thermostat setback, load factor) with disclaimer provenance. | ✅ **ACTIVE** |
| **Constrained Optimization** | `optimization_engine.py` | Solves constrained optimization for HVAC setpoints within thermal comfort envelopes ($22.0^\circ\text{C} - 25.0^\circ\text{C}$). | ✅ **ACTIVE** |
| **Outcome Verification Engine** | `outcome_verification.py` | Pre/post-action window telemetry verification classifying outcomes into `VERIFIED_SUCCESS`, `PARTIAL_SUCCESS`, `NO_IMPACT`, `DEGRADATION`. | ✅ **ACTIVE** |

---

## 3. 🤖 Machine Learning & Advanced Tabular ML (`src/models/`)
| Technology | Package / Framework | Role & Purpose | Status |
| :--- | :--- | :--- | :--- |
| **Scikit-Learn** | `scikit-learn>=1.2.0` | Classical ML algorithms (Linear Regression, Random Forest, Isolation Forest, Local Outlier Factor). | ✅ **ACTIVE** |
| **XGBoost** | `xgboost>=1.7.0` | Primary gradient-boosted decision trees for structured energy and occupancy regression. | ✅ **ACTIVE** |
| **LightGBM** | `lightgbm>=3.3.0` | High-efficiency challenger forecasting model for fast tabular inference. | ✅ **ACTIVE** |
| **CatBoost** | `catboost>=1.1.0` | Categorical-aware gradient boosting for facility domain modeling and categorical features. | ✅ **ACTIVE** |
| **Optuna** | `optuna>=3.0.0` | Automated hyperparameter optimization (Bayesian search) for XGBoost/LightGBM tuning. | ✅ **ACTIVE** |
| **Joblib** | `joblib>=1.2.0` | Serialization and persistence of trained ML models and pipeline metadata. | ✅ **ACTIVE** |

---

## 4. 📈 Time-Series Forecasting & Alignment (`src/models/forecasting.py`)
| Technology | Package / Adapter | Role & Purpose | Status |
| :--- | :--- | :--- | :--- |
| **Prophet** | `prophet>=1.1.0` | Time-series forecaster capturing daily and weekly seasonality patterns. | ✅ **ACTIVE** |
| **Moving Average Adapter** | Custom Adapter | 24-hour rolling window moving average baseline for short-term trajectory benchmarking. | ✅ **ACTIVE** |
| **Naive Forecast Adapter** | Custom Adapter | Historical mean and previous-observation baseline forecaster for chronological model comparison. | ✅ **ACTIVE** |

---

## 5. 🔍 Explainable AI (XAI) & GenAI Decision Layer (`src/explainability/`, `src/recommendations/`)
| Technology | Component | Role & Purpose | Status |
| :--- | :--- | :--- | :--- |
| **SHAP (SHapley Additive exPlanations)** | `shap>=0.41.0` | TreeExplainer feature attributions quantifying local feature drivers (e.g. +42% HVAC Load). | ✅ **ACTIVE** |
| **Grounded GenAI Engine** | `src/recommendations/genai_engine.py` | Converts backend structured JSON DIF evidence into clear natural-language executive summaries. | ✅ **ACTIVE** |
| **Offline Rule-Based AI Engine** | `src/recommendations/copilot.py` | Deterministic fallback explanation generator when LLM API keys are absent. | ✅ **ACTIVE** |

---

## 6. 🗺️ Geospatial GIS & Mapping (`src/features/geospatial.py`)
| Technology | Package | Role & Purpose | Status |
| :--- | :--- | :--- | :--- |
| **GeoPandas** | `geopandas>=0.12.0` | Spatial DataFrames managing campus building geometry and sensor location coordinates. | ✅ **ACTIVE** |
| **Folium** | `folium>=0.14.0` | Interactive Leaflet GIS maps displaying telemetry heatmaps, building markers, and popup cards. | ✅ **ACTIVE** |
| **Shapely & PyProj** | `shapely>=2.1.0` | Spatial geometry manipulation and coordinate reference system (CRS `EPSG:4326`) projection. | ✅ **ACTIVE** |

---

## 7. ⚡ Backend Microservices & REST API (`api/`)
| Technology | Package | Role & Purpose | Status |
| :--- | :--- | :--- | :--- |
| **FastAPI** | `fastapi>=0.95.0` | Asynchronous RESTful API framework powering `/api/v1/intelligence/` and operational endpoints. | ✅ **ACTIVE** |
| **Uvicorn** | `uvicorn>=0.21.0` | Production ASGI web server running FastAPI. | ✅ **ACTIVE** |
| **Pydantic v2** | `pydantic>=2.0.0` | Data validation, request/response schema modeling, and type safety across all endpoints. | ✅ **ACTIVE** |
| **Unified Service Layer** | `src/services/` | Decoupled domain service layer (`FacilityService`, `EnergyService`, `SimulationService`). | ✅ **ACTIVE** |

---

## 8. 🎨 Presentation & Dashboard UI Layer (`web/`, `app.py`)
| Technology | Framework / Interface | Role & Purpose | Status |
| :--- | :--- | :--- | :--- |
| **Streamlit Dashboard** | `app.py` | Interactive analytical dashboard with translucent glassmorphic tabs, INR (₹) formatting, and KPI cards. | ✅ **ACTIVE** |
| **Liquid Glass Web App** | `web/index.html`, `web/index.css` | Modern HTML5/Vanilla CSS web app featuring frosted glassmorphism, responsive navigation, and tab views. | ✅ **ACTIVE** |
| **Plotly Express** | `plotly>=5.13.0` | High-charting interactive time-series plots, 24-hour scenario curves, and thermal heatmaps. | ✅ **ACTIVE** |

---

## 9. 🔒 Security, Authentication & Role-Based Access Control (RBAC) (`src/auth/`)
| Technology | Component | Role & Purpose | Status |
| :--- | :--- | :--- | :--- |
| **Argon2id & PyJWT** | Security Layer | Password hashing and stateless JSON Web Token authentication. | ✅ **ACTIVE** |
| **4-Tier Server-Side RBAC** | `src/auth/security.py` | Granular permission control (`FACILITY_ADMIN`, `OPERATIONS_TECH`, `SUSTAINABILITY_OFFICER`, `CAMPUS_VIEWER`). | ✅ **ACTIVE** |

---

## 10. 📡 IoT Hardware Prototype & Telemetry Gateways (`hardware/`, `src/data/`)
| Technology | Component | Role & Purpose | Status |
| :--- | :--- | :--- | :--- |
| **ESP32 Microcontroller** | `hardware/esp32/firmware/main.ino` | C++ firmware reading physical DHT22/energy sensors and publishing telemetry via Wi-Fi. | ✅ **ACTIVE** |
| **Paho-MQTT Gateway** | `src/data/mqtt_consumer.py` | Asynchronous MQTT broker subscriber (`estateiq/telemetry/#`) ingesting live hardware telemetry. | ✅ **ACTIVE** |
| **365-Day Synthetic Dataset** | `facility_dataset/` | 365-day 15-minute resolution synthetic IoT telemetry database with annotated ground-truth anomalies. | ✅ **ACTIVE** |

---

## 📌 EstateIQ-DIF v2.0 Pipeline Flow

```text
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │                                   TELEMETRY INPUTS                                     │
 │  365-Day Synthetic Dataset  •  ESP32 Hardware (MQTT)  •  Live Telemetry (15-min intervals)  │
 └───────────────────────────────────────────┬────────────────────────────────────────────┘
                                             │
                                             ▼
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │                                  1. DATA QUALITY ENGINE                                │
 │       Completeness Score  •  Freshness Score  •  Consistency Score  •  Sensor Reliability   │
 └───────────────────────────────────────────┬────────────────────────────────────────────┘
                                             │
                                             ▼
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │                                 2. CONTEXTUAL BASELINE                                 │
 │     Weather Sensitivity  •  Occupancy Schedule  •  Operating Hours  •  COLD_START Mode  │
 └───────────────────────────────────────────┬────────────────────────────────────────────┘
                                             │
                                             ▼
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │                              3. ADAPTIVE ENSEMBLE FORECAST                             │
 │    XGBoost  •  LightGBM  •  CatBoost  •  Prophet  (Error-Weighted: w_i = rel_i / Σrel)   │
 └───────────────────────────────────────────┬────────────────────────────────────────────┘
                                             │
                                             ▼
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │                             4. MULTI-SIGNAL ANOMALY FUSION                             │
 │   Residual Z-Score  •  Isolation Forest  •  LOF  •  Physics & Domain Rules  •  Persistence │
 └───────────────────────────────────────────┬────────────────────────────────────────────┘
                                             │
                                             ▼
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │                          5. MODEL CONSENSUS & CONFIDENCE ENGINE                        │
 │       Model Agreement %  •  Independent Decision Confidence Score ∈ [0, 100]%         │
 └───────────────────────────────────────────┬────────────────────────────────────────────┘
                                             │
                                             ▼
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │                           6. BUSINESS IMPACT & COST OF INACTION                        │
 │      Tariff Loss (₹9.50/kWh)  •  CO2e Footprint  •  7-Day & 30-Day Cost of Inaction    │
 └───────────────────────────────────────────┬────────────────────────────────────────────┘
                                             │
                                             ▼
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │                            7. DECISION & RECOMMENDATION RANKING                        │
 │       Utility Function Ranking  •  "Why Recommended"  •  "Why NOT Alternatives"        │
 └───────────────────────────────────────────┬────────────────────────────────────────────┘
                                             │
                                             ▼
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │                            8. OUTCOME VERIFICATION & LEARNING                          │
 │     Pre/Post Telemetry  •  4-Tier Status (VERIFIED_SUCCESS to DEGRADATION)  •  Feedback │
 └────────────────────────────────────────────────────────────────────────────────────────┘
```