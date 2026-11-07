# 📚 EstateIQ Documentation Index & Knowledge Base

Welcome to the **EstateIQ Sustainable Facility & Estate Intelligence Platform** documentation suite. This directory contains architectural specifications, engineering guides, API references, data dictionaries, hardware schemas, and compliance reports.

---

## 🧭 Master Documentation Directory

```
docs/
├── README.md                           # Master Documentation Index (This Document)
│
├── 🏛️ Architecture & System Design
│   ├── ARCHITECTURE.md                 # System architecture, micro-services, and design patterns (Root)
│   ├── TECH_STACK_ALIGNMENT.md         # Framework alignment across FastAPI, Streamlit, and ML engines
│   ├── IOT_ARCHITECTURE.md             # Edge IoT topology, data paths, and broker integration
│   └── RBAC.md                         # Role-Based Access Control matrix and permissions
│
├── 🤖 Artificial Intelligence & Machine Learning
│   ├── AI_INTEGRATION.md               # Groq AI Cloud, Llama-3.3-70B, Evidence Packets & diagnostics
│   ├── AI_PIPELINE.md                  # Co-Pilot query parsing, reasoning DAG, and fallback heuristics
│   ├── ML_PIPELINE.md                  # Forecasting engines (Prophet, CatBoost, Random Forest)
│   └── ABLATION_STUDY.md               # Empirical backtesting, component ablations & benchmark metrics
│
├── 🔌 Hardware, Sensors & Device Registry
│   ├── HARDWARE_PROTOTYPE.md           # ESP32 edge gateway, Modbus metrology, and PCB specifications
│   ├── IOT_DEVICE_REGISTRY.md          # Device registration, pairing codes, and health lifecycles
│   ├── IOT_PROTOCOL.md                 # Telemetry envelope schemas (v1.0) and canonical metrics
│   ├── IOT_LAN_SETUP.md                # Multi-laptop local Wi-Fi pairing and network routing
│   └── FINALIST_HARDWARE_SOFTWARE_REVIEW.md # Review of metrology, safety, and demo procedures
│
├── 🎮 Simulators & Virtual Testbeds
│   ├── RESOURCE_SIMULATOR.md           # Multi-utility simulator (Electricity, Water, Air, Waste) on port 8503
│   └── IOT_SIMULATOR_ARCHITECTURE.md   # Interactive 12-device simulator on port 8502
│
├── 📖 APIs & Data Dictionary
│   ├── API_DOCUMENTATION.md            # Comprehensive FastAPI REST endpoint specifications
│   └── DATA_DICTIONARY.md              # Feature definitions, units, bounds, and provenance badges
│
├── 🛡️ Security, Governance & Verification
│   ├── SECURITY.md                     # Platform security posture, secret hygiene, and input sanitization
│   ├── SECURITY_IMPLEMENTATION_REPORT.md # Security audit findings, token scoping, and auth gates
│   ├── KNOWN_LIMITATIONS.md            # Operational boundaries, assumptions, and ethical guardrails
│   └── ACCEPTANCE_SPECIFICATION.md     # Finalist phase gates (0–10) and acceptance criteria
│
└── 📝 Research & Hackathon Presentation
    ├── IEEE_RESEARCH_PAPER.md          # 7-page IEEE-style research draft and ReportLab build pipeline
    ├── presentation.md                 # Official 3-minute hackathon presentation script & Q&A
    ├── DEMO_GUIDE.md                   # Step-by-step hackathon demonstration walkthrough
    └── EXPLANATION.md                  # Comprehensive architectural deep-dive
```

---

## ⚡ Quick Links by Role

### 👨‍💻 For Backend & Full-Stack Developers
- [API Documentation](API_DOCUMENTATION.md): Complete REST endpoint references for `/api/v1/*`.
- [Data Dictionary](DATA_DICTIONARY.md): Canonical telemetry metrics, units, ranges, and validation schemas.
- [AI Integration Guide](AI_INTEGRATION.md): Configuring Groq AI Cloud, API keys, and fallback logic.

### 🔌 For Hardware & IoT Engineers
- [ESP32 Firmware & Hardware Guide](../hardware/esp32/README.md): Circuit schematics, Eastron SDM630 Modbus pinouts, YF-S201 turbine dividers, and Arduino setup.
- [Hardware Prototype Specification](HARDWARE_PROTOTYPE.md): PCB safety, 150 Ω current loop shunt mandate, and low-voltage isolation.
- [IoT Device Registry Guide](IOT_DEVICE_REGISTRY.md): Device lifecycles (ONLINE/STALE/OFFLINE), pairing codes, and heartbeat monitoring.

### 🎮 For Presenters & Demonstrators
- [Demo Guide](DEMO_GUIDE.md): Scripted hackathon demonstration flow with repeatable anomaly scenarios.
- [Resource Simulator Guide](RESOURCE_SIMULATOR.md): Running the dedicated multi-utility web controller on port 8503.
- [Presentation Blueprint](presentation.md): 3-minute pitch transcript, slide cues, and judge Q&A preparation.

### 🔬 For Researchers & Reviewers
- [IEEE Research Paper Overview](IEEE_RESEARCH_PAPER.md): Summary of the EstateIQ-DIF research draft, PDF build tools, and experimental results.
- [Ablation Study](ABLATION_STUDY.md): Systematic component ablation isolating seasonal baselines, domain rules, and persistence tracking.
- [Known Limitations & Governance](KNOWN_LIMITATIONS.md): Simulation disclosures, human-in-the-loop decisions, and non-automation mandates.

---

## 📊 Provenance Badging Standard

EstateIQ strictly enforces end-to-end data provenance tracking. Every chart, table, card, and API response displays an explicit provenance badge:

| Badge | Provenance Type | Meaning / Verification Condition |
| :--- | :--- | :--- |
| `[REAL SENSOR]` | Physical Hardware | Ingested from registered physical gateway (`ESP32_EDGE_GATEWAY_01`) authenticated with valid API key. |
| `[SIMULATED IoT]` | Virtual Simulator | Emitted by local IoT simulators (`resource-simulator-app` or `iot-simulator-app`). |
| `[UNVERIFIED SENSOR - DEMO MODE]` | Unauthenticated | Self-declared physical sensor payload without valid gateway credential in dev mode. |
| `[CSV IMPORT]` | Seed Data | Loaded from deterministic campus evaluation dataset (`facility_dataset/`). |
| `[DERIVED / ML FORECAST]` | Model Output | Computed by contextual baseline, adaptive ensemble, or DIF consensus engine. |
