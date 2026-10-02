# 📖 Data Dictionary & Catalog

Dataset catalog for **GEC Smart Campus IoT Dataset**.

---

## 📊 Major Database Tables (`facility.db`)

### 1. `energy_readings`
| Column | Data Type | Unit | Range | Description |
| :--- | :--- | :--- | :--- | :--- |
| `timestamp` | DATETIME | ISO8601 | 2026-01-01 to 2026-06-29 | 15-minute interval timestamp |
| `building_id` | TEXT | ID | BLD001 to BLD010 | Campus building identifier |
| `electricity_kwh` | FLOAT | kWh | $\ge 0$ | Total 15-min electricity consumption |
| `hvac_kwh` | FLOAT | kWh | $\ge 0$ | HVAC sub-meter consumption |
| `power_factor` | FLOAT | ratio | 0.70 to 1.00 | Electrical power factor |
| `renewable_generation_kwh` | FLOAT | kWh | $\ge 0$ | Rooftop solar energy generated |
| `grid_import_kwh` | FLOAT | kWh | $\ge 0$ | Net electricity drawn from grid |

### 2. `water_readings`
| Column | Data Type | Unit | Range | Description |
| :--- | :--- | :--- | :--- | :--- |
| `water_consumption_liters` | FLOAT | Liters | $\ge 0$ | Total 15-min water consumption |
| `water_flow_rate_lpm` | FLOAT | LPM | $\ge 0$ | Water flow rate in Liters Per Minute |
| `tank_level_percent` | FLOAT | % | 0.0 to 100.0 | Overhead storage tank level |

### 3. `waste_readings`
| Column | Data Type | Unit | Range | Description |
| :--- | :--- | :--- | :--- | :--- |
| `bin_id` | TEXT | ID | BIN_01 to BIN_32 | Smart bin identifier |
| `fill_level_percent` | FLOAT | % | 0.0 to 100.0 | Ultrasonic fill level percentage |
| `overflow_within_2h` | INT | binary | 0 or 1 | Target: Bin overflow within 2 hours |
| `overflow_within_4h` | INT | binary | 0 or 1 | Target: Bin overflow within 4 hours |

### 4. `air_quality_readings`
| Column | Data Type | Unit | Range | Description |
| :--- | :--- | :--- | :--- | :--- |
| `pm25` | FLOAT | $\mu g/m^3$ | $\ge 0$ | Particulate matter PM2.5 concentration |
| `pm10` | FLOAT | $\mu g/m^3$ | $\ge 0$ | Particulate matter PM10 concentration |
| `aqi` | FLOAT | index | 0 to 500 | Indian CPCB Air Quality Index proxy |

### 5. `equipment_sensor_readings`
| Column | Data Type | Unit | Range | Description |
| :--- | :--- | :--- | :--- | :--- |
| `asset_id` | TEXT | ID | AST_CHILLER_01 ... | Asset identifier |
| `temperature_c` | FLOAT | °C | 20.0 to 110.0 | Operating temperature |
| `vibration_mm_s` | FLOAT | mm/s | 0.0 to 15.0 | Vibration amplitude |
| `maintenance_risk_score` | FLOAT | score | 0.0 to 1.0 | Predictive maintenance risk score |
