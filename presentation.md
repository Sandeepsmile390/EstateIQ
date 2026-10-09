# EstateIQ-DIF v2.0 — Hackathon Presentation & Technical Blueprint

> **Official Hackathon Guide & Technical Blueprint for Presenting EstateIQ-DIF v2.0**
> 
> *An AI-Powered Facility Decision-Intelligence & Energy Optimization Engine with Edge IoT Ingestion, AWEHA-Inspired Adaptive Ensemble, EstateIQ-DIF Meta-Reasoning, Grounded Groq AI Copilot, Cost of Inaction Intelligence, and Closed-Loop Outcome Verification.*

---

## 1. Executive Pitch & Hackathon Hook (0 – 30 Seconds)

### The Hook
> *"Facilities consume 40% of global commercial energy, yet 30% is wasted due to contextual operational anomalies—like HVAC running at full capacity in empty buildings or uncoordinated transformer overloads. Traditional monitoring dashboards only tell you **WHAT** happened after the power bill arrives. **EstateIQ-DIF v2.0** is the first closed-loop Facility Decision-Intelligence Engine that ingests live telemetry, determines contextual anomalies using AWEHA-inspired adaptive ensembles, calculates root causes via SHAP, translates tech metrics into ₹ rupees and 7-day/30-day cost of inaction, simulates what-if interventions under thermal constraints, gets human approval, and automatically verifies closed-loop saved energy."*

### Elevator Summary
- **Target Audience:** Campus Facilities, Hospitals, Corporate Parks, Industrial Estates, PSUs.
- **Primary Showcase:** College Campus Electrical Grid, HVAC, Transformer, Water, Waste, and Sub-meter Optimization.
- **Core Value Proposition:** **Observe → Contextualize → Predict → Prioritize → Simulate → Act → Verify → Closed-Loop Save.**

---

## 2. End-to-End System Architecture & Data Flow

### 2.1 Complete End-to-End Data Pipeline

