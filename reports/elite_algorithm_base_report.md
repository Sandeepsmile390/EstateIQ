# EstateIQ Elite Algorithm: Base Technical Report

**Review date:** 2 November 2026  
**Scope:** Static review of the EstateIQ project and `elite-algorithm-package`; no tests or benchmarks were run for this report.  
**Purpose:** Describe the current algorithm accurately, explain how it fits into EstateIQ, assess the credibility of its evaluation, and define the work needed to make it a defensible algorithmic contribution.

## 1. Executive summary

“Elite Algorithm” is the product name used for EstateIQ’s decision-intelligence pipeline. The core implementation is `EstateIQDIF` in `src/intelligence/dif_engine.py`. The package in `elite-algorithm-package/` is primarily a wrapper, evaluator, metrics library, chart generator, and complexity benchmark around that engine.

The useful design idea is a layered decision workflow: validate quality, screen against an expected baseline, score anomalous behavior, estimate confidence and impact, assign priority, and propose a next action. It is explainable at the rule/evidence level and returns typed results. However, the checked-in live implementation is not currently a learned multi-model ensemble in several claimed stages:

- The adaptive ensemble uses fixed RMSE values and algebraically transforms the contextual estimate; it does not call the named XGBoost, LightGBM, CatBoost, or Prophet models.
- “Isolation Forest” and “LOF” anomaly scores are threshold-derived proxies, not outputs from those detectors.
- The critical-path SHAP values are fixed example values, not computed per-event explanations.
- The safety-gate module is not called by `EstateIQDIF.analyze`; confidence is used in the decision engine, but that is not the same as checking all safety requirements.
- The evaluation package creates model predictions and anomaly labels/scores from random formulas, including predictions derived directly from test targets. These results cannot establish generalization or real-world accuracy.

Therefore the strongest accurate description today is: **a deterministic, rule-driven decision-intelligence prototype with a contextual heuristic, proxy anomaly fusion, confidence/impact/priority logic, and recommendation output, accompanied by an evaluation harness whose current metrics are not valid evidence for deployed model accuracy.** This is still a reasonable foundation. It needs clearer separation between implemented rules, real model inference, and illustrative/demo values.

### At-a-glance algorithm inventory

The answer to “how many algorithms does EstateIQ include?” depends on what is being counted. These counts must not be added together: they describe different layers.

| Inventory level | Count | What is actually present |
|---|---:|---|
| Named Elite decision algorithm | **1** | EstateIQ-DIF, orchestrated by `src/intelligence/dif_engine.py` and called by the Elite package wrapper. |
| Decision stages in the current DIF execution path | **12** | Quality check, contextual baseline/early exit, execution-path selection, prediction/ensemble, anomaly fusion, confidence, impact, risk, opportunity, decision/priority, selective explanation, and recommendation ranking. The fast path skips several downstream stages. |
| Domain model pipelines in `src/models/` | **9** | Air, emissions, energy, equipment, parking, safety, traffic, waste, and water. These are separate product capabilities, not nine models run for every Elite decision. |
| Candidate estimators in `src/models/selector.py` | **7 regression / 6 classification** | Each list includes its naive baseline. The chosen candidates differ by task; this is not a single 13-model ensemble. |
| Actual scikit-learn anomaly detector classes in `src/anomaly/detector.py` | **2** | Isolation Forest and Local Outlier Factor are implemented as separate detector options, but the core EAC path currently uses threshold-based proxy values instead of calling them. |
| Named ensemble challengers in the Elite wrapper | **4** | XGBoost, LightGBM, CatBoost, and Prophet are named, but predictions are generated from arithmetic transforms of the contextual estimate in the current `EstateIQAdaptiveEnsemble`; these are not live model inferences. |

**What the Elite algorithm makes:** for each energy event it returns a contextual expected value and deviation, a rule/proxy anomaly score and severity, a deterministic confidence score, estimated cost/carbon impact, a risk/priority decision, and a ranked advisory recommendation. The wrapper also returns water-flow and AQI values in its telemetry payload, but the current DIF decision path does not perform water or air anomaly analysis from those fields.

