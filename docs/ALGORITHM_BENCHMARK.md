# ⚡ EstateIQ-DIF Algorithm Benchmark Suite & Scientific Evaluation Guide

**Application Entry Point:** `benchmark_app.py`  
**Command:** `streamlit run benchmark_app.py --server.port 8503`  
**Evaluation Target:** EstateIQ Dynamic Intelligence Fusion (EstateIQ-DIF) against reference baselines  
**Dataset Provenance:** `facility_dataset/data/raw/energy_readings.csv` (Physics-Constrained Synthetic Dataset)  

---

## 1. Overview & Purpose

The **EstateIQ Algorithm Benchmark Suite** is a dedicated evaluation platform designed for the BPUT Hackathon and scientific auditing. It compares the real **EstateIQ-DIF** engine against standard statistical and time-series baselines on the project's canonical energy dataset.

The application rigorously separates:
1. **Energy Load Forecasting** (Regression task evaluated on continuous chronological horizons)
2. **Anomaly Classification** (Imbalanced event detection task evaluated on ground-truth labeled intervals)
3. **Computational Complexity** (Theoretical Big-O asymptotic derivations versus empirical latency/throughput measurements)

---

## 2. Dataset Provenance & Integrity

### Primary Dataset
* **Path:** `facility_dataset/data/raw/energy_readings.csv`
* **Provenance Badge:** `[SYNTHETIC DATA — PHYSICS CONSTRAINED]`
* **Total Rows:** `350,400` quarter-hourly intervals (365 days × 24 hours × 4 intervals/hr × 10 buildings)
* **Monitored Buildings:** `BLD001` through `BLD010`
* **Sampling Interval:** `15 minutes` (96 intervals per building per day)
* **Ground-Truth Anomaly Labels:** 42 positive intervals (`anomaly_flag = 1`) across 2 documented episodes:
  * **Episode 1 (`BLD003`):** 25 intervals of `hvac_fault` on 2026-02-15 from 11:00 to 17:00 UTC+05:30.
  * **Episode 2 (`BLD001`):** 17 intervals of `after_hours_usage` on 2026-03-22 from 01:00 to 05:00 UTC+05:30.
* **Class Imbalance:** Anomalies constitute `0.012%` of the dataset.

> [!IMPORTANT]
> All bundled facility telemetry is generated under physics constraints with injected anomalies for audit backtesting. It is **not** measured production telemetry, and empirical metrics reflect synthetic benchmark evaluation.

---

## 3. Evaluated Algorithms

### A. Energy Forecasting Algorithms
1. **7-Day Seasonal-Naive Reference (Lag 672):**
   * *Horizon:* 15-minute intervals.
   * *Mechanism:* Predicts the matching time slot from exactly 7 days prior ($y_t = y_{t - 672}$).
2. **Previous-Interval Persistence (Lag 1):**
   * *Mechanism:* Predicts the immediately prior interval reading ($y_t = y_{t-1}$).
3. **Training-Set Historical Mean:**
   * *Mechanism:* Static benchmark predicting the scalar mean of the training set ($y_t = \bar{y}_{\text{train}}$).
4. **EstateIQ Seasonal Baseline Profile (`SeasonalBaselineModel`):**
   * *Mechanism:* Learns building-specific median and MAD scale parameters for each day-of-week and 15-minute slot strictly from training history.

### B. Anomaly Detection Algorithms
1. **EstateIQ-DIF (Pointwise, Default Threshold = 55/100):**
   * *Implementation:* Uses `src/intelligence/dif_engine.py` with `SeasonalBaselineModel`.
   * *Mechanism:* Normalized two-sided contextual residual ($80\%$ weight) combined with domain rule evaluation ($20\%$ weight). Flags an anomaly when composite score $\ge 55.0$.
2. **EstateIQ-DIF (Persistence-Gated, $n \ge 2$):**
   * *Mechanism:* Requires sustained elevated score ($\ge 55.0$) over 2 or more consecutive chronological intervals within the 60-minute window. Filters out single-interval transient noise.
3. **Seasonal Gaussian Baseline ($\mu \pm 2.5\sigma$):**
   * *Mechanism:* Standardized slot-wise distance based on training mean and standard deviation per weekday slot.
4. **Rolling 7-Day Z-Score ($z \ge 3.0$):**
   * *Mechanism:* Moving window mean and standard deviation over preceding 672 steps ($z = |y_t - \mu_{7d}| / \sigma_{7d}$).
5. **Static Historical Percentile (P99):**
   * *Mechanism:* Flags readings exceeding the 99th percentile of the training distribution.
6. **EstateIQ-DIF Ablations:**
   * *Residual-Only:* Contextual residual weight = $1.0$, Domain rules weight = $0.0$.
   * *Domain-Rules-Only:* Domain rules weight = $1.0$, Contextual residual weight = $0.0$.

---

## 4. Evaluated Metrics & Formulas