```text
[ PHYSICAL SENSORS / ESP32 ]   or   [ REAL-TIME IOT SIMULATOR ]   or   [ 365-DAY ANNOTATED TELEMETRY ]
                                              │
                                              ▼ (MQTT / JSON HTTP Post)
                       ┌──────────────────────────────────────────────┐
                       │  1. EDGE INGESTION & DATA QUALITY LAYER      │
                       │  • Data Quality Score (Completeness/Freshness)│
                       │  • Pydantic Schema Validation & Sanitization  │
                       └──────────────────────┬───────────────────────┘
                                              │
                                              ▼
                       ┌──────────────────────────────────────────────┐
                       │  2. CONTEXTUAL BASELINE & COLD START ENGINE  │
                       │  • Dynamic Normal Bounds (Weather/Schedule)   │
                       │  • COLD_START Fallback Mode (<14 days history) │
                       └──────────────────────┬───────────────────────┘
                                              │
                                              ▼
                       ┌──────────────────────────────────────────────┐
                       │  3. AWEHA ADAPTIVE ENSEMBLE FORECASTING      │
                       │  • Out-of-Sample Reliability Weighting (1/RMSE)│
                       │  • XGBoost / LightGBM / CatBoost / Prophet   │
                       └──────────────────────┬───────────────────────┘
                                              │
                                              ▼
                       ┌──────────────────────────────────────────────┐
                       │  4. MULTI-SIGNAL ANOMALY FUSION & PERSISTENCE│
                       │  • Residual Z-Score + Isolation Forest + LOF  │
                       │  • Physics Rules (PF < 0.82, Ambient vs HVAC) │
                       │  • Temporal Persistence Window (Multi-Interval)│
                       └──────────────────────┬───────────────────────┘
                                              │
                                              ▼
                       ┌──────────────────────────────────────────────┐
                       │  5. MODEL CONSENSUS & INDEPENDENT CONFIDENCE │
                       │  • Executed Model Voting & Agreement %       │
                       │  • Independent Confidence Score ∈ [0, 100]%   │
                       └──────────────────────┬───────────────────────┘
                                              │
                                              ▼
                       ┌──────────────────────────────────────────────┐
                       │  6. BUSINESS IMPACT & COST OF INACTION       │
                       │  • Grid Tariff Loss (₹9.50/kWh) & CO2e        │
                       │  • 7-Day & 30-Day Cost of Inaction Breakdown │
                       └──────────────────────┬───────────────────────┘
                                              │
                                              ▼
                       ┌──────────────────────────────────────────────┐
                       │  7. DECISION ENGINE & RECOMMENDATION RANKING │
                       │  • Priority Classification (P1 to P4)        │
                       │  • Multi-Attribute Utility Function Ranking  │
                       │  • "Why Recommended" & "Why NOT Alternatives"│
                       └──────────────────────┬───────────────────────┘
                                              │
                                       ┌──────┴──────┐
                                       │             │
                                       ▼             ▼
┌──────────────────────────────────────────────┐   ┌──────────────────────────────────────────────┐
│  8. GROUNDED GROQ AI COPILOT                 │   │  9. STREAMLIT / LIQUID-GLASS WEB UI          │
│  • Model: Llama-3.3-70b-versatile             │   │  • Operational Cockpit & Energy Analytics   │
│  • Strict Evidence JSON Grounding System     │   │  • Translucent Glassmorphic Tabs & ₹ Display │
│  • Deterministic Offline Fallback Engine     │   │  • What-If Interactive Simulator Sandbox    │
└──────────────────────┬───────────────────────┘   └──────────────────────┬───────────────────────┘
                       │                                                  │
                       └──────────────────────┬───────────────────────────┘
                                              │
                                              ▼
                       ┌──────────────────────────────────────────────┐
                       │ 10. HUMAN APPROVAL & ACTION CENTER           │
                       │ • Workflow: PENDING → APPROVED → COMPLETED    │
                       │ • MQTT Control Signal Dispatch (Relays)      │
                       └──────────────────────┬───────────────────────┘
                                              │
                                              ▼
                       ┌──────────────────────────────────────────────┐
                       │ 11. CLOSED-LOOP OUTCOME VERIFICATION         │
                       │ • Pre/Post Action Window Telemetry Snapshot  │
                       │ • 4-Tier Status (VERIFIED_SUCCESS/DEGRADATION)│
                       │ • Model Baseline Closed-Loop Weight Update   │
                       └──────────────────────────────────────────────┘
```

### 2.2 Data Provenance & Trust Badges
To guarantee 100% data integrity during presentation, every dataset and metric displayed in EstateIQ carries an unforgeable **Provenance Badge**:

1. `[REAL SENSOR]` — Live physical telemetry received from hardware ESP32 microcontrollers over MQTT.
2. `[SIMULATED SENSOR]` — Live synthesized stream mimicking real-world hardware behavior in real-time.
3. `[SYNTHETIC DATA]` — Historical canonical 365-day benchmark dataset with ground-truth anomaly annotations.
4. `[MODEL PREDICTION]` — Inference output produced by trained specialist ML algorithms (XGBoost/LightGBM/Prophet).
5. `[AI INTERPRETATION]` — Natural language analysis generated by Groq AI strictly grounded in EstateIQ-DIF evidence.
6. `[VERIFIED RESULT]` — Empirically measured before-vs-after post-intervention savings.

---

## 3. Layer-by-Layer Technical Implementation

### Layer 1: Data Acquisition & Edge Hardware Ingestion
- **Physical Hardware:** ESP32 microcontrollers running modular C++ Arduino firmware (`hardware/esp32/firmware/main.ino`). Reads current (SCT-013 CT sensors), voltage (ZMPT101B), temperature (DHT22), and light/occupancy status.
- **Edge Simulator:** `hardware/esp32/scripts/iot_simulator.py` simulates multi-building sensor payloads pushing data via HTTP POST / MQTT to `/api/v1/telemetry/ingest`.
- **Data Validation:** FastAPI backend utilizes Pydantic validation models enforcing schema bounds, out-of-range detection, and missing value handling before writing to persistence engines.
- **Annotated Ground-Truth Dataset:** `facility_dataset/` powers a 365-day (35,040 15-min intervals) dataset incorporating ground-truth anomaly annotations (`anomaly_flag`, `anomaly_type`) for rigorous precision/recall backtesting.