## 2. Where the Elite algorithm sits in the project

The overall project contains multiple related but distinct layers:

1. **Data and ingestion:** facility datasets, generated data, repository access, canonical telemetry normalization, device registry, MQTT consumer, and simulators.
2. **Domain prediction models:** modules under `src/models/` for energy, water, waste, air, traffic, parking, equipment, safety, and emissions. Training utilities and model artifacts are separate from the live DIF decision engine.
3. **General anomaly tools:** `src/anomaly/detector.py` implements scikit-learn Isolation Forest and Local Outlier Factor fitting for a supplied dataframe.
4. **DIF decision engine:** `src/intelligence/dif_engine.py` composes quality assessment, context filtering, adaptive-ensemble interface, anomaly scoring, confidence, business impact, risk, opportunities, prioritization, and recommendations.
5. **Applications:** FastAPI endpoints and Streamlit/web dashboards expose many analytics and decision features.
6. **Elite package:** wraps the DIF engine for event evaluation and contains a separate benchmark/report-generation path.

An important boundary: the existence of trained specialist models elsewhere in `src/models/` does not mean `EstateIQDIF` is using those models. The live link must be demonstrated in code and in the evaluation path before metrics can be attributed to the Elite pipeline.

## 3. Current event-processing algorithm

The main method accepts an `EventData` record with identifiers, a timestamp string, `actual_kwh`, hour/day, occupancy, temperature, HVAC load, and optional extra features. The `elite_algo` package’s wrapper supplies defaults for many inputs, calls `EstateIQDIF.analyze`, and converts the typed result into a dictionary.

The engine’s effective sequence is:

1. **Quality assessment.** If a non-empty telemetry dataframe is supplied, `DataQualityEngine` scores it. If none is supplied, the engine assigns fixed values (94 quality, 98 completeness, 99 freshness, 92 consistency, 90 sensor reliability). Low quality returns a restricted “insufficient data” result.
2. **Context filter / early exit.** `EstateIQContextFilter` estimates energy using a fixed formula based on hour, occupancy, and temperature. The current `DIFConfig` default early-exit threshold is 15%, although some project documentation says 10%; align that discrepancy. Events inside the threshold return a fast-path result and skip later stages.
3. **Execution path selection.** Otherwise it chooses a critical path when deviation exceeds 25% or energy exceeds 180; other deviations use the intelligence path.
4. **Prediction interface.** `EstateIQAdaptiveEnsemble` constructs a champion estimate from the contextual expected value and residual. Critical events get three algebraically generated challenger values. Fixed RMSE metadata produces weights.
5. **Anomaly consensus.** It combines a contextual deviation score, two deviation-derived proxy scores labeled Isolation Forest and LOF, and domain-rule score. It increments a per-building consecutive-event counter and maps score/persistence to an anomaly level.
6. **Confidence.** It combines quality, the computed agreement percentage, a default 365-day history assumption, fixed 95% completeness, and sensor reliability using configured weights.
7. **Business impact and risk.** Positive excess energy is multiplied by configured tariff and carbon factors, then annualized. Risk combines anomaly and annualized cost.
8. **Opportunity and decision priority.** It creates a fixed HVAC opportunity, then scores priority from weighted anomaly/context/impact/risk/opportunity terms and confidence.
9. **Explanation.** The critical path returns a fixed list of SHAP-like feature values; non-critical events skip attribution.
10. **Recommendation.** It creates one fixed HVAC recommendation with prewritten “why” and “why not” text and ranks the candidate list.

### Core formulas implemented by the current DIF path

Let $h$ be hour, $o$ occupancy, $T$ temperature in Celsius, $y$ observed energy, and $\epsilon$ the configured small denominator guard.

