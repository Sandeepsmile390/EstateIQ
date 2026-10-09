# 🌱 EstateIQ-DIF v2.0 — Sustainable Facility & Estate Intelligence Platform for India

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![Tests Passing](https://img.shields.io/badge/Tests-76%2F76%20Passing-success.svg)](tests/)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Dashboard-Streamlit-FF4B4B.svg)](https://streamlit.io/)
[![Groq AI](https://img.shields.io/badge/AI-Groq%20LPU-orange.svg)](https://groq.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**EstateIQ-DIF v2.0** is an AI-powered facility decision intelligence engine that combines AWEHA-inspired adaptive ensemble forecasting with contextual baselines, multi-signal anomaly fusion, confidence estimation, cost-of-inaction analysis, what-if simulation, and closed-loop outcome verification to turn raw facility IoT data into verified operational decisions.

Repository: [https://github.com/Sandeepsmile390/EstateIQ](https://github.com/Sandeepsmile390/EstateIQ)

---

## 🧠 EstateIQ-DIF v2.0 & Grounded Groq AI Architecture

The closed-loop decision-intelligence pipeline operates as follows:

```text
PHYSICAL / SIMULATED TELEMETRY ──► FASTAPI INGESTION ──► DATA REPOSITORY
                                                               │
                                                               ▼
SPECIALIST ML ENGINES (XGBoost / LightGBM / CatBoost / Prophet / SHAP)
                                                               │
                                                               ▼
                    ESTATEIQ-DIF v2.0 DECISION ENGINE
  • Adaptive Ensemble (AWEHA Error-Weighted)  • Contextual Baseline (COLD_START)
  • Multi-Signal Anomaly Fusion (IF+LOF+Rules) • Temporal Persistence Window
  • Model Consensus Engine                    • Independent Confidence (0-100%)
  • Cost of Inaction (7-Day / 30-Day)         • Utility Recommendation Ranker
  • What-If Simulation                        • 4-Tier Outcome Verification
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

- **ECF (EstateIQ Context Filter)**: Fast first-stage screening providing $O(1)$ early exit (**0.02 ms**) for nominal readings ($<10\%$ deviation).
- **EAE (EstateIQ Adaptive Ensemble)**: Dynamic out-of-sample error-weighted model selection ($w_i = \text{reliability}_i / \sum \text{reliability}_i$, where $\text{reliability}_i = 1 / (\text{RMSE}_i + \epsilon)$).
- **EAC (EstateIQ Anomaly Consensus)**: Normalized multi-detector signal fusion across contextual residual, Isolation Forest, LOF, physics consistency rules ($\text{PF} < 0.82$, off-peak surges), and temporal persistence window tracking.
- **ECI (EstateIQ Confidence Intelligence)**: Independent multi-factor confidence calculation ($0–100\%$) evaluated separately from physical anomaly severity.
- **EBI (EstateIQ Business Impact)**: Calculates surge kWh, hourly/daily cost (₹9.50/kWh baseline tariff), 7-day & 30-day Cost of Inaction (₹), and $\text{CO}_2\text{e}$ carbon footprint.
- **EDI (EstateIQ Decision Intelligence)**: Multi-attribute utility ranking (`P1_CRITICAL` to `P4_LOW`), complete with grounded "Why Recommended" and "Why NOT Alternatives" evidence.
- **Outcome Verification**: Pre/post-action window telemetry verification classifying outcomes into `VERIFIED_SUCCESS`, `PARTIAL_SUCCESS`, `NO_IMPACT`, or `DEGRADATION` with closed-loop model feedback.
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
Open **`http://localhost:8501/`** for the Streamlit Power BI-style Dashboard.

### Step 7: Execute Automated Test Suite
```bash
python -m unittest discover tests
```

---

## 📚 Complete Documentation Suite

| Document | Description |
|---|---|
| 📋 [**Tech Stack Specification**](TECHSTACK.md) | Comprehensive production technology stack & pipeline architecture |
| 📊 [**Ablation Study**](docs/ABLATION_STUDY.md) | Empirical backtesting & ablation benchmark evaluating DIF v2.0 |
| 📐 [**Architecture Guide**](docs/ARCHITECTURE.md) | Technical stack, components, unified service layer & design system |
| 🤖 [**AI Integration Guide**](docs/AI_INTEGRATION.md) | Groq AI Cloud integration, Evidence Packet schemas & diagnostics |
| 📊 [**ML Pipeline**](docs/ML_PIPELINE.md) | Multi-model ML training, Prophet, CatBoost, Random Forest & Isolation Forest |
| 🌐 [**API Documentation**](docs/API_DOCUMENTATION.md) | FastAPI REST endpoints specification & AI Copilot contracts |
| 📖 [**Data Dictionary**](docs/DATA_DICTIONARY.md) | Telemetry features, MongoDB schemas, and Data Provenance badges |
| 🎮 [**Demo Guide**](docs/DEMO_GUIDE.md) | Step-by-step hackathon demonstration walkthrough & scenarios |
| 📋 [**Acceptance Specification**](docs/ACCEPTANCE_SPECIFICATION.md) | Verified phase gates (0–10), product requirements & scorecard |
| 🎤 [**Presentation Blueprint**](presentation.md) | Official 3-minute hackathon presentation script & Q&A guide |

---

## 📜 License
Licensed under the [MIT License](LICENSE).
