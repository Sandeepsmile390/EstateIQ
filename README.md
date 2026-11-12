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
| **FastAPI REST Backend** | `8000` | FastAPI, Pydantic, Uvicorn | Telemetry ingestion, polling telemetry snapshot, AI copilot, RBAC, analytics |
| **Streamlit Analytical Dashboard** | `8501` | Streamlit, Plotly, Folium | Campus operations cockpit, topological map, What-If simulator, audit logs |
| **Resource Simulator Server** | `8502` | Python HTTP, Threaded Simulator | Standalone utility controller for Electricity, Water, Air, and Waste |
| **Liquid Glass Web Client** | Browser (`:8000`) | HTML5, Vanilla JS, CSS3 | Fast-polling monitoring UI with verified hardware telemetry and Waste Bin node |

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

## 🚀 How to Start the Whole Project (Step-by-Step)

EstateIQ is designed to run end-to-end with or without physical hardware. Follow these steps to start all services:

### 1. Prerequisites & Virtual Environment
```powershell
# Windows (PowerShell)
git clone https://github.com/Sandeepsmile390/EstateIQ.git
cd EstateIQ
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```
*(On Linux/macOS: `source .venv/bin/activate`)*

---

### 2. Start the Backend API & Live Web Dashboard (Primary Application)
The primary backend is a FastAPI application that serves the core REST API, ingestion pipeline, anomaly detection engine, AI copilot, and the rich live dashboard.

```powershell
# Set environment variables for demo / hardware telemetry
$env:GATEWAY_API_KEY="gw_secret_estateiq_hw_2026"
$env:ALLOW_UNVERIFIED_DEMO_INGESTION="true"

# Launch FastAPI server on Port 8000
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```
*(On CMD: `set GATEWAY_API_KEY=gw_secret_estateiq_hw_2026 && set ALLOW_UNVERIFIED_DEMO_INGESTION=true && python -m uvicorn api.main:app --host 0.0.0.0 --port 8000`)*  
*(On Linux/macOS: `export GATEWAY_API_KEY="gw_secret_estateiq_hw_2026" && export ALLOW_UNVERIFIED_DEMO_INGESTION="true" && python -m uvicorn api.main:app --host 0.0.0.0 --port 8000`)*

#### 🌐 Accessing the Live Dashboards:
* **Live IoT Telemetry & Sensor Gateway Monitor:** [http://localhost:8000/#iot-monitor](http://localhost:8000/#iot-monitor)
* **Campus Main Decision Platform:** [http://localhost:8000](http://localhost:8000)
* **Node #2 PZEM Metrology Dashboard:** [http://localhost:8000/pzem](http://localhost:8000/pzem)
* **Interactive Swagger REST API Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)

---

### 3. (Optional) Ingesting Physical ESP32 Hardware
EstateIQ supports two independent physical ESP32 nodes:

* **Node #1: Multi-Sensor Edge Gateway (Sonar, Water Flow, DHT11, MQ-135, OLED)**
  * Firmware sketch: [`hardware/esp32/firmware/main/main.ino`](hardware/esp32/firmware/main/main.ino)
  * Upload via Arduino IDE or PlatformIO.
  * Over Wi-Fi: automatically transmits telemetry to `http://<your-pc-ip>:8000/api/v1/iot/telemetry`.
  * Over USB Serial Bridge (e.g. COM7):
    ```powershell
    python tools/esp32_serial_bridge.py --port COM7
    ```
* **Node #2: Dedicated PZEM-004T AC Metrology Gateway**
  * Firmware sketch: [`hardware/esp32/firmware_pzem/main/main.ino`](hardware/esp32/firmware_pzem/main/main.ino)
  * Features an embedded real-time web server on Port 80 and direct HTTP ingestion to the backend.

---

### 4. (Optional) Start the Multi-Page Streamlit Analytics Cockpit (Port 8501)
For executive analytics, campus topological maps, and advanced What-If scenario simulations:
```powershell
# Open a new terminal:
streamlit run app.py --server.port 8501
```
Open **[http://localhost:8501](http://localhost:8501)** in your browser.

---

### 5. (Optional) Start the Standalone Multi-Utility Resource Simulator (Port 8502)
To stress-test facility scenarios (HVAC surge, pipe bursts, bin overflows, power sags) through synthetic simulation:
```powershell
# Open a new terminal:
cd resource-simulator-app
python server.py
```
Open **[http://localhost:8502](http://localhost:8502)** in your browser.

---

### 6. Start the EstateIQ Algorithm Benchmark App (Port 8503)
Scientifically evaluate the real **EstateIQ-DIF** engine against standard statistical and time-series baselines (7-day seasonal naive, persistence, seasonal Gaussian, rolling Z-score, static P99, and ablations) for energy forecasting, anomaly detection, and computational Big-O complexity:
```powershell
# Open a new terminal:
streamlit run benchmark_app.py --server.port 8503
```
Open **[http://localhost:8503](http://localhost:8503)** in your browser. Complete scientific methodology and Big-O derivations: [`docs/ALGORITHM_BENCHMARK.md`](docs/ALGORITHM_BENCHMARK.md).

---

### 7. Demo Credentials & User Roles
| Username / Email | Password | Role | Access Level |
|---|---|---|---|
| `admin` / `admin@estateiq.in` | `password123` | `FACILITY_ADMIN` | Full campus management, live gateway approvals, system settings |
| `tech` / `tech@estateiq.in` | `password123` | `OPERATIONS_TECH` | Acknowledge & resolve alerts, work order execution |
| `sustainability` / `esg@estateiq.in` | `password123` | `ESG_AUDITOR` | ESG carbon footprint, compliance audits, CSV exports |

---

## ⚡ Physical ESP32 Hardware Edge Gateway Integration

EstateIQ integrates seamlessly with physical edge microcontrollers running verified sensor firmware:

- **Edge Microcontroller**: ESP32 / ESP32-S3 DevKit (`ESP32_EDGE_GATEWAY_01`).
- **Energy Metrology**: PZEM-004T UART metering module. Confirm the exact board revision, isolation arrangement and wiring before mains use.
- **Water Sensing**: ZJ-S201/YF-S201 turbine pulse input. Calibrate pulses per litre for the installed sensor and flow path.
- **Other Sensors**: Ultrasonic tank/bin distance, DHT11 temperature/humidity and MQ-135 raw gas response. MQ-135 is not a calibrated CO₂/AQI/PM instrument.
- **Transport**: Direct HTTP REST POST to the configured `/api/v1/iot/telemetry` endpoint; MQTT support depends on the firmware configuration.
- **Data Provenance**: A `real_sensor` claim alone is unverified. The server marks hardware verified only when the gateway credential is provisioned and validated.
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