1. **Contextual expected energy (heuristic)**

   $$
   B = 45 + H(h) + 0.12o + 2.5\max(0,T-24),\qquad
   H(h)=\begin{cases}35,&8\le h\le18\\15,&\text{otherwise}\end{cases}
   $$

   $$
   r=y-B,\qquad d=100\frac{r}{\max(|B|,\epsilon)},\qquad
   s_c=\min(100,\max(0,2|d|))
   $$

   The nominal spread estimate is `0.08B`. The code’s contextual score uses `2|d|`, while the anomaly-consensus contextual component below uses `2.5|d|`.

2. **Adaptive ensemble interface (not live estimator inference)**

   $$
   \hat y_{champ}=B+0.85r
   $$

   For the critical path, challenger values are fixed multiples of the champion: LightGBM (`0.98 × champion`), CatBoost (`1.02 × champion`), Prophet (`0.95 × champion`). For each named model `i`, the code calculates

   $$
   q_i=\frac{1}{RMSE_i+10^{-4}},\qquad w_i=\frac{q_i}{\sum_jq_j},\qquad
   \hat y=\sum_iw_i\hat y_i
   $$

   These weights use hard-coded RMSE metadata; the prediction values above are derived from `B` and `r`, not output by fitted XGBoost/LightGBM/CatBoost/Prophet artifacts.

3. **Anomaly fusion**

   $$
   s_{ctx}=\min(100,2.5|d|)
   $$

   The current proxy score `s_IF` is 88 when `d > 15`, 65 when `d > 10`, and 15 otherwise; `s_LOF = min(100, 0.9 × s_IF)`. The rule score is 90 if any configured off-peak surge, temperature/HVAC mismatch, or `PF < 0.82` rule fires, and 10 otherwise.

   $$
   s_A=0.35s_{ctx}+0.25s_{IF}+0.20s_{LOF}+0.20s_{rule}
   $$

   Raw anomaly is `s_A ≥ 40`. Consecutive raw anomalies are counted per building in process memory. Severity thresholds are: <20 NORMAL, 20–<40 LOW, 40–<60 MODERATE, 60–<80 HIGH, and ≥80 CRITICAL only when persistence is at least two; otherwise the ≥80 result is HIGH. “Agreement” is the fraction of those four component scores that are at least 40. Since IF and LOF are proxies derived from the same deviation, this is not independent detector/model consensus.

4. **Confidence score (weighted heuristic)**

   $$
   C=0.25Q+0.25A+0.20H_c+0.15F+0.15S
   $$

   `Q` is quality, `A` is the component-threshold agreement percentage, `H_c = min(100, 100 × days/365)` historical coverage, `F` completeness, and `S` sensor reliability. In the current default event path, quality values are hard-coded to 94/98/99/92/90, history defaults to 365 days, and feature completeness to 95. Thus this is a deterministic score, not a calibrated probability of correctness.

5. **Impact, risk, and priority**

   $$
   e=\max(0,y-B),\quad cost_{hour}=e\cdot tariff,\quad
   cost_{day}=24\cdot cost_{hour},\quad cost_{30d}=30\cdot cost_{day}
   $$

   Default tariff is ₹9.50/kWh; annual cost is twelve times the 30-day estimate. Carbon uses `e × 0.82` kg per assumed hour, then scales to 24 hours/day and 365 days/year.

   $$
   risk=\min(100,0.6s_A+annualCost/10{,}000)
   $$

   The decision score is the configured weighted sum:

   $$
   D=0.20s_{context}+0.30s_A+0.15s_{forecastDev}+0.15s_{impact}+0.10risk+0.10s_{opportunity}
   $$

   Here `s_forecastDev = min(100, 2|d|)`, `s_impact = min(100, 100 × annualCost/500,000)`, and the current opportunity score defaults to 65. Priority thresholds are `D ≥ 75` plus high confidence for P1; `D ≥ 55` for P2; `D ≥ 35` for P3; otherwise P4.

