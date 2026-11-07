# EstateIQ-DIF Evaluation Package

This package documents and evaluates the implemented EstateIQ Decision Intelligence Framework (DIF) path. “Elite” is the project name; the evaluated core is a robust seasonal contextual baseline, a two-sided residual score, operating-rule fusion, and bounded temporal persistence.

## Evidence and scope

The bundled source telemetry is generated/simulated. There are 350,400 quarter-hour readings for ten buildings and 42 injected anomalous records in two episodes. Reported anomaly metrics are point-wise results on two generated episodes, not estimates of real-facility performance. Forecast scores are from a 7-day seasonal-naive reference and simple comparators, not a fitted Elite forecasting model. Water, waste, independent decision accuracy, calibration, causal savings, and external validation are **not evaluated**.

The report deliberately does not claim that this code path executes CatBoost, XGBoost, LightGBM, Prophet, Isolation Forest, LOF, SHAP, calibrated uncertainty, or a trained optimization model. The optional fitted profile is `SeasonalBaselineModel`; the default DIF path can use a labeled heuristic cold-start baseline if no fitted artifact is supplied.

## Reproduce

From the repository root:

```powershell
python elite-algorithm-package/run_evaluation.py
```

To fit an inspectable profile, provide a timezone-aware cutoff explicitly:

```powershell
python elite-algorithm-package/train_dif_baseline.py --train-through 2026-10-31T23:45:00+05:30 --output models/dif_seasonal_baseline.json
```

The profile trainer reads only timestamp, building, and energy fields. Review the cutoff and dataset provenance before using the resulting artifact.

## Outputs

- `reports/evaluation_report.md` - evaluation protocol, results, complexity and benchmark notes.
- `reports/evaluation_results.json` - machine-readable metrics and provenance.
- `reports/metrics_summary.csv` - metric summary.
- `charts/*.svg` - generated forecast, confusion-matrix, ROC/PR, and pipeline figures.
- `../research/ieee/estateiq_elite_dif_research_paper.md` - editable generic IEEE-style manuscript.
- `../output/pdf/estateiq_elite_dif_ieee_research_paper.pdf` - typeset research draft.

## Method summary

For each building and weekly quarter-hour slot, the fitted baseline stores the median and a robust scale `max(1.4826 * MAD, relative floor, absolute floor)`. For residual `r = actual - expected`, `z = r / max(scale, epsilon)` and contextual score `C = 100 * (1 - exp(-abs(z)/3))`. The total score is the configured weighted sum of contextual score and a binary active-rule score. It is not a probability. Per-building persistence state is bounded and updated chronologically.

Complexity: expected `O(N)` fit over `N` training rows; expected `O(1)` scalar lookup/scoring per event; retained profile and persistence memory `O(S+B)` for `S` slot profiles and at most `B` tracked buildings. An optional dataframe scan is `O(NF)` for `F` columns.

## IEEE publication note

The paper is a generic conference-style research draft with blank author fields. Before submission, select a venue, adopt its current template/page limit, verify references and dataset redistribution terms, and replace simulated-data evidence with an external evaluation appropriate to the claimed contribution. See the [IEEE paper structure guidance](https://conferences.ieeeauthorcenter.ieee.org/write-your-paper/structure-your-paper/) and [submission process](https://journals.ieeeauthorcenter.ieee.org/submit-your-article-for-peer-review/the-ieee-article-submission-process/).