### Layer 2: Contextual Baseline & Cold-Start Engine
- **Dynamic Contextual Baselines:** Calculates expected building consumption based on thermal sensitivity, occupancy, operating schedules, and facility fingerprints:
  $$\text{Expected Load} = f(\text{Building}, \text{Hour}, \text{Occupancy}, \text{Temperature}, \text{DayType})$$
- **`COLD_START` Fallback Mode:** Facilities with $<14$ days of telemetry dynamically expand prediction intervals ($1.8\times$) to avoid false alarms during onboarding.
- **Residual Analysis:** Deviation is computed as $\text{Residual} = \text{Actual} - \text{Expected}$.

### Layer 3: AWEHA-Inspired Adaptive Ensemble & Specialist ML
- **Adaptive Forecasting Ensemble:**
  - Dynamic reliability weights: $w_i = \text{reliability}_i / \sum \text{reliability}_i$, where $\text{reliability}_i = 1 / (\text{RMSE}_i + \epsilon)$ derived from out-of-sample chronological validation.
  - Candidate models: `XGBoostRegressor`, `LGBMRegressor`, `CatBoostRegressor`, `Prophet`.
- **Multi-Signal Anomaly Zoo:**
  - `Isolation Forest`: Isolates multidimensional anomalies in feature space.
  - `Local Outlier Factor (LOF)`: Identifies localized density drops.
  - `Physics Consistency Rules`: Checks power factor ($\text{PF} < 0.82$), off-peak load spikes, and ambient temp vs HVAC load correlations.
  - `Temporal Persistence Window`: Tracks consecutive anomaly intervals to eliminate false alerts from 1-reading telemetry spikes.
- **Explainability (XAI):**
  - Integrated `SHAP (SHapley Additive exPlanations)` TreeExplainer computes exact feature contributions ($\Delta\text{kWh}$) for every prediction (e.g., HVAC load +42%, Ambient Temperature +11%, Occupancy +18%).

### Layer 4: EstateIQ-DIF (Dynamic Intelligence Framework)
EstateIQ-DIF is the core meta-reasoning engine (`src/intelligence/dif_engine.py`) that unifies specialist ML outputs into actionable decisions:
1. **Complexity Monitor:** Routes normal requests to fast exit pathways (**0.02 ms latency** and **80% early exit efficiency**).
2. **Model Consensus Engine:** Computes voting agreement % across executed model engines.
3. **Independent Confidence Engine:** Formulates a deterministic confidence score $\in [0, 100]\%$ separate from physical anomaly severity.
4. **Business Impact Engine:** Translates raw $\text{kWh}$ deviations into financial cost ($\text{INR } ₹9.50/\text{kWh}$), $\text{kg CO}_2\text{e}$ carbon emissions, and 7-day & 30-day Cost of Inaction projections.
5. **Next Best Action & Utility Ranker:** Multi-attribute utility function ranking candidate actions by benefit, sustainability, risk, effort, and confidence, complete with "Why Recommended" and "Why NOT Alternatives" evidence.

### Layer 5: Grounded Groq AI Intelligence Engine
- **Groq Cloud Integration:** Powered by `llama-3.3-70b-versatile` running on Groq's Ultra-Low Latency LPU infrastructure (`src/ai/groq_client.py`).
- **Grounded Evidence Injection:** Groq NEVER computes or guesses numbers. It receives a JSON evidence packet strictly containing verified DIF v2.0 outputs.
- **Deterministic Offline Fallback:** If the Groq API key is absent or network fails, EstateIQ smoothly defaults to a deterministic templates engine (`src/ai/ai_service.py`), ensuring 100% uptime during hackathon demos.

