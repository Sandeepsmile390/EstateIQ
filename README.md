# 🌱 EstateIQ-DIF v2.0 — Sustainable Facility & Estate Intelligence Platform for India

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![Acceptance Tests Passing](https://img.shields.io/badge/Acceptance%20Tests-143%2F143%20Passing-success.svg)](tests/test_final_round_acceptance.py)
[![Hardware Integration Tests](https://img.shields.io/badge/Hardware%20Tests-12%2F12%20Passing-success.svg)](tests/test_hardware_integration.py)
[![Resource Simulator Tests](https://img.shields.io/badge/Simulator%20Tests-8%2F8%20Passing-success.svg)](tests/test_resource_simulator.py)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Dashboard-Streamlit-FF4B4B.svg)](https://streamlit.io/)
[![Offline Local Demo](https://img.shields.io/badge/Offline%20Demo-Zero%20Dependency-green.svg)](docs/DEMO_GUIDE.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**EstateIQ-DIF v2.0** is an AI-powered facility decision intelligence engine that combines AWEHA-inspired adaptive ensemble forecasting with contextual baselines, multi-signal anomaly fusion, confidence estimation, cost-of-inaction analysis, what-if simulation, and closed-loop outcome verification to turn raw facility IoT data into verified operational decisions.

Fully compliant with **`EstateIQ_Final_Round_Implementation_Report.pdf` (Version 1.0, Problem Statement PS-04)**.

Repository: [https://github.com/Sandeepsmile390/EstateIQ](https://github.com/Sandeepsmile390/EstateIQ)

---

## 🏛️ System Overview & Architecture Stack

EstateIQ provides a complete multi-tier facility decision platform supporting four independent service ports:

| Service Component | Port | Technology | Primary Function |
|---|---|---|---|
| **FastAPI REST Backend** | `8000` | FastAPI, Pydantic, Uvicorn | Telemetry ingestion, SSE real-time stream, AI copilot, RBAC, analytics |
| **Streamlit Analytical Dashboard** | `8501` | Streamlit, Plotly, Folium | Campus operations cockpit, GIS map, What-If simulator, audit logs |
| **IoT Multi-Device Simulator** | `8502` | Streamlit, Physics Engine | 12 virtual device profiles, 14 anomaly scenarios, LAN auto-pairing |
| **Multi-Utility Resource Simulator** | `8503` | FastAPI, HTML5/Chart.js | Isolated controller for Electricity, Water, Air Quality, and Waste |
| **Liquid Glass Web Client** | Browser | HTML5, Vanilla JS, CSS3 | Real-time monitoring UI with SSE stream and verified hardware telemetry |

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

### Step 3: Launch FastAPI Backend Server (Port 8000)
```bash
# Terminal 1: API
uvicorn api.main:app --host 127.0.0.1 --port 8000
# or on Windows:
run_api.bat
# or on Linux/macOS:
./run_api.sh
```
- Health Check: `curl http://127.0.0.1:8000/health` (responds with `{"status":"HEALTHY","version":"2.0.0","database":"CONNECTED"}`)
- Interactive Swagger OpenAPI Docs: **`http://127.0.0.1:8000/docs`**
- Real-Time SSE Telemetry Stream: **`http://127.0.0.1:8000/api/v1/iot/telemetry/stream`**

### Step 4: Launch Streamlit Command Center Dashboard (Port 8501)
```bash
# Terminal 2: Dashboard
streamlit run app.py --server.port 8501
# or on Windows:
run_dashboard.bat
# or on Linux/macOS:
./run_dashboard.sh
```
Open **`http://localhost:8501/`** for the Streamlit Multipage Command Center.

### Step 5: (Optional) Launch IoT Multi-Device Simulator (Port 8502)
```bash
# Terminal 3: Multi-Device Simulator
cd iot-simulator-app
python run.py
# or on Windows:
run_iot_simulator.bat
```
Open **`http://localhost:8502`** for the 12-device physics simulator.

### Step 6: (Optional) Launch Multi-Utility Resource Simulator (Port 8503)
```bash
# Terminal 4: Multi-Utility Resource Simulator
cd resource-simulator-app
python run.py
# or on Windows:
run_resource_simulator.bat
```
Open **`http://localhost:8503`** for the dedicated Electricity, Water, Air Quality, and Waste controller.

### Step 7: Demo Credentials & Role Access
| Username | Password | Role | Permitted Actions |
|---|---|---|---|
| `admin` / `admin@estateiq.in` | `password123` | `administrator` | Full campus config, demo seed/reset, thresholds, user roles, batch rollback |
| `tech` / `tech@estateiq.in` | `password123` | `operations` | Acknowledge/assign alerts, update action status, record completion notes |
| `sustainability` / `esg@estateiq.in` | `password123` | `sustainability` | What-if scenarios, sustainability metrics, scoped CSV and printable reports |

---

## ⚡ Physical ESP32 Hardware Edge Gateway Integration

EstateIQ integrates seamlessly with physical edge microcontrollers running verified sensor firmware:

- **Edge Microcontroller**: ESP32 / ESP32-S3 DevKit (`ESP32_EDGE_GATEWAY_01`).
- **Energy Metrology**: Eastron SDM630 Modbus RTU via Mornsun TD301D485H galvanically isolated RS-485 transceiver (2500 VDC barrier).
- **Water Sensing**: YF-S201 turbine pulse counter with 10k/20k level divider.
- **Transports Supported**: Direct HTTP REST POST (`/api/v1/iot/telemetry`) and authenticated MQTT.
- **Data Provenance**: Physical readings are marked `[REAL SENSOR]` (`source_type: "hardware"`, `is_verified_hardware: true`).
- **Firmware Guide**: See [hardware/esp32/README.md](hardware/esp32/README.md) and [docs/HARDWARE_PROTOTYPE.md](docs/HARDWARE_PROTOTYPE.md).

---

## 🧪 Automated Testing Suite

EstateIQ includes comprehensive automated unit, integration, and regression test suites:

```bash
# 1. Run Final Round Acceptance Test Suite (143/143 Passing)
python -m pytest tests/test_final_round_acceptance.py -v

# 2. Run Physical Hardware Gateway Integration Tests (12/12 Passing)
python -m pytest tests/test_hardware_integration.py -v

# 3. Run Standalone Resource Simulator Tests (8/8 Passing)
python -m pytest tests/test_resource_simulator.py -v

# 4. Run Canonical Telemetry & Provenance Tests
python -m pytest tests/test_canonical_telemetry.py -v

# 5. Run Elite-DIF Evaluator and Paper Benchmarks
python elite-algorithm-package/run_evaluation.py
```

---

## 📚 Complete Documentation Suite

| Document | Description |
|---|---|
| 📖 [**Master Documentation Index**](docs/README.md) | Central categorized knowledge base across all modules, guides, and standards |
| 📋 [**Tech Stack Specification**](TECHSTACK.md) | Comprehensive production technology stack, packages, and engine architecture |
| 📐 [**System Architecture Guide**](docs/ARCHITECTURE.md) | Full 10-layer architectural view: edge, ingestion, ML, DIF, copilot, and UI |
| 🌐 [**API Documentation**](docs/API_DOCUMENTATION.md) | FastAPI REST endpoints specification, SSE stream, schemas, and auth contracts |
| ⚡ [**Hardware Prototype Specification**](docs/HARDWARE_PROTOTYPE.md) | Verified ESP32 edge gateway, Modbus metrology, isolated wiring, and BOM |
| 🔌 [**ESP32 Firmware & Hardware Guide**](hardware/esp32/README.md) | Complete step-by-step ESP32 wiring, Arduino setup, dual HTTP/MQTT transport |
| 🎛️ [**Standalone Resource Simulator**](docs/RESOURCE_SIMULATOR.md) | Dedicated 4-utility simulator architecture, physics formulas, and Port 8503 API |
| 🎮 [**IoT Simulator Architecture**](docs/IOT_SIMULATOR_ARCHITECTURE.md) | 12-device virtual campus telemetry generator and Port 8502 LAN architecture |
| 📡 [**IoT Ingestion & Edge Architecture**](docs/IOT_ARCHITECTURE.md) | Edge-to-cloud data flow, dual transport, buffer queues, and endpoint routes |
| 📜 [**IoT Telemetry Protocol**](docs/IOT_PROTOCOL.md) | Standardized JSON telemetry envelopes for physical and simulated sensors |
| 📊 [**Ablation Study**](docs/ABLATION_STUDY.md) | Empirical backtesting and ablation benchmark evaluating DIF v2.0 |
| 🤖 [**AI Integration Guide**](docs/AI_INTEGRATION.md) | Groq AI Cloud LPU integration, Evidence Packet schemas, and diagnostics |
| 📈 [**ML Pipeline**](docs/ML_PIPELINE.md) | Multi-model training, Prophet, CatBoost, Random Forest, and Isolation Forest |
| 📖 [**Data Dictionary**](docs/DATA_DICTIONARY.md) | Telemetry features, database schemas, and data provenance badging standards |
| 🎮 [**Demo Guide**](docs/DEMO_GUIDE.md) | Step-by-step hackathon demonstration walkthrough and scripted timeline |
| 📋 [**Acceptance Specification**](docs/ACCEPTANCE_SPECIFICATION.md) | Verified phase gates (0–10), product requirements, and scorecard |
| ⚠️ [**Known Limitations & Governance**](docs/KNOWN_LIMITATIONS.md) | Operational boundaries, read-only decision support, and ethical guardrails |
| 📝 [**Academic Research Suite**](research/README.md) | 7-page generic IEEE conference research paper, LaTeX math, and PDF build guide |
| 📄 [**IEEE Research Paper Overview**](docs/IEEE_RESEARCH_PAPER.md) | Code-grounded method, formulas, complexity, and publication instructions |
| 🎤 [**Presentation Blueprint**](docs/presentation.md) | Official 3-minute hackathon presentation script, slide alignments, and Q&A |

---

## ⚠️ Scientific Integrity & Provenance Disclosures

1. **Synthetic & Simulated Telemetry**:
   - Telemetry signals generated by the built-in simulators or seed scripts are **SYNTHETIC** or **SIMULATED**.
   - These records model statistical patterns and physical behaviors of an Indian engineering campus for repeatable evaluation. They are **not official utility bills, certified environmental measurements, or government filings**.
   - All charts, tables, API responses, and reports explicitly display provenance badges (`[REAL SENSOR]`, `[SYNTHETIC IoT]`, `[SIMULATED DATA]`).

2. **Advisory Decision Support (Human-in-the-Loop)**:
   - EstateIQ is strictly an **advisory decision-support system**.
   - It **does not** automatically actuate or manipulate physical HVAC equipment, water pumps, electrical breakers, valves, or municipal waste dispatchers.
   - All recommendations require explicit human review, authorization, and operational assignment by a qualified facility engineer or administrator.

3. **Academic Evaluation Scope**:
   - The bundled research evaluation reports point-wise anomaly metrics evaluated across 426 test intervals containing two generated anomaly episodes. It demonstrates algorithmic behavior and runtime complexity but does not establish general performance on uncalibrated real-world buildings.

---

## 📜 License
Licensed under the [MIT License](LICENSE).