6. **Recommendation utility**

   For candidate `j`, benefits are normalized against the maximum candidate values in that invocation:

   $$
   U_j=\max(0,40\frac{saving_j}{maxSaving}+20\frac{CO2_j}{maxCO2}+20\frac{confidence_j}{100}
   -effortPenalty_j-riskPenalty_j-10\frac{implementationCost_j}{maxCost})
   $$

   The current DIF supplies one fixed HVAC candidate; with one candidate, sorting does not create a meaningful comparative ranking.

**Unit/assumption caveat:** `actual_kwh` is not associated with an interval in `EventData`, but the impact engine treats the excess as an hourly rate and annualizes it as if it persisted continuously. Until input interval is explicit and impacts use interval energy/power consistently, 7-day/30-day/annual values must be labeled as scenario estimates, not measured losses or savings.

### Algorithmic complexity of code that currently executes

Use `N` for rows in an optional telemetry dataframe, `F` for its columns/features, `M ≤ 4` for named ensemble entries, `R` for recommendation candidates, and `B` for the number of buildings stored in persistence state. These are asymptotic bounds for the code path, not benchmark claims.

| Executed stage | Time | Additional space | Reason / qualification |
|---|---:|---:|---|
| Quality evaluation when dataframe supplied | $O(NF)$ typical | $O(NF)$ at worst, implementation-dependent | Data-quality calculations scan the provided data; absent/empty dataframe uses fixed defaults in $O(1)$. |
| Context heuristic and path selection | $O(1)$ | $O(1)$ | Fixed number of scalar operations. |
| Current ensemble arithmetic | $O(M)$ | $O(M)$ | At most four hard-coded predictions/weights; no tree traversal occurs in this path. With fixed $M\le4$, this is $O(1)$. |
| Proxy anomaly fusion and persistence lookup | $O(1)$ expected | $O(1)$ per call; $O(B)$ retained state | Constant signals and dictionary operations; state grows with distinct building IDs. |
| Confidence, impact, risk, decision scoring | $O(1)$ | $O(1)$ | Fixed number of scalar calculations. |
| SHAP-like output currently returned | $O(1)$ | $O(1)$ | A fixed list of four example entries is constructed; TreeSHAP is not executed here. |
| Recommendation ranking | $O(R\log R)$ | $O(R)$ | Sorting candidate recommendations; current DIF gives one, so this is effectively constant. |
| **Total per event** | **$O(NF+R\log R)$** with a dataframe; **$O(1)$** without one for current fixed $M$ | **$O(NF+R+B)$** worst-case including input/retained state; **$O(B)$** incremental persistent state without dataframe | This bound describes the implementation today. It must not be replaced with theoretical costs for models that are only named in metadata. |

The separate trained tree models have their own fit/inference complexity, but they are not part of the `EstateIQDIF.analyze` execution path reviewed here. The package’s manually listed $O(MT)$, detector $O(KN)$, and TreeSHAP $O(MF^2)$ values are therefore not valid descriptions of the current per-event Elite implementation.

### Accuracy and metrics: what can be reported today

There is no defensible single “Elite accuracy” value in the repository. EstateIQ-DIF produces anomaly severity, a confidence score, a decision priority, and advisory recommendations; the current package does not measure those outputs against a valid independent test set with ground-truth decisions. Confidence is a weighted score, not accuracy. R² belongs to regression forecasting, and F1/precision/recall belong to classification; they cannot be merged into one accuracy figure.

The model registry contains the following task-level results, labeled as **reported synthetic-data metrics**. They are not Elite-DIF end-to-end accuracy and were not independently reproduced for this report:

| Task | Registry-reported algorithm | Reported metric(s) | Interpretation / caveat |
|---|---|---|---|
| Energy forecast | Linear Regression | MAE 2.3851 kWh; RMSE 3.002 kWh; R² 0.9966 | Regression error/fit on the registered synthetic dataset; not an anomaly accuracy score. |
| Water forecast | Linear Regression | MAE 7.8545 L; RMSE 9.8889 L; R² 0.9997 | Synthetic task metric; unusually high fit requires independent validation before generalization claims. |
| Waste overflow | Logistic Regression | Precision 1.000; recall 0.997; F1 0.9985; ROC-AUC 1.000 | Synthetic classification result; not the Elite EAC anomaly score. |
| Air PM2.5 | Linear Regression | MAE 1.7804; RMSE 2.2177; R² 0.9770 | Registry metric; units/dataset and test design should accompany publication. |
| Traffic congestion | CatBoost | Precision 0.9848; recall 0.9701; F1 0.9774; ROC-AUC 0.999 | Synthetic classification result. |
| Parking occupancy | Gradient Boosting | MAE 0.1281; RMSE 0.1689; R² 0.6852 | Weaker fit; registry MAPE is extremely large because near-zero targets make MAPE unstable. |
| Equipment risk | Random Forest | Precision/recall/F1/ROC-AUC all 1.000 | Perfect synthetic result should trigger a label/feature leakage audit; not real-world evidence. |
| Emissions forecast | Linear Regression | MAE 4.1666; RMSE 5.1936; R² 0.9885 | Synthetic task metric; not attributable to Elite-DIF as a whole. |

Separately, the Elite package evaluator has invalid headline evaluation paths: forecast predictions are produced as test targets plus random noise; anomaly labels are randomly assigned and then anomaly scores are generated from those same labels; waste outcomes and predictions both threshold the same fill-level values. Consequently, even a perfect-looking accuracy/F1/AUC from that evaluator is a property of the constructed toy example, not evidence that the deployed Elite algorithm generalizes. The repository’s aggregate model numbers should be published only with dataset fingerprint, sample count, exact time/site split, model artifact version, baseline comparison, and a reproducible evaluation run.

For reference, the standard metrics have distinct meanings and formulas. Let $y_i$ be the true numeric value, $\hat y_i$ its forecast, and $N$ the sample count. For classification, $TP$, $FP$, $TN$, and $FN$ are true positives, false positives, true negatives, and false negatives:

| Metric | Formula | Use / caution |
|---|---|---|
| MAE | $\frac{1}{N}\sum_i |y_i-\hat y_i|$ | Average absolute forecast error, in the target’s units. |
| RMSE | $\sqrt{\frac{1}{N}\sum_i(y_i-\hat y_i)^2}$ | Penalizes larger forecast errors; same units as the target. |
| R² | $1-\frac{\sum_i(y_i-\hat y_i)^2}{\sum_i(y_i-\bar y)^2}$ | Relative fit to the test-set mean; can be negative and is not classification accuracy. |
| Accuracy | $\frac{TP+TN}{TP+TN+FP+FN}$ | Can look high when normal events dominate; do not use alone for anomaly detection. |
| Precision | $\frac{TP}{TP+FP}$ | Of flagged anomalies, the fraction that are true anomalies. |
| Recall | $\frac{TP}{TP+FN}$ | Of true anomalies, the fraction detected. |
| F1 | $2\frac{Precision\cdot Recall}{Precision+Recall}$ | Harmonic mean of precision and recall; computed at a defined decision threshold. |
| ROC-AUC | Area under the ROC curve (TPR vs. FPR over thresholds) | Ranking metric; can look optimistic with severe class imbalance. Include PR-AUC and the confusion matrix for rare anomalies. |

The Elite engine’s current **confidence** field is not one of these metrics. It is an uncalibrated score generated at inference time, whereas accuracy/precision/recall/F1 require independent labels and predictions.

**Metrics to report after correcting evaluation:** forecasting MAE, RMSE, and R² against identical chronological test timestamps and seasonal-naive/persistence baselines; anomaly confusion matrix, precision, recall, F1, PR-AUC/ROC-AUC (where appropriate), false-positive rate per device-day, and detection delay on untouched labels; calibration error if confidence is meant to estimate probability; and decision-level operator acceptance/verification rates only when those outcomes are actually recorded.

The package README calls this an eight-stage process, while the live DIF implementation has more internal steps and the wrapper itself only delegates to the DIF engine. The report should use one canonical stage diagram tied to current code.

## 4. Stage-by-stage implementation assessment