### Layer 6: Action Center, What-If Simulator & Constrained Optimization
- **What-If Simulation:** Interactively modifies operating parameters (thermostat setback, load factor) with explicit disclaimer provenance.
- **Constrained Optimization:** Solves optimal thermostat setpoints under thermal comfort envelope constraints ($22.0^\circ\text{C} - 25.0^\circ\text{C}$).
- **Human-in-the-Loop Workflow:** Actions transition cleanly through state machine stages: `NEW` $\rightarrow$ `ASSIGNED` $\rightarrow$ `APPROVED` $\rightarrow$ `COMPLETED` $\rightarrow$ `VERIFIED`.

### Layer 7: Closed-Loop Outcome Verification
- **Verification Protocol:** After an action is executed, EstateIQ observes post-intervention telemetry across a set window.
- **4-Tier Status Classification:** Classifies outcomes into `VERIFIED_SUCCESS`, `PARTIAL_SUCCESS`, `NO_IMPACT`, or `DEGRADATION`.
- **Closed-Loop Learning:** Automatically updates model recommendation weights based on verified real-world outcomes.

---

## 4. Where Inputs Go & Where Outputs Are Displayed

| Action / Data Element | Source / Ingestion Path | Processing Engine | Visual Location in Streamlit / Web UI |
| :--- | :--- | :--- | :--- |
| **Live Telemetry Stream** | ESP32 Sensor / IoT Simulator | FastAPI (`/api/v1/telemetry/ingest`) | **Live Operational Cockpit** (Top KPI Cards & Real-Time Gauges) |
| **Anomaly Detection** | 365-Day Baseline / Telemetry | Multi-Signal Fusion (IF + LOF + Residual) | **Anomaly Alerts Panel** (High Priority Red Flash & Score Dial) |
| **Root Cause Drivers** | Anomaly Record | SHAP TreeExplainer | **XAI Breakdown View** (Horizontal Waterfall & SHAP Feature Bar Chart) |
| **Financial & Inaction Cost** | Deviating $\text{kWh}$ | Tariff & Cost of Inaction Engine | **Financial Impact Card** (Hourly Waste ₹, 7-Day & 30-Day Inaction Cost, $\text{kg CO}_2\text{e}$) |
| **Natural Language Advice**| Structured Evidence Packet | Groq AI (`llama-3.3-70b`) / Fallback | **EstateIQ Groq AI Copilot Modal** (Formatted Markdown Insight) |
| **Intervention Testing** | User Input Sliders | What-If Simulation Engine | **What-If Sandbox** (Before vs After Scenario Comparison Curve) |
| **Why / Why Not Rationale** | Recommendation Ranker | Next Best Action Engine | **Action Center Card** ("Why Recommended" & "Why NOT Alternatives" List) |
| **Execution & Approval** | User Click ("Approve Action") | Action State Machine | **Action Center Table** (Status badge moves PENDING $\rightarrow$ APPROVED) |
| **Verified Savings** | Post-Action Telemetry Stream | Outcome Verification Engine | **Verification Audit Trail** (Green Verified Stamp with Saved ₹ Count) |

---

## 5. Step-by-Step 3-Minute Live Hackathon Demo Script

### Minute 0:00 – 0:45 | Ingestion & Anomaly Detection
1. **Action:** Open Streamlit Dashboard (`http://localhost:8501`). Point to the top status badge showing `[SYSTEM HEALTH: 100% | 76/76 TESTS PASSING]`.
2. **Narrative:** *"Notice our system status. EstateIQ is actively ingesting IoT telemetry from Block B Academic Hall. Current load is 145.2 kWh. Look at our Contextual Baseline—based on Wednesday 2:00 PM schedule, 40% occupancy, and 28°C ambient temp, expected load is only 82.0 kWh."*
3. **Visual Focus:** Point to the red Anomaly Banner showing **Anomaly Score: 0.88 (Critical)** with multi-signal fusion confirmation.

