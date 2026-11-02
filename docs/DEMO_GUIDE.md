# 🎯 EstateIQ Hackathon Final Round Live Demo Guide

**Sustainable Facility & Estate Intelligence Platform (Problem Statement PS-04)**

This guide provides the exact 4–5 minute rehearsal script for the core local demo journey defined in `EstateIQ_Final_Round_Implementation_Report.pdf`:

> **Core Demo Journey:**
> **Load or generate data ➔ inspect data quality ➔ view facility trends ➔ detect an evidence-backed alert ➔ forecast or simulate a change ➔ record an action ➔ export a scoped report.**

The core demo runs 100% locally and offline without external AI, cloud services, or physical sensors.

---

## ⏱️ 4.5-Minute Scripted Timeline (Table 12)

| Time | Presenter Action | Evaluator Observed Output |
|---|---|---|
| **0:00 - 0:30** | Introduce college campus (`COLLEGE_01`), 14 zones, and source labels | Configurable facility context; clear `[SYNTHETIC IoT]` and `[CSV IMPORT]` provenance tags |
| **0:30 - 1:00** | Open Overview: point to Energy, Water, AQI, Waste KPIs and Data Quality banner | Operational KPIs, trend lines, timestamp freshness, and data-quality status |
| **1:00 - 1:45** | Open known Energy Spike alert in `BLOCK_B` | Alert has severity (`CRITICAL`), observed value (145.2 kWh), baseline (78.0 kWh), +86.1% deviation, and next action |
| **1:45 - 2:15** | Show 24-hour Energy Forecast and evaluation assumptions | 24-hour hourly horizon, seasonal-naive comparator, chronological holdout MAE/RMSE |
| **2:15 - 2:45** | Adjust energy reduction slider in What-If Simulator | Proportional scenario calculation (₹9.50/kWh tariff), baseline vs scenario delta, and `"Estimate, not verified savings"` label |
| **2:45 - 3:15** | Open Water overnight leak or Waste overflow; accept/assign recommendation | Multi-domain reuse; alert status transitions (`ACKNOWLEDGED` ➔ `ASSIGNED`), notes, and audit record persist |
| **3:15 - 3:45** | Export scoped CSV readings & printable summary report | Report strictly scoped to `COLLEGE_01`, selected zone/date range, with provenance labels and data limits |
| **3:45 - 4:15** | Demonstrate server-side RBAC enforcement | Operations user blocked with `403 Forbidden` on admin-only endpoints; UI hiding is not the only gate |
| **4:15 - 4:30** | Conclude with honest limitations & scaling roadmap | Clear boundary between synthetic prototype insight and official verified utility measurements |

---

## 🚀 Step-by-Step Execution Guide

### Pre-Demo Preparation (1 Command)
```bash
# Seed deterministic test data with known anomalies
python scripts/seed_demo_data.py
```
This seeds:
- Facility: `COLLEGE_01` (GEC Smart Campus)
- 14 campus zones (Academic blocks, hostels, canteen, library, utility)
- 1,680 canonical hourly readings across 14 days
- 4 deterministic injected anomalies:
  1. **Energy Surge**: `BLOCK_B` at 145.2 kWh (+86.1% over 78.0 kWh baseline).
  2. **Water Leak**: `BLOCK_B` at 380 L/hr during closed hours (00:00–05:00).
  3. **Waste Overflow**: `CANTEEN` bin at 94% fill with projection < 1 hour.
  4. **Air Quality Spike**: `BLOCK_A` PM2.5 at 142.5 µg/m³.

---

### Step 1: Start Applications
```bash
# Terminal 1: FastAPI REST Backend
uvicorn api.main:app --host 127.0.0.1 --port 8000

# Terminal 2: Streamlit Multipage Command Center
streamlit run app.py --server.port 8501
```
Open **`http://localhost:8501`** in your browser.

---

