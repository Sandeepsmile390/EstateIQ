# EstateIQ-DIF Jury Presentation Brief & Executive One-Pager

**Competition:** BPUT Hackathon 2026 | **Track:** Algorithm Track & Decision Intelligence Framework  
**Dataset:** `facility_dataset/data/raw/energy_readings.csv` (Synthetic Physics-Constrained) | **Sample Size:** N=426 intervals, 42 anomalies

---

## 1. The Core Comparison: EstateIQ-DIF vs Isolation Forest

```
┌──────────────────────────────────────────────┬──────────┬──────────┬───────────┬──────────────┐
│ Model Architecture                           │ F1-Score │ Recall   │ Precision │ False Alerts │
├──────────────────────────────────────────────┼──────────┼──────────┼───────────┼──────────────┤
│ 1. EstateIQ-DIF (Persistence Gated, n>=2) ★  │  0.9524  │  0.9524  │  0.9524   │ 0.45 / day   │
│ 2. Isolation Forest (Contextual Features)    │  0.7711  │  0.7619  │  0.7805   │ 2.03 / day   │
│ 3. EstateIQ-DIF (Pointwise, Thresh=55)       │  0.7000  │  1.0000  │  0.5385   │ 8.11 / day   │
│ 4. Local Outlier Factor (LOF Novelty)        │  0.6667  │  0.5476  │  0.8519   │ 0.90 / day   │
│ 5. Seasonal Gaussian Baseline (μ ± 2.5σ)     │  0.6176  │  1.0000  │  0.4468   │ 11.72 / day  │
│ 6. Isolation Forest (Univariate Energy-Only) │  0.0400  │  0.0238  │  0.1250   │ 1.58 / day   │
└──────────────────────────────────────────────┴──────────┴──────────┴───────────┴──────────────┘
```

---

## 2. What DIF Did Better vs What It Did Not Do Better

### What DIF Did Better:
1. **False Alarm Suppression:** The persistence gate (n >= 2) reduced false alarms from 8.11 down to **0.45 alerts/day** (a **94.4% reduction**), outperforming Isolation Forest (2.03 alerts/day) by a factor of 4.5x.
2. **Subtle Off-Hours Surge Detection:** DIF's 672-slot weekly median caught after-hours nocturnal waste episodes that unsupervised tree algorithms partially missed.
3. **100% Decomposable Auditability:** Every DIF alert explains its exact residual deviation, standard score (z), and triggered operating rules.

### What DIF Did Not Do Better (Honest Limitations):
1. **Raw Feature Extraction Overhead:** DIF takes ~1.2 ms per reading to compute complete facility impact, financial scenario projections, and confidence bounds, whereas Isolation Forest's pre-compiled C-tree traversals execute in ~91 µs.
2. **One-Interval Alert Latency:** Requiring n >= 2 consecutive intervals delays alert emission by exactly one 15-minute interval (15.0 min detection delay).

---

## 3. Mandatory Synthetic Data Disclosure
> ⚠️ **Jury Caveat:** The evaluated telemetry data consists of 350,400 synthetic quarter-hour intervals with two injected ground-truth fault episodes. While the benchmark protocol is strictly chronological and leakage-free, these results are preliminary and require validation on additional episodes and live physical facility telemetry.

---

## 4. Recommended 60-Second Jury Speaking Script

> *"Good afternoon, members of the jury.*  
>  
> *To rigorously validate our system, we compared our proposed **EstateIQ-DIF** algorithm against scikit-learn's **Isolation Forest**, **Local Outlier Factor**, and **Seasonal Gaussian** baselines on the same chronological held-out synthetic test set.*  
>  
> *On this 426-interval benchmark containing 42 injected anomaly intervals, **contextual Isolation Forest** achieved an F1-score of **0.7711**, catching 32 anomalies but generating 9 false alarms—averaging over 2 false alerts per day.*  
>  
> *In contrast, **EstateIQ-DIF with temporal persistence gating** achieved an F1-score of **0.9524**, catching 40 of 42 anomaly intervals while reducing false alarms to just 2 across the entire evaluation—an average of **0.45 false alerts per day**.*  
>  
> *However, we remain scientifically honest: because DIF requires two consecutive intervals to confirm a persistent fault, it introduces a 15-minute verification delay. Furthermore, because these experiments were conducted on two synthetic anomaly episodes, additional validation on live building data is essential before production deployment.*  
>  
> *All code, metrics, and figures are fully reproducible via our repository benchmark script. Thank you."*
