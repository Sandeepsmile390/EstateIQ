# 🌱 EstateIQ-DIF v2.0 — Sustainable Facility & Estate Intelligence Platform for India

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![Tests Passing](https://img.shields.io/badge/Tests-143%2F143%20Passing-success.svg)](tests/)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Dashboard-Streamlit-FF4B4B.svg)](https://streamlit.io/)
[![Offline Local Demo](https://img.shields.io/badge/Offline%20Demo-Zero%20Dependency-green.svg)](docs/DEMO_GUIDE.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**EstateIQ-DIF v2.0** is an AI-powered facility decision intelligence engine that combines AWEHA-inspired adaptive ensemble forecasting with contextual baselines, multi-signal anomaly fusion, confidence estimation, cost-of-inaction analysis, what-if simulation, and closed-loop outcome verification to turn raw facility IoT data into verified operational decisions.

Fully compliant with **`EstateIQ_Final_Round_Implementation_Report.pdf` (Version 1.0, Problem Statement PS-04)**.

Repository: [https://github.com/Sandeepsmile390/EstateIQ](https://github.com/Sandeepsmile390/EstateIQ)

---

## 🚀 Core Local Demo Journey (Offline, Zero-Cloud, Zero-Hardware)

The core offline demo works end-to-end locally with synthetic/simulated demo data:
```text
Load or generate data ➔ inspect data quality ➔ view facility trends ➔ detect an evidence-backed alert ➔ forecast or simulate a change ➔ record an action ➔ export a scoped report
```

### Seed & Reset Commands
- **Seed Repeatable Demo Data**:
  ```bash
  python scripts/seed_demo_data.py
  ```
  Generates 14 days of hourly campus telemetry across 14 zones for Energy, Water, Air Quality, and Waste with 4 injected anomalies (Energy spike in `BLOCK_B` at 145.2 kWh, overnight water leak in `BLOCK_B` at 380 L/hr, waste overflow at `CANTEEN` at 94%, PM2.5 surge in `BLOCK_A` at 142.5 µg/m³).
- **Reset Environment to Clean Baseline**:
  ```bash
  python scripts/reset_demo.py
  ```

---

## 🛠️ Quick Start & Execution Guide

### Step 1: Environment Setup
```bash
git clone https://github.com/Sandeepsmile390/EstateIQ.git
cd EstateIQ
pip install -r requirements.txt
cp .env.example .env
```

### Step 2: Seed Deterministic Campus Dataset
```bash
python scripts/seed_demo_data.py
```

### Step 3: Launch FastAPI Backend Server
```bash
# Terminal 1: API
uvicorn api.main:app --host 127.0.0.1 --port 8000
# or on Windows:
run_api.bat
# or on Linux/macOS:
./run_api.sh
```
Check health: `curl http://127.0.0.1:8000/health` (responds with `{"status":"HEALTHY","version":"2.0.0","database":"CONNECTED"}`)
Open **`http://127.0.0.1:8000/docs`** for interactive Swagger documentation.

### Step 4: Launch Streamlit Command Center Dashboard
```bash
# Terminal 2: Dashboard
streamlit run app.py --server.port 8501
# or:
streamlit run app/dashboard/Home.py --server.port 8501
# or on Windows:
run_dashboard.bat
# or on Linux/macOS:
./run_dashboard.sh
```
Open **`http://localhost:8501/`** for the Streamlit Multipage Command Center.

### Step 5: Demo Credentials & Role Access
| Username | Password | Role | Permitted Actions |
|---|---|---|---|
| `admin` / `admin@estateiq.in` | `password123` | `administrator` | Full campus config, demo seed/reset, thresholds, user roles, batch rollback |
| `tech` / `tech@estateiq.in` | `password123` | `operations` | Acknowledge/assign alerts, update action status, record completion notes |
| `sustainability` / `esg@estateiq.in` | `password123` | `sustainability` | What-if scenarios, sustainability metrics, scoped CSV and printable reports |

### Step 6: Execute Automated Test Suite (143/143 Passing)
```bash
# Run Acceptance Test Suite (T-01 through T-15)
python -m pytest tests/test_final_round_acceptance.py -v

# Run Full Regression Suite
python -m pytest tests/
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
| 🧠 [**Elite Algorithm Base Report (PDF)**](output/pdf/estateiq_elite_algorithm_base_report.pdf) | Professional report covering algorithm inventory, implementation, formulas, complexity, reported metrics, and accuracy limitations; [Markdown source](reports/elite_algorithm_base_report.md) |
| 🎤 [**Presentation Blueprint**](presentation.md) | Official 3-minute hackathon presentation script & Q&A guide |

---

## 📜 License
Licensed under the [MIT License](LICENSE).
