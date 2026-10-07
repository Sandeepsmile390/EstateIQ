# 🌱 EstateIQ — Full Technology Stack Specification

Below is the complete, comprehensive technology stack implemented in **EstateIQ**, aligned with the **Sustainable Facility and Estate Intelligence Dashboard for India** problem statement.

---

## 1. 🐍 Core Programming Language & Runtime
| Technology | Version / Requirement | Role & Purpose | Status |
| :--- | :--- | :--- | :--- |
| **Python** | `Python 3.11+` | Primary programming language across data pipelines, ML models, REST APIs, and analytical dashboards. | ✅ **CURRENTLY USED** |

---

## 2. 📊 Data Engineering & Processing
| Technology | Package | Role & Purpose | Status |
| :--- | :--- | :--- | :--- |
| **Pandas** | `pandas>=2.0.0` | 15-minute time-series telemetry aggregation, feature engineering, data cleaning, and rolling-window calculation. | ✅ **CURRENTLY USED** |
| **NumPy** | `numpy>=1.24.0` | Numerical calculations, array vectorization, residual matrix operations, and trigonometric time encoding (`hour_sin`, `hour_cos`). | ✅ **CURRENTLY USED** |
| **SciPy** | `scipy>=1.10.0` | Statistical distributions, z-score outlier detection, and signal processing. | ✅ **CURRENTLY USED** |

---

## 3. 🤖 Machine Learning & Advanced Tabular ML
| Technology | Package | Role & Purpose | Status |
| :--- | :--- | :--- | :--- |
| **Scikit-Learn** | `scikit-learn>=1.2.0` | Standard ML algorithms (Linear Regression, Logistic Regression, Random Forest, Gradient Boosting, IsolationForest, LOF). | ✅ **CURRENTLY USED** |
| **XGBoost** | `xgboost>=1.7.0` | Non-linear gradient boosted decision trees for structured energy and occupancy prediction. | ✅ **CURRENTLY USED** |
| **LightGBM** | `lightgbm>=3.3.0` | Fast, memory-efficient gradient boosting for low-latency inference on structured IoT datasets. | ✅ **CURRENTLY USED** |
| **CatBoost** | `catboost>=1.1.0` | Categorical-aware gradient boosting for facility domain classification and traffic flow modeling. | ✅ **CURRENTLY USED** |
| **Optuna** | `optuna>=3.0.0` | Automated hyperparameter optimization (Bayesian search) for XGBoost/LightGBM tuning. | ✅ **CURRENTLY USED** |
| **Joblib** | `joblib>=1.2.0` | Serialization and deserialization of fitted ML model artifacts and metadata. | ✅ **CURRENTLY USED** |

---

## 4. 📈 Time-Series Forecasting Engine
| Technology | Package | Role & Purpose | Status |
| :--- | :--- | :--- | :--- |
| **Prophet** | `prophet>=1.1.0` | Time-series forecasting baseline with automated trend and multi-seasonality (daily, weekly) decomposition. | ✅ **CURRENTLY USED** |
| **Moving Average** | Custom Adapter | 24-hour rolling window moving average baseline for short-term demand trajectory benchmarking. | ✅ **CURRENTLY USED** |
| **Naive Forecaster** | Custom Adapter | Historical mean & last-observed value baseline forecaster for chronological pipeline validation. | ✅ **CURRENTLY USED** |

---

## 5. 🔍 Explainable AI (XAI) & GenAI Decision Support
| Technology | Package | Role & Purpose | Status |
| :--- | :--- | :--- | :--- |
| **SHAP** | `shap>=0.41.0` | Game-theoretic TreeExplainer quantifying local feature attributions (+42% HVAC, +18% Occupancy). | ✅ **CURRENTLY USED** |
| **Grounded GenAI Engine** | Custom Core Engine | Converts structured JSON evidence into 7-part operational explanations without hallucinations. | ✅ **CURRENTLY USED** |
| **Offline AI Engine** | Custom Fallback | Deterministic rule-based explanation engine when LLM API keys are absent (`OFFLINE AI INSIGHT ENGINE`). | ✅ **CURRENTLY USED** |

---

## 6. 🗺️ Geospatial & GIS Intelligence
| Technology | Package | Role & Purpose | Status |
| :--- | :--- | :--- | :--- |
| **GeoPandas** | `geopandas>=0.12.0` | Geospatial DataFrames (`Point`, `Polygon`) mapping campus building coordinates and asset locations. | ✅ **CURRENTLY USED** |
| **Folium** | `folium>=0.14.0` | Interactive Leaflet-based map rendering with marker clustering and popup telemetry cards. | ✅ **CURRENTLY USED** |
| **OpenStreetMap** | Tile Layer | Free, open-source cartographic tile renderer for campus GIS maps. | ✅ **CURRENTLY USED** |
| **Shapely & PyProj** | `shapely>=2.1.0` | Spatial geometry manipulation and coordinate reference system (CRS `EPSG:4326`) conversions. | ✅ **CURRENTLY USED** |

---

## 7. 📡 IoT Telemetry & Protocol Gateways
| Technology | Package / Component | Role & Purpose | Status |
| :--- | :--- | :--- | :--- |
| **IoT Digital Twin Simulator** | `facility_dataset/generator/` | 365-day 15-minute resolution synthetic IoT telemetry generator for 19 campus domain tables. | ✅ **CURRENTLY USED** |
| **Paho-MQTT** | `paho-mqtt>=1.6.0` | Hardware sensor gateway readiness interface for ESP32/Arduino MQTT brokers (`estateiq/telemetry/#`). | ✅ **CURRENTLY USED** |

