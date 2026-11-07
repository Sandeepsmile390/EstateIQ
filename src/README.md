# EstateIQ Source Code Architecture (`src/`)

This directory contains the core business logic, algorithmic engines, unified service layer, and device registry powering the **EstateIQ Facility Decision Intelligence Platform**.

---

## 🏛️ Package Architecture & Subsystems

```text
src/
├── intelligence/       # EstateIQ-DIF v2.0 Decision Intelligence Meta-Engine
├── registry/           # Central IoT Device Registry & Edge Gateway Provisioning
├── data/               # Canonical Pydantic Telemetry Schemas & Ingestion Validators
├── services/           # Unified Service Layer (Shared by FastAPI and Streamlit)
├── ai/                 # Grounded GenAI Engine & Groq Cloud LPU (llama-3.3-70b-versatile)
├── auth/ & security/   # 4-Tier Role-Based Access Control (RBAC) & Gateway Keys
├── scenarios/          # What-If Parametric Simulation Engine (₹9.50/kWh Tariff)
├── explainability/     # Explainable AI (SHAP TreeExplainer Feature Attributions)
├── recommendations/    # Grounded Action Synthesis & Offline Rule Fallback
├── models/             # Time-Series Forecasters & Tabular Regressors
└── analytics/          # KPI Calculation & Data Quality Scoring
```

---

## 🔍 Subsystem Highlights

### 1. Decision Intelligence Framework (`src/intelligence/`)
- `dif_engine.py`: Master DIF orchestrator synthesizing baseline residuals, domain rules, and persistence into actionable Evidence Packets.
- `seasonal_baseline.py`: Robust weekly quarter-hour (672-slot) median-MAD contextual baselines with heuristic fallback.
- `domain_rules.py`: Deterministic facility physics rules (e.g. low power factor $<0.82$, off-peak night surges, thermal anomalies).
- `anomaly_consensus.py`: Multi-signal fusion combining contextual residual score ($S_c$) and active rule score ($S_r$).
- `confidence_engine.py`: Independent confidence estimation ($0-100$) evaluating data quality, sensor health, and history depth.
- `business_impact.py`: Cost of Inaction calculations in Indian Rupees (₹) and $\text{CO}_2\text{e}$ carbon footprint projections.
- `outcome_verification.py`: Closed-loop pre/post action telemetry verification classifying operational outcomes.

### 2. Device Registry & Gateway Authority (`src/registry/`)
- `device_registry.py`: Central registry managing hardware meters, edge microcontrollers (`ESP32_EDGE_GATEWAY_01`), virtual simulator instances, and streaming heartbeats. Auto-provisions physical gateways and maps data provenance flags.

### 3. Canonical Data Schemas (`src/data/`)
- `telemetry_schema.py`: Strict Pydantic model enforcing protocol `version: "1.0"`, UTC ISO 8601 timestamps, monotonic sequence numbers, and provenance tags (`source_type: "hardware"` vs `"simulated_iot"`).

### 4. Unified Service Layer (`src/services/`)
Ensures that calculations, tariffs, KPI metrics, and data aggregations are computed identically whether accessed via the FastAPI REST backend or the Streamlit analytical cockpit.

---

## 📚 Related Documentation

- [System Architecture Guide](../docs/ARCHITECTURE.md)
- [Technology Stack Specification](../TECHSTACK.md)
- [Master Documentation Index](../docs/README.md)
