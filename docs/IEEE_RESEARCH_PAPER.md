# EstateIQ-DIF Academic Research Paper Suite

This document indexes the formal IEEE conference-style academic paper documenting the **EstateIQ Decision Intelligence Framework (DIF)**.

---

## 📄 Manuscript & Artifact Links

- **Typeset Multi-Page PDF**: [output/pdf/estateiq_elite_dif_ieee_research_paper.pdf](../output/pdf/estateiq_elite_dif_ieee_research_paper.pdf)
- **Editable Academic Manuscript**: [research/ieee/estateiq_elite_dif_research_paper.md](../research/ieee/estateiq_elite_dif_research_paper.md)
- **Research Suite Guide**: [research/README.md](../research/README.md)
- **ReportLab PDF Typesetter Script**: [research/ieee/build_ieee_paper.py](../research/ieee/build_ieee_paper.py)
- **Publication Figure Generator**: [research/ieee/generate_ieee_figures.py](../research/ieee/generate_ieee_figures.py)
- **Evaluation Runner**: [elite-algorithm-package/run_evaluation.py](../elite-algorithm-package/run_evaluation.py)
- **Evaluation Results**: [elite-algorithm-package/reports/evaluation_results.json](../elite-algorithm-package/reports/evaluation_results.json)

---

## 🏛️ Paper Summary & Key Specifications

- **Title**: *EstateIQ-DIF: Robust Seasonal-Baseline and Rule-Fusion Framework for Scalable Building Energy Anomaly Triage*
- **Format**: Generic IEEE conference draft, two-column layout, Times New Roman typography, formal Roman numeral sectioning, running headers, and page numbering.
- **Compiled Length**: 7 pages including extended ablation tables, mathematical formulations, and bibliographical references.
- **Mathematical Formulations**: 25 display equations covering:
  - Weekly slot decomposition: $s(t) = 96 \cdot d(t) + q(t)$
  - Robust seasonal baseline: $\mu_s = \operatorname{median}(\{y_{i,s}\})$ and $\sigma_s = \max(1.4826 \cdot \operatorname{MAD}_s, \sigma_{\min})$
  - Residual score: $r_t = y_t - \mu_{s(t)}$, $z_t = r_t / \sigma_{s(t)}$, $S_c(t) = 100 \cdot (1 - \exp(-|z_t|/3))$
  - Operating rule fusion: $S_r(t) = \max_k \{R_k(t) \cdot \omega_k\}$
  - Composite anomaly score: $S_{\text{DIF}}(t) = w_c \cdot S_c(t) + w_r \cdot S_r(t)$ with $w_c = 0.8, w_r = 0.2$
  - Bounded temporal persistence: consecutive interval confirmation count $k_t \ge 2$ with threshold $\tau = 55.0$.
  - Algorithmic time and memory complexity bounds: $O(1)$ per-interval inference, $O(N)$ profile training, bounded $O(B)$ memory.

---

## 📊 Evaluation & Benchmarking

The manuscript benchmarks EstateIQ-DIF against standard statistical baselines across 426 evaluated test intervals (including two ground-truth anomalous episodes totaling 42 anomalous records):

| Method / Architecture | Precision | Recall | F1-Score | ROC-AUC | PR-AUC |
|---|---|---|---|---|---|
| **EstateIQ-DIF (Proposed)** | **0.7069** | **0.9762** | **0.8200** | **0.9846** | **0.9712** |
| Seasonal Mean + Std (Gaussian) | 0.7321 | 0.9762 | 0.8367 | 0.9764 | 0.9573 |
| Rolling 7-Day Z-Score ($z \ge 3.0$) | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.7380 |
| Static Historical P99 Threshold | 0.0000 | 0.0000 | 0.0000 | 0.8951 | 0.4907 |
| Hard Persistence-Gated ($S \ge 55 \wedge n \ge 2$) | **0.9512** | **0.9286** | **0.9398** | — | — |

---

## ⚠️ Scientific Integrity & Venue Disclosure

1. **Simulated Telemetry Provenance**: Telemetry utilized in this evaluation is synthetically generated across ten simulated campus buildings. The results demonstrate algorithmic precision, recall, and computational efficiency under controlled conditions; they do not establish real-world building triage accuracy on uncalibrated physical sensors.
2. **Generic Draft**: This manuscript is intentionally prepared as a generic conference draft with anonymized author placeholders. Before formal submission, select a target IEEE conference venue, format into the venue's official LaTeX/Word template, and evaluate prospective real-world facility deployments.