### Forecasting Regression Metrics
* **MAE (Mean Absolute Error):** $\frac{1}{N} \sum_{i=1}^N |y_i - \hat{y}_i|$ (kWh)
* **RMSE (Root Mean Squared Error):** $\sqrt{\frac{1}{N} \sum_{i=1}^N (y_i - \hat{y}_i)^2}$ (kWh)
* **$R^2$ Score (Coefficient of Determination):** $1 - \frac{\sum (y_i - \hat{y}_i)^2}{\sum (y_i - \bar{y})^2}$
* **Safe MAPE (Mean Absolute Percentage Error):**
  $$\text{MAPE} = \frac{100\%}{|S_{\ge 0.5}|} \sum_{i \in S_{\ge 0.5}} \left|\frac{y_i - \hat{y}_i}{y_i}\right|$$
  *Near-zero actual values ($< 0.5$ kWh) are explicitly filtered from the percentage denominator to avoid division distortion.*
* **Max Absolute Error:** $\max |y_i - \hat{y}_i|$ (kWh)

### Anomaly Classification Metrics
* **Confusion Matrix:** True Positives (TP), False Positives (FP), True Negatives (TN), False Negatives (FN).
* **Precision:** $\frac{\text{TP}}{\text{TP} + \text{FP}}$ *(Avoids false alarm fatigue)*
* **Recall (Sensitivity):** $\frac{\text{TP}}{\text{TP} + \text{FN}}$ *(Ensures critical surges are caught)*
* **Specificity:** $\frac{\text{TN}}{\text{TN} + \text{FP}}$
* **Balanced Accuracy:** $\frac{\text{Recall} + \text{Specificity}}{2}$
* **F1-Score:** $2 \cdot \frac{\text{Precision} \cdot \text{Recall}}{\text{Precision} + \text{Recall}}$
* **False Positive Rate (FPR):** $\frac{\text{FP}}{\text{FP} + \text{TN}} = 1 - \text{Specificity}$
* **ROC-AUC:** Area under the Receiver Operating Characteristic curve via Mann–Whitney $U$ rank statistic.
* **PR-AUC (Average Precision):** Stepwise area under the Precision-Recall curve.
* **Event-Level Detection Rate:** Proportion of contiguous anomaly episodes with $\ge 1$ true positive alert.
* **Mean Detection Delay:** Average elapsed time from episode onset to first alert.

> [!NOTE]
> Because anomalies represent only $\approx 0.01\%$ of intervals, **Precision, Recall, F1-Score, and PR-AUC** are the primary metrics. Raw accuracy is uninformative (a dummy model predicting all-zero achieves $> 99.9\%$ raw accuracy).

---

## 5. Theoretical Big-O vs Empirical Runtime

| Algorithm | Stage | Fit Time Complexity | Online Scoring Complexity | State Space Complexity | Working Memory | Key Code Assumptions |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **EstateIQ-DIF (Complete)** | Dynamic Intelligence Fusion | $O(N)$ expected | **$O(1)$ expected** | $O(S + B)$ | $O(1)$ | Hash lookup in $S=6720$ slot profiles. Fast Path A early exits for $\approx 85\%$ of normal telemetry. State bounded by capacity $B=10000$. |
| **Seasonal Baseline Profile** | Grouped Median/MAD | $O(N)$ expected | **$O(1)$ expected** | $O(S)$ | $O(1)$ | Grouped median across $N$ training rows; $O(1)$ dictionary key lookup. |
| **7-Day Seasonal Naive** | Lag-672 Buffer Shift | $O(1)$ (No fitting) | **$O(1)$** | $O(W)$ | $O(1)$ | Direct array offset lookup `vals[t - 672]` from rolling FIFO buffer ($W=672$). |
| **Previous Persistence** | Single-step Persistence | $O(1)$ (No fitting) | **$O(1)$** | $O(1)$ | $O(1)$ | Stores prior scalar observation $y_{t-1}$. |
| **Seasonal Gaussian** | Parametric Slot Stats | $O(N)$ | **$O(1)$ expected** | $O(S)$ | $O(1)$ | Slot-wise mean and variance hash map lookup. |
| **Rolling 7-Day Z-Score** | Moving Window Z-Score | $O(1)$ | **$O(1)$ to $O(W)$** | $O(W)$ | $O(W)$ | Sliding window buffer of $W=672$ elements. |
| **Static Percentile P99** | Order Statistic | $O(N \log N)$ or $O(N)$ | **$O(1)$** | $O(1)$ | $O(1)$ | Single scalar comparison against training P99 threshold. |

### Scientific Rigor Notice
Theoretical Big-O describes asymptotic scaling as $N \to \infty$. Empirical latency measures wall-clock execution on a specific CPU architecture, subject to Python GIL dispatch, CPU cache lines, and OS thread scheduling. **One empirical runtime measurement must never be presented as proof of asymptotic time complexity.**

---

## 6. How to Run the Benchmark App

### Step 1: Start the Streamlit Application
```powershell
# Windows (PowerShell)
streamlit run benchmark_app.py --server.port 8503
```
Open **[http://localhost:8503](http://localhost:8503)** in your web browser.

### Step 2: Running Automated Unit & Regression Tests
```powershell
# Run the complete benchmark test suite:
pytest tests/test_benchmark_app.py -v
```

### Step 3: Exporting Results
* Navigate to **Tab 5 ("Reproducibility & Export")**.
* Download `estateiq_benchmark_config.json` containing the exact dataset SHA-256 fingerprint, hyperparameters, and environment specs.
* Download `estateiq_forecasting_metrics.csv` and `estateiq_anomaly_metrics.csv`.

