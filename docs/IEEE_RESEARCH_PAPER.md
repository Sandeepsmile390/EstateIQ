# EstateIQ-DIF Academic Research Paper Suite

This document indexes the formal IEEE conference-style academic paper documenting the **EstateIQ Decision Intelligence Framework (EstateIQ-DIF)**.

---

## 📄 Manuscript & Artifact Links

- **Typeset Multi-Page PDF**: [output/pdf/estateiq_elite_dif_ieee_research_paper.pdf](../output/pdf/estateiq_elite_dif_ieee_research_paper.pdf)
- **Editable Academic Manuscript**: [research/ieee/estateiq_elite_dif_research_paper.md](../research/ieee/estateiq_elite_dif_research_paper.md)
- **Research Suite Guide**: [research/README.md](../research/README.md)
- **ReportLab PDF Typesetter Script**: [research/ieee/build_ieee_paper.py](../research/ieee/build_ieee_paper.py)
- **Equation Typesetter**: [research/ieee/render_equations.py](../research/ieee/render_equations.py)
- **Publication Figure Generator**: [research/ieee/generate_ieee_figures.py](../research/ieee/generate_ieee_figures.py)
- **Automated Test Suite**: [tests/test_adaptive_reporting_and_anomaly.py](../tests/test_adaptive_reporting_and_anomaly.py), [tests/test_ai_grounding_and_telemetry_contract.py](../tests/test_ai_grounding_and_telemetry_contract.py) (225 passing tests)
- **Evaluation Runner**: [elite-algorithm-package/run_evaluation.py](../elite-algorithm-package/run_evaluation.py)
- **Evaluation Results**: [elite-algorithm-package/reports/evaluation_results.json](../elite-algorithm-package/reports/evaluation_results.json)

---

## 🏛️ Paper Summary & Key Specifications

- **Title**: *EstateIQ-DIF: An Adaptive Multi-Modal Telemetry and Robust Statistical Decision Framework for Real-Time Commercial Building Anomaly Triage*
- **Format**: Generic IEEE conference draft, two-column layout, Times New Roman typography, formal Roman numeral sectioning, running headers, and page numbering.
- **Compiled Length**: 8 pages including 11 formal tables, 9 publication figures, 30 rendered display equations, and complete bibliographical references.
- **Mathematical Formulations**: 30 display equations covering:
  - Weekly slot decomposition: $s(t) = 96 \cdot d(t) + q(t)$ (Eq 4)
  - Robust seasonal baseline: $\mu_s = \operatorname{median}(\{y_{i,s}\})$ and $\sigma_s = \max(1.4826 \cdot \operatorname{MAD}_s, \rho |m_s|, \sigma_{\mathrm{abs}})$ (Eq 6–8)
  - Bounded exponential residual scoring: $C(z_t) = 100 \cdot (1 - \exp(-|z_t|/3.0))$ (Eq 15)
  - Domain operating-rule fusion: $S_t = 0.80 \cdot C(z_t) + 0.20 \cdot R_t$ (Eq 16–20)
  - Bounded temporal persistence tracking: $n_t \ge 2$ consecutive intervals with threshold $\theta = 55.0$ (Eq 21)
  - Continuation financial and carbon impact projections: $\Phi_{\mathrm{annual}}$ and $E_{\mathrm{annual}}$ (Eq 22–25)
  - **Adaptive Telemetry Reporting Cadence State Machine**: $\Theta_t \in \{\text{NORMAL\_15M}, \text{ANOMALY\_5M}, \text{RECOVERY\_5M}\}$ with $M=3$ hysteresis recovery cycles (Eq 26–27)
  - **Network Transmission Payload Reduction Efficiency**: $\eta_{\text{tx}} = 66.7\%$ reduction during nominal operation (Eq 28)
  - **Ultrasonic Acoustic Tank Metrology**: Distance $D = (v_{\text{sound}} \cdot \Delta t)/2$ with acoustic deadband compensation (Eq 29)
  - **Resistive Voltage Divider Scaling**: $V_{\text{ADC}} = V_{\text{sensor}} \times \frac{R_2}{R_1 + R_2} = 3.00\text{ V} \le 3.30\text{ V}$ protecting ESP32 ADC (Eq 30)

