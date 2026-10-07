# 🧠 Machine Learning Pipeline Documentation

Detailed ML architecture for **Sustainable Facility and Estate Intelligence Dashboard for India**.

---

## 🛠️ Model Selection & Unified Forecasting Hierarchy

EstateIQ implements a unified forecasting model hierarchy comparing baseline and advanced algorithms on chronological validation splits:

```text
Naive Baseline
      ↓
Moving Average (24h)
      ↓
Prophet Time-Series
      ↓
XGBoost Regressor
      ↓
LightGBM Regressor
```

### Unified Forecasting Adapters (`src/models/forecasting.py`)

- **`NaiveForecastAdapter`**: Predicts historical mean or last observed value.
- **`MovingAverageForecastAdapter`**: Rolling window moving average (default 24h).
- **`ProphetForecastAdapter`**: Dedicated time-series forecasting adapter using `prophet.Prophet` with yearly, weekly, and daily seasonality decomposition.
- **`XGBoostForecastAdapter`**: Gradient boosted decision tree regressor for structured feature matrices.
- **`LightGBMForecastAdapter`**: LightGBM regressor optimized for low-latency inference.

---

## 🔬 Chronological Validation Strategy

1. **Chronological Splitting**:
   - Telemetry data is split strictly by timestamp: **70% Train, 15% Validation, 15% Test**.
   - Random shuffling is prohibited to prevent time-series lookahead bias.

2. **Feature Engineering without Target Leakage**:
   - 15-minute resolution lag features: `lag_1` (15m), `lag_4` (1h), `lag_24` (6h), `lag_96` (24h).
   - Historical rolling window statistics: `rolling_mean_4` (1-hour window shifted by 1).
   - Future target columns are generated strictly from future observations and never included in feature matrix $X$.

---

## 📊 Model Comparison Benchmarks

| Module | Evaluated Candidates | Winning Model | Metric | Winning Score | Baseline Score |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Energy Forecast** | Naive, MovingAvg, Prophet, XGBoost, LightGBM | **Moving Average / XGBoost** | RMSE | **2.93 kWh** | 46.98 kWh |
| **Water Usage** | Linear, Random Forest, XGBoost | **Linear Regression** | MAE | **2.41 L** | 38.50 L |
| **Waste Overflow** | Logistic, Random Forest, CatBoost | **Logistic Regression** | F1 Score | **0.941** | 0.00 |
| **Air Quality** | Linear, Gradient Boosting, XGBoost | **Linear Regression** | RMSE | **3.12 PM2.5** | 42.10 PM2.5 |
| **Traffic Flow** | Random Forest, LightGBM, CatBoost | **CatBoost Classifier** | F1 Score | **0.985** | 0.00 |
| **Parking Occupancy** | Linear, Gradient Boosting, XGBoost | **Gradient Boosting** | RMSE | **0.041 Ratio** | 0.38 Ratio |
| **Equipment Risk** | Logistic, Random Forest, CatBoost | **Random Forest** | F1 Score | **0.962** | 0.00 |

---

## 🔒 Safety & Non-Definitive Wording Rules

- **Water**: Uses wording *"Possible abnormal water-use pattern detected. Physical inspection may be required."*
- **Air Quality**: Describes outputs as *"environmental decision-support indicators, not official regulatory measurements."*
- **Equipment**: Uses *"maintenance-risk indicator"* (Does NOT claim equipment breakdown is proven).
- **Safety**: Uses empirical distribution analysis (Does NOT manufacture artificial causal relationships).
