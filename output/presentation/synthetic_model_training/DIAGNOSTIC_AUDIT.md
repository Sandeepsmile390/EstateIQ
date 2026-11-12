# EstateIQ Synthetic Data & Model Training: Comprehensive Diagnostic Audit

**Target Environment:** Local Windows Laptop (Intel Core Ultra 5 125H CPU)  
**Authoritative Dataset:** `facility_dataset/data/synthetic_model_training/energy_readings_model_training.csv`  
**Ground-Truth Events:** `facility_dataset/data/synthetic_model_training/ground_truth_events_model_training.csv`  
**Dataset SHA-256:** `ca70b9272a5d4ff8ee7957d76c2cffa7661d130d5f5c8daea1e013c10a0489c2`  
**Evaluation Window:** 2026-01-01 to 2026-06-30 (86,880 15-minute readings across 5 campus facilities)

---

## 1. Data Generation Architecture

The synthetic facility telemetry is generated using `src/data_generator_v2/generator_v2.py` and `src/data_generator_v2/fault_injection.py`. It simulates five distinct campus buildings:
1. **BLD001 (Academic Block A):** 45,000 sq ft, 1,200 capacity, VRF Central HVAC.
2. **BLD002 (Academic Block B):** 40,000 sq ft, 1,000 capacity, VRF Central HVAC.
3. **BLD003 (Computer Science Block):** 50,000 sq ft, 1,500 capacity, Chiller FCU HVAC (high baseline plug load).
4. **BLD004 (Administration Block):** 25,000 sq ft, 300 capacity, Split AC (strict 09:00–18:00 schedule).
5. **BLD005 (Campus Library):** 35,000 sq ft, 800 capacity, Central AHU (extended 08:00–22:00 schedule).

### Physical Principles Modeled
- **Diurnal & Weekly Cycles:** Operating schedules vary between weekdays and weekends.
- **Dynamic Occupancy:** Head count curves drive auxiliary equipment and lighting demand.
- **Ambient Weather & Seasonal Shift:** Temperature climbs from winter (12°C–25°C in Jan–Mar) to peak summer (35°C–42°C in Apr–Jun), inducing realistic seasonal thermal drift on HVAC power.
- **Measurement Noise:** Zero-mean Gaussian sensor jitter ($\sigma = 0.03 \cdot \mu$) is applied to all analog registers.

---

## 2. Telemetry Schema & Column Mapping

| Column Name | Category | Units / Type | Description | Model Input Feature? |
| :--- | :--- | :--- | :--- | :---: |
| `timestamp` | Time Index | ISO-8601 (`+05:30`) | Telemetry acquisition timestamp | Derived Features Only (`hour`, `dow`) |
| `building_id` | Identifier | String (`BLD001`–`BLD005`) | Facility entity identifier | **NO** (Used for grouping/splits) |
| `electricity_kwh` | Main Sensor | kWh (float) | Total facility electricity consumption | **YES** |
| `hvac_kwh` | Submeter | kWh (float) | Heating/ventilation/air conditioning submeter | **YES** |
| `lighting_kwh` | Submeter | kWh (float) | Indoor and perimeter lighting submeter | **YES** |
| `equipment_kwh` | Submeter | kWh (float) | Plug loads, server rooms, lab appliances | **YES** |
| `other_kwh` | Submeter | kWh (float) | Auxiliary pumps, elevators, fans | **YES** |
| `power_factor` | Power Quality | Float ($0.0 - 1.0$) | Displacement power factor | **YES** |
| `temperature_c` | Context | °C (float) | Local ambient outdoor dry-bulb temperature | **YES** |
| `occupancy_count` | Context | Integer | Estimated building occupant head count | **YES** |
| `anomaly_flag` | Target Label | Integer ($0$ or $1$) | **Authoritative Ground-Truth Binary Target** | **STRICTLY EXCLUDED (LEAKAGE)** |
| `anomaly_type` | Target Mode | String | Injected anomaly category | **STRICTLY EXCLUDED (LEAKAGE)** |
| `fault_category` | Target Class | String | `nominal`, `building_fault`, `sensor_quality_fault` | **STRICTLY EXCLUDED (LEAKAGE)** |
| `event_id` | Target Entity | String | Identifier linking to ground-truth events registry | **STRICTLY EXCLUDED (LEAKAGE)** |

