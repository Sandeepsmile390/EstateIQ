# 🏢 GEC Smart Campus Multi-Module Facility Intelligence IoT Dataset

A production-quality synthetic IoT dataset generator for **GEC Smart Campus** covering 180 days (Jan 01, 2026 to June 29, 2026) at 15-minute intervals (17,280 timestamps per series).

---

## 📌 Dataset Overview

1. **What the dataset represents**:
   - Telemetry from 10 buildings, 35 equipment assets, 32 waste bins, 4 parking zones, 6 traffic locations, and 7 air quality sensor nodes across an engineering college campus in India.
2. **Why it is synthetic**:
   - Built to demonstrate end-to-end data engineering, dashboard visualization, ML forecasting, anomaly detection, SHAP explainability, and What-If simulation without requiring live hardware connection during hackathons.
3. **Reproducibility**:
   - Uses a deterministic seed `SEED = 42`. Running `python generator/main.py` twice generates 100% identical CSVs and SQLite database.

---

## 🏗️ Directory Structure

```
facility_dataset/
│
├── generator/
│   ├── main.py                  # Master orchestrator script
│   ├── config.py                # SEED = 42, time range, paths, logging
│   ├── facility_generator.py    # Generates facilities, buildings, locations, assets
│   ├── weather_generator.py     # 15-min weather readings (temp, humidity, solar, rain)
│   ├── occupancy_generator.py   # 15-min building occupancy by profile
│   ├── energy_generator.py      # Energy consumption & sub-meters physics
│   ├── water_generator.py       # Water consumption & tank levels
│   ├── waste_generator.py       # Bin fill trajectories & overflow targets
│   ├── air_quality_generator.py # PM2.5, PM10, AQI & pollutant readings
│   ├── traffic_generator.py     # Campus traffic & vehicle fleet mix
│   ├── parking_generator.py     # Parking zone occupancy ratios
│   ├── equipment_generator.py   # Asset sensor telemetry & maintenance wear
│   ├── safety_generator.py      # Sparse safety incident logs
│   ├── emissions_generator.py   # Scope 1 & 2 GHG CO2e estimates
│   ├── event_generator.py      # Campus calendar (exams, sports, rain, heatwaves)
│   ├── anomaly_generator.py    # Injects ground-truth anomaly scenarios
│   ├── ml_dataset_generator.py # Builds ML lag features & future targets
│   └── validator.py             # Data bounds validation & quality reports
│
├── config/
│   ├── facility_config.json     # Campus metadata, building profiles, zones
│   ├── anomalies.json           # Ground-truth anomaly injection scenarios
│   ├── scoring_weights.json     # Sustainability score weight profile
│   └── emission_factors.json    # CEA India & IPCC carbon conversion constants
│
├── data/
│   ├── raw/                     # Raw 15-minute IoT sensor CSVs
│   ├── processed/               # Cleaned & joined multi-sensor streams
│   └── ml/                      # ML-ready datasets with lags and targets
│
├── reports/
│   ├── validation_report.json   # Physical bounds & row count checks
│   ├── data_quality_report.csv  # Missing rates & duplicate timestamp audits
│   └── generator.log            # Execution log
│
├── facility.db                  # SQLite Database containing all tables
├── data_dictionary.csv          # Catalog of columns, data types, units, ranges
├── requirements.txt
└── README.md
```

---

## 🔗 Connected Domain Physics Relationships

The generator enforces strict cross-module physical dependencies:

```text
Outdoor Temperature ↑ ──► HVAC Load ↑ ──► Electricity kWh ↑ ──► CO2e Emissions ↑
Building Occupancy ↑  ──► Sub-meter Energy ↑ ──► Water Consumption ↑ ──► Waste Fill Rate ↑
Campus Gate Traffic ↑ ──► Parking Occupancy ↑ ──► Gate PM2.5 / AQI ↑
Operating Hours ↑     ──► Asset Vibration & Temperature ↑ ──► Maintenance Risk Score ↑
Rainfall ↑            ──► Traffic Speed ↓ ──► Washout of PM2.5 / PM10 ↓
```

---

## 🎯 Target Leakage Prevention in ML Datasets

In `data/ml/`, features and target variables are strictly separated:
- **Historical Features**: Use strictly past lag observations (`lag_1`, `lag_4` [1h], `lag_24` [6h], `lag_96` [24h]) and historical rolling averages (`rolling_mean_4`).
- **Future Targets**:
  - `energy_next_1h`: Energy consumption 1 hour into the future.
  - `overflow_within_2h`: Bin overflow flag within next 2 hours.
  - `overflow_within_4h`: Bin overflow flag within next 4 hours.
  - `failure_within_24h`: Maintenance requirement flag within next 24 hours.
- 🔒 **Ground Truth Anomaly Labels** (`anomaly_flag`, `anomaly_type`) exist **ONLY** for model evaluation and are never fed as input features during training.

---

## ⚡ How to Regenerate & Run

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Dataset Generator
```bash
python generator/main.py
```

---

## 🔌 Connecting Real IoT Sensor Data Later

To transition from synthetic prototype data to live IoT deployment:
1. Replace `generator/` raw CSV writers with an MQTT / Kafka subscriber service.
2. Ingest sensor payloads directly into the SQLite database `facility.db` or PostgreSQL.
3. Keep the same schema in `data_dictionary.csv` to ensure downstream ML pipelines (`api/main.py` and `dashboard_app.py`) work without code changes!
