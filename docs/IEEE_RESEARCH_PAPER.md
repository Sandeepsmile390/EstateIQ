# Elite-DIF Academic Research Paper Suite

This document indexes the formal IEEE conference-style academic paper documenting the **Elite Decision Intelligence Framework (Elite-DIF)** algorithm.

---

## 🏛️ Project & Hackathon Identification

- **Team Name**: **Elite**
- **Team ID**: **BH26PS04T039**
- **Problem Statement**: **Problem Statement-04** (Smart Campus / Institutional Facility Energy & Utility Optimization)
- **Competition Venue**: **BPUT Hackathon 2026**
- **Dates**: **12–13 November 2026**
- **Track**: Algorithm Track & Decision Intelligence Framework

---

## 📄 Manuscript & Artifact Links

- **Typeset Multi-Page PDF**: [output/pdf/estateiq_elite_dif_ieee_research_paper.pdf](../output/pdf/estateiq_elite_dif_ieee_research_paper.pdf)
- **Academic Manuscript Markdown**: [research/ieee/estateiq_elite_dif_research_paper.md](../research/ieee/estateiq_elite_dif_research_paper.md)
- **ReportLab PDF Typesetter Script**: [research/ieee/build_ieee_paper.py](../research/ieee/build_ieee_paper.py)
- **Equation Typesetter**: [research/ieee/render_equations.py](../research/ieee/render_equations.py)
- **Publication Figure Generator**: [research/ieee/generate_ieee_figures.py](../research/ieee/generate_ieee_figures.py)
- **Automated Test Suite**: [tests/test_adaptive_reporting_and_anomaly.py](../tests/test_adaptive_reporting_and_anomaly.py), [tests/test_ai_grounding_and_telemetry_contract.py](../tests/test_ai_grounding_and_telemetry_contract.py) (225 passing tests)
- **Evaluation Runner**: [elite-algorithm-package/run_evaluation.py](../elite-algorithm-package/run_evaluation.py)
- **Evaluation Results**: [elite-algorithm-package/reports/evaluation_results.json](../elite-algorithm-package/reports/evaluation_results.json)

---

## 🏛️ Paper Summary & Key Algorithmic Specifications

- **Title**: *Elite-DIF: An Interpretable Robust Seasonal-Baseline, Scale-Floored Residual Scoring, and Evidence-Fused Decision Intelligence Algorithm for Real-Time Commercial Building Anomaly Triage*
- **Format**: Formal IEEE conference draft, two-column layout, Times New Roman typography, formal Roman numeral sectioning, running headers, and page numbering.
- **Compiled Length**: 8 pages including 11 formal tables, 9 publication figures, 30 rendered display equations, and complete bibliographical references.
- **Mathematical Formulations**: 30 display equations covering:
  - Weekly slot decomposition: $s(t) = 96 \cdot d(t) + 4 \cdot h(t) + \lfloor m(t)/15 \rfloor$ (Eq 4)
  - Robust non-parametric seasonal baseline: $m_{(b,s)} = \operatorname{median}(\{y_i\})$ with 50% breakdown point (Eq 6)
  - Dispersion estimation via consistency-scaled MAD: $\sigma_{(b,s)} = \max(1.4826 \cdot \operatorname{MAD}_{(b,s)}, \rho |m_{(b,s)}|, \sigma_{\mathrm{abs}})$ with relative floor $\rho=0.05$ and absolute floor $\sigma_{\text{abs}}=0.5\text{ kWh}$ eliminating division-by-zero singularities (Eq 7–8)
  - Piecewise-linear deterministic cold-start heuristic with occupancy and temperature offsets (Eq 9–11)
  - Early-exit screening filter ($\mathcal{E}_t$) pruning ~78% of un-anomalous events (Eq 14)
  - Bounded exponential residual scoring: $C(z_t) = 100 \cdot (1 - \exp(-|z_t|/3.0))$ (Eq 15)
  - Propositional domain operating-rule evidence signal matrix: $R_t \in \{0.0, 100.0\}$ (Eq 16–19)
  - Convex evidence score fusion: $S_t = 0.80 \cdot C(z_t) + 0.20 \cdot R_t$ (Eq 20)
  - Bounded temporal persistence state machine: $n_t \ge 2$ consecutive intervals with threshold $\theta = 55.0$ and $O(1)$ LRU cache (Eq 21)
  - Continuation financial and carbon impact projections: $\Phi_{\mathrm{annual}}$ and $E_{\mathrm{annual}}$ (Eq 22–25)
  - **Dynamic Adaptive Reporting Cadence State Machine**: $\Theta_t \in \{\text{NORMAL\_15M}, \text{ANOMALY\_5M}, \text{RECOVERY\_5M}\}$ with $M=3$ hysteresis recovery cycles (Eq 26–27)
  - **Network Transmission Payload Reduction Efficiency**: $\eta_{\text{tx}} = 66.7\%$ reduction during nominal operation (Eq 28)
  - **Acoustic Sonar Thermal Compensation**: Distance $D = (v_{\text{sound}}(T) \cdot \Delta t)/2$ with deadband compensation (Eq 29)
  - **Flow Pulse Integration & Monotonic Delta Isolation**: $Q_t = (f_{\text{pulse}}/K_{\text{cal}}) \times 60$ and $\Delta y_t = \max(0, y_t - y_{t-1})$ (Eq 30)