---

## 3. Ground-Truth Anomaly Taxonomy & Injected Scenarios

The dataset features 15 ground-truth episodes (241 training intervals, 70 validation intervals, and 543 held-out test intervals):

### A. Operational / Equipment Faults (`building_fault`)
1. **After-Hours Energy Surge (`after_hours_surge`):** Unscheduled lighting and plug load operation during deep night hours ($2.4\times - 2.65\times$ base load).
2. **HVAC Stuck On (`hvac_stuck_on`):** Chiller or VRF contactor welded shut, consuming $+32\ \text{kW} - +40\ \text{kW}$ extra power through the night.
3. **Gradual Energy Drift (`gradual_drift`):** Slow refrigerant loss inducing progressive COP degradation up to $+55\%$ excess consumption over 72 hours.
4. **Transient Surge (`transient_surge`):** Elevator motor start or load spike ($2.8\times - 3.2\times$) lasting 15–30 minutes (1–2 intervals).
5. **Weekend Schedule Mismatch (`weekend_schedule_mismatch`):** Unbooked holiday schedule running full weekday cooling and lighting ($+25\ \text{kW} - +32\ \text{kW}$).

### B. Sensor Quality Faults (`sensor_quality_fault`)
1. **Meter Flatline (`meter_flatline`):** Submeter Modbus/RS485 register frozen at invariant reading ($6.8 - 7.2\ \text{kWh}$).
2. **Meter Dropout (`meter_dropout`):** Gateway LoRaWAN packet loss causing telemetry drop to $0.0\ \text{kWh}$ during peak campus daytime.

---

## 4. Evaluation Split Design & Leakage Prevention

To ensure strict chronological evaluation with zero data contamination:

```
[--- Train: Jan 1 – Mar 15 (74 days) ---] [--- Val: Mar 16 – Mar 31 (16 days) ---] [--- Test: Apr 1 – Jun 30 (91 days) ---]
   35,520 intervals (370 bld-days)           7,680 intervals (80 bld-days)           43,680 intervals (455 bld-days)
   241 anomaly intervals (5 events)          70 anomaly intervals (2 events)         543 anomaly intervals (8 events)
```

### Anti-Leakage Mandates:
1. **Zero Feature Leakage:** `anomaly_flag`, `anomaly_type`, `fault_category`, and `event_id` are purged from the model feature matrix $X$.
2. **Zero Preprocessing Leakage:** Scalers (`StandardScaler`) and imputers are fit exclusively on $X_{\text{train}}$. Validation and test slices are transformed using training statistics.
3. **Zero Test Tuning:** Isolation Forest contamination, Random Forest probability cutoff, and DIF decision thresholds are calibrated exclusively on the validation slice. Test data is processed once in a single forward pass.
4. **Temporal Integrity:** Out-of-order and duplicate timestamps are blocked by the online streaming ingestion pipeline.

---

## 5. False Alert Denominator & Exposure Audit

Prior benchmarks occasionally conflated **portfolio calendar days** ($91$ days) with **building-days** ($91 \times 5 = 455$ building-days). 

$$\text{Test Exposure} = \frac{43,680\ \text{total test intervals}}{96\ \text{intervals / day}} = 455.0\ \text{building-days}$$

$$\text{False Alerts per Building-Day} = \frac{\text{False Positives (FP)}}{455.0}$$

$$\text{Alerts per Portfolio Calendar Day} = \frac{\text{False Positives (FP)}}{91.0}$$

Both units are explicitly calculated, labeled, and verified in the evaluation tables.

---

## 6. Installed Environment & Toolchain

- **Python Runtime:** 3.11.0 (64-bit Windows)
- **Scikit-Learn:** 1.9.1 (Provides `RandomForestClassifier`, `IsolationForest`, `StandardScaler`, `metrics`)
- **Joblib:** 1.6.0 (Model serialization)
- **Pandas:** 3.0.5
- **NumPy:** 2.x
- **Matplotlib:** 3.10.x
- **Hardware Platform:** Intel Core Ultra 5 125H CPU (14 cores / 18 threads) — all algorithms run 100% locally on CPU without GPU or cloud dependency.

