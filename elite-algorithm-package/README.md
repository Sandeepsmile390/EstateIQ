# EstateIQ-DIF Python Package

This package exposes the implemented EstateIQ Decision Intelligence Framework (DIF) electricity anomaly-triage path and its evaluation tools. The core combines a seasonal median–MAD baseline, two-sided residual scoring, explicit operating rules, weighted evidence fusion, and bounded temporal persistence. It is not a trained multi-model ensemble.

## Install and use

From the repository root, install the package in editable mode:

```powershell
python -m pip install -e ".\\elite-algorithm-package"
```

Core dependencies are NumPy and pandas. Install optional evaluation and test tools with:

```powershell
python -m pip install -e ".\\elite-algorithm-package[evaluation,test]"
```

Minimal API example:

```python
from datetime import datetime, timezone
from elite_algo import DIFConfig, EstateIQDIF, EventData, SeasonalBaselineModel

# Fit only on historical training rows; never include the evaluation period.
baseline = SeasonalBaselineModel(min_observations=8).fit(training_dataframe)
detector = EstateIQDIF(config=DIFConfig(), baseline_model=baseline)

event = EventData(
    event_id="meter-1-0001",
    facility_id="campus",
    building_id="building-1",
    timestamp=datetime.now(timezone.utc).isoformat(),
    actual_kwh=24.8,
    hour=12,
    day_of_week=0,
    occupancy=35,
    temperature=25.0,
    interval_hours=0.25,
)
decision = detector.analyze(event)
print(decision.anomaly.anomaly_score, decision.anomaly.anomaly_level.value)
```

The convenience wrapper `EliteAlgorithmPipeline` returns a JSON-friendly dictionary. Its `water_flow_lmin` and `air_aqi` fields are echoed for demo compatibility and are **not analyzed** by the electricity DIF detector. The core package API accepts optional power factor in `EventData.extra_features`; other resource detectors are separate project components.

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
- `../research/ieee/estateiq_elite_dif_research_paper.md` - editable research manuscript.
- `../output/pdf/estateiq_elite_dif_ieee_research_paper.pdf` - typeset research draft.

## Method summary

For each building and UTC weekly quarter-hour slot, the fitted baseline stores the median and a robust scale `max(1.4826 * MAD, relative floor, absolute floor)`. For residual `r = actual - expected`, `z = r / max(scale, epsilon)` and contextual score `C = 100 * (1 - exp(-abs(z)/3))`. The total score is the configured weighted sum (default 80% contextual score, 20% active-rule score). It is not a probability. Per-building persistence state is bounded and updated chronologically. All event timestamps must include a timezone; the convenience wrapper normalizes them to UTC.

Complexity: expected `O(N)` fit over `N` training rows; expected `O(1)` scalar lookup/scoring per event; retained profile and persistence memory `O(S+B)` for `S` slot profiles and at most `B` tracked buildings. An optional dataframe scan is `O(NF)` for `F` columns.

## Validation limits

Bundled anomaly results use generated data and only two injected episodes. They are preliminary synthetic evidence, not proof of generalization or live-facility accuracy. The current evaluator's anomaly metrics are not a direct Isolation Forest or LOF comparison. Do not claim the algorithm is superior to those methods until they are run on the same leakage-safe split.

## IEEE publication note

The paper is a generic conference-style research draft with blank author fields. Before submission, select a venue, adopt its current template/page limit, verify references and dataset redistribution terms, and replace simulated-data evidence with an external evaluation appropriate to the claimed contribution. See the [IEEE paper structure guidance](https://conferences.ieeeauthorcenter.ieee.org/write-your-paper/structure-your-paper/) and [submission process](https://journals.ieeeauthorcenter.ieee.org/submit-your-article-for-peer-review/the-ieee-article-submission-process/).