| Stage | Current behavior | Assessment |
|---|---|---|
| Data quality | Real dataframe scoring only when passed; otherwise optimistic fixed defaults. | Useful gate concept, but default confidence is not evidence-based. Wire the actual sample’s freshness, completeness, and sensor status into every event. |
| Contextual expectation | Fixed heuristic: base + time-of-day HVAC factor + occupancy + temperature. | Transparent and fast, but not a learned historical baseline; the day-of-week field is not used here. Make inputs/configuration visible and compare against facility/zone history. |
| Adaptive forecast | Fixed validation metrics; formula-derived champion; challenger variants of that same champion. | Reliability weighting is implemented mathematically, but model predictions and weights are not currently learned or updated from validation. Connect actual model adapters or name this as a heuristic estimator. |
| Anomaly fusion | Context score plus threshold maps and domain rules; IF/LOF names are proxies. | Signals are correlated because they originate from the same contextual deviation. Agreement therefore overstates independent detector consensus. Feed real detector outputs or rename the proxies and avoid claiming model consensus. |
| Persistence | Process-local consecutive count keyed by building. | Gives a simple temporal debounce, but it is lost on restart, assumes events arrive in order and at regular intervals, and does not reset after time gaps. Track timestamps and sequence/window rules. |
| Confidence | Weighted deterministic score; several fields are fixed/defaulted. | Explainable calculation, but not calibrated probability. Label as a confidence score until calibrated against held-out outcomes. |
| Business impact | Configured tariff/carbon arithmetic and annualization. | Useful scenario estimate. Confirm the input interval/unit: a 15-minute kWh value is treated as though the excess persisted hourly and then 24 hours/day, 365 days/year. Show duration and assumptions explicitly. |
| Priority | Weighted score and thresholds, with one opportunity score default. | Reproducible, but weights/thresholds need documented rationale and evaluation against operator outcomes. Priority text should remain advisory. |
| SHAP explanation | Static values inserted on critical path. | Not a valid SHAP explanation. Use the fitted model’s explainer on the actual feature vector, or remove the SHAP label and explain rules actually triggered. |
| Recommendation | One hard-coded HVAC action, fixed savings percentage, static rationale. | Useful demo example, not a domain-general action recommender. Tie actions and savings assumptions to the actual metric, evidence, confidence, and facility configuration. |
| Safety approval | A separate `AISafetyGate` exists, but the main DIF flow does not invoke it. | The algorithm’s output must not be described as safety-gated until the gate is part of the execution path and its decision is returned. Human approval should remain explicit. |

## 5. Evaluation package: what its metrics currently establish

The evaluator has useful scaffolding: it calculates regression/classification metrics, includes naive and historical-mean baselines, splits energy chronology into 70/15/15 sections, and writes CSV/Markdown and chart outputs. Those are good building blocks. The current metric-generation methods, however, invalidate the headline accuracy claims:

### Forecast evaluation

- Energy specialist predictions are created as `test_series + random_noise`. This uses the ground-truth test value to construct its own prediction. It is target leakage by construction, not evaluation of the trained energy model.
- The fallback energy series is synthetic. If used, it is not representative facility evidence.
- The naive baseline’s multi-step predictions use earlier values from the test series after the first test point. This can be a valid rolling one-step protocol only if described as such and predictions are made sequentially; it is not a fixed-origin forecast.
- Water predictions also use `test_series + random_noise`, again deriving predictions from answers.
- The report’s dataset name and test-split descriptions are therefore not sufficient to establish that predictions came from a held-out fitted model.

### Anomaly and waste evaluation

- Anomaly ground-truth labels are randomly assigned to 30 of 300 rows. Scores are then drawn from a low range for normal rows and a higher range for the labeled anomalies. Thresholding these scores makes the task nearly guaranteed by construction; it does not exercise the project’s `AnomalyDetectorEngine` or the DIF proxy fusion.
- Waste labels and predictions both use a threshold on the same fill-level values, with small noise in prediction. This measures a synthetic threshold perturbation, not a trained overflow model on unseen future bins.
- The generated ROC/PR chart curves are hand-constructed arrays and the chart labels show example AUC/F1 values. They are not plotted from the evaluator’s true scores/labels. The confusion matrix plot has fallback counts if results are absent.

