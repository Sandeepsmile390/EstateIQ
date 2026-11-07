# EstateIQ Generated Outputs & Publications

This directory houses compiled publication artifacts, generated PDF reports, and visual preview renders produced by the **EstateIQ** build pipelines.

---

## 📄 Output Artifacts

| Artifact | Format | Description |
|---|---|---|
| [`pdf/estateiq_elite_dif_ieee_research_paper.pdf`](pdf/estateiq_elite_dif_ieee_research_paper.pdf) | PDF (7 Pages) | Formal generic IEEE conference-style research paper draft documenting EstateIQ-DIF, mathematical formulations (1)–(25), complexity bounds, and benchmark evaluations. |
| [`pdf/estateiq_elite_algorithm_base_report.pdf`](pdf/estateiq_elite_algorithm_base_report.pdf) | PDF | Comprehensive technical baseline report detailing the algorithm inventory, formulas, and metric boundaries. |
| `pdf/pages/` & `pdf/*.png` | PNG Renders | High-resolution image renders of compiled PDF pages for visual inspection and quality assurance. |

---

## 🛠️ How to Rebuild

To regenerate the IEEE research paper PDF from the editable markdown manuscript:
```bash
python scripts/generate_ieee_paper_pdf.py
```
Or run the builder directly:
```bash
python research/ieee/build_ieee_paper.py
```