---

## 📊 Evaluation & Empirical Benchmarks

### 1. Injected Fault Classification Benchmark (426 Test Intervals)

| Method / Architecture | Precision | Recall | F1-Score | ROC-AUC | PR-AUC | Detection Outcome |
|---|---|---|---|---|---|---|
| **EstateIQ-DIF (Proposed)** | **0.7069** | **0.9762** | **0.8200** | **0.9846** | **0.9712** | **41 TP, 17 FP, 1 FN** |
| Seasonal Mean + Std (Gaussian) | 0.7321 | 0.9762 | 0.8367 | 0.9764 | 0.9573 | 41 TP, 15 FP, 1 FN |
| Rolling 7-Day Z-Score ($|z| \ge 3.0$) | 0.0000 | 0.0000 | 0.0000 | 0.7380 | 0.2825 | 0 TP, 0 FP, 42 FN |
| Static Historical P99 Threshold | 0.0000 | 0.0000 | 0.0000 | 0.8951 | 0.4907 | 0 TP, 0 FP, 42 FN |
| Hard Persistence-Gated ($S \ge 55 \land n \ge 2$) | **0.9512** | **0.9286** | **0.9398** | — | — | **39 TP, 2 FP, 3 FN** |

### 2. Sequential Holdout Replay Benchmark: Noise Glitch Rejection

| Evaluation Model | True Positives | False Positives | True Negatives | False Negatives | Specificity | Sensitivity | Performance Verdict |
|---|---|---|---|---|---|---|---|
| **EstateIQ-DIF (Adaptive)** | **3** | **0** | **32** | **0** | **100.0%** | **100.0%** | **ADAPTIVE SUPERIOR SPECIFICITY** |
| Static Threshold (3.0 kW) | 3 | 1 | 31 | 0 | 96.9% | 100.0% | Trips on transient inrush glitch |

### 3. Network Payload and Reporting Cadence Analysis

| Reporting Strategy | Nominal Interval | Anomaly Interval | Reports / Day | Relative Payload | Fault Dispatch Latency |
|---|---|---|---|---|---|
| Fixed High-Frequency | 5 minutes (300 s) | 5 minutes (300 s) | 288 packets | 100.0% | $< 5\text{ minutes}$ |
| Fixed Standard AMI | 15 minutes (900 s) | 15 minutes (900 s) | 96 packets | 33.3% | Up to $15\text{ minutes}$ (Blind spot) |
| **EstateIQ Adaptive Cadence** | **15 minutes (900 s)** | **5 minutes (300 s)** | **96–120 packets** | **33.3%–41.7%** | **Instantaneous ($< 2\text{ s}$ via edge trip)** |

---

## ⚠️ Scientific Integrity & Venue Disclosure

1. **Simulated Telemetry Provenance**: Longitudinal multi-building energy benchmarks utilize synthetic telemetry across ten simulated commercial buildings. The results demonstrate algorithmic precision, recall, and computational efficiency under controlled conditions.
2. **Physical Hardware Validation**: Physical edge gateway firmware (`hardware/esp32/firmware/main.ino`) has been engineered and validated on dual-core ESP32 hardware using Modbus RTU electrical submeters, acoustic fluid sonars, Hall flow turbines, and analog gas sensors.
3. **Metrological Honesty**: Revenue-grade electrical submeters (PZEM Class 1.0) and calibrated flow turbine pulses are classified as metrologically verified measurements. In contrast, MQ-135 readings are recorded as indicative raw ADC voltage counts (`mq135_raw_adc`) reflecting relative air quality trends, and are not presented as certified laboratory $\text{CO}_2$ or $\text{AQI}$ concentrations.
4. **Generic Research Draft**: This manuscript is intentionally prepared as a generic conference draft with anonymized author placeholders. Before formal submission, select a target IEEE conference venue (e.g., IEEE SmartGridComm, IEEE ISGT, or IEEE CASE), format into the venue's official template, and evaluate prospective real-world facility deployments.