### Minute 0:45 – 1:30 | SHAP Explanation & Groq AI Grounding
1. **Action:** Click on **"Explain Anomaly (XAI)"**.
2. **Narrative:** *"Why is this happening? Traditional AI gives black-box numbers. EstateIQ uses SHAP values to explain root causes: HVAC load is contributing +42% of the excess load, ambient temperature +11%, and occupancy only +18%. This proves HVAC is running at 100% capacity despite partial building occupancy."*
3. **Action:** Click **"Ask Groq AI Copilot"**.
4. **Narrative:** *"Our Groq AI Copilot uses Llama-3.3-70b running on Groq LPUs. It doesn't guess or hallucinate—it ingests our exact SHAP evidence packet and generates an executive summary instantly: 'Block B HVAC setpoint misconfiguration detected. 30-day cost of inaction: ₹3,86,784.'"*

### Minute 1:30 – 2:15 | What-If Simulation & Human-in-the-Loop Approval
1. **Action:** Navigate to **"What-If Scenario Simulator"**. Adjust slider: *Reduce HVAC load by 20% & adjust setpoint to 24.5°C*. Click **"Run Simulation"**.
2. **Narrative:** *"Before taking action, facility managers can simulate interventions. The model calculates that adjusting HVAC setpoints will drop consumption by 38.5 kWh/hour, saving ₹327.25/hour and 31.5 kg CO₂/hour without impacting occupant comfort."*
3. **Action:** Click **"Approve Intervention & Dispatch Control Signal"**.
4. **Narrative:** *"EstateIQ enforces Human-in-the-Loop governance. I click Approve. The action transitions to APPROVED and sends a control MQTT packet to the ESP32 relay."*

### Minute 2:15 – 3:00 | Closed-Loop Verification & Summary
1. **Action:** Scroll to **"Action Center & Closed-Loop Verification"**.
2. **Narrative:** *"Most AI platforms stop at recommendations. EstateIQ closes the loop. Following the action, our engine reads post-intervention telemetry for 60 minutes. As you can see, actual load dropped to 84.1 kWh, achieving `[VERIFIED_SUCCESS]` state. The system automatically tags this record with a `[VERIFIED RESULT]` badge and updates model recommendation weights in real-time."*
3. **Closing Line:** *"EstateIQ transforms passive facility data into verified financial and carbon savings."*

---

## 6. Hackathon Judge Viva & Technical Q&A

### Q1: Why tree-based models (XGBoost/LightGBM/CatBoost) instead of Deep Learning (LSTM/Transformers)?
> **Answer:** Facility energy telemetry is structured, tabular data with distinct calendar periodicities and exogenous variables (weather, occupancy schedules). Gradient-boosted trees consistently outperform deep learning on tabular data, require significantly less training data, execute inference in sub-milliseconds (0.02ms in our benchmarks), and offer direct, exact feature attribution through SHAP TreeExplainer. LSTMs can be introduced later for long-horizon sequence modeling once years of high-frequency physical data accumulate.

### Q2: How do you prevent your Groq AI Copilot from hallucinating numbers or actions?
> **Answer:** We enforce strict separation between calculation and explanation. All math, baseline forecasts, anomaly scores, SHAP values, and financial waste figures are computed deterministically by EstateIQ-DIF in Python. Groq's Llama-3.3-70b model receives a constrained System Prompt and a structured JSON evidence packet. It is instructed to *only* explain the provided JSON context and explicitly state "data unavailable" if asked about unverified variables.

### Q3: How does your baseline differ from simple historical averaging?
> **Answer:** Historical averaging fails because energy consumption is highly context-dependent (a 100 kWh load on a hot Monday afternoon is normal, but 100 kWh at 3:00 AM on a Sunday is severe waste). EstateIQ computes a *Contextual Dynamic Baseline* using multi-variable regression considering hour-of-day, day-of-week, academic calendar status, ambient temperature, and live occupancy counts. Features include `COLD_START` fallback for new buildings.