---

## 8. ⚡ Backend Microservices & API Architecture
| Technology | Package | Role & Purpose | Status |
| :--- | :--- | :--- | :--- |
| **FastAPI** | `fastapi>=0.95.0` | High-performance asynchronous RESTful API framework with automatic OpenAPI (`/docs`) generation. | ✅ **CURRENTLY USED** |
| **Uvicorn** | `uvicorn>=0.21.0` | Production-grade ASGI web server running FastAPI. | ✅ **CURRENTLY USED** |
| **Pydantic** | `pydantic>=2.0.0` | Strict data validation, request/response schema modeling, and type enforcement. | ✅ **CURRENTLY USED** |
| **Unified Service Layer** | `src/services/` | `FacilityService`, `EnergyService`, and `SimulationService` providing a single source of truth. | ✅ **CURRENTLY USED** |

---

## 9. 🎨 Presentation & Dashboard UI Layer
| Technology | Package / Component | Role & Purpose | Status |
| :--- | :--- | :--- | :--- |
| **Streamlit** | `streamlit>=1.20.0` | Primary analytical presentation layer recommended by problem statement for Power BI-style dashboards. | ✅ **CURRENTLY USED** |
| **Plotly Express** | `plotly>=5.13.0` | Interactive demand curves, 24-hour scenario curves, and multi-zone thermal area charts. | ✅ **CURRENTLY USED** |
| **Liquid Glass Web UI** | `web/index.html` + CSS | Modern web interface (HTML5, Vanilla CSS, JS) with dark mode, frosted surfaces, and glassmorphic aesthetics. | ✅ **CURRENTLY USED** |
| **FontAwesome & Lucide** | Icon Libraries | SVG and web font icons for UI components. | ✅ **CURRENTLY USED** |

---

## 10. 🔒 Security & Authorization (RBAC)
| Technology | Component | Role & Purpose | Status |
| :--- | :--- | :--- | :--- |
| **Argon2id / PyJWT** | Security Layer | Password hashing and stateless JWT token authentication. | ✅ **CURRENTLY USED** |
| **4-Tier RBAC** | `src/auth/security.py` | Server-side role permissions (`FACILITY_ADMIN`, `OPERATIONS_TECH`, `SUSTAINABILITY_OFFICER`, `CAMPUS_VIEWER`). | ✅ **CURRENTLY USED** |

---

## 11. 💾 Database & Persistence Architecture
| Technology | Package / Engine | Role & Purpose | Status |
| :--- | :--- | :--- | :--- |
| **In-Memory / SQLite** | Built-in Python DB | Default zero-dependency database backend for instant hackathon execution. | ✅ **CURRENTLY USED** |
| **MongoDB / Motor** | `pymongo`, `motor` | Document store for high-throughput IoT time-series telemetry with in-memory fallback. | 🔄 **FUTURE READY** |
| **PostgreSQL** | Relational DB | Production persistence layer target. | 🔄 **FUTURE READY** |

---

## 📌 Architecture Summary Flow

```text
               ┌─────────────────────────────────────────────────────────┐
               │                     DATA SOURCES                        │
               │   365-Day IoT Simulator  •  MQTT Sensor Gateway (paho)  │
               └────────────────────────────┬────────────────────────────┘
                                            │
                                            ▼
               ┌─────────────────────────────────────────────────────────┐
               │                  DATA ENGINEERING                       │
               │             Pandas  •  NumPy  •  SciPy                  │
               └────────────────────────────┬────────────────────────────┘
                                            │
                                            ▼
               ┌─────────────────────────────────────────────────────────┐
               │              MACHINE LEARNING & FORECASTING             │
               │   scikit-learn  •  Prophet  •  XGBoost  •  LightGBM     │
               │            CatBoost  •  Optuna  •  SHAP                 │
               └────────────────────────────┬────────────────────────────┘
                                            │
                                            ▼
               ┌─────────────────────────────────────────────────────────┐
               │                 UNIFIED SERVICE LAYER                   │
               │            Facility, Energy & Simulation Services       │
               └─────────────────────┬─────────────┬─────────────────────┘
                                     │             │
                    ┌────────────────┘             └────────────────┐
                    ▼                                               ▼
   ┌─────────────────────────────────┐             ┌─────────────────────────────────┐
   │       FASTAPI BACKEND           │             │       STREAMLIT DASHBOARD       │
   │  REST API • Uvicorn • Pydantic  │             │   Power BI-Style Analytical UI  │
   │      Liquid Glass Web App       │             │   GeoPandas / Folium GIS Maps   │
   └─────────────────────────────────┘             └─────────────────────────────────┘
```





Open / Synthetic / Sensor-style Data
                ↓
        Data Quality Layer
                ↓
        Feature Engineering
                ↓
 ┌──────────────┼───────────────┐
 ↓              ↓               ↓
Forecasting   Anomaly       ML Prediction
Models        Detection
 └──────────────┼───────────────┘
                ↓
       ESTATEIQ INTELLIGENCE
          FUSION ENGINE
                ↓
      ┌─────────┼─────────┐
      ↓         ↓         ↓
   Context   Explain   Confidence
      ↓         ↓         ↓
      └─────────┼─────────┘
                ↓
        Business / Impact
                ↓
          Prioritization
                ↓
       Plain-language AI
       Recommendations
                ↓
          What-If Simulation
                ↓
          Action Decision
                ↓
        Outcome Verification