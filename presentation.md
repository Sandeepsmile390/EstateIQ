# EstateIQ — Teacher Presentation & Technical Explanation

> Teacher/viva-ready explanation of EstateIQ: problem, architecture, data flow, ML models, model selection, security, explainability, business value, limitations, and future scope.
>
> **Audit note:** The current repository has a strong architecture, but source inspection shows unresolved production gaps. Do not present claimed PASS statuses as verified until the fixes in the Antigravity prompt are implemented and re-tested.

## 1. What is EstateIQ?

**EstateIQ is an AI-powered facility decision-intelligence platform that detects operational inefficiencies, explains their causes, quantifies business impact, simulates interventions, and verifies measurable improvements.**

Target users:
- Universities and colleges
- Hospitals
- Corporate campuses
- Government facilities
- PSUs
- Industrial estates
- Municipal facilities

The strongest demonstration is electricity/energy management for a college campus, while the architecture supports water, waste, air quality, mobility, parking, assets, safety and emissions.

## 2. Problem

Traditional dashboards mainly answer **what happened**. EstateIQ is designed to answer:

1. What is happening?
2. Is it abnormal for this context?
3. Why is it happening?
4. What will happen next?
5. What should we do?
6. What will it cost?
7. What if we intervene?
8. Did the intervention actually work?

Core loop:

```text
OBSERVE → UNDERSTAND → PREDICT → PRIORITIZE → SIMULATE → ACT → VERIFY → SAVE
```

## 3. Campus Example

```text
Grid → Transformer → Main Meter → Building → Sub-meter → HVAC/Lighting/Equipment
                         ↘
                           DG
```

If Block B consumes 145 kWh when the contextual model expects 82 kWh, EstateIQ should detect the deviation, identify drivers such as HVAC/occupancy/temperature, forecast near-term load, estimate financial impact, recommend an action, simulate the intervention, and later verify the actual result.

## 4. Architecture

```text
Sensors / Smart Meters / Synthetic IoT
                ↓
       Ingestion + Validation
                ↓
     Data Repository + Provenance
                ↓
        Feature Engineering
                ↓
      ML / Anomaly / XAI Engine
                ↓
  Decision Intelligence / Business Impact
                ↓
 Recommendation → What-If → Approval
                ↓
            Action Center
                ↓
           Verification
                ↓
          KPI / Savings
```

### Technology stack

**Backend:** Python, FastAPI, Pydantic, Pandas, NumPy, Joblib

**ML:** Scikit-learn, XGBoost, LightGBM, CatBoost, Optuna, SHAP

**Data:** SQLite + MongoDB connector architecture, CSV/synthetic telemetry

**Frontend:** HTML, CSS, JavaScript, Chart.js, liquid-glass design system

## 5. Data Pipeline

The generator creates timestamped facility telemetry for energy, occupancy, weather, water, waste, air, traffic, parking, equipment, safety and emissions.

Important principle: data should contain realistic relationships rather than independent random values.

Example:

```text
Occupancy ↑ → HVAC ↑ → Electricity ↑
Temperature ↑ → Cooling demand ↑ → Electricity ↑
```

The system is currently primarily a simulated/synthetic IoT prototype. A production deployment can ingest real meters and sensors through MQTT/API gateways.

## 6. Feature Engineering

The current pipeline creates:

- Hour
- Day of week
- Month
- Weekend
- Peak-hour flag
- Sine/cosine time encoding
- Lag features
- Rolling mean
- Rolling standard deviation

For time-series data, chronological splitting is preferable:

```text
Past 70% → Train
Next 15% → Validation
Latest 15% → Test
```

This reduces future-data leakage.

## 7. Models

### Linear Regression

Baseline/interpretable model:

```text
Energy = β0 + β1(occupancy) + β2(temp) + β3(HVAC) + ...
```

Good for a simple reference, but limited for nonlinear relationships.

### Random Forest

Combines many decision trees. Strong for nonlinear tabular data and robust without heavy feature scaling.

### Gradient Boosting

Builds trees sequentially, with later trees correcting earlier errors.

### XGBoost

Optimized gradient boosting. Strong for structured nonlinear tabular problems and feature interactions. The repository also contains Optuna-based tuning.

### LightGBM

Efficient gradient boosting suited to larger tabular datasets.

### CatBoost

Gradient boosting model included as a candidate and useful for complex tabular relationships.

## 8. Model Selection

EstateIQ compares candidates instead of assuming one algorithm is always best.

Regression candidates:
- Naive baseline
- Linear Regression
- Random Forest
- Gradient Boosting
- XGBoost
- LightGBM
- CatBoost

Classification candidates:
- Majority baseline
- Logistic Regression
- Random Forest
- XGBoost
- LightGBM
- CatBoost

Regression metrics:
- MAE
- RMSE
- R²
- MAPE

Classification metrics:
- Precision
- Recall
- F1
- ROC-AUC
- PR-AUC

Current code primarily selects regression by validation RMSE and classification by validation F1. A production version should also consider calibration, stability, latency, drift and operational cost.

### Viva answer: Why tree models instead of deep learning?

> Facility telemetry is structured/tabular data. Gradient-boosted trees usually provide strong nonlinear performance with less data, simpler training and better explainability through SHAP. LSTM/transformer models can be added later when enough real sequential sensor history is available.

## 9. Energy Forecasting

Inputs can include:

```text
Historical energy
Occupancy
Temperature
HVAC
Lighting
Equipment
Calendar/time
Lag features
```

Output can be predicted at multiple horizons such as 15 minutes, 1 hour, 4 hours, 24 hours and 7 days.

Longer horizons must carry greater uncertainty.

**Important current gap:** the current `/api/v1/energy/forecast` source still uses fixed multipliers on the latest value. It must be replaced with genuine model inference.

## 10. Contextual Energy Baseline

A simple average is insufficient.

Instead:

```text
Expected Energy =
f(building, hour, occupancy, temperature,
  operating schedule, historical pattern, equipment context)
```

Then:

```text
Residual = Actual − Expected
```

A large residual is stronger evidence of abnormal operation than simply comparing against a global average.

## 11. Anomaly Detection

Use a hybrid approach:

```text
Contextual residual
+
Isolation Forest / LOF
+
Operating schedule
+
Occupancy
+
Business rules
```

Isolation Forest isolates unusual observations; LOF compares local density.

Example:

> High energy during a packed campus event may be normal. High energy at 3 AM with near-zero occupancy is more suspicious.

## 12. SHAP Explainability

SHAP estimates how individual features contribute to a prediction.

Example:

```text
HVAC load       +42%
Occupancy       +18%
Temperature     +11%
Previous load    +7%
```

Correct interpretation:

> These features strongly influenced the model prediction.

Incorrect interpretation:

> SHAP proves these features physically caused the entire event.

## 13. Decision Trace

The intended trace is:

```text
1. Observed data
2. Contextual baseline
3. Deviation
4. ML forecast
5. Anomaly score
6. SHAP explanation
7. Priority
8. Recommendation
9. Assumptions
10. What-If impact
11. Action / verification
```

**Important current gap:** `src/decisions/trace.py` currently contains fixed forecast multipliers, fixed SHAP-like percentages, fixed recommendations and fixed tariff assumptions. The production version must call the real model, SHAP engine, anomaly engine, business-impact engine and What-If engine.

## 14. Recommendation Engine

Recommendations should consume validated evidence:

```text
Observed data
+ baseline
+ anomaly
+ model prediction
+ SHAP
+ business impact
+ operating context
```

Then produce:

- What happened
- What is predicted
- Why it was flagged
- Severity
- Recommended action
- Assumptions
- Limitations

The current recommendation module is deterministic/rule-based. That is useful for offline reliability. If an LLM is enabled, it must be a genuine grounded LLM call; the product must not claim a live LLM when none was called.

## 15. AI Copilot

Recommended architecture:

```text
User question
 → permission check
 → intent/tool selection
 → query EstateIQ data
 → run analytics
 → structured evidence
 → grounded LLM explanation
```

The LLM must not be the source of operational truth.

## 16. Business Impact

Translate technical anomalies into:

```text
Avoidable kWh × tariff = avoidable cost
```

Also support:

- Time-of-use tariffs
- Demand charges
- DG fuel cost
- CO₂e
- Monthly/annual impact
- Confidence intervals

## 17. Transformer and DG Intelligence

Transformer:

- Load %
- Voltage/current
- Temperature
- Peak load
- Overload duration
- Power factor
- Power quality

DG:

- Runtime
- Fuel consumption
- Generated energy
- Starts/stops
- Fuel cost
- Cost per generated kWh
- CO₂e

This makes the electricity module particularly relevant to Indian campuses.

## 18. What-If Simulation

Example:

```text
Reduce HVAC load by 20%
        ↓
Run model
        ↓
Baseline vs simulated demand
        ↓
Estimated kWh / ₹ / CO₂e impact
```

Always label this as **SIMULATED / MODEL ESTIMATE**. It is not guaranteed physical savings.

## 19. Action Center

A mature workflow:

```text
NEW → ASSIGNED → IN_PROGRESS → COMPLETED → VERIFIED
```

Example:

```text
AI detects HVAC issue
→ Admin approves
→ Engineer acts
→ System measures post-action consumption
→ EstateIQ compares before/after
→ Outcome becomes verified evidence
```

## 20. Provenance and Data Quality

Recommended states:

- OBSERVED
- SYNTHETIC
- DERIVED
- PREDICTED
- SIMULATED
- MODEL ESTIMATE
- CACHED
- NO_DATA
- INSUFFICIENT_DATA

Data quality should affect AI confidence.

Monitor:

- Missing values
- Stale sensors
- Duplicates
- Outliers
- Sensor uptime
- Timestamp synchronization
- Range violations
- Calibration age

## 21. Facility Benchmarking

Raw energy cannot fairly compare buildings.

Use:

- kWh/m²
- kWh/occupant
- kWh/operating hour
- CO₂e/m²

This allows normalized building benchmarking.

## 22. Current Repository Audit — What Is Good

Verified strengths include:

- FastAPI backend
- Central data repository
- Multiple domain generators
- Multiple ML model families
- Chronological split
- Model comparison
- Optuna XGBoost tuning
- SHAP implementation
- What-If engine
- Recommendation engine
- Provenance concepts
- Modular facility domains
- Liquid-glass frontend design system
- Tests and extensive documentation

## 23. Current Repository Audit — What Is NOT Yet Properly Implemented

### Critical A — Authentication

`src/auth/security.py` currently contains hard-coded role tokens and a default JWT secret. The login request accepts a role rather than proving identity.

**Required:** real users, Argon2id password hashing, secure access/refresh tokens, rotation/revocation, rate limiting, environment-only secrets and MFA-ready design.

### Critical B — RBAC / Object Authorization

Frontend permission hiding is not enough. Every sensitive API route must enforce authorization server-side.

Every resource must be checked against the user's facility scope to prevent BOLA/IDOR.

### Critical C — Fake fallback data

The repository contains fallback operational values such as 145.2, 50.0, 78.5, 110.5 and 580.

Replace these with:

```text
DATA AVAILABLE → real value
DATA MISSING → NO_DATA
DATA INSUFFICIENT → INSUFFICIENT_DATA
```

### Critical D — Static forecasts

Replace fixed forecast multipliers with real model inference.

### Critical E — Static Decision Trace

Replace hard-coded SHAP, forecasts, recommendations and financial assumptions with outputs from real engines.

### Critical F — Frontend static operational charts

`web/js/charts.js` contains hard-coded chart arrays. Backend/API must become the operational source of truth.

### Critical G — Frontend fail-open fallbacks

Do not show fake values after API failure. Use LOADING/SUCCESS/NO_DATA/INSUFFICIENT_DATA/ERROR/OFFLINE states.