---

## 📊 Evaluation & Empirical Benchmarks

### 1. Injected Fault Classification Benchmark (426 Test Intervals)

| Method / Architecture | Precision | Recall | F1-Score | ROC-AUC | PR-AUC | Detection Outcome |
|---|---|---|---|---|---|---|
| **Elite-DIF (Proposed)** | **0.7069** | **0.9762** | **0.8200** | **0.9846** | **0.9712** | **41 TP, 17 FP, 1 FN** |
| Seasonal Mean + Std (Gaussian) | 0.7321 | 0.9762 | 0.8367 | 0.9764 | 0.9573 | 41 TP, 15 FP, 1 FN |
| Rolling 7-Day Z-Score ($|z| \ge 3.0$) | 0.0000 | 0.0000 | 0.0000 | 0.7380 | 0.2825 | 0 TP, 0 FP, 42 FN |
| Static Historical P99 Threshold | 0.0000 | 0.0000 | 0.0000 | 0.8951 | 0.4907 | 0 TP, 0 FP, 42 FN |
| Hard Persistence-Gated ($S \ge 55 \land n \ge 2$) | **0.9512** | **0.9286** | **0.9398** | — | — | **39 TP, 2 FP, 3 FN** |

### 2. Sequential Holdout Replay Benchmark: Noise Glitch Rejection

| Evaluation Model | True Positives | False Positives | True Negatives | False Negatives | Specificity | Sensitivity | Performance Verdict |
|---|---|---|---|---|---|---|---|
| **Elite-DIF (Adaptive)** | **3** | **0** | **32** | **0** | **100.0%** | **100.0%** | **ADAPTIVE SUPERIOR SPECIFICITY** |
| Static Threshold (3.0 kW) | 3 | 1 | 31 | 0 | 96.9% | 100.0% | Trips on transient inrush glitch |

### 3. Network Payload and Reporting Cadence Analysis

| Reporting Strategy | Nominal Interval | Anomaly Interval | Reports / Day | Relative Payload | Fault Dispatch Latency |
|---|---|---|---|---|---|
| Fixed High-Frequency | 5 minutes (300 s) | 5 minutes (300 s) | 288 packets | 100.0% | $< 5\text{ minutes}$ |
| Fixed Standard AMI | 15 minutes (900 s) | 15 minutes (900 s) | 96 packets | 33.3% | Up to $15\text{ minutes}$ (Blind spot) |
| **Elite Adaptive Cadence** | **15 minutes (900 s)** | **5 minutes (300 s)** | **96–120 packets** | **33.3%–41.7%** | **Instantaneous ($< 2\text{ s}$ via edge trip)** |

---

## ⚠️ Scientific Integrity & Algorithmic Scope

1. **Simulated Telemetry Provenance**: Longitudinal multi-building energy benchmarks utilize 350,400 synthetic quarter-hour telemetry intervals across ten simulated commercial buildings over 365 days. The results rigorously demonstrate algorithmic precision, recall, and computational efficiency under controlled ground-truth conditions.
2. **Formal Algorithmic Rigor**: All mathematical derivations for 672-slot median baselining, scale-flooring, bounded exponential saturation, propositional rule matrices, convex fusion, and dynamic cadence hysteresis are documented with formal asymptotic complexity bounds ($O(1)$ single-event time and memory).
3. **Reproducibility Guarantee**: The entire algorithm and experimental benchmark suite can be re-run with exact deterministic outputs via `python elite-algorithm-package/run_evaluation.py` and `python research/ieee/build_ieee_paper.py`.
