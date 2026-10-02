# 🧠 Machine Learning Pipeline Documentation

Detailed ML architecture for **Sustainable Facility and Estate Intelligence Dashboard**.

---

## 🛠️ Model Selection & Training Methodology

1. **Chronological Validation Strategy**:
   - Time-series data is split strictly chronologically: **70% Train, 15% Validation, 15% Test**.
   - Random shuffling is prohibited to prevent lookahead bias.

2. **Feature Engineering without Target Leakage**:
   - 15-minute resolution lag features:
     - `lag_1` (15 min ago)
     - `lag_4` (1 hour ago)
     - `lag_24` (6 hours ago)
     - `lag_96` (24 hours ago)
   - Historical rolling window averages: `rolling_mean_4` (1-hour window shifted by 1).
   - Future targets (e.g. `energy_next_1h`, `overflow_within_2h`) are computed strictly from future observations and NEVER fed as input features.

3. **Candidate Model Benchmark Results**:

| Module | Winning Model | Validation Metric | Score | Baseline Score |
| :--- | :--- | :--- | :--- | :--- |
| **Energy Consumption** | Linear Regression | RMSE | **2.934 kWh** | 46.98 kWh |
| **Water Usage** | Linear Regression | MAE | **2.41 Liters** | 38.50 Liters |
| **Waste Overflow (2h)** | Logistic Regression | F1 Score | **0.941** | 0.00 |
| **Air Quality (PM2.5)** | Linear Regression | RMSE | **3.12 $\mu g/m^3$** | 42.10 $\mu g/m^3$ |
| **Traffic Congestion** | CatBoost Classifier | F1 Score | **0.985** | 0.00 |
| **Parking Occupancy** | Gradient Boosting | RMSE | **0.041 Ratio** | 0.38 Ratio |
| **Equipment Risk** | Random Forest | F1 Score | **0.962** | 0.00 |

---

## 🔒 Safety & Non-Definitive Wording Rules

- **Water**: Uses wording *"Possible abnormal water-use pattern detected. Physical inspection may be required."* (Does NOT claim a pipe leak is proven).
- **Air Quality**: Describes outputs as *"environmental decision-support indicators, not official regulatory measurements."*
- **Equipment**: Uses *"maintenance-risk indicator"* (Does NOT claim equipment will definitely fail).
- **Safety**: Uses empirical distribution analysis (Does NOT manufacture artificial causal relationships).
