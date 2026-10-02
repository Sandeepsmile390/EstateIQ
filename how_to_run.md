# 🚀 EstateIQ — Comprehensive Run & Demonstration Guide

### Step 1: Open Terminal & Navigate to Project Root
Open PowerShell, Command Prompt, or your IDE terminal and ensure you are in the project folder:
```bash
cd d:\Hackathon\Model
```

### Step 2: Install Required Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Initialize Database & Generate IoT Telemetry Data
Initialize the SQLite database (`facility.db`) and generate 180 days of realistic multi-module IoT sensor telemetry:
```bash
python scripts/setup_database.py
```
*(Creates `facility_dataset/facility.db` containing 16 indexed domain tables).*

### Step 4: Train & Register Machine Learning Models
Train all 9 domain ML models (Energy, Water, Waste, Air Quality, Traffic, Parking, Equipment Maintenance, Safety, and Carbon Emissions):
```bash
python train_all_modules.py
```
*(Builds and serializes joblib model artifacts into the `models/` directory).*

### Step 5: Verify Models & View Performance Metrics
Run the evaluation audit script to verify trained models and export performance metrics:
```bash
python scripts/evaluate_models.py
```
*(Generates `reports/model_metrics.csv` and `reports/model_metrics.json`).*

### Step 6: Run Automated Integration Tests
Verify that all 29 automated unit and pipeline integration tests pass:
```bash
python -m unittest discover tests
```
*(Output: `Ran 29 tests in 0.31s ... OK (29/29 PASSED)`).*

---

### Step 7: Launch Applications

#### 🌐 Option A: FastAPI Web App & Liquid Glass Dashboard (Main UI)
```bash
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```
- **Main Web Application**: `http://localhost:8000/`
- **Interactive OpenAPI/Swagger Docs**: `http://localhost:8000/docs`

#### 📊 Option B: Streamlit Operational Intelligence Dashboard
Open a second terminal window and run:
```bash
streamlit run app.py --server.port 8501
```
- **Streamlit Dashboard**: `http://localhost:8501/`

---

### 🌐 How to Explore Features & Demonstrate EstateIQ

1. **Dashboard Overview (`http://localhost:8000/`)**:
   - High-level facility metrics, total energy (kWh), water recovery, waste diversion, and the **Sustainability Score (82/100 Gold Grade)**.
   - **Data Provenance Badges**: Tagged as `[SYNTHETIC IoT DATA]`, `[OBSERVED]`, `[ML FORECAST]`, and `[SIMULATED]`.

2. **11-Step Decision Trace Audit Ledger**:
   - Click **Inspect Active Signals** or **View Decision Trace** on any alert card.
   - Inspect the complete 11-step audit trail: Observed Data ➔ Expected Baseline ➔ Deviation (+86.1%) ➔ ML Forecast ➔ Anomaly Score ➔ SHAP Attribution ➔ Priority Score ➔ Grounded Recommendation ➔ Assumptions ➔ What-If Impact ➔ Recorded Action.

3. **Multi-Horizon Time Controls**:
   - Switch between **`15 Min`**, **`1 Hour`**, **`24 Hours`**, **`7 Days`**, **`1 Month`**, and **`1 Year`** views across Energy, Water, Waste, Mobility, Air Quality, and Equipment health tabs.

4. **Interactive What-If Scenario Simulator**:
   - Adjust operational sliders (HVAC Setback, Solar PV kWp, Greywater %, Tariff rate) and view real-time target load curves, cost savings in **₹ Lakhs/mo**, and CO₂e reductions.

5. **Grounded AI Co-Pilot**:
   - Ask queries like *"Why is energy consumption high in Block B Hostel?"* or *"Which waste bins will overflow?"*. Operates with LLM API or deterministic offline fallback.

6. **Role-Based Access Control (RBAC)**:
   - Switch active session roles using the header avatar menu (**RS Administrator**, **Alex Chen - Operations Engineer**, **Dr. Priya Sharma - ESG Auditor**, **Sam Taylor - Viewer**).