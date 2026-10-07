# EstateIQ Intelligence Fusion Engine Specification
## EstateIQ-DIF — Dynamic Intelligence Fusion Algorithm Architecture
### Closed-Loop AI Decision Intelligence, Adaptive Learning, Multi-Source Confidence, & Outcome Verification

---

## 1. EXECUTIVE OVERVIEW

EstateIQ is an AI-powered Sustainable Facility and Estate Intelligence platform engineered for complex institutional campuses (colleges, hospitals, government facilities, corporate parks, and industrial estates).

The **EstateIQ Intelligence Fusion Engine (EstateIQ-DIF)** sits directly **ABOVE** specialized Machine Learning models (XGBoost, LightGBM, CatBoost, Random Forest, Prophet, Isolation Forest, LOF, SHAP). It orchestrates model outputs, sensor quality, facility context, financial impact, risk, explainability, and operational constraints into a transparent, confidence-aware decision-support ecosystem.

---

## 2. ESTATEIQ-DIF ALGORITHM ARCHITECTURE

```text
                  EstateIQ-DIF
                       │
        ┌──────────────┼──────────────┐
        ↓              ↓              ↓
       ECF            EAE            EAC
   Context Filter   Adaptive       Anomaly
                    Ensemble      Consensus
        │              │              │
        └──────────────┼──────────────┘
                       ↓
                      ECI
                  Confidence
                       ↓
                      EBI
                Business Impact
                       ↓
                  Risk/Opportunity
                       ↓
                      EDI
              Decision Intelligence
                       ↓
             Recommendation Ranker
                       ↓
                   What-If
                       ↓
                  Verification
                       ↓
                  Calibration
```

---

## 3. CLOSED-LOOP DECISION ARCHITECTURE

The platform moves facility management from passive monitoring to an autonomous decision intelligence loop:

```text
OBSERVE → VALIDATE → CONTEXTUALIZE → PREDICT → DETECT → EXPLAIN → FUSE → QUANTIFY → PRIORITIZE → SIMULATE → OPTIMIZE → APPROVE → ACT → VERIFY → CALIBRATE
```

```mermaid
graph TD
    RawData[RAW FACILITY DATA] --> DQ[DATA QUALITY ENGINE]
    DQ --> Baseline[FACILITY FINGERPRINT & CONTEXTUAL BASELINE]
    DQ --> ML[SPECIALIZED ML ENGINES\nXGBoost | Prophet | IsolationForest | LOF | SHAP]
    Baseline --> Fusion[ESTATEIQ INTELLIGENCE FUSION ENGINE]
    ML --> Fusion
    Fusion --> Confidence[CONFIDENCE ENGINE]
    Fusion --> Impact[BUSINESS IMPACT & COST OF INACTION]
    Fusion --> Consensus[MODEL CONSENSUS ENGINE]
    Confidence --> SafetyGate[AI SAFETY GATE]
    Impact --> Priority[OPPORTUNITY & PRIORITY RANKER]
    Consensus --> SafetyGate
    Priority --> SafetyGate
    SafetyGate --> HumanApproval[HUMAN-IN-THE-LOOP APPROVAL]
    HumanApproval --> Action[BMS/FACILITY ACTION]
    Action --> Verification[OUTCOME VERIFICATION ENGINE]
    Verification --> Calibration[RE-CALIBRATION & DECISION MEMORY]
```

---

## 4. ENGINE COMPONENTS & MATHEMATICAL FORMULATIONS

### 4.1 Data Quality Engine (`src/data_quality/quality_score.py`)
Computes a composite **Data Quality Score (0–100%)** across 4 primary sensor telemetry dimensions:

$$ \text{Quality Score} = 0.35 \times \text{Completeness} + 0.25 \times \text{Freshness} + 0.20 \times \text{Consistency} + 0.20 \times \text{Sensor Reliability} $$

If Data Quality $< 70\%$, downstream decision confidence is automatically penalized.

---

### 4.2 ECF — EstateIQ Context Filter (`src/intelligence/context_filter.py`)
Computes expected baseline consumption and dynamic normal bounds ($\pm 1.96\sigma$). Provides an early exit for nominal readings ($<10\%$ deviation):

$$ \text{Expected Value} = f(\text{hour}, \text{day}, \text{occupancy}, \text{temperature}) $$
$$ \text{Residual} = \text{Actual kWh} - \text{Expected Value} $$
$$ \text{Relative Deviation (\%)} = \left( \frac{\text{Residual}}{\max(|E|, \epsilon)} \right) \times 100\% $$

---

### 4.3 EAE — Adaptive Ensemble (`src/intelligence/adaptive_ensemble.py`)
Implements a Champion/Challenger model selection architecture:
- **Champion Model**: LightGBM (executed by default)
- **Challenger Models**: XGBoost, CatBoost, Prophet (executed only on Path C or when confidence is low)

---

