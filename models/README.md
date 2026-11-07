# EstateIQ Machine Learning Models & Saved Artifacts

This directory houses trained machine learning models, baseline statistical profiles, and serialization metadata for the **EstateIQ Facility Decision Intelligence Platform**.

---

## 📦 Model Artifacts Inventory

### 1. Robust Seasonal Baseline Model (`dif_baseline.json`)
- **Format**: JSON serialized dictionary.
- **Role**: Core baseline model for the EstateIQ Decision Intelligence Framework (DIF).
- **Structure**: Stores robust median ($\mu_s$) and median absolute deviation scale ($\sigma_s = \max(1.4826 \cdot \text{MAD}_s, \sigma_{\min})$) across 672 weekly quarter-hour slots for 10 campus buildings.
- **Evaluation**: Benchmarked in `elite-algorithm-package/` and typeset in the IEEE conference draft (`research/ieee/estateiq_elite_dif_research_paper.md`).

### 2. Time-Series Forecasters
- `forecast_best_model.joblib`: Best performing energy forecasting model artifact.
- `forecast_metadata.joblib`: Hyperparameters, train/validation split cutoffs, and validation metrics (MAE, RMSE, MAPE).
- `energy_consumption_model.joblib` & `energy_kwh_prediction_model.joblib`: Tabular regression models for hourly and 15-minute campus energy consumption.

### 3. Multi-Utility Domain Models
- **Water Consumption**: `water_usage_forecasting_model.joblib` & metadata.
- **Air Quality**: `air_pm25_prediction_model.joblib` (predicts PM2.5 concentrations and EPA AQI categories).
- **Waste Management**: `waste_overflow_2hr_model.joblib` (2-hour predictive waste bin overflow classifier).
- **Emissions & ESG**: `emissions_forecasting_model.joblib` (predicts Scope 1 and Scope 2 GHG $\text{CO}_2\text{e}$ emissions).
- **Equipment & Maintenance**: `equipment_maintenance_risk_model.joblib` (evaluates asset wear and maintenance risk scores).
- **Campus Mobility**: `parking_occupancy_forecasting_model.joblib` & `traffic_congestion_class_model.joblib`.

### 4. Model Registry (`model_registry.json`)
The central model registry catalogs model identifiers, algorithms (Random Forest, CatBoost, XGBoost, LightGBM, Prophet), feature lists, target variables, and performance evaluation summaries.

---

## 🛠️ Retraining & Fitting Profiles

### To fit a new seasonal baseline profile:
```bash
python elite-algorithm-package/train_dif_baseline.py \
  --train-through 2026-10-31T23:45:00+05:30 \
  --output models/dif_baseline.json
```

### To retrain domain ML models:
```bash
python scripts/train_models.py
```