### Decision-layer metrics

- The package runs 100 generated events through the DIF wrapper, which is the closest current section to measuring the actual decision engine.
- The metric named `false_alert_suppression_rate_pct` counts records where `confidence.gate_passed` is false. The evaluator does not determine which alerts were false against ground truth. It is a low-confidence gate rate, not a false-alert suppression rate.
- The default agreement metric counts how many of four signals clear a score threshold. Because the “detectors” are not independent models, this is signal-threshold agreement, not model agreement.
- “Total identified cost surge” sums per-event hourly impacts. It is not verified savings or realized ROI.

### Complexity and report claims

- The Big-O table is manually declared and describes stages/models that are not all executed in the current DIF code (e.g. tree-model inference and SHAP complexity despite proxy predictions and static attributions).
- The empirical benchmark measures elapsed time for generated events, but its event values are random and the process is stateful. It does not isolate cold-start vs warm inference, report distributions/percentiles, or establish scalability. Memory delta from process RSS around a short run is noisy and may be zero or misleading.
- The report generation path describes the metrics as scientific validation and specialist models even though key evaluator methods use synthetic formulas. Existing `metrics_summary.csv`, markdown results, and charts should be treated as stale/unverified artifacts until regenerated through a corrected evaluation.

**Conclusion:** Reported values such as near-perfect anomaly precision/recall and high forecast R² should not be presented as evidence of production or real-world performance. The evaluation harness should be corrected before the report or charts are used to support claims.

## 6. Reproducibility and engineering observations

- The package imports the parent project by editing `sys.path`; this works as a repository-local script pattern but makes the package less independently installable.
- Global pipeline state means the persistence counter carries across calls and benchmark runs. Evaluation results may depend on call ordering unless state is reset.
- `process_telemetry_event` defaults missing values to plausible campus readings. This is convenient for a demo but can hide missing input. Production callers should provide required data or receive explicit missing-data outcomes.
- The wrapper constructs separate baseline, SHAP, business-impact, and priority engine objects that are not used in its method; the DIF engine owns the execution path. Remove dead dependencies or make their role real.
- Several outputs imply realized savings/automated action while the action system is advisory/simulated. Keep “estimated”, “recommended”, “approved”, “recorded”, and “verified” as different statuses.
- Complexity results are not unit-test assertions. They should not be interpreted as algorithmic complexity proof.

## 7. Recommended remediation plan

### Priority 0: correct the scientific claims

1. Change the report/README wording now: identify rule-derived and synthetic benchmark outputs as illustrative. Remove “scientifically validated”, “100% accuracy”, “false alert suppression”, and causal/verified-savings claims unless there is matching evidence.
2. Mark old generated metrics and charts as illustrative or regenerate them after fixing the evaluator. Store evaluation timestamp, source dataset fingerprint, code version, split boundaries, and model artifact/version.

### Priority 1: make the evaluation measure real behavior

1. Build a single evaluator that loads the actual chronological dataset and reports exactly which source/table/columns were used. Fail clearly if a required dataset or target is missing; do not silently swap in a generated series while labeling it as facility data.
2. Train/select a model using train/validation only. Generate test predictions only from features available at the prediction timestamp. Use a clearly stated rolling-origin or fixed-origin evaluation protocol.
3. Compare against persistence, seasonal-naive, and training-mean baselines using the same timestamps and metrics. Report MAE/RMSE/MAPE with units, sample count, test time range, and per-facility results where available.
4. For anomaly detection, create explicit injected anomalies in a held-out fixture or use independently labeled observations. Fit detectors on training/normal data only, select thresholds on validation, and score untouched test labels. Report confusion matrix, precision, recall, F1, ROC-AUC/PR-AUC when class balance supports them, and false-positive rate.
5. Evaluate the actual `EstateIQDIF` output against ground truth. Define what counts as a false alert, a missed event, and a successfully suppressed alert before computing those metrics. Rename confidence-gate rate until this is done.
6. Draw ROC/PR charts from actual test scores; remove synthetic curves and hardcoded confusion-matrix fallbacks.

