# 🌱 EstateIQ — Sustainable Facility and Estate Intelligence Platform for India

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Dashboard-Streamlit-FF4B4B.svg)](https://streamlit.io/)
[![Groq AI](https://img.shields.io/badge/AI-Groq%20LPU-orange.svg)](https://groq.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**EstateIQ** is an AI-powered facility decision intelligence platform that combines specialized machine-learning models with contextual facility intelligence, confidence estimation, business-impact analysis, simulation, and outcome verification to turn facility data into measurable operational decisions.

Repository: [https://github.com/Sandeepsmile390/EstateIQ](https://github.com/Sandeepsmile390/EstateIQ)

---

## 🧠 EstateIQ-DIF & Grounded Groq AI Architecture

The decision-intelligence pipeline operates in a closed loop:

```text
PHYSICAL / SIMULATED TELEMETRY ──► FASTAPI INGESTION ──► DATA REPOSITORY
                                                              │
                                                              ▼
SPECIALIST ML ENGINES (XGBoost / Prophet / Isolation Forest / SHAP)
                                                              │
                                                              ▼
                        ESTATEIQ-DIF DECISION ENGINE
                                                              │
                                                              ▼
                   AI CONTEXT BUILDER (Evidence Packet JSON)
                                                              │
                                                              ▼
                         GROQ AI COPILOT (Llama-3.3-70b)
                                                              │
                                                              ▼
                     PYDANTIC VALIDATED AI RESPONSE
```

- **ECF (EstateIQ Context Filter)**: Fast first-stage screening providing $O(1)$ early exit for nominal readings ($<10\%$ deviation).
- **EAE (EstateIQ Adaptive Ensemble)**: Champion (XGBoost) / Challenger (LightGBM, CatBoost, Prophet) model selection architecture.
- **EAC (EstateIQ Anomaly Consensus)**: Normalized multi-detector signal fusion across contextual residual, Isolation Forest, LOF, and domain rules ($0–100$).
- **ECI (EstateIQ Confidence Intelligence)**: Deterministic multi-source confidence calculation ($0–100\%$).
- **EBI (EstateIQ Business Impact)**: Calculates surge kWh, hourly/daily cost (₹), annual Cost of Inaction (₹/year), and $\text{CO}_2\text{e}$ emissions.
- **EDI (EstateIQ Decision Intelligence)**: Weighted decision score and priority classifier (`P1_CRITICAL`, `P2_HIGH`, `P3_MEDIUM`, `P4_LOW`).
- **Grounded Groq AI Copilot**: Server-side LPU execution (`llama-3.3-70b-versatile`) answering queries using verified DIF evidence packets without hallucinating metrics.

---

## 🛠️ Quick Start & Execution Guide

### Step 1: Environment Setup
```bash
git clone https://github.com/Sandeepsmile390/EstateIQ.git
cd EstateIQ
pip install -r requirements.txt
cp .env.example .env
```

Set your Groq API key in `.env`:
```env
ESTATEIQ_MODE=production
GROQ_ENABLED=true
GROQ_API_KEY=gsk_your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
```

### Step 2: Run AI Health & Diagnostic Audit
```bash
python scripts/check_ai.py
```

### Step 3: Generate 365-Day Digital Twin Dataset
```bash
python -m facility_dataset.generator.main
```

### Step 4: Train & Register All ML Models
```bash
python train_all_modules.py
```

### Step 5: Launch FastAPI Backend Server
```bash
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```
Open **`http://localhost:8000/`** for the Liquid Glass Web Dashboard.

### Step 6: Launch Streamlit Command Center Dashboard
```bash
streamlit run app.py --server.port 8501
```
Open **`http://localhost:8501/`** for the Streamlit Power BI-style Dashboard (includes **AI Facility Assistant** and **AI REST API & Diagnostics** tabs).

### Step 7: Execute Automated Test Suite
```bash
python -m unittest discover -s tests
```

---

## 📚 Complete Documentation Suite

| Document | Description |
|---|---|
| 📋 [**Tech Stack Alignment**](docs/TECH_STACK_ALIGNMENT.md) | Problem Statement Technology Audit Matrix & Verification Status |
| 📐 [**Architecture Guide**](docs/ARCHITECTURE.md) | Technical stack, components, unified service layer & design system |
| 🤖 [**AI Integration Guide**](docs/AI_INTEGRATION.md) | Groq AI Cloud integration, Evidence Packet schemas & diagnostics |
| 📊 [**ML Pipeline**](docs/ML_PIPELINE.md) | Multi-model ML training, Prophet, CatBoost, Random Forest & Isolation Forest |
| 🌐 [**API Documentation**](docs/API_DOCUMENTATION.md) | FastAPI REST endpoints specification & AI Copilot contracts |
| 📖 [**Data Dictionary**](docs/DATA_DICTIONARY.md) | Telemetry features, MongoDB schemas, and Data Provenance badges |
| 🎮 [**Demo Guide**](docs/DEMO_GUIDE.md) | Step-by-step hackathon demonstration walkthrough & scenarios |
| 📋 [**Acceptance Specification**](ACCEPTANCE_SPECIFICATION.md) | Verified phase gates (0–10), product requirements & scorecard |

---

## 📜 License
Licensed under the [MIT License](LICENSE).