### Q4: What happens if the internet connection or Groq API fails during operation?
> **Answer:** EstateIQ is built with offline resilience. The core intelligence engine (EstateIQ-DIF), specialist ML models, anomaly detectors, and decision trace algorithms run 100% locally on FastAPI. If the Groq API key is missing or internet drops, our offline fallback generator seamlessly creates structured, deterministic natural language summaries, ensuring zero operational downtime.

### Q5: How do you handle noisy or missing IoT sensor data?
> **Answer:** Ingestion routes data through Pydantic sanitization filters. Out-of-bounds readings are quarantined, missing time steps are interpolated, and sensor health metrics are calculated continuously. Low quality data dynamically lowers the EstateIQ-DIF *Confidence Score* ($\in [0, 100]\%$), signaling to operators that recommendations carry higher uncertainty.

### Q6: How does the system handle Indian electricity tariffs and backup power (DG sets)?
> **Answer:** EstateIQ features dedicated Indian facility power analytics (`src/intelligence/business_impact.py`). It calculates Time-of-Use (ToU) peak vs off-peak rates (₹9.50/kWh grid tariff baseline), maximum demand penalty thresholds, power factor penalties, 7-day/30-day cost of inaction, and Diesel Generator (DG) operational costs.

### Q7: Can EstateIQ integrate with existing BMS (Building Management Systems)?
> **Answer:** Yes. EstateIQ supports standard MQTT messaging and RESTful JSON APIs (`/api/v1/telemetry/ingest`). It acts as an overlay intelligence layer on top of existing BACnet, Modbus, or SCADA hardware without requiring expensive hardware replacements.

### Q8: What is the computational latency of the EstateIQ-DIF decision engine?
> **Answer:** EstateIQ-DIF incorporates an Early Exit Complexity Monitor (`src/intelligence/complexity_monitor.py`). For normal operational states (80% of telemetry), it executes lightweight baseline checks and early-exits in **0.02 milliseconds**. Full ensemble processing with SHAP calculation takes under 15 milliseconds, enabling real-time edge performance.

### Q9: How do you prove that savings didn't just happen by chance?
> **Answer:** Our Closed-Loop Verification engine (`src/intelligence/outcome_verification.py`) compares pre-intervention baseline telemetry against actual post-action telemetry over a verified window. It classifies outcomes into 4 tiers (`VERIFIED_SUCCESS`, `PARTIAL_SUCCESS`, `NO_IMPACT`, `DEGRADATION`) and updates model recommendation weights in real-time.

### Q10: How scalable is this architecture across a large university campus with 50+ buildings?
> **Answer:** The FastAPI backend is stateless and horizontally scalable. Data ingestion and feature calculation can be distributed across worker threads or microservices. Specialist models are trained per building category (Academic, Dormitory, Lab, Admin) to maintain high precision while sharing unified inference routines.

---

## 7. Production Benchmark Evidence & Verification

- **Automated Test Suite:** **76 / 76 Tests Passing (100% Pass Rate)** (`python -m unittest discover tests`)
- **System Execution Latency:** Average decision latency **0.02 ms** on Fast Path (80% early exit efficiency).
- **Ablation Study Empirical Validation:** Anomaly F1-Score **0.961**, False Alarm Rate **0.6%** (97.5% reduction vs static thresholds), Cost of Inaction Accuracy **97.3%** on 365-day annotated dataset ([docs/ABLATION_STUDY.md](file:///d:/Hackathon/Model/docs/ABLATION_STUDY.md)).
- **ML Baseline Precision:** $R^2 > 0.94$, $\text{RMSE} = 3.18 \text{ kWh}$ on canonical 365-day dataset.
- **GitHub Repository:** `https://github.com/Sandeepsmile390/EstateIQ.git` (Release Candidate Main Branch).

---

*EstateIQ-DIF v2.0 Presentation Blueprint — Ready for Hackathon Demonstration.*
