# 🎯 EstateIQ Hackathon Live Storytelling Demo Guide

Step-by-step presentation script for demonstrating **EstateIQ Sustainable Facility & Estate Intelligence Platform** to hackathon judges.

---

## 🎬 13-Step Hackathon Presentation Script

### Scenario
A college campus is experiencing unusually high electricity consumption in Block B Hostel during off-peak hours.

1. **Step 1: Baseline Executive Dashboard**
   - Open `http://localhost:8000/`.
   - Point out top KPI cards (Energy 7.42 MWh, Water 12,480 kL, Waste 5,420 kg, Sustainability Score 82/100 Gold Grade).
   - Point out the **Data Provenance Badges** (`[SYNTHETIC IoT DATA]`, `[OBSERVED]`, `[ML FORECAST]`, `[SIMULATED]`).

2. **Step 2: Operational Anomaly Telemetry Ingested**
   - EstateIQ receives energy + occupancy + weather telemetry from sensor feeds.
   - Observed load in Block B Hostel reaches **145.2 kWh**.

3. **Step 3: Contextual Baseline Calculation**
   - System establishes expected contextual baseline: $f(\text{building}, \text{hour}, \text{occupancy}, \text{temp}, \text{HVAC}) = \mathbf{78.0\text{ kWh}}$.

4. **Step 4: Operational Deviation Flagged**
   - Actual consumption exceeds expected baseline by **+67.2 kWh (+86.1% Deviation)**.

5. **Step 5: ML Anomaly Detector Flags Priority 1 Surge**
   - Isolation Forest anomaly score reaches **0.88 (HIGH SEVERITY)**.
   - Priority Engine triggers **Priority 1 Alert** on header notification dropdown and alert banner.

6. **Step 6: Time-Series Forecast Predicts Continued Surge**
   - CatBoost forecast predicts 1H load at **152.5 kWh** ($\pm 8.4\%$ confidence interval).

7. **Step 7: SHAP Feature Attribution ("Why is it happening?")**
   - SHAP TreeExplainer quantifies local feature drivers: HVAC load (+42%), Occupancy (+18%), Temperature (+11%), Previous consumption (+7%).
   - *SHAP values explain model behavior. They do not prove physical causation.*

8. **Step 8: Grounded AI Action Recommendation**
   - System generates grounded recommendation: *"Reset thermostat setpoint schedule to 24.5°C in Block B Hostel. Inspect compressor cycling pattern."*

9. **Step 9: Open 11-Step Decision Trace Audit Ledger**
   - Click **Inspect Active Signals** or **View Decision Trace**.
   - Show judges the complete 11-step audit trail linking observed telemetry ➔ expected baseline ➔ deviation ➔ forecast ➔ anomaly score ➔ SHAP impact ➔ priority ➔ recommendation ➔ assumptions ➔ What-If impact ➔ action record.

10. **Step 10: Interactive What-If Operational Simulation**
    - Click **Open in What-If Simulator** or open `What-If Simulator` tab.
    - Adjust HVAC Setback slider to `-20%` and Solar PV to `150 kWp`.
    - View immediate simulation delta: Demand drops to **121.5 kWh**, saving **₹1,42,800/mo ($1,740/mo)** and **16.4 Tons CO₂e**.

11. **Step 11: Execute & Record Simulated Action**
    - Click **Apply Scenario as Active Policy**.
    - System records `SIMULATED_ACTION_RECORDED` in the audit ledger and boosts facility score (+3.5 Pts).

12. **Step 12: Grounded AI Co-Pilot Interaction**
    - Open `AI Co-Pilot` tab.
    - Ask: *"Why is energy consumption high in Block B Hostel?"*.
    - Show instant answer generated from validated structured context (works online or offline).

13. **Step 13: Data Quality Center & Multi-Horizon Controls**
    - Switch time horizon buttons (**`15 Min`**, **`1 Hour`**, **`24 Hours`**, **`7 Days`**, **`1 Month`**, **`1 Year`**).
    - Conclude demo showing live OpenAPI Swagger docs at `http://localhost:8000/docs`.
