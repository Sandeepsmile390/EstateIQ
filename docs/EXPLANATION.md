# 📖 EstateIQ Repository & Codebase Explanation Guide

> **Authoritative Guide to Understanding Why Every File, Module, Directory, and Script Exists in the EstateIQ Codebase.**
> 
> *This document provides a clear, step-by-step walkthrough of the entire project repository. Use this guide during code reviews, hackathon viva examinations, teacher audits, and developer onboarding.*

---

## 📑 Table of Contents

1. [High-Level Project Directory Structure](#1-high-level-project-directory-structure)
2. [Root Directory Files](#2-root-directory-files)
3. [FastAPI REST API Layer (`api/`)](#3-fastapi-rest-api-layer-api)
4. [Core Intelligence & Meta-Reasoning Engine (`src/intelligence/`)](#4-core-intelligence--meta-reasoning-engine-srcintelligence)
5. [Machine Learning & Time-Series Models (`src/models/` & `src/anomaly/`)](#5-machine-learning--time-series-models-srcmodels--srcanomaly)
6. [Explainability (XAI) Engine (`src/explainability/`)](#6-explainability-xai-engine-srcexplainability)
7. [Grounded Groq AI Copilot Layer (`src/ai/` & `src/recommendations/`)](#7-grounded-groq-ai-copilot-layer-srcai--srcrecommendations)
8. [Unified Service Layer (`src/services/`)](#8-unified-service-layer-srcservices)
9. [Data Storage & IoT Ingestion Layer (`src/data/` & `src/data_quality/`)](#9-data-storage--iot-ingestion-layer-srcdata--srcdata_quality)
10. [Action Center, Work Orders & Scenarios (`src/decisions/` & `src/scenarios/`)](#10-action-center-work-orders--scenarios-srcdecisions--srcscenarios)
11. [Security & Role-Based Access Control (`src/auth/`)](#11-security--role-based-access-control-srcauth)
12. [Presentation & Web Interfaces (`app.py` & `web/`)](#12-presentation--web-interfaces-apppy--web)
13. [Hardware & Edge Simulator (`hardware/`)](#13-hardware--edge-simulator-hardware)
14. [365-Day Digital Twin Dataset (`facility_dataset/`)](#14-365-day-digital-twin-dataset-facility_dataset)
15. [Automated Test Suite (`tests/`)](#15-automated-test-suite-tests)
16. [Documentation Suite (`docs/`)](#16-documentation-suite-docs)

---

## 1. High-Level Project Directory Structure

```text
EstateIQ/
├── api/                           # FastAPI REST API controllers & server entrypoints
├── src/                           # Primary application source code
│   ├── intelligence/              # EstateIQ-DIF v2.0 Decision Meta-Reasoning Engine
│   ├── models/                    # Unified ML forecasting adapters & model selector
│   ├── anomaly/                   # Isolation Forest & LOF anomaly detectors
│   ├── explainability/            # SHAP TreeExplainer local feature attribution
│   ├── ai/                        # Grounded Groq AI cloud copilot & fallback engine
│   ├── services/                  # Unified Service Layer (Facility, Energy, Simulation)
│   ├── data/                      # Data repository, MQTT consumers, DB connectors
│   ├── data_quality/              # Data Quality Engine & scoring metrics
│   ├── decisions/                 # Action Center, Work Orders & Decision Trace
│   ├── scenarios/                 # What-If scenario simulation sandbox
│   ├── auth/                      # Argon2id/JWT security & 4-tier RBAC
│   ├── features/                  # Feature engineering & Folium GIS mapping
│   ├── priority/                  # Priority classification scoring engine
│   └── recommendations/           # Action recommendation generators
├── web/                           # Liquid Glass HTML5/Vanilla CSS web application
├── facility_dataset/              # 365-day 15-min digital twin telemetry & dataset generator
├── hardware/                      # ESP32 C++ firmware & IoT edge Python simulator
├── tests/                         # 76-test unit test suite & DIF benchmark script
├── docs/                          # Comprehensive technical documentation & ablation study
├── app.py                         # Streamlit Analytical Command Center Dashboard
├── train_all_modules.py           # Script to train & register all 9 specialist ML models
├── TECHSTACK.md                   # Technology stack specification & pipeline flow
├── ARCHITECTURE.md                # Multi-view architecture documentation
├── presentation.md                # 3-minute hackathon presentation script & judge Q&A
└── README.md                      # Primary project overview & quick start guide
```

---

## 2. Root Directory Files

* **`app.py`**: The main entrypoint for the Streamlit Analytical Dashboard. Provides Power BI-style command center tabs, interactive Plotly charts, Folium campus GIS maps, real-time KPI metrics (in Indian Rupees ₹), What-If sandbox sliders, and the Groq AI Copilot interface.
* **`train_all_modules.py`**: Automated script that trains, evaluates, and serializes all 9 specialist ML models (Energy, Water, Waste, Air Quality, Traffic, Parking, Equipment Risk, Safety, Emissions) using chronological splits and saves fitted artifacts to `models/`.
* **`README.md`**: Primary repository landing page featuring setup instructions, architecture summary, test badge, quick start steps, and documentation links.
* **`TECHSTACK.md`**: Complete technology stack specification outlining every library, package version, role, and status across Python, FastAPI, ML, Streamlit, and security.
* **`ARCHITECTURE.md`**: Exhaustive 10-layer architectural reference detailing system topology, data flows, meta-reasoning formulations, and security matrices.
* **`presentation.md`**: Official hackathon presentation blueprint containing a 3-minute live presentation script, judge viva Q&A answers, and benchmark proof.
* **`requirements.txt`**: List of all Python dependencies (`fastapi`, `streamlit`, `xgboost`, `lightgbm`, `catboost`, `prophet`, `shap`, `scikit-learn`, `groq`, `geopandas`, `folium`).
* **`.env.example` & `.env`**: Environment configuration file for API keys (`GROQ_API_KEY`), database ports, and application mode (`production` vs `demo`).

---

## 3. FastAPI REST API Layer (`api/`)

* **`api/main.py`**: The FastAPI server entrypoint (`uvicorn api.main:app`). Exposes production-ready RESTful endpoints:
  - `GET /health` — Diagnostics & service availability check.
  - `POST /api/v1/intelligence/analyze` — Executes full EstateIQ-DIF v2.0 decision pipeline.
  - `POST /api/v1/energy/forecast` — Multi-model forecasting endpoint.
  - `POST /api/v1/ai/copilot` — Interrogates grounded Groq AI Copilot.
  - `GET /docs` — Automatically generated Swagger OpenAPI interactive documentation.

---

## 4. Core Intelligence & Meta-Reasoning Engine (`src/intelligence/`)

This directory houses **EstateIQ-DIF v2.0**, the core decision-intelligence meta-algorithm that orchestrates specialist ML models:

* **`dif_engine.py`**: Master orchestrator (`EstateIQDIF`). Connects data quality checks, contextual baselines, adaptive ensembles, anomaly consensus, confidence scoring, cost of inaction, utility ranking, and selective SHAP execution into a single unified analysis loop.
* **`adaptive_ensemble.py`**: Implements AWEHA-inspired out-of-sample error-weighted forecasting ($w_i = \text{reliability}_i / \sum \text{reliability}_i$). Dynamically calculates weights for XGBoost, LightGBM, CatBoost, and Prophet based on validation RMSE.
* **`contextual_baseline.py`**: Computes physics- and schedule-aware expected baseline values based on thermal sensitivity, occupancy, and operating hours. Features **`COLD_START` Fallback Mode** for facilities with $<14$ days of history.
* **`anomaly_consensus.py`**: Fuses residual z-scores, Isolation Forest scores, LOF outlier scores, and Physics consistency rules ($\text{PF} < 0.82$, off-peak surges). Implements a **Temporal Persistence Window** to distinguish transient noise from sustained anomalies.
* **`model_consensus.py`**: Computes voting agreement and disagreement metrics across executed models.
* **`confidence_engine.py` & `confidence.py`**: Computes a deterministic decision confidence score $\in [0, 100]\%$ separate from physical anomaly severity. Evaluates Data Quality, Model Consensus, History Depth, Feature Completeness, and Sensor Reliability.
* **`business_impact.py`**: Translates raw excess kWh into monetary loss (₹9.50/kWh baseline grid tariff), carbon footprint ($\text{kg CO}_2\text{e}$), and explicit **7-day & 30-day Cost of Inaction** projections.
* **`opportunity_engine.py`**: Scans domain signals to discover proactive energy reduction, peak load shifting, and thermostat setback opportunities.
* **`decision_engine.py`**: Synthesizes scores into priority levels (`P1_CRITICAL` to `P4_LOW`) and operational next steps.
* **`recommendation_ranker.py`**: Multi-attribute utility function ranking candidate recommendations by benefit, sustainability, risk, effort, and confidence.
* **`complexity_monitor.py`**: Monitors DIF pipeline complexity, tracking inference latency, Fast Path early exit percentage, and SHAP execution frequency.
* **`outcome_verification.py`**: Pre/post-action window telemetry verification engine classifying outcomes into `VERIFIED_SUCCESS`, `PARTIAL_SUCCESS`, `NO_IMPACT`, or `DEGRADATION` with closed-loop weight updates.
* **`safety_gate.py`**: AI safety gate evaluating whether recommendations meet confidence thresholds before physical execution.
* **`scoring.py`**: Multi-dimension scoring engine computing normalized priority, anomaly, and risk scores.
* **`types.py`**: Strongly typed Python dataclasses (`EventData`, `QualityResult`, `ContextualResult`, `PredictionResult`, `AnomalyResult`, `ConfidenceResult`, `ImpactResult`, `RecommendationCandidate`, `DecisionResult`).
* **`config.py`**: Configuration dataclass (`DIFConfig`) defining weights, thresholds, and tariff parameters.

---

## 5. Machine Learning & Time-Series Models (`src/models/` & `src/anomaly/`)

* **`src/models/forecasting.py`**: Unified forecasting adapters (`NaiveForecastAdapter`, `MovingAverageForecastAdapter`, `ProphetForecastAdapter`, `XGBoostForecastAdapter`, `LightGBMForecastAdapter`) and `UnifiedForecastingEngine` evaluating candidate models using chronological splits.
* **`src/models/selector.py`**: Model selection logic comparing candidate regressors and selecting the model minimizing validation RMSE.
* **`src/anomaly/detector.py`**: Unsupervised anomaly detection engine (`AnomalyDetectorEngine`) implementing Isolation Forest and Local Outlier Factor (LOF) algorithms.

---

## 6. Explainability (XAI) Engine (`src/explainability/`)

* **`shap_engine.py` & `explainer.py`**: Wraps SHAP (`SHapley Additive exPlanations`) TreeExplainer to compute exact feature attributions ($\Delta\text{kWh}$) for model predictions. Explains *WHY* an anomaly occurred (e.g. HVAC Load +42%, Ambient Temperature +11%, Occupancy +18%).

---

## 7. Grounded Groq AI Copilot Layer (`src/ai/` & `src/recommendations/`)

* **`src/ai/groq_client.py`**: Low-level client interface communicating with Groq Cloud LPU infrastructure (`llama-3.3-70b-versatile`).
* **`src/ai/ai_service.py`**: Higher-level AI service wrapper that orchestrates grounded prompt generation and fallback template execution.
* **`src/ai/context_builder.py`**: Converts raw backend telemetry and DIF decision objects into a constrained, grounded JSON Evidence Packet.
* **`src/ai/prompts.py`**: System prompts enforcing strict evidence compliance (forbids Groq from hallucinating numbers or unverified actions).
* **`src/ai/safety.py` & `usage_tracker.py`**: Token counter, PII masking, rate limiting, and safety boundary enforcer.
* **`src/recommendations/copilot.py` & `genai_engine.py`**: Grounded operational recommendation generators and deterministic template fallbacks.

---

## 8. Unified Service Layer (`src/services/`)

To prevent code duplication between REST APIs and Streamlit UI:
* **`facility_service.py`**: Domain service managing building overview metrics, building fingerprints, and Folium GIS maps.
* **`energy_service.py`**: Domain service managing energy demand forecasting, contextual baselines, SHAP feature attributions, and financial waste calculations.
* **`simulation_service.py`**: Domain service executing What-If scenario simulations (thermostat setback, solar PV addition, tariff shifts).

---

## 9. Data Storage & IoT Ingestion Layer (`src/data/` & `src/data_quality/`)

* **`src/data/repository.py`**: Data Repository interface serving clean telemetry DataFrames to services and API endpoints.
* **`src/data/mqtt_consumer.py`**: Asynchronous Paho-MQTT subscriber listening to `estateiq/telemetry/#` for live ESP32 edge sensor data.
* **`src/data/generator.py`**: Multi-module synthetic data generator producing datasets for energy, water, waste, air quality, traffic, parking, equipment, safety, and emissions.
* **`src/data/mongo_db.py`**: MongoDB document store connector with automatic fallback to in-memory/SQLite storage.
* **`src/data_quality/quality_score.py`**: Evaluates data quality metrics (Completeness, Freshness, Consistency, Sensor Reliability) and assigns a Data Quality Score (0–100).

---

## 10. Action Center, Work Orders & Scenarios (`src/decisions/` & `src/scenarios/`)

* **`src/decisions/action_center.py`**: Manages the life cycle of operational recommendations and interventions.
* **`src/decisions/work_orders.py`**: Work order state machine managing state transitions (`NEW` $\rightarrow$ `ASSIGNED` $\rightarrow$ `APPROVED` $\rightarrow$ `COMPLETED` $\rightarrow$ `VERIFIED`).
* **`src/decisions/trace.py`**: 11-Step Decision Trace engine recording complete step-by-step diagnostic audit trails.
* **`src/scenarios/whatif.py`**: What-If scenario simulator (`WhatIfScenarioEngine`) computing predicted changes in kWh, cost savings (₹), and CO₂e reduction under modified inputs.

---

## 11. Security & Role-Based Access Control (`src/auth/`)

* **`src/auth/security.py`**: Security module implementing Argon2id password hashing, stateless JWT session tokens, and 4-tier Role-Based Access Control (`FACILITY_ADMIN`, `OPERATIONS_TECH`, `SUSTAINABILITY_OFFICER`, `CAMPUS_VIEWER`). Protected routes enforce permissions server-side.

---

## 12. Presentation & Web Interfaces (`app.py` & `web/`)

* **`app.py`**: Streamlit analytical command center dashboard featuring translucent glassmorphic tabs, Indian Rupees (₹) formatting, Folium GIS map, Plotly charts, and Groq AI interface.
* **`web/index.html`**: HTML5 web page for the Liquid Glass web interface.
* **`web/css/index.css` & `design-system.css`**: CSS stylesheet implementing Canva-inspired frosted glass aesthetics, dark mode themes, and responsive UI containers.
* **`web/js/app.js` & `charts.js`**: JavaScript client managing tab switching, API fetch requests, and Plotly chart re-rendering.

---

## 13. Hardware & Edge Simulator (`hardware/`)

* **`hardware/esp32/firmware/main.ino`**: C++ Arduino firmware for ESP32 edge microcontroller reading SCT-013 CT sensors, ZMPT101B voltage sensors, and DHT22 temperature sensors, publishing JSON over Wi-Fi/MQTT.
* **`hardware/esp32/scripts/iot_simulator.py`**: Python script simulating multi-building edge hardware telemetry streams for testing edge ingestion pipelines without physical hardware attached.

---

## 14. 365-Day Digital Twin Dataset (`facility_dataset/`)

* **`facility_dataset/facility.db`**: SQLite database containing 365 days of 15-minute aligned telemetry (35,040 rows/building) across campus blocks.
* **`facility_dataset/generator/`**: Modular dataset generator scripts (`energy_generator.py`, `water_generator.py`, `anomaly_generator.py`, `main.py`) used to build annotated benchmark datasets with ground-truth anomaly annotations.

---

## 15. Automated Test Suite (`tests/`)

* **`test_ai_integration.py`**: Tests Groq AI integration, context builder, and fallback response contracts.
* **`test_ai_copilot_universal.py`**: Universal test suite verifying AI Copilot responses across all domain scenarios.
* **`test_api.py`**: Tests FastAPI REST endpoints (/health, /api/v1/intelligence/analyze, forecast, scenarios).
* **`test_anomaly.py`**: Tests Isolation Forest and LOF anomaly detector functionality.
* **`test_forecasting.py`**: Tests unified forecasting adapters and chronological validation splitting.
* **`test_ml.py`**: Tests machine learning model training and feature engineering.
* **`test_pipeline.py`**: End-to-end test suite verifying the complete DIF pipeline flow.
* **`test_simulation.py`**: Tests What-If scenario simulations.
* **`test_work_orders_and_notifications.py`**: Tests action center work order state machine transitions.
* **`benchmark_dif.py`**: Automated performance and complexity benchmark measuring inference latency, Fast Path exit efficiency, and selective SHAP frequency.

---

## 16. Documentation Suite (`docs/`)

* **`docs/ABLATION_STUDY.md`**: Empirical ablation benchmark comparing Baseline Single-Model ML vs EstateIQ-DIF v2.0 on 365-day telemetry.
* **`docs/ACCEPTANCE_SPECIFICATION.md`**: Master acceptance scorecard and product-quality checklist (76/76 unit tests passing).
* **`docs/ARCHITECTURE.md`**: Exhaustive 10-layer architectural reference.
* **`docs/AI_INTEGRATION.md`**: Groq AI Cloud integration, Evidence Packet JSON schemas, and safety guidelines.
* **`docs/ML_PIPELINE.md`**: Detailed ML architecture, model comparison benchmarks, and chronological validation rules.
* **`docs/API_DOCUMENTATION.md`**: Complete FastAPI REST endpoint reference and JSON contracts.
* **`docs/DATA_DICTIONARY.md`**: Telemetry features, database schemas, and data provenance badges.
* **`docs/DEMO_GUIDE.md`**: Step-by-step hackathon live storytelling demo walkthrough script.
* **`docs/SECURITY.md` & `RBAC.md`**: Role-based access control policies, security personas, and secret management guidelines.
