# EstateIQ-DIF IEEE Research Draft & Experimental Artifacts

This directory contains the academic research manuscript, automated ReportLab PDF typesetting pipeline, mathematical equation renderers, publication figure generators, and extended ablation experiment runners for the **EstateIQ Decision Intelligence Framework (EstateIQ-DIF)**.

---

## Directory Overview

```
research/
├── README.md                                  # Research Suite Documentation (This Document)
└── ieee/
    ├── estateiq_elite_dif_research_paper.md   # Editable full-length generic IEEE conference draft
    ├── build_ieee_paper.py                    # Automated two-column IEEE PDF typesetter (ReportLab)
    ├── generate_ieee_figures.py               # Publication-grade vector & high-DPI figure generator
    ├── render_equations.py                    # Matplotlib-based LaTeX math glyph rasterizer
    ├── run_extended_experiments.py            # Systematic ablation & threshold sensitivity sweeps
    ├── extended_experiment_results.json       # Serialized empirical results across 426 test intervals
    ├── figures/                               # Generated high-resolution publication charts (Fig 1–8)
    └── equations/                             # Rendered LaTeX display equations (Eq 1–25)
```

---

## 📄 Manuscript Overview

- **Title:** *EstateIQ-DIF: A Robust Seasonal-Baseline and Rule-Fusion Framework for Building Energy Anomaly Triage*
- **Target Venue:** Generic IEEE Conference Draft (Placeholder - Venue template applied upon selection).
- **Format:** IEEE standard two-column format, Times New Roman typography, 7 rendered pages, formal section headers (I through VII), mathematical formulations (1)–(25), 8 publication figures, and 5 formal IEEE tables.
- **Methodology:**
  1. 672 weekly quarter-hour slot group medians for seasonal expected load.
  2. Median Absolute Deviation (MAD) scaled by 1.4826 with dual scale floors for robust dispersion.
  3. Bounded, two-sided exponential standardized residual scoring.
  4. Operating domain rules (off-peak night surge, daytime HVAC schedule mismatch, baseline ratios).
  5. Convex score fusion ($S_t = w_c \cdot C_t + w_r \cdot R_t$).
  6. Temporal persistence tracking with Least-Recently-Used (LRU) bounded cache.

---

## 🛠️ Reproduction & PDF Generation

To regenerate all figures, render all display equations, and compile the typeset PDF:

```bash
# Step 1: Execute Extended Experiments & Serialized Metrics
python research/ieee/run_extended_experiments.py

# Step 2: Render LaTeX Math Equations to Crisp Vector Images
python research/ieee/render_equations.py

# Step 3: Generate High-Resolution Publication Figures
python research/ieee/generate_ieee_figures.py

# Step 4: Typeset the Multi-Page IEEE PDF
python research/ieee/build_ieee_paper.py
```

The resulting PDF is compiled to:
`output/pdf/estateiq_elite_dif_ieee_research_paper.pdf`

---

## 🔬 Key Empirical Results (Simulated Dataset)

*Note: In accordance with scientific disclosure standards, all evaluated telemetry is synthetic. Two injected fault episodes establish internal computational validity, not real-building generalizability.*

| Configuration / Variant | Precision | Recall | F1-Score | ROC-AUC | PR-AUC | False Positive Rate |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **EstateIQ-DIF (Proposed Full Model)** | **0.7069** | **0.9762** | **0.8200** | **0.9846** | **0.9712** | **0.0443** |
| Seasonal Mean + Std (Gaussian) | 0.7321 | 0.9762 | 0.8367 | 0.9764 | 0.9573 | 0.0391 |
| Rolling 7-Day Z-Score ($|z| \ge 3.0$) | 0.0000 | 0.0000 | 0.0000 | 0.7380 | 0.2825 | 0.0000 |
| Static Historical P99 Threshold | 0.0000 | 0.0000 | 0.0000 | 0.8951 | 0.4907 | 0.0000 |
| Hard Persistence Gated ($S \ge 55 \land n \ge 2$) | 0.9512 | 0.9286 | 0.9398 | 0.9846 | 0.9712 | 0.0052 |

### Key Findings
1. **Rule Fusion Suppresses False Positives:** Removing domain rules nearly doubles false alarms from 17 to 32 (precision drops from 0.7069 to 0.5616).
2. **Persistence Filtering:** Requiring 2 consecutive interval confirmations eliminates 88.2% of transient alarms at the cost of a 15-minute confirmation delay.
3. **Held-Out Campus Generalization:** Evaluated across 5,376 clean intervals on 8 unprofiled campus buildings, persistence gating achieves a 0.04% false-alarm rate.