### 4.4 EAC — Anomaly Consensus Engine (`src/intelligence/anomaly_consensus.py`)
Normalizes multi-detector signals across contextual residual, Isolation Forest, LOF, and domain rules:

$$ \text{Anomaly Score} = 0.35 \cdot S_{\text{contextual}} + 0.30 \cdot S_{\text{isolation\_forest}} + 0.15 \cdot S_{\text{lof}} + 0.20 \cdot S_{\text{domain\_rules}} $$

---

### 4.5 ECI — Multi-Source Confidence Engine (`src/intelligence/confidence_engine.py`)
Formulates deterministic confidence ($0-100\%$) combining 5 evidence signals:

$$ \text{Confidence} = 0.30 \times S_{\text{consensus}} + 0.25 \times \text{DQ} + 0.15 \times C_{\text{coverage}} + 0.15 \times C_{\text{sensor\_rel}} + 0.15 \times C_{\text{shap}} $$

Low confidence ($<60\%$) prevents automated high-impact recommendation execution.

---

### 4.6 EBI — Business Impact & Cost of Inaction Engine (`src/intelligence/business_impact.py`)
Translates physical kWh surges into financial and carbon metrics:

$$ \text{Daily Avoidable Cost (₹)} = (\text{Actual kWh} - \text{Expected kWh}) \times \text{Tariff Rate (₹9.50/kWh)} $$
$$ \text{Cost of Inaction (Annualized)} = \text{Daily Avoidable Cost} \times 365 $$
$$ \text{CO}_2\text{e Surge (kg)} = (\text{Actual kWh} - \text{Expected kWh}) \times 0.82\text{ kg CO}_2\text{e/kWh} $$

---

### 4.7 EDI — Decision Intelligence Engine (`src/intelligence/decision_engine.py`)
Synthesizes normalized evidence into composite decision scores and classifies priority:

$$ \text{Decision Score} = 0.20 S_{\text{ctx}} + 0.25 S_{\text{anom}} + 0.15 S_{\text{fcst}} + 0.15 S_{\text{impact}} + 0.15 S_{\text{risk}} + 0.10 S_{\text{opp}} $$

Priority levels: `P1_CRITICAL` ($\ge 75$ + High Confidence), `P2_HIGH` ($\ge 55$), `P3_MEDIUM` ($\ge 35$), `P4_LOW` ($< 35$).

---

### 4.8 Outcome Verification Engine (`src/intelligence/outcome_verification.py`)
Compares post-action telemetry against pre-action baselines to verify realized savings:

$$ \Delta_{\text{verified}} = \left( \frac{\text{Baseline}_{\text{pre}} - \text{Observed}_{\text{post}}}{\text{Baseline}_{\text{pre}}} \right) \times 100\% $$

- If $\Delta_{\text{verified}} \ge \Delta_{\text{target}}$: Outcome is marked `VERIFIED_SAVINGS_ACHIEVED`.
- Else: Outcome is marked `EXPECTED_IMPACT_NOT_ACHIEVED`, triggering AI re-calibration.

---

## 5. ADAPTIVE EXECUTION PATHS

1. **Path A (Fast Path)**: ECF contextual residual check $\rightarrow$ Early exit for normal readings ($0.02\text{ ms}$).
2. **Path B (Intelligence Path)**: Champion model execution $\rightarrow$ Consensus $\rightarrow$ Business Impact $\rightarrow$ Recommendation ranking.
3. **Path C (Critical Path)**: Full multi-model ensemble $\rightarrow$ Selective SHAP feature attribution $\rightarrow$ What-If optimization $\rightarrow$ Human approval workflow.

---

## 6. REST API ENDPOINTS

The Intelligence Fusion Engine exposes standardized REST endpoints under `/api/v1/intelligence/*`:

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/intelligence/fusion` | `POST` | Executes complete Fusion Engine analysis on telemetry batch |
| `/api/v1/intelligence/confidence` | `POST` | Computes multi-source confidence breakdown |
| `/api/v1/intelligence/model-consensus` | `POST` | Evaluates agreement across XGBoost, Prophet, LOF & IsolationForest |
| `/api/v1/intelligence/business-impact` | `POST` | Computes surge monetary impact and Cost of Inaction |
| `/api/v1/intelligence/opportunities` | `GET` | Returns ranked facility optimization opportunities |
| `/api/v1/intelligence/verify-outcome` | `POST` | Verifies pre- vs post-action telemetry impact |
| `/api/v1/intelligence/feedback` | `POST` | Records human approval, rejection, and operational feedback |

---

## 7. PROVENANCE BADGES

Every API response and UI visualization explicitly includes grounded provenance tracking:

- `[OBSERVED]`: Direct IoT telemetry from physical or simulated meters
- `[PREDICTED]`: Output from trained specialized ML models (XGBoost, Prophet, LOF)
- `[SIMULATED]`: Generated by What-If constrained optimization scenarios
- `[SYNTHETIC IoT DATA]`: Generated by 365-day realistic campus data generator
