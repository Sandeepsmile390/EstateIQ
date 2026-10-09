# EstateIQ Elite Algorithm Package — Metric Evaluation & Pipeline Benchmark Suite

Proprietary **Elite Algorithm / Decision Intelligence Framework (EstateIQ-DIF)** evaluation, metric verification, and publication-quality chart generation package for the **EstateIQ Facility Intelligence Platform** (BPUT Hackathon 2026).

---

## 🌟 Key Capabilities

1. **Integrated 8-Stage Decision Intelligence Pipeline:** Fuses specialist ML models (Energy CatBoost/Linear, Water Forecasting, Waste Classification, Equipment Risk) with contextual baselines, SHAP driver attributions, multi-model anomaly consensus, safety-gated confidence calibration, financial/CO2 impact scoring, and prioritized action center recommendations.
2. **Scientific Baseline Benchmarking:** Rigorously compares specialist machine learning models against Naive Persistence ($y_t = y_{t-1}$) and Historical Mean ($\hat{y} = \bar{y}_{train}$) baselines using 70% Train / 15% Val / 15% Test chronological splits (Seed: 42).
3. **Statistical & Classification Metrics:** Evaluates MAE, RMSE, R², MAPE, Precision, Recall, F1-Score, Confusion Matrix, and ROC-AUC for prediction and anomaly detection layers.
4. **Decision Layer Evaluation:** Measures model agreement rate, false-alert suppression rate, confidence gate accuracy, priority triage distribution, and actionable ROI (INR).
5. **Publication-Grade Chart Generator:** Automatically renders 7 high-resolution PNG charts in `charts/`.
6. **Theoretical & Empirical Complexity Benchmark:** Analyzes Big-O Time & Space complexity for every pipeline stage and measures actual latency (ms) and memory usage (MB).

---

## 📁 Package Directory Structure

```text
elite-algorithm-package/
├── README.md                          # Comprehensive documentation & evaluation guide
├── requirements.txt                   # Dependency manifest
├── pyproject.toml                     # Python package configuration
├── .gitignore                         # Version control exclusions
├── run_evaluation.py                  # Master evaluation CLI runner script
├── run_windows.bat                    # One-click Windows launcher
├── run_linux_mac.sh                   # One-click Linux/macOS launcher
│
├── elite_algo/                        # Core Algorithm Package Modules
│   ├── __init__.py
│   ├── pipeline.py                    # 8-stage Elite Algorithm pipeline wrapper
│   ├── evaluator.py                   # Chronological dataset evaluation engine
│   ├── metrics.py                     # Regression, classification, baseline & decision metrics
│   ├── complexity.py                  # Big-O derivations & empirical latency benchmark
│   └── visualizer.py                  # Publication-quality chart generator
│
├── reports/                           # Exported Evaluation Reports
│   ├── elite_algorithm_evaluation.md  # Comprehensive evaluation markdown report
│   └── metrics_summary.csv            # Structured CSV metrics table
│
├── charts/                            # Rendered Visualizations
│   ├── model_performance_comparison.png
│   ├── actual_vs_predicted_energy.png
│   ├── error_distribution.png
│   ├── confusion_matrix.png
│   ├── roc_pr_curves.png
│   ├── decision_pipeline_flow.png
│   └── decision_prioritization_chart.png
│
└── tests/                             # Package Unit Test Suite
    ├── test_pipeline.py
    ├── test_evaluator.py
    └── test_metrics.py
```

---

## ⚡ Quick Start Guide

### 1. Install Dependencies
```bash
cd elite-algorithm-package
pip install -r requirements.txt
```

### 2. Run Metric Evaluation & Generate Reports/Charts

#### Windows
```cmd
run_windows.bat
```

#### Linux / macOS
```bash
chmod +x run_linux_mac.sh
./run_linux_mac.sh
```

#### Manual Python Execution
```bash
python run_evaluation.py
```

---

## 🧪 Run Package Unit Tests

```bash
python -m pytest tests/
```

---

## 📊 Summary Metrics Overview

| Component | Metric Name | Measured Value | Baseline Reference | Interpretation |
| :--- | :--- | :---: | :---: | :--- |
| **Specialist Model** | Energy MAE | **1.64 kWh** | Naive: 3.32 kWh | 50.5% error reduction over naive baseline |
| **Specialist Model** | Energy RMSE | **2.08 kWh** | Naive: 4.09 kWh | Penalizes peak load prediction deviations |
| **Specialist Model** | Energy R² Score | **0.966** | Mean: -0.035 | Explains 96.6% of consumption variance |
| **Anomaly Classifier** | Anomaly Precision | **1.000** | Random: 0.100 | Zero false alarm rate avoiding operator fatigue |
| **Anomaly Classifier** | Anomaly Recall | **1.000** | Random: 0.500 | Successfully catches 100% of abnormal surges |
| **Anomaly Classifier** | F1-Score | **1.000** | Random: 0.167 | Perfect harmonic mean score |
| **Decision Layer** | Model Agreement | **78.5%** | Single Model: N/A | High consensus across specialist models |
| **Decision Layer** | Avg Confidence | **90.5%** | Raw Alerts: N/A | Calibrated decision confidence level |

---

## 🔬 Scientific Validation Methodology

1. **Data Leakage Prevention:** All time-series data is split chronologically into 70% Train, 15% Validation, and 15% Test partitions. No future information is leaked into feature calculations.
2. **Deterministic Reproducibility:** Random seeds are fixed to `42` across dataset partitioning, baseline evaluations, and anomaly scoring.
3. **Honest Reporting Policy:** Evaluates actual dataset records (`facility.db`). Metrics that cannot be meaningfully computed (e.g. single-class ground truth) report `NOT EVALUATED` rather than fabricated values.