### Step 2: Inspect Facility Overview & Quality Banner
1. In the sidebar, verify Facility is set to **`GEC Smart Campus (COLLEGE_01)`**.
2. Point to the **Data Quality & Provenance Banner**:
   - Total readings: `1,680`
   - Quality State: `100% VALID` (or shows suspect/stale counts)
   - Source: `[SYNTHETIC IoT DATA]` clearly marked.
3. Observe the top KPI tiles:
   - Energy Consumption (kWh)
   - Water Usage (L)
   - Waste Generated (kg / % Fill)
   - Prototype Sustainability Scorecard (Gold Grade, operational indicator).

---

### Step 3: CSV Import & Column Mapping Validation
1. Click the **`CSV Import & Data Quality`** tab.
2. Click **Download Sample CSV Template** to demonstrate the canonical schema.
3. Test uploading a custom or malformed file:
   - Evaluator sees the first 20 rows previewed with automatic column name inference.
   - Row-by-row validation shows exact line numbers and rejection causes (e.g. invalid timestamps, impossible negative values, unknown zones).
   - Duplicate prevention stops re-importing identical timestamps.
   - Batch ID is logged with single-click rollback capability.

---

### Step 4: Evidence-Backed Anomaly Alerts
1. Navigate to the **`Alerts & Actions Center`** tab (or click **⚡ Run Anomaly Analysis** in the sidebar).
2. Click on the top Critical Alert:
   - **Entity**: `BLOCK_B` (Hostel)
   - **Observed Value**: `145.2 kWh`
   - **Baseline / Threshold**: `78.0 kWh` (+86.1% deviation)
   - **Severity**: `CRITICAL`
   - **Evidence**: 14-day rolling hour-of-week median with Median Absolute Deviation (MAD).
   - **Recommended Action**: *"Inspect HVAC/compressor scheduling in Block B Hostel."*

---

### Step 5: Short-Term Forecast & What-If Scenario Simulation
1. Navigate to the **`Energy & What-If Simulator`** tab.
2. View the 24-hour hourly energy forecast:
   - Demonstrates chronological train/test holdout validation.
   - Compares model performance with deterministic seasonal-naive baseline.
   - If historical data is limited or external ML is disabled, seasonal-naive fallback operates automatically without crashing.
3. Test the What-If simulation:
   - Move the **Assumed Energy Reduction** slider to `15%`.
   - Set Tariff: `₹9.50/kWh`.
   - View instant recalculated baseline vs scenario delta: `150 kWh` reduction, saving `₹1,425`.
   - Point out the mandatory disclaimer: *"Estimate, not verified savings"*.

---

### Step 6: Persistent Action Workflow & Audit History
1. In the Alerts tab, select the `BLOCK_B` alert.
2. Update its state:
   - Change Status to **`IN_PROGRESS`**
   - Assign to: `tech`
   - Set Due Date: Tomorrow
   - Add Operator Note: *"Facilities team dispatched to check chiller setpoints."*
3. Click **Update Alert Status**.
4. Refresh browser or restart the app:
   - The state, assignee, note, and timestamps persist in SQLite.
   - An immutable record appears in `audit_events`.

---

### Step 7: Export Scoped Report
1. Click the **`Reports & Scoped Exports`** tab.
2. Choose Scope:
   - Facility: `COLLEGE_01`
   - Zone: `BLOCK_B`
   - Metric: `energy_kwh`
3. Click **Download Filtered CSV**:
   - Contains only matching records without leaking other facilities or zones.
4. Click **Printable Summary Report**:
   - Generates clean, printer-friendly summary report with KPIs, data quality metrics, model evaluation, and limitations statement.

---

### Step 8: Server-Side RBAC Verification
1. Log in or query API as operations role (`tech`):
   - Attempting `POST /admin/demo/reset` or updating facility thresholds returns `403 Forbidden`.
   - Demonstrates backend authorization rather than client-side cosmetic button hiding.

---

## 🔄 Emergency Reset Procedure
If at any point during presentation you want to restore the system to the clean demo state:
```bash
python scripts/reset_demo.py
```
This wipes transient modifications and re-seeds the exact deterministic benchmark dataset.
