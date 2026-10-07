# ESTATEIQ INTELLIGENCE FUSION ENGINE (EIFE)
## Algorithm & System Architecture Specification Document
**Project Name:** EstateIQ — Sustainable Facility and Estate Intelligence Platform  
**Target Submission:** Faculty Evaluators, Teachers & Technical Hackathon Judges  

---

## 1. ALGORITHM OVERVIEW & OBJECTIVE

Standard machine learning deployments in IoT/Facility management follow a rigid, open-loop workflow:
$$\text{DATA} \longrightarrow \text{MODEL} \longrightarrow \text{DASHBOARD}$$

The **EstateIQ Intelligence Fusion Engine (EIFE)** sits directly **ABOVE** specialized machine-learning models (XGBoost, LightGBM, CatBoost, Random Forest, Prophet, Isolation Forest, LOF, SHAP). It orchestrates model outputs, sensor quality, facility context, financial impact, risk, explainability, and operational constraints into a transparent, closed-loop decision architecture:

$$\text{OBSERVE} \rightarrow \text{VALIDATE} \rightarrow \text{PREDICT} \rightarrow \text{DETECT} \rightarrow \text{EXPLAIN} \rightarrow \text{FUSE} \rightarrow \text{QUANTIFY} \rightarrow \text{PRIORITIZE} \rightarrow \text{SIMULATE} \rightarrow \text{OPTIMIZE} \rightarrow \text{APPROVE} \rightarrow \text{ACT} \rightarrow \text{VERIFY} \rightarrow \text{LEARN}$$

---

## 2. CONCEPTUAL ARCHITECTURE

```text
                       ┌─────────────────────────┐
                       │    RAW FACILITY DATA    │
                       └────────────┬────────────┘
                                    │
                       ┌────────────▼────────────┐
                       │   DATA QUALITY ENGINE   │
                       └────────────┬────────────┘
                                    │
         ┌──────────────────────────┴──────────────────────────┐
         │                                                     │
┌────────▼─────────────────────────┐         ┌─────────────────▼─────────────────┐
│ FACILITY FINGERPRINT & BASELINE │         │  SPECIALIZED ML EVIDENCE ENGINES  │
│ • Hour/Weekday/Season Profiles   │         │ • XGBoost Regressor (Demand)      │
│ • Gaussian Bounds (±1.96σ)       │         │ • Prophet (Time-Series Baseline)  │
└────────────────┬─────────────────┘         │ • Isolation Forest (Anomaly)      │
                 │                           │ • Local Outlier Factor (LOF)      │
                 │                           │ • SHAP (Feature Attribution)      │
                 │                           └─────────────────┬─────────────────┘
                 │                                             │
                 └──────────────────────────┬──────────────────┘
                                            │
                               ┌────────────▼────────────┐
                               │ MODEL CONSENSUS ENGINE  │
                               └────────────┬────────────┘
                                            │
                               ┌────────────▼────────────┐
                               │ ESTATEIQ FUSION ENGINE  │
                               └────────────┬────────────┘
                                            │
             ┌──────────────────────────────┼──────────────────────────────┐
             │                              │                              │
┌────────────▼────────────┐    ┌────────────▼────────────┐    ┌────────────▼────────────┐
│   CONFIDENCE ENGINE     │    │     BUSINESS IMPACT     │    │    OPPORTUNITY RANKER   │
│  (0–100% Deterministic) │    │   (Cost of Inaction)    │    │  (ROI & Effort Matrix)  │
└────────────┬────────────┘    └────────────┬────────────┘    └────────────┬────────────┘
             │                              │                              │
             └──────────────────────────────┼──────────────────────────────┘
                                            │
                               ┌────────────▼────────────┐
                               │      AI SAFETY GATE     │
                               └────────────┬────────────┘
                                            │
                               ┌────────────▼────────────┐
                               │ HUMAN-IN-THE-LOOP (BMS) │
                               └────────────┬────────────┘
                                            │
                               ┌────────────▼────────────┐
                               │  OUTCOME VERIFICATION   │
                               └────────────┬────────────┘
                                            │
                               ┌────────────▼────────────┐
                               │ AI CALIBRATION MEMORY   │
                               └─────────────────────────┘
```

---

## 3. MATHEMATICAL FORMULATIONS & SUB-ENGINES

### Sub-Engine 1: Data Quality Engine
Before making any decision, the system validates raw telemetry across 4 dimensions:

$$\text{Data Quality Score (DQ)} = 0.35 \cdot C_{\text{completeness}} + 0.25 \cdot C_{\text{freshness}} + 0.20 \cdot C_{\text{consistency}} + 0.20 \cdot C_{\text{reliability}}$$

*If $\text{DQ} < 70\%$, downstream decision confidence is automatically penalized.*

---

### Sub-Engine 2: Contextual Baseline & Facility Fingerprint
Learns facility-specific hourly, daily, and thermal operating profiles. Expected consumption is calculated dynamically:

$$\text{Expected Value } (E) = f(\text{hour}, \text{day\_of\_week}, \text{occupancy}, \text{ambient\_temperature})$$

Gaussian statistical bounds adapt to individual building noise:

$$\text{Upper Bound} = E + 1.96 \cdot \sigma_{\text{baseline}}$$
$$\text{Lower Bound} = E - 1.96 \cdot \sigma_{\text{baseline}}$$

---

### Sub-Engine 3: Model Consensus Engine
Combines predictions from multiple distinct ML models ($M$). Model consensus evaluates signal agreement:

$$\text{Consensus Score } (S_{\text{consensus}}) = \sum_{m \in M} w_m \cdot I(\text{Agreement}_m) \times 100\%$$
$$\text{Disagreement Score} = 100\% - S_{\text{consensus}}$$

*If models disagree (e.g., XGBoost predicts surge while Prophet predicts normal), confidence is reduced and a model disagreement alert is raised.*

---

### Sub-Engine 4: Multi-Source Confidence Engine
Generates a transparent, deterministic decision confidence score ($0-100\%$):

$$\text{Confidence} = 0.30 \cdot S_{\text{consensus}} + 0.25 \cdot \text{DQ} + 0.15 \cdot C_{\text{coverage}} + 0.15 \cdot C_{\text{sensor\_rel}} + 0.15 \cdot C_{\text{shap}}$$

- **Confidence $\ge 80\%$**: High trust — action recommended for immediate execution.
- **Confidence $< 60\%$**: Low trust — safety gate mandates manual data verification.

---

### Sub-Engine 5: Business Impact & Cost of Inaction Engine
Converts physical anomalies into financial metrics (INR ₹) and carbon footprint:

$$\text{Daily Avoidable Surge Cost (₹)} = (\text{Actual kWh} - \text{Expected kWh}) \times \text{Tariff Rate (₹/kWh)}$$
$$\text{Cost of Inaction (Annualized ₹)} = \text{Daily Avoidable Cost} \times 365$$
$$\text{CO}_2\text{e Emissions Surge (kg)} = (\text{Actual kWh} - \text{Expected kWh}) \times 0.82 \text{ kg CO}_2\text{e/kWh}$$

---

### Sub-Engine 6: Constrained Optimization Engine
Formulates optimal HVAC thermostat setback and peak shifting targets subject to thermal comfort bounds:

$$\min_{\theta} \text{Energy Cost}(\theta) \quad \text{subject to} \quad 22.0^\circ\text{C} \le T_{\text{indoor}}(\theta) \le 25.0^\circ\text{C}$$

---

### Sub-Engine 7: AI Safety Gate & Human-in-the-Loop Protocol
Evaluates 5 safety checkpoints before executing physical facility interventions:
1. **Data Quality Check**: $\text{DQ} \ge 60\%$
2. **Confidence Check**: $\text{Confidence} \ge 65\%$
3. **Consensus Check**: $S_{\text{consensus}} \ge 50\%$
4. **Safety Risk Threshold**: High-risk physical control operations require human authorization.
5. **Human Approval**: BMS command dispatch requires authorized administrator approval.

---

### Sub-Engine 8: Closed-Loop Outcome Verification Engine
After an operational action is executed, the engine compares post-action telemetry against pre-action baselines:

$$\Delta_{\text{verified}} = \left( \frac{\text{Baseline}_{\text{pre}} - \text{Observed}_{\text{post}}}{\text{Baseline}_{\text{pre}}} \right) \times 100\%$$

$$\text{Status} = \begin{cases} 
\text{VERIFIED\_SAVINGS\_ACHIEVED}, & \text{if } \Delta_{\text{verified}} \ge \Delta_{\text{target}} \\
\text{EXPECTED\_IMPACT\_NOT\_ACHIEVED}, & \text{otherwise}
\end{cases}$$

Verified results are stored in the AI Decision Memory for autonomous re-calibration.

---

## 4. GROUNDED DATA PROVENANCE BADGES

To eliminate hallucinated output claims, every metric and UI visual displays provenance:

- `[OBSERVED]`: Direct IoT telemetry from physical or simulated meters
- `[PREDICTED]`: Output from trained specialized ML models (XGBoost, Prophet, LOF)
- `[SIMULATED]`: Output from What-If constrained optimization scenarios
- `[SYNTHETIC IoT DATA]`: Output from the 365-day realistic campus data generator

---

## 5. SUMMARY OF KEY TECHNICAL ADVANTAGES

1. **Does NOT Replace Standard ML**: Preserves proven models (XGBoost, Prophet, Isolation Forest, SHAP) as specialized evidence providers.
2. **Deterministic & Defensible**: Eliminates black-box LLM hallucinations by using grounded statistical equations.
3. **Empirical Closed-Loop**: Measures actual post-action savings instead of declaring success prematurely.
4. **Safety First**: Enforces human-in-the-loop authorization before adjusting physical infrastructure.