### Critical H — GenAI labeling

The current recommendation engine is rule-based. Only show “LLM online” when a real LLM request has occurred.

### Critical I — Priority formula

Current priority includes resource effort as a positive priority component. Separate priority from execution complexity.

### Critical J — Generator documentation inconsistency

Central generator configuration defines a 365-day range, while the energy generator documentation still says 180 days. Use one authoritative duration configuration.

### Critical K — Acceptance documentation overclaims

`ACCEPTANCE_SPECIFICATION.md` claims PASS and full security/trace/365-day status, but source inspection shows unresolved contradictions. Final acceptance must be generated from actual test evidence.

### Critical L — CI/CD

The repository tree does not show a conventional `.github/workflows` CI pipeline. Add lint, tests, security/dependency scans, build checks and deployment validation.

## 24. Current-Market Features Worth Adding

Recent 2026 facility-management and energy-system trends support:

### Demand-response intelligence
Use flexible building loads to reduce/shift peaks.

### Power-quality intelligence
Monitor voltage, power factor, harmonics and imbalance.

### Predictive maintenance
Move from simple risk flags toward condition trend → maintenance priority → work order → verification.

### Operational digital twin
A useful twin is not only a 3D model. It combines:

```text
Live state
+ history
+ AI prediction
+ simulation
+ asset relationships
+ decisions
```

### Agent/tool-based Copilot
Let AI call verified EstateIQ tools instead of answering from memory.

### Carbon-aware operations
Combine electricity, DG, renewables and emission factors.

### OT/IoT cybersecurity
Device identity, secure MQTT, credential rotation, least privilege, audit logs and network-segmentation guidance.

### Human approval
AI recommends; authorized humans approve; actions are verified.

## 25. What Not to Add

Avoid:

- Fake real-time data
- Fake LLM responses
- Unsupported certifications
- “100% accurate AI”
- Unvalidated health claims
- Automatic equipment control without safety approval
- Excessive 3D/gaming effects
- Decorative features with no operational value

## 26. Recommended Teacher Demo

1. Campus overview.
2. Open Energy.
3. Select Block B.
4. Show actual vs contextual expected load.
5. Show anomaly.
6. Open SHAP drivers.
7. Show forecast.
8. Translate deviation into ₹ and CO₂e.
9. Open recommendation.
10. Run What-If with HVAC -20%.
11. Approve action.
12. Show verification.
13. Ask Copilot: “Why was Block B flagged?”

The key message:

> **This is not just a dashboard; it is a decision-intelligence loop.**

## 27. Viva Answers

**Why tree models?**  
Facility telemetry is structured/tabular. Boosted trees capture nonlinear interactions well, work with moderate data, train quickly and are explainable with SHAP.

**Why not LSTM?**  
LSTM can be valuable for large sequential datasets, but the current hackathon problem is better served by tabular boosting plus lag/rolling features. Deep sequence models can be added after sufficient real sensor history exists.

**How do you detect anomalies?**  
Compare actual usage with a contextual baseline, combine residual deviation with unsupervised anomaly detection and operating rules.

**What is SHAP?**  
A model-explanation method that estimates each feature's contribution to an individual prediction.

**Is What-If guaranteed?**  
No. It is a model-based simulation. Actual savings must be verified after implementation.

**Is the data real?**  
The prototype uses synthetic IoT-style telemetry. The architecture is designed for future real sensor integration.

**What makes EstateIQ different?**  
It connects detection → explanation → business impact → recommendation → simulation → action → verification.

## 28. Final Positioning

> **EstateIQ is an AI-powered facility decision-intelligence platform that detects operational inefficiencies, explains their causes, quantifies business impact, simulates interventions, and verifies measurable improvements.**

The dashboard is only the interface. The core innovation is the decision loop:

```text
Facility Data
→ Context
→ ML
→ Explainability
→ Business Impact
→ Decision
→ Simulation
→ Human Approval
→ Action
→ Verification
```