### Priority 2: align live algorithm and architecture claims

1. Decide whether the adaptive stage is a real model ensemble or a contextual heuristic. For a real ensemble, connect trained model adapters and out-of-sample validation metrics from saved artifacts. Calculate model weights only from a validation period and log them with each decision. Otherwise rename it to avoid implying model inference.
2. Replace proxy IF/LOF scores with actual detector outputs from `src/anomaly/detector.py`, fit on appropriate training history. Keep the contextual and rules signals separate and document their correlation.
3. Use a facility/zone historical baseline, operating schedule and timezone. Do not fabricate a 365-day history or default quality score when evidence is absent.
4. Compute SHAP only for a supported fitted model and the actual row; otherwise return evidence-based rule explanations with explicit provenance.
5. Invoke an explicit safety/approval gate before any action can be marked executable. Keep the recommendation advisory and avoid describing the app as controlling equipment.
6. Make event IDs unique under concurrent/rapid events and handle out-of-order, duplicated, stale, or missing telemetry. Persist temporal persistence state or make the scope/process-reset behavior explicit.
7. Reconcile documented pipeline stage counts, model names, algorithm flow, and output units across `README.md`, `ARCHITECTURE.md`, `docs/ABLATION_STUDY.md`, and the Elite package.

### Priority 3: decision quality and maintainability

1. Put tariffs, emission factors, thresholds, confidence weights, and action savings assumptions in facility configuration with source/effective-date metadata.
2. Calculate business impact from interval-aware energy deltas and a stated continuation scenario. Do not annualize one event without explicitly labeling the persistence assumption.
3. Add a decision trace containing input provenance, data-quality evidence, baseline version, model versions and predictions, detector scores, weights, threshold/rule IDs, confidence components, impact assumptions, priority, and recommendation rationale.
4. Add evaluation focused on edge cases and invariants: missing values, zeros, counter reset, one-class labels, timezone boundaries, repeated event IDs, state reset, no model artifact, and optional detector failures.
5. Keep the Elite package’s benchmark deterministic and isolated from production process state; report median and p95 latency over repeated runs after warm-up, and use a profiler for memory rather than interpreting a single RSS delta.

## 8. Suggested accurate product description

> **EstateIQ Elite Algorithm (EstateIQ-DIF)** is a prototype decision-support pipeline that combines facility-context rules, telemetry quality checks, anomaly evidence, confidence scoring, estimated business impact, prioritization, and advisory recommendations. Some current prediction, detector, and explanation values are heuristic or illustrative. Predictive and anomaly performance should be reported only from a corrected, chronological, held-out evaluation of the actual fitted models and decision outputs. Recommendations are advisory; savings are estimates until verified using measured pre/post data.

## 9. Code reviewed

- `src/intelligence/dif_engine.py`
- `src/intelligence/adaptive_ensemble.py`
- `src/intelligence/anomaly_consensus.py`
- `src/intelligence/context_filter.py`
- `src/intelligence/confidence_engine.py`
- `src/intelligence/business_impact.py`
- `src/intelligence/decision_engine.py`
- `src/intelligence/recommendation_ranker.py`
- `src/intelligence/safety_gate.py`
- `src/intelligence/types.py`
- `src/anomaly/detector.py`
- `src/models/energy/pipeline.py`
- `elite-algorithm-package/elite_algo/pipeline.py`
- `elite-algorithm-package/elite_algo/evaluator.py`
- `elite-algorithm-package/elite_algo/metrics.py`
- `elite-algorithm-package/elite_algo/complexity.py`
- `elite-algorithm-package/elite_algo/visualizer.py`
- `elite-algorithm-package/run_evaluation.py`
- Existing package report, metrics CSV, README, and selected tests

