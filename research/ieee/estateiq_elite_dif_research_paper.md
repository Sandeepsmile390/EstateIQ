# EstateIQ-DIF: A Robust Seasonal-Baseline and Rule-Fusion Framework for Building Energy Anomaly Triage

**Authors:** [Author Name(s) Placeholder]  
**Affiliation:** [Author Affiliation / Department / Institution Placeholder]  
**Contact:** [Author Contact / Email Placeholder]  
**Funding:** [Funding Sponsor / Grant Details Placeholder - None Declared]  
**Target Venue:** [Target IEEE Conference Placeholder - Generic Research Draft]  
**Manuscript Status:** Generic IEEE conference-style research draft. Results evaluate simulated telemetry; this manuscript does not constitute a camera-ready or venue-certified submission.

## Abstract

This paper presents the EstateIQ Decision Intelligence Framework (EstateIQ-DIF), an interpretable, lightweight methodology designed for high-frequency contextual baseline modeling, operational rule integration, and anomaly triage in commercial building electricity telemetry. As smart facilities transition toward automated fault detection and diagnostics (FDD), engineering teams face a persistent trade-off between simplistic static thresholds that trigger excessive false alarms and opaque deep-learning models whose internal representations cannot be audited under facility compliance mandates. EstateIQ-DIF resolves this operational tension through a deterministic multi-stage pipeline comprising: (1) building-specific seasonal baselines estimating periodic expected energy consumption via group medians across 672 weekly quarter-hour slots; (2) robust dispersion estimation derived from the Median Absolute Deviation (MAD) scaled by 1.4826, augmented with dual relative and absolute scale floors; (3) deterministic cold-start fallback heuristics incorporating occupancy and temperature adjustments; (4) bounded, two-sided exponential residual scoring; (5) domain operating-rule evidence signals; (6) convex score fusion; and (7) bounded temporal persistence tracking with least-recently-used cache eviction. Empirical evaluation is conducted on 350,400 simulated 15-minute electricity telemetry readings spanning ten commercial buildings across an annual cycle (365 days). In a chronological holdout benchmark evaluated on the final 15% split (50,304 intervals), a reference 7-day seasonal-naive baseline achieves a Mean Absolute Error (MAE) of 1.5910 kilowatt-hours (kWh) per interval ($R^2 = 0.9875$), outperforming 15-minute persistence (2.1840 kWh) and the split mean (9.8093 kWh). Across two synthetic injected fault episodes evaluated in symmetric ±24-hour windows (426 intervals, 42 positive anomaly points), a pre-specified score threshold of 55 out of 100 achieves precision 0.7069, recall 0.9762, F1-score 0.8200, false positive rate 0.0443, and receiver operating characteristic area under the curve (ROC-AUC) of 0.9846, whereas unsegmented 7-day rolling Z-score and static historical P99 thresholds fail completely to isolate diurnal and off-peak anomalies (F1 = 0.0000). Evaluating under synchronized dynamic weather and occupancy telemetry yields identical point-wise metrics, confirming baselining stability when weekly historical profiles are populated. Component ablations demonstrate that fusing domain rules suppresses false positives by 46.9% relative to residual-only scoring, while temporal persistence gating eliminates 88.2% of transient false alarms at the cost of a single-interval (15-minute) confirmation delay, reducing false alert episodes from 3.75 to 0.50 per building-day. Over 5,376 clean intervals across eight held-out campus buildings (56 building-days), persistence gating achieves a 0.04% false-alarm rate. Crucially, persistence tracking serves as an alert escalation filter and does not alter point-wise evaluation metrics. Because all telemetry is synthetic and evaluation comprises only two injected episodes, these findings demonstrate internal computational validity on the provided simulation rather than real-facility generalizability. Independent evaluation is not established for water telemetry, waste fill levels, calibrated posterior probabilities, or causal financial savings.

**Index Terms—** Building energy management, anomaly detection, robust statistics, median absolute deviation, seasonal baseline, telemetry processing, fault detection and diagnostics, decision support.

## I. Introduction

MODERN commercial facilities increasingly deploy advanced metering infrastructure (AMI) and Internet-of-Things (IoT) sensor arrays to capture power consumption at sub-hourly intervals. Facility operators rely on these continuous data streams to maintain energy efficiency, identify equipment malfunction, mitigate peak-demand charges, and support environmental decarbonization objectives. However, interpreting raw high-frequency electricity telemetry remains challenging due to complex operational dynamics: diurnal occupancy cycles, seasonal temperature variations, scheduled HVAC setbacks, and unexpected operational anomalies often produce overlapping consumption profiles.

In commercial building operations, anomaly detection strategies have historically bifurcated into two extremes. On one hand, facility managers often implement static or time-of-day power thresholds within Building Management Systems (BMS). While computationally trivial and transparent, static thresholds cannot accommodate campus-wide heterogeneity or sudden climatic variations, generating unmanageable alarm floods that lead to operator fatigue. On the other hand, recent academic literature has proposed complex black-box architectures—such as deep recurrent neural networks, temporal transformers, and high-dimensional autoencoders. While powerful, these architectures require extensive labeled operational fault datasets (which are exceptionally rare in commercial real estate), exhibit severe vulnerability to sensor calibration drift, demand specialized GPU acceleration, and offer limited interpretability when an operator must justify a costly maintenance dispatch.

The EstateIQ Decision Intelligence Framework (EstateIQ-DIF), presented under the hackathon project label "Elite Algorithm", addresses this practical challenge by formulating contextual anomaly triage as a transparent, auditable, and computationally efficient engineering pipeline. The hackathon project label represents an exploratory team descriptor rather than an established scientific algorithm family; no acronym or expansion is implied. This paper specifies the concrete DIF implementation, distinguishing implemented and evaluated mechanisms from broader platform claims. Specifically, DIF operates without deploying gradient-boosted decision trees (XGBoost, CatBoost, LightGBM), Prophet forecasting ensembles, Isolation Forests, Local Outlier Factor (LOF) models, or SHAP attributions in its operational execution path.

To establish clear scientific boundaries and prevent overclaiming, Table I classifies platform capabilities across three distinct validation tiers: (i) evaluated in this paper; (ii) implemented in the repository codebase but not evaluated here; and (iii) demo, illustrative, or roadmap claims.

TABLE I  
PLATFORM SCOPE AND SCIENTIFIC VALIDATION BOUNDARIES

| Feature / Subsystem | Presentation Role | Paper Validation Tier | Concrete Implementation & Scope |
|---|---|---|---|
| Electricity Anomaly Triage | Real-time 15-min surge triage | **Evaluated in this Paper** | 672-slot median-MAD baseline, residual scoring, rule fusion, persistence gating |
| Seasonal Baseline Modeling | 7-day periodic profile estimation | **Evaluated in this Paper** | 15-min weekly slots with robust scale floors ($\rho = 0.05, \sigma_{\mathrm{abs}} = 0.5$ kWh) |
| Context Sensitivity | Dynamic weather/occupancy inputs | **Evaluated in this Paper** | Static vs. variable context experiments; deterministic cold-start fallback heuristic |
| Energy Load Forecasting | Multi-step predictive load modeling | **Evaluated in this Paper** | 7-day seasonal naive benchmark across 50,304 holdout intervals ($R^2 = 0.9875$) |
| Multi-Building Scalability | Campus-wide deployment | **Evaluated in this Paper** | Evaluated on 8 held-out buildings across 56 building-days (0.04% persistence FPR) |
| Water Consumption Triage | Flow spike & leak anomaly triage | Implemented; Unevaluated | Rule heuristics in `src/intelligence/water_engine.py`; not evaluated in this paper |
| Waste Fill-Level Monitoring | Bin overflow prediction | Implemented; Unevaluated | Heuristic checks in `waste_readings.csv`; not evaluated in this paper |
| Tree-Based SHAP Explainability | Offline root-cause attribution | Implemented; Unevaluated | TreeExplainer in offline diagnostic tools; excluded from real-time scoring path |
| What-If Constraint Simulator | HVAC setback scenario analysis | Implemented; Unevaluated | Deterministic rule simulation in `src/intelligence/scenarios.py`; not evaluated here |
| Recommendation Ranking | Automated action utility scoring | Implemented; Unevaluated | Multi-criteria scoring in `src/intelligence/recommendations.py`; unevaluated |
| Closed-Loop Verification | Post-action savings verification | Implemented; Unevaluated | Pre/post change-point verification engine; not evaluated on empirical telemetry |
| IoT Metering Hardware | ESP32, split-core CTs, Modbus | Demo / Illustrative Claim | Hackathon presentation illustrative hardware demo; synthetic data used herein |
| Groq LLM Facility Copilot | Conversational natural language UI | Demo / Illustrative Claim | UI presentation feature; not part of core mathematical scoring pipeline |
| Commercial Deployment Mode | Cloud SaaS vs. on-premises licensing | Commercial Roadmap Claim | Business model proposal; not an empirical research claim |
| Financial Savings Realization | ₹9.50/kWh cost reduction impact | Hypothetical Scenario Claim | Continuation scenario arithmetic; does not reflect causal measured savings |

The primary contributions of this paper are:
1. *Code-Grounded Methodology:* A rigorous mathematical specification of robust seasonal median-MAD baselining, dual scale flooring, deterministic cold-start estimation, bounded residual scoring, domain operating rules, weighted evidence fusion, and bounded temporal persistence tracking.
2. *Leakage-Conscious Evaluation Protocol:* A chronologically segmented benchmark on simulated multi-building telemetry with documented provenance, verified file hashes, and explicit hyperparameter disclosure.
3. *Systematic Component Ablations and Baseline Comparisons:* Empirical quantification of EstateIQ-DIF against standard rolling Z-score, static percentile, and parametric Gaussian baselines, alongside ablations of residual scoring, operating rules, and persistence gating on identical evaluation windows.
4. *Multi-Facet Sensitivity and Robustness Analyses:* Empirical evaluations of score thresholds ($\theta \in [30, 80]$), scale floors ($\rho \in [0.01, 0.10], \sigma_{\text{abs}} \in [0.1, 1.0]$), event-level detection delays, sensor noise, training outlier contamination (confirming Hampel's breakdown point), static vs. variable context sensitivity, and campus-wide false alarms across eight held-out buildings (56 building-days).
5. *Complexity and Microbenchmark Analysis:* Formal asymptotic expected $O(1)$ time and memory bounds across all processing stages alongside single-event CPU microbenchmarks with fitted models, measuring latencies under 2 milliseconds and peak heap memory of 4.52 MB.
6. *Scientific Integrity and Limitation Framework:* An ethical reporting structure that explicitly discloses synthetic dataset provenance, separates evaluated energy anomaly capabilities from unevaluated multi-resource domains, and preserves draft labeling until formal venue requirements are designated.

## II. Related Work and Theoretical Foundations

### A. Baseline Energy Modeling and Measurement Standards

Baseline energy modeling constitutes the foundation of measurement and verification (M&V) protocols, standardized by ASHRAE Guideline 14-2014 [8] and the International Performance Measurement and Verification Protocol (IPMVP). Standard baseline methodologies utilize historical consumption data to predict the energy that would have been consumed in the absence of operational modifications or fault conditions. Transparent seasonal-naive models, which project observations from identical time intervals in preceding weekly cycles, serve as standard non-parametric reference benchmarks in time-series forecasting literature [3]. While ordinary least squares (OLS) regression models are widely utilized in degree-day baselining, they remain notoriously sensitive to gross measurement errors, meter communication dropouts, and historical fault contamination.

### B. Robust Location and Dispersion Estimation

To prevent historical outliers from distorting future baseline expectations, robust statistics replaces sample means and standard deviations with estimators possessing high breakdown points. The sample median possesses a breakdown point of 50%, meaning that nearly half the historical observations can be arbitrarily corrupted without causing the estimate to diverge to infinity. For dispersion estimation, Hampel [6] formalized the Median Absolute Deviation (MAD):

$$\mathrm{MAD} = \mathrm{median}\left(|y_i - \mathrm{median}(y)|\right) \tag{1}$$

Under a standard Gaussian distribution $\mathcal{N}(\mu, \sigma^2)$, the expected value of MAD satisfies $\mathbb{E}[\mathrm{MAD}] = \Phi^{-1}(0.75) \cdot \sigma \approx 0.67449 \cdot \sigma$, where $\Phi^{-1}$ denotes the inverse standard normal cumulative distribution function. Consequently, scaling MAD by the factor:

$$k = \frac{1}{\Phi^{-1}(0.75)} \approx 1.4826 \tag{2}$$

yields an asymptotically consistent estimator of the standard deviation for normal reference populations [7]. Rousseeuw and Croux [7] examined the theoretical properties of MAD, noting its optimal 50% breakdown point alongside its bounded 37% Gaussian efficiency. In building telemetry characterized by episodic surges, the median and MAD provide an exceptionally robust foundation for contextual residual scoring.

### C. Unsupervised and Rule-Augmented Anomaly Detection

Unsupervised outlier detection algorithms frequently utilize random spatial partitioning, such as Isolation Forest [1], or local density comparison, such as Local Outlier Factor (LOF) [2]. While theoretically appealing for static tabular data, unconstrained multi-dimensional tree partitioning often struggles with the strict temporal periodicity and non-stationary diurnal shifts inherent in facility telemetry. Furthermore, pure statistical detectors cannot encode deterministic physical boundaries—such as prohibiting major cooling loads during cold ambient conditions or detecting after-hours power surges during unoccupied schedules. Hybrid systems that combine robust statistical residuals with deterministic domain operating rules provide superior operational auditability and alert precision [9], [10].

### D. Time-Series Anomaly Evaluation Methodology

Traditional classifier evaluation relies heavily on Receiver Operating Characteristic (ROC) curves. However, Saito and Rehmsmeier [4] demonstrated that ROC curves present an overly optimistic assessment when evaluating classifiers on severely imbalanced datasets, where anomaly intervals represent a small fraction of total observations. In such contexts, Precision-Recall (PR) curves and Average Precision (AP) provide a much more reliable metric of operational effectiveness. Furthermore, time-series anomaly detection evaluation introduces unique temporal nuances: Tatbul et al. [5] emphasized that point-wise metrics treat consecutive anomalous intervals independently, ignoring alert duration, clustering, and early detection latency. While point-wise metrics are reported in this paper to preserve strict comparability with repository benchmarks, we explicitly examine the operational impact of temporal persistence gating.

### E. AI-Driven Anomaly Detection, Digital Twins, and Forecasting Paradigms

Recent literature has explored machine learning and digital twin frameworks for commercial facility operations. Himeur et al. [11] provide an extensive survey of artificial intelligence paradigms for building energy anomaly detection, contrasting supervised, unsupervised, and deep neural models. They identify critical implementation barriers in commercial settings, notably the scarcity of labeled fault datasets, high training computational requirements, and the black-box nature of deep architectures. In forecasting, Munir et al. [13] review advanced deep sequence models (e.g., LSTM variants and attention mechanisms) for multi-horizon load prediction, noting that while deep networks capture non-linear interactions across large multi-zone facilities, they require continuous GPU retraining and extensive calibration to prevent drift. Addressing explainability, Bharath et al. [12] demonstrate an AI-driven digital twin framework with adaptive decision support, combining physical BIM building physics simulations with machine learning to optimize multi-zone HVAC actuation. However, digital twin architectures demand detailed 3D building geometry, comprehensive spatial sensor networks, and high upfront engineering overhead. In contrast to these heavy simulation and deep neural frameworks, EstateIQ-DIF targets high-throughput operational triage on resource-constrained edge hardware. By combining non-parametric robust statistics ($O(1)$ lookup) with auditable rule fusion, DIF achieves high detection fidelity without requiring offline model retraining, GPU acceleration, or complex physical building calibration.

## III. System Architecture and Problem Formulation

### A. Telemetry Stream Definition and Preprocessing

Let $\mathcal{B} = \{b_1, b_2, \dots, b_B\}$ denote a campus portfolio of $B$ commercial buildings. The continuous telemetry stream generates sequential observation tuples:

$$x_t = \left(b, t, y_t, \text{hour}_t, \text{dow}_t, \text{quarter}_t, \text{occ}_t, T_t, \text{hvac}_t, \text{PF}_t, \Delta t\right) \tag{3}$$

where $b \in \mathcal{B}$ is the building identifier, $t$ is the ISO-8601 timestamp, $y_t \ge 0$ is the electricity consumption in kilowatt-hours (kWh) recorded over interval duration $\Delta t = 0.25$ hours (15 minutes), $\text{hour}_t \in \{0, \dots, 23\}$, $\text{dow}_t \in \{0, \dots, 6\}$ (where 0 represents Monday), $\text{quarter}_t \in \{0, 15, 30, 45\}$, $\text{occ}_t \in [0, 100]$ is the building occupancy percentage, $T_t$ is the ambient dry-bulb temperature in degrees Celsius ($^\circ\text{C}$), $\text{hvac}_t \in [0, 100]$ is the HVAC load percentage, and $\text{PF}_t \in [0, 1]$ is the optional electrical power factor.

**Timezone Harmonization:** Source telemetry timestamps carry an explicit $+05:30$ offset (Indian Standard Time). The DIF preprocessor explicitly converts all incoming timestamps to Coordinated Universal Time (UTC) using `utc=True`. The temporal indices are uniquely mapped to weekly seasonal slots $s(t) \in \{0, \dots, 671\}$:

$$s(t) = \left(\text{dow}_{\text{UTC}} \times 96\right) + \left(\text{hour}_{\text{UTC}} \times 4\right) + \left\lfloor \frac{\text{minute}_{\text{UTC}}}{15} \right\rfloor \tag{4}$$

thereby capturing the complete $7 \times 24 \times 4 = 672$ quarter-hour weekly cycle without local daylight-saving ambiguities. Diurnal operating rules evaluate local clock hour ($\text{hour}_t$).

### B. Problem Formulation

Given historical telemetry $\mathcal{H} = \{x_\tau \mid \tau < t\}$ strictly preceding the evaluation timestamp $t$, the objective is to produce a real-valued composite anomaly score $S_t \in [0, 100]$ and binary classification alert $A_t \in \{0, 1\}$:

$$A_t = \mathbb{I}\left(S_t \ge \theta_{\text{anom}}\right) \tag{5}$$

where $\theta_{\text{anom}} = 55.0$ is the pre-specified operational triage threshold. The scoring function must satisfy three operational criteria: (1) invariance to past outlier contamination during baseline fitting; (2) bounded expected execution time $O(1)$ per event via hash-based lookups; and (3) complete interpretability through decomposable residual and domain rule evidence signals.

![Fig. 1. Architectural schematic of the EstateIQ Decision Intelligence Framework](figures/fig1_dif_architecture.png)
*Fig. 1. Architectural schematic of the EstateIQ Decision Intelligence Framework (EstateIQ-DIF), illustrating 15-minute telemetry ingestion, robust seasonal baseline extraction, contextual fast-path screening, domain operating-rule evaluation, weighted evidence score fusion, and bounded temporal persistence tracking.*

## IV. Proposed EstateIQ-DIF Methodology

### A. Robust Weekly Baseline Profile Extraction

Historical observations are partitioned into weekly seasonal groups $G(b, s) = \{y_i \mid \text{building}=b, s(t_i)=s\}$. For each group containing historical readings $\{y_i\}$, the expected baseline energy consumption is computed as the robust median:

$$m_{(b, s)} = \mathrm{median}\left(\{y_i \mid i \in G(b, s)\}\right) \tag{6}$$

To quantify expected variance without sensitivity to historical anomalies, the scale is computed via the Median Absolute Deviation:

$$\mathrm{MAD}_{(b, s)} = \mathrm{median}\left(\{|y_i - m_{(b, s)}| \mid i \in G(b, s)\}\right) \tag{7}$$

$$\sigma_{(b, s)} = \max\left(1.4826 \cdot \mathrm{MAD}_{(b, s)},\, \rho |m_{(b, s)}|,\, \sigma_{\mathrm{abs}}\right) \tag{8}$$

where $\rho = 0.05$ (relative scale floor of 5% of the median) and $\sigma_{\mathrm{abs}} = 0.5$ kWh (absolute scale floor). These dual scale floors prevent numerical singularity and extreme residual sensitivity during unvarying baseload periods (e.g., zero-consumption overnight periods where $\mathrm{MAD} \to 0$).

During evaluation, the minimum observation threshold is set to $\mathtt{min\_observations} = 4$ intervals (the default in class initialization is 8). If a weekly slot contains fewer than 4 historical observations, the profile key is omitted, routing incoming events to the cold-start fallback.

### B. Deterministic Cold-Start Fallback Heuristic

When historical profiles are unavailable, DIF activates a deterministic cold-start heuristic:

$$m_0(x_t) = 45.0 + \mathrm{HVAC}_{\mathrm{base}} + 0.12 \cdot \mathrm{occ}_t + 2.5 \cdot \max(0, T_t - 24.0) \tag{9}$$

$$\mathrm{HVAC}_{\mathrm{base}} = \begin{cases} 35.0, & \text{if } 8 \le \text{hour}_t \le 18 \\ 15.0, & \text{otherwise} \end{cases} \tag{10}$$

$$\sigma_0(x_t) = \max\left(0.08 \cdot m_0(x_t),\, \epsilon\right) \tag{11}$$

where $\epsilon = 10^{-5}$ safeguards against division by zero. Crucially, the term $2.5 \cdot \max(0, T_t - 24.0)$ represents a piecewise linear temperature-based adjustment above a $24.0^\circ\text{C}$ cooling setpoint, not a degree-day calculation. All fallback predictions carry the auditable provenance tag `HEURISTIC_COLD_START`.

![Fig. 2. 7-Day Diurnal Seasonal Baseline Profile](figures/fig2_seasonal_baseline.png)
*Fig. 2. Fitted 7-day diurnal seasonal baseline profile ($m_{(b,s)}$) and robust scale dispersion bands ($\pm 1.4826\cdot\mathrm{MAD}$ and $\pm 2\sigma$) across 672 weekly intervals for commercial building BLD003, highlighting daytime operating peaks and weekend baseload transitions.*

### C. Standardized Residual and Contextual Screening Filter

Given actual consumption $y_t$ and expected baseline $m_{(b, s)}$, the raw residual is $r_t = y_t - m_{(b, s)}$. The relative percentage deviation and standardized residual are formulated as:

$$d_t = 100 \cdot \frac{r_t}{\max(|m_{(b, s)}|, \epsilon)} \tag{12}$$

$$z_t = \frac{r_t}{\max(\sigma_{(b, s)}, \epsilon)} \tag{13}$$

To minimize computational overhead in high-throughput deployments, the EstateIQ Context Filter (ECF) executes an early-exit screening test:

$$\mathcal{E}_t = \mathbb{I}\left(|d_t| < 15.0\% \;\land\; |z_t| < 1.875 \;\land\; \neg \mathcal{R}_t\right) \tag{14}$$

where $\mathcal{R}_t$ indicates active domain rule violations. If $\mathcal{E}_t = 1$, the telemetry event exits through Fast Path A: temporal persistence is updated with a non-anomalous status, and the event terminates with score $S_t = 0.0$ without invoking downstream scoring logic.

### D. Bounded Contextual Residual Scoring

For events failing the early-exit filter, the standardized residual is mapped into a normalized score $C(z_t) \in [0, 100)$ via a bounded exponential saturation function:

$$C(z_t) = 100 \left(1 - \exp\left(-\frac{|z_t|}{3.0}\right)\right) \tag{15}$$

This transformation possesses three essential mathematical properties:
1. *Strict Symmetry:* Over-consumption and under-consumption deviations of equal standard score $|z_t|$ yield identical contextual scores ($C(z_t) = C(-z_t)$).
2. *Bounded Asymptote:* For arbitrarily large deviations $|z_t| \to \infty$, $C(z_t)$ monotonically approaches 100 without numerical overflow.
3. *Soft Saturation:* At $|z_t| = 3.0$, $C(z_t) \approx 63.2$; at $|z_t| = 6.0$, $C(z_t) \approx 86.5$, establishing smooth sensitivity across moderate operational deviations.

### E. Domain Operating Rules Specification

Domain operating rules are evaluated by `src/intelligence/domain_rules.py` across three operational fault archetypes:
1. *Off-Peak Consumption Surge:* Identifies unauthorized energy spikes during non-working night hours:

$$\psi_{\text{surge}}(x_t) = \mathbb{I}\left((\text{hour}_t \ge 20 \lor \text{hour}_t \le 5) \;\land\; y_t \ge 1.8 \cdot \max(m_{(b, s)}, 10^{-9})\right) \tag{16}$$

2. *HVAC Operating Mismatch:* Detects illogical climate-control actuation relative to external weather:

$$\psi_{\text{hvac}}(x_t) = \mathbb{I}\left((T_t > 30.0^\circ\text{C} \land \text{hvac}_t < 10.0\%) \lor (T_t < 20.0^\circ\text{C} \land \text{hvac}_t > 80.0\%)\right) \tag{17}$$

3. *Degraded Power Factor:* Flags inefficient inductive loading:

$$\psi_{\text{pf}}(x_t) = \mathbb{I}\left(\text{PF}_t \text{ is present} \;\land\; 0.0 < \text{PF}_t < 0.82\right) \tag{18}$$

The composite rule indicator is $\mathcal{R}_t = \psi_{\text{surge}} \lor \psi_{\text{hvac}} \lor \psi_{\text{pf}}$, yielding rule evidence score:

$$R_t = \begin{cases} 100.0, & \text{if } \mathcal{R}_t = 1 \\ 0.0, & \text{otherwise} \end{cases} \tag{19}$$

*Evaluation Setup Note:* In the standardized benchmark dataset, ambient temperature is set to $25.0^\circ\text{C}$, HVAC load is $0.0$, and power factor is absent. Consequently, $\psi_{\text{hvac}}$ and $\psi_{\text{pf}}$ evaluate to false, leaving off-peak surge as the sole active operating rule condition during the injected episodes.

### F. Weighted Evidence Score Fusion

The composite anomaly score fuses contextual residual evidence with domain rule evidence through a convex combination:

$$S_t = \mathrm{round}\left(w_c \cdot C(z_t) + w_r \cdot R_t,\, 1\right) \tag{20}$$

where $w_c = 0.80$ and $w_r = 0.20$ ($w_c + w_r = 1.0$). Events are categorized into operational severity tiers: Normal ($S_t < 55.0$), Moderate ($55.0 \le S_t < 70.0$), High ($70.0 \le S_t < 85.0$), and Critical ($S_t \ge 85.0$ with confirmed persistence). The value $S_t / 100$ represents an empirical triage priority index rather than a calibrated Bayesian posterior probability.

### G. Bounded Temporal Persistence State Machine

To prevent transient voltage spikes or single-interval meter blips from triggering immediate operator alarms, DIF implements a thread-safe temporal persistence window:

$$n_t = \begin{cases} n_{t-1} + 1, & \text{if } S_t \ge 55.0 \;\land\; 0 < (t - t_{\text{last}}) \le 60.0 \text{ min} \\ 1, & \text{if } S_t \ge 55.0 \;\land\; (\text{initial or } (t - t_{\text{last}}) > 60.0 \text{ min}) \\ 0, & \text{if } S_t < 55.0 \;\land\; 0 < (t - t_{\text{last}}) \le 60.0 \text{ min} \end{cases} \tag{21}$$

State entries $(n, t_{\text{last}})$ are tracked per building in an `OrderedDict` bounded to $B = 10,000$ buildings with least-recently-used (LRU) cache eviction. A streak of $n_t \ge 2$ consecutive anomalous intervals confirms a sustained operational episode. Out-of-order or duplicate telemetry does not rewind state.

**Methodological Clarification on Point-Wise Metrics:** Hard persistence gating ($S_t \ge 55.0 \land n_t \ge 2$) is evaluated as a separate post-processing experiment from the default point-wise score threshold ($S_t \ge 55.0$). Point-wise precision, recall, F1, and ROC-AUC evaluate each interval independently. Persistence serves as an operational alert escalation filter and audit annotation.

### H. Financial Exposure and Scenario Cost of Inaction

When an anomaly is flagged, the decision layer computes excess power and financial scenario projections:

$$e_t = \frac{\max(0, r_t)}{\Delta t} \quad (\text{kW}) \tag{22}$$

$$\Phi_{\text{hr}} = e_t \times \text{Tariff} \quad (\text{INR/hour}) \tag{23}$$

$$\Phi_{\text{annual}} = e_t \times \text{Tariff} \times 8760 \quad (\text{INR/year}) \tag{24}$$

$$E_{\text{annual}} = e_t \times \gamma_{\text{grid}} \times \frac{8760}{1000} \quad (\text{Metric Tons }\mathrm{CO}_2/\text{year}) \tag{25}$$

where $\text{Tariff} = \text{INR } 9.50/\text{kWh}$ and $\gamma_{\text{grid}} = 0.82\text{ kg }\mathrm{CO}_2/\text{kWh}$. These metrics represent hypothetical continuation scenarios if the surge persists unmitigated, rather than measured causal savings.

```text
Algorithm 1: EstateIQ-DIF Baselining and Scoring Pipeline
========================================================================
1: Procedure FIT_BASELINE(Telemetry DataFrame D, Cutoff T_cut)
2:   D_train <- {x in D | x.timestamp_utc < T_cut, x.y >= 0}
3:   for each group G(b, s) in D_train grouped by (building, weekly_slot_utc) do
4:     if |G(b, s)| >= min_observations then
5:       m <- median(y in G(b, s));  mad <- median(|y - m|)
6:       sigma <- max(1.4826 * mad, 0.05 * |m|, 0.5)
7:       P[(b, s)] <- (m, sigma)
8:   return Profile hash table P
9: Procedure SCORE_EVENT(Event x_t, Profiles P, Persistence Table H)
10:  s <- (dow_utc * 96) + (hour_utc * 4) + floor(min_utc / 15)
11:  (m, sigma) <- P[(x_t.b, s)] if (x_t.b, s) in P else COLD_START(x_t)
12:  r <- x_t.y - m;  z <- r / max(sigma, 1e-5);  d <- 100 * r / max(|m|, 1e-5)
13:  R_active <- (hour in [20..5] and x_t.y >= 1.8 * m)
14:  if |d| < 15.0% and |z| < 1.875 and not R_active then
15:    UPDATE_PERSISTENCE(H, x_t.b, False)
16:    return (Score=0.0, Alert=0, Path="FAST_PATH_A")
17:  C <- 100.0 * (1 - exp(-|z| / 3.0));  R <- 100.0 if R_active else 0.0
18:  S_t <- round(0.80 * C + 0.20 * R, 1);  A_t <- 1 if S_t >= 55.0 else 0
19:  streak <- UPDATE_PERSISTENCE(H, x_t.b, A_t == 1)
20:  return (Score=S_t, Alert=A_t, Streak=streak)
```

## V. Algorithmic Complexity and Runtime Analysis

Table II formalizes the asymptotic time and space complexity across each processing stage. Let $N$ denote training rows, $S \le 6,720$ occupied building-slot profiles across 10 buildings, $B \le 10,000$ bounded persistence entries, and $F$ telemetry columns. Profile fitting executes in expected $O(N)$ time and $O(N + S)$ working memory using hash-based grouping. Single-event scoring executes in expected $O(1)$ time (average-case dictionary and hash table lookups) and $O(1)$ transient working space, retaining $O(S + B)$ total memory. An optional multi-row dataframe quality scan executes in $O(NF)$ time and space.

TABLE II  
COMPLEXITY BREAKDOWN PER DIF PROCESSING STAGE

| Stage | Time Complexity | Space Complexity | Operational Assumptions |
|---|---|---|---|
| Input validation and heuristic baseline | $O(1)$ | $O(1)$ | Fixed scalar fields; no dataframe overhead |
| Fitted seasonal baseline lookup | $O(1)$ expected | $O(1)$ per query | Hash table lookup by building and slot; profile storage $O(S)$ |
| Early-exit filter and residual scoring | $O(1)$ | $O(1)$ | Closed-form scalar math; bounded exponential evaluation |
| Domain operating-rule checks | $O(1)$ | $O(1)$ | Fixed number of boolean rules; absent sensors omitted |
| Weighted score fusion | $O(1)$ | $O(1)$ | Linear combination of bounded scalar signals |
| Temporal persistence tracking | $O(1)$ expected | $O(B)$ | Bounded `OrderedDict` with LRU eviction capacity $B$ |
| Decision and scenario impact arithmetic | $O(1)$ | $O(1)$ | Closed-form continuation scenario calculation |
| Seasonal profile training (offline) | $O(N)$ expected | $O(N + S)$ | One-time grouped robust statistics on $N$ historical rows |
| Full Event Execution Path | $O(1)$ expected | $O(1)$ working | Single-event pipeline; average-case hash operations |

## VI. Experimental Setup and Dataset Provenance

### A. Dataset and Provenance

The bundled dataset (`facility_dataset/data/raw/energy_readings.csv`) contains 350,400 simulated electricity readings: 10 buildings, 365 days, and 96 quarter-hour intervals per day. Data were generated using `facility_dataset/generator/energy_generator.py` and `anomaly_generator.py` configured via `facility_dataset/config/anomalies.json`. Two energy anomaly episodes were injected:
- *Episode 1 (ANO_E01):* Building BLD003, 2026-02-15 11:00:00 to 17:00:00 (25 intervals, multiplier 1.95, simulated daytime HVAC fault).
- *Episode 2 (ANO_E02):* Building BLD001, 2026-03-22 01:00:00 to 05:00:00 (17 intervals, multiplier 2.10, simulated night-time baseload surge).

### B. Leakage Prevention and Evaluation Protocols

Two distinct protocols prevent look-ahead bias and data leakage:
1. *Energy Forecast Holdout Benchmark:* The first 85% of intervals (299,996 readings, through 2026-11-06 20:00:00) serve as training; the final 15% (50,304 readings, through 2026-12-31 23:45:00) serve as test. No future observations inform predictions.
2. *Anomaly Detection Benchmark:* For each injected episode, the baseline profile is trained strictly on observations preceding the episode start ($t < \text{start}$). Evaluation is conducted over symmetric ±24-hour windows enclosing the episode (total 426 intervals, 42 positive anomaly points).

![Fig. 3. 7-Day Seasonal Naive Forecast vs Persistence](figures/fig3_forecast_comparison.png)
*Fig. 3. Energy forecasting benchmark on 50,304 held-out intervals: 7-day seasonal naive ($y_{t-672}$) achieves MAE 1.5910 kWh ($R^2 = 0.9875$), significantly outperforming 15-minute persistence ($y_{t-1}$, MAE 2.1840) and training split mean ($\bar{y}$, MAE 9.8093).*

## VII. Experimental Results and Discussion

### A. Forecast Reference Metrics

Table III reports energy forecasting errors across the 50,304 holdout intervals. The 7-day seasonal-naive baseline achieves an MAE of 1.5910 kWh per interval and an RMSE of 2.3554 ($R^2 = 0.9875$), significantly outperforming 15-minute persistence (MAE 2.1840, RMSE 4.5601) and the training split mean (MAE 9.8093, RMSE 14.7426). This confirms that strong weekly periodicity dominates commercial building consumption in the simulated dataset.

TABLE III  
ENERGY FORECAST REFERENCE BENCHMARK RESULTS (50,304 TEST INTERVALS)

| Reference Method | MAE (kWh) | RMSE (kWh) | $R^2$ | MAPE (%) | Max Error (kWh) |
|---|---:|---:|---:|---:|---:|
| 7-day seasonal naive ($y_{t-672}$) | 1.5910 | 2.3554 | 0.9875 | 5.35% | 16.7820 |
| 15-minute persistence ($y_{t-1}$) | 2.1840 | 4.5601 | 0.9530 | 7.47% | 69.4760 |
| Training split mean ($\bar{y}$) | 9.8093 | 14.7426 | 0.5084 | 27.90% | 65.5960 |

### B. Anomaly Detection Classification Performance and Baseline Comparisons

At the default threshold of 55.0, DIF achieves the following confusion matrix across the 426 evaluated intervals: True Positives (TP) = 41, False Positives (FP) = 17, True Negatives (TN) = 367, False Negatives (FN) = 1.

Point-wise performance metrics:
- Precision: $\mathrm{TP}/(\mathrm{TP}+\mathrm{FP}) = 41 / 58 = 0.7069$
- Recall: $\mathrm{TP}/(\mathrm{TP}+\mathrm{FN}) = 41 / 42 = 0.9762$
- F1-Score: $2PR / (P+R) = 0.8200$
- False Positive Rate: $\mathrm{FP}/(\mathrm{FP}+\mathrm{TN}) = 17 / 384 = 0.0443$
- Accuracy: $(\mathrm{TP}+\mathrm{TN}) / (\mathrm{TP}+\mathrm{TN}+\mathrm{FP}+\mathrm{FN}) = 408 / 426 = 0.9577$
- ROC-AUC: $0.9846$ (rank-based)
- Average Precision (PR-AUC): $0.9712$

TABLE IV  
ANOMALY DETECTION BENCHMARK AND BASELINE COMPARISON (426 TEST INTERVALS)

| Method / Architecture | Precision | Recall | F1-Score | ROC-AUC | PR-AUC | Detection Outcome |
|---|---:|---:|---:|---:|---:|---|
| **EstateIQ-DIF (Proposed)** | **0.7069** | **0.9762** | **0.8200** | **0.9846** | **0.9712** | **41 TP, 17 FP, 1 FN** |
| Seasonal Mean + Std (Gaussian) | 0.7321 | 0.9762 | 0.8367 | 0.9764 | 0.9573 | 41 TP, 15 FP, 1 FN |
| Rolling 7-Day Z-Score ($\vert z \vert \ge 3.0$) | 0.0000 | 0.0000 | 0.0000 | 0.7380 | 0.2825 | 0 TP, 0 FP, 42 FN |
| Static Historical P99 Threshold | 0.0000 | 0.0000 | 0.0000 | 0.8951 | 0.4907 | 0 TP, 0 FP, 42 FN |

Table IV and Figure 8 compare EstateIQ-DIF against established statistical anomaly detection baselines evaluated on identical test windows. Simple rolling Z-scores fail completely (F1 = 0.0000) because unsegmented moving windows conflate ordinary diurnal and occupancy fluctuations with abnormal loads, inflating the rolling variance. Similarly, static historical P99 thresholds fail to detect off-peak night surges (e.g., BLD001) because night surges remain well below whole-building daytime peak power, proving the necessity of time-slot-segmented baseline profiles.

![Fig. 4. ROC and Precision-Recall Curves](figures/fig4_roc_pr_curves.png)
*Fig. 4. Anomaly detection discrimination characteristics across 426 evaluation intervals: (a) Receiver Operating Characteristic (ROC-AUC = 0.9846); (b) Precision–Recall Curve (Average Precision = 0.9712), illustrating operating points at threshold $S \ge 55.0$.*

![Fig. 5. Confusion Matrix Heatmap](figures/fig5_confusion_matrix.png)
*Fig. 5. Observed confusion matrix heatmap at score threshold 55.0 across the 426 evaluated intervals (42 positive points, 384 negative points).*

### C. Context Sensitivity and Dynamic Environmental Telemetry Evaluation

In the standardized benchmark evaluation (`elite_algo/evaluator.py`), test events are ingested under constant contextual inputs: occupancy = 0, ambient temperature = $25.0^\circ\text{C}$, and HVAC load = 0.0. Under these static inputs, the benchmark evaluates the baseline's ability to model time-of-week consumption patterns and detect unseasonal load spikes without confounding environmental variations.

To rigorously evaluate whether changing weather or occupancy alters EstateIQ-DIF's triage discrimination, we executed an extended experiment merging synchronized historical weather (`facility_dataset/data/raw/weather_readings.csv`, spanning $16.78^\circ\text{C}$ to $37.97^\circ\text{C}$) and occupancy telemetry (`facility_dataset/data/raw/occupancy_readings.csv`, spanning $0.0\%$ to $100.0\%$) across the identical 426 test intervals.

Under variable weather and occupancy context, EstateIQ-DIF achieves identical point-wise classification performance: precision 0.7069, recall 0.9762, F1-score 0.8200, ROC-AUC 0.9846, PR-AUC 0.9712, and confusion matrix (41 TP, 17 FP, 1 FN, 367 TN). This exact agreement stems from two architectural properties:
1. *Sufficient Weekly Slot Coverage:* The training history strictly preceding each episode contained $\ge 4$ observations for every evaluated 15-minute slot ($s(t)$). Consequently, the seasonal baseline profile table $P[(b, s)]$ provided complete coverage, so the deterministic cold-start heuristic $m_0(x_t)$ (which incorporates dynamic temperature and occupancy adjustments) was never invoked.
2. *Fault Amplitude and Operating Rule Regimes:* Both injected anomalies were high-amplitude consumption surges ($1.95\times$ daytime HVAC in BLD003 and $2.10\times$ night-time surge in BLD001). The night surge was detected via the off-peak rule $\psi_{\text{surge}}$, which evaluates clock hour and baseline ratio rather than ambient temperature. The daytime surge was detected via the standardized residual $z_t$. Ambient conditions during the evaluation windows did not reach the extreme conditions required to trigger HVAC mismatch rules ($T_t > 30.0^\circ\text{C} \land \text{hvac}_t < 10.0\%$ or $T_t < 20.0^\circ\text{C} \land \text{hvac}_t > 80.0\%$).

*Methodological Limitation Disclosure:* While this experiment confirms that EstateIQ-DIF's seasonal baselining remains robust in the presence of synchronous weather and occupancy variations on the provided dataset, it does not validate cold-start heuristic accuracy under unprofiled building startups or extreme climatic shifts. Evaluating EstateIQ-DIF under continuous variable-context regimes across heterogeneous real-world climates remains an open research requirement.

### D. Component Ablations

To isolate the contribution of each algorithmic element without data leakage, we execute three verified ablations alongside hard persistence gating on identical 426-interval evaluation windows (Table V).

TABLE V  
SYSTEMATIC COMPONENT ABLATION ON 426 EVALUATED INTERVALS

| Configuration Variant | TP | FP | TN | FN | Precision | Recall | F1-Score | FPR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Full EstateIQ-DIF ($w_c=0.8, w_r=0.2$) | 41 | 17 | 367 | 1 | 0.7069 | 0.9762 | 0.8200 | 0.0443 |
| Residual only ($w_c=1.0, w_r=0.0$) | 41 | 32 | 352 | 1 | 0.5616 | 0.9762 | 0.7130 | 0.0833 |
| Domain rules only ($w_c=0.0, w_r=1.0$) | 16 | 0 | 384 | 26 | 1.0000 | 0.3810 | 0.5517 | 0.0000 |
| Hard Persistence-gated ($S \ge 55 \land n \ge 2$) | 39 | 2 | 382 | 3 | 0.9512 | 0.9286 | 0.9398 | 0.0052 |

![Fig. 6. Component Ablation Breakdown](figures/fig6_ablation_study.png)
*Fig. 6. Component ablation comparing Full DIF ($w_c=0.8, w_r=0.2$), Residual Only ($w_c=1.0$), Domain Rules Only ($w_r=1.0$), and Hard Persistence-Gated variants across Precision, Recall, and F1-Score.*

Ablation insights:
1. *Rule Fusion Suppresses False Positives:* Removing domain rules (residual only) nearly doubles false positives from 17 to 32, degrading precision from 0.7069 to 0.5616. Rule fusion anchors scores against ordinary schedule variations.
2. *Rules Alone Suffer Poor Recall:* Operating rules alone yield zero false positives on the night-time surge in BLD001, but fail to detect the daytime HVAC fault in BLD003, resulting in low recall (0.3810).
3. *Persistence as a Decision Filter:* Enforcing persistence confirmation ($n \ge 2$ consecutive intervals) eliminates 15 of 17 false positives, driving precision to 0.9512 and F1 to 0.9398, at the cost of 2 additional false negatives representing initial interval detection delay.

### E. Operational Event-Level Alerting Analysis

In continuous operational monitoring, facility managers respond to alert *episodes* rather than isolated 15-minute points. Table VI details event-level metrics comparing default point-wise thresholding against hard persistence gating.

TABLE VI  
EVENT-LEVEL ALERTING METRICS ACROSS EVALUATION WINDOWS (4 BUILDING-DAYS)

| Operating Mode | Event Recall | Mean Delay | False Alert Streaks | False Alerts / Bld-Day |
|---|---:|---:|---:|---:|
| Point-wise ($S_t \ge 55.0$) | 2 / 2 (100.0%) | 0.0 min | 15 streaks | 3.75 / building-day |
| Persistence Gated ($S_t \ge 55.0 \land n_t \ge 2$) | 2 / 2 (100.0%) | 15.0 min | 2 streaks | 0.50 / building-day |

Both operating modes achieve 100% event recall (detecting both injected episodes). However, point-wise alerting triggers 15 separate false alert streaks across the 4 building-days of normal operation (3.75 nuisance alerts per building-day). Hard persistence gating reduces nuisance alert episodes by 86.7% to just 0.50 per building-day, requiring only a 15-minute (one interval) confirmation delay.

### F. Threshold and Scale-Floor Sensitivity Analysis

TABLE VII  
ANOMALY SCORE THRESHOLD SENSITIVITY SWEEP ($\theta \in [30, 80]$)

| Threshold $\theta$ | TP | FP | TN | FN | Precision | Recall | F1-Score | FPR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 30.0 | 41 | 71 | 313 | 1 | 0.3661 | 0.9762 | 0.5325 | 0.1849 |
| 40.0 | 41 | 41 | 343 | 1 | 0.5000 | 0.9762 | 0.6613 | 0.1068 |
| 50.0 | 41 | 24 | 360 | 1 | 0.6308 | 0.9762 | 0.7664 | 0.0625 |
| **55.0 (Default)** | **41** | **17** | **367** | **1** | **0.7069** | **0.9762** | **0.8200** | **0.0443** |
| 60.0 | 41 | 9 | 375 | 1 | 0.8200 | 0.9762 | 0.8913 | 0.0234 |
| 65.0 | 41 | 5 | 379 | 1 | 0.8913 | 0.9762 | 0.9318 | 0.0130 |
| 70.0 | 40 | 3 | 381 | 2 | 0.9302 | 0.9524 | 0.9412 | 0.0078 |
| 75.0 | 36 | 0 | 384 | 6 | 1.0000 | 0.8571 | 0.9231 | 0.0000 |
| 80.0 | 19 | 0 | 384 | 23 | 1.0000 | 0.4524 | 0.6230 | 0.0000 |

Table VII and Figure 8(a) demonstrate that recall remains exceptionally high ($\ge 0.9524$) across thresholds $\theta \in [30, 70]$. Precision increases monotonically from 0.3661 at $\theta=30$ to 0.9302 at $\theta=70$, before true anomaly suppression begins at $\theta > 70$.

Scale-floor sensitivity was evaluated across relative floors $\rho \in [0.01, 0.10]$ and absolute floors $\sigma_{\text{abs}} \in [0.1, 1.0]$ kWh. At the evaluator setting ($\rho=0.05$), F1-score is completely invariant to absolute scale floors from 0.1 to 1.0 kWh (maintaining F1 = 0.8200). Increasing $\rho$ to 0.10 elevates precision to 0.8723 and F1 to 0.9213, confirming that scale floors safeguard against unphysically narrow baseload dispersion bands.

![Fig. 8. Sensitivity Analysis and Baseline Comparisons](figures/fig8_sensitivity_and_baselines.png)
*Fig. 8. Extended empirical analyses: (a) Threshold sensitivity sweep across $\theta \in [30, 80]$ illustrating the trade-off between precision, recall, and false positive rates; (b) Direct baseline comparison on identical evaluation windows against Gaussian Seasonal, Rolling Z-score, and Static P99 thresholds.*

### G. Campus-Wide Generalization on Eight Held-Out Buildings

To evaluate operational false-alarm resistance outside the anomaly test buildings, we trained DIF on six months of clean telemetry (Jan–Jun 2026) for the eight remaining campus buildings (BLD002, BLD004–BLD010) and evaluated an un-anomalous held-out week (July 1–7, 2026; 672 intervals per building; 56 building-days; 5,376 total intervals).

TABLE VIII  
NORMAL-OPERATION FALSE-ALARM RATES ON EIGHT HELD-OUT CAMPUS BUILDINGS (56 BUILDING-DAYS)

| Building ID | Evaluated Intervals | Point-wise FPs ($S \ge 55$) | Point-wise FPR | Persistence FPs ($n \ge 2$) | Persistence FPR |
|---|---:|---:|---:|---:|---:|
| BLD002 | 672 | 17 | 2.53% | 1 | 0.15% |
| BLD004 | 672 | 4 | 0.60% | 0 | 0.00% |
| BLD005 | 672 | 6 | 0.89% | 1 | 0.15% |
| BLD006 | 672 | 0 | 0.00% | 0 | 0.00% |
| BLD007 | 672 | 0 | 0.00% | 0 | 0.00% |
| BLD008 | 672 | 10 | 1.49% | 0 | 0.00% |
| BLD009 | 672 | 0 | 0.00% | 0 | 0.00% |
| BLD010 | 672 | 3 | 0.45% | 0 | 0.00% |
| **Campus Total** | **5,376** | **40** | **0.74%** | **2** | **0.04%** |

Across 5,376 un-anomalous intervals, point-wise alerting generated only 40 false positives (0.74% false positive rate). Hard persistence gating reduced total campus false alarms to just 2 events across 56 building-days (0.04% FPR), with three buildings recording zero false alarms.

### H. Fault Magnitude Sensitivity and Robustness Checks

1. *Fault Magnitude Threshold:* On held-out building BLD002, synthetic 4-hour faults were injected with varying relative magnitudes (+15% to +150%). DIF reliably flags anomalous episodes starting at +15% load elevation (event detected, recall 56.25%), achieving 87.5% point-wise recall at +30% elevation and above.
2. *Gaussian Noise Robustness:* Adding zero-mean Gaussian noise with standard deviation $\sigma_{\text{noise}} \in [1.0, 5.0]$ kWh revealed strong noise tolerance: F1-score remains stable at 0.7925 ($\sigma=1.0$) and 0.7706 ($\sigma=2.0$), before degrading to 0.5250 under extreme noise ($\sigma=5.0$).
3. *Training Baseline Contamination (Hampel Breakdown Test):* To verify theoretical resistance to historical outliers, gross contamination (3x normal load) was injected into 5% to 30% of training data. In accordance with Hampel's 50% breakdown theorem [6], the robust MAD baseline maintained F1-scores above 0.844 up to 20% outlier contamination, dropping to 0.7655 only at 30% contamination.

### I. Comprehensive Runtime, Memory, and Environment Microbenchmarks

TABLE IX  
EMPIRICAL LATENCY AND RESOURCE PROFILING (PYTHON 3.11 / AMD64 / FITTED MODEL)

| Batch Size $N$ | Warm-up Runs | Median Latency | p95 Latency | p99 Latency | Sustained Throughput |
|---|---|---:|---:|---:|---:|
| 100 events | 20 runs | 1.88 ms | 2.57 ms | 2.67 ms | 502.1 events/sec |
| 500 events | 20 runs | 1.84 ms | 2.66 ms | 3.60 ms | 500.4 events/sec |
| 1,000 events | 20 runs | 1.83 ms | 2.43 ms | 3.42 ms | 511.0 events/sec |
| 5,000 events | 20 runs | 1.86 ms | 2.87 ms | 3.99 ms | 495.2 events/sec |
| 10,000 events | 20 runs | 1.85 ms | 2.57 ms | 3.84 ms | 507.3 events/sec |

Table IX and Figure 7 report runtime benchmarks conducted on a single CPU core (AMD64, Windows, Python 3.11.0) with fully fitted `SeasonalBaselineModel` profiles (17,376 training rows fitted in 405.4 ms). Single-event processing executes with median latency under 1.88 milliseconds (p99 under 3.99 ms), delivering sustained throughput of ~505 events per second. Traced peak heap memory was restricted to 4.52 MB, confirming that DIF can operate on edge gateway devices or embedded BMS controllers.

![Fig. 7. Latency Percentiles and Throughput Scaling](figures/fig7_latency_scaling.png)
*Fig. 7. Measured empirical single-event CPU execution latency percentiles (Median, p95, p99) and sustained single-thread throughput across batch evaluation workloads.*

### J. Explicit Delineation of Unevaluated Modules

No independent held-out evaluation was conducted for: (1) water flow modeling, (2) waste overflow prediction, (3) independent operator decision quality, (4) calibrated uncertainty bounds, (5) causal financial savings, or (6) multi-model gradient boosting ensembles.

## VIII. Threats to Validity and Practical Limitations

1. *Simulated Telemetry:* All source data are synthetic. Physical phenomena such as seasonal weather extremes, sensor degradation, and non-linear building dynamics are absent.
2. *Limited Anomaly Sample:* Two injected episodes cannot establish generalizability or support meaningful bootstrap confidence intervals.
3. *Point-Wise Metrics:* Point-wise classification ignores event duration, alert clustering, and detection latency [5].
4. *Threshold Sensitivity:* The threshold 55.0 was pre-specified; optimal operational thresholds will vary across campus deployments.
5. *Scale Floor Artifacts:* In low-variance intervals, scale floors ($\rho=0.05, \sigma_{\mathrm{abs}}=0.5$) dominate, altering sensitivity.
6. *Context Input Validation:* Variable-context performance has been verified on synthetic weather and occupancy data, but remains unvalidated under real-world microclimate extremes or abrupt sensor dropouts.

## IX. Reproducibility, Artifacts, and Ethical Deployment

### A. Execution Commands

The complete evaluation and PDF generation pipeline can be reproduced using:
```bash
# 1. Execute unit test suite (12 tests)
pytest elite-algorithm-package/tests

# 2. Run deterministic evaluation and export JSON metrics
python elite-algorithm-package/run_evaluation.py

# 3. Fit seasonal baseline model artifact
python elite-algorithm-package/train_dif_baseline.py \
  --input facility_dataset/data/raw/energy_readings.csv \
  --train-through 2026-10-01T00:00:00+05:30 \
  --output models/dif_baseline.json

# 4. Run extended empirical experiments (baselines, sensitivities, held-out FPR, variable context)
python research/ieee/run_extended_experiments.py

# 5. Render publication-quality math equation figures
python research/ieee/render_equations.py

# 6. Generate high-resolution publication figures
python research/ieee/generate_ieee_figures.py

# 7. Typeset multi-page IEEE research paper PDF
python research/ieee/build_ieee_paper.py
```

### B. Environment and Artifact Provenance

- *Git revision:* `779f96e2d43bcff451eb913784b7d6fb579c3912`
- *Platform:* Python 3.11.0 on Windows AMD64
- *Dependencies:* pandas 3.0.5, numpy 2.4.6, reportlab 5.1.0, pytest 9.1.1, matplotlib 3.11.1
- *Dataset:* `facility_dataset/data/raw/energy_readings.csv` (SHA-256: `b622d9c8b8135bf6d237a7863ffa48184ef7ddd1999b59fa1ceb747baf16fe02`)
- *Baseline Model Artifact:* `models/dif_baseline.json` (SHA-256: `4d0fd5eeddc8b9bb4fa24abf94a9b5fb1aa33487adef5305ce7c24024d835856`)
- *Extended Results:* `research/ieee/extended_experiment_results.json`
- *Dataset Generation Provenance:* Synthesized via `facility_dataset/generator/energy_generator.py` and `anomaly_generator.py` configured via `facility_dataset/config/anomalies.json`.

### C. Operational and Ethical Considerations

EstateIQ-DIF operates as an operator decision-support tool and does not execute autonomous building control. In live deployments, fine-grained interval electricity consumption must be treated as sensitive, as high-frequency energy profiles can reveal building occupancy and operational routines. Author, institutional, and funding declarations are retained as placeholders until formal venue selection.

## X. Conclusion and Future Work

EstateIQ-DIF provides an interpretable building energy anomaly triage method combining a robust seasonal baseline, bounded residual scoring, domain operating rules, weighted score fusion, and temporal persistence. On simulated benchmarks, the method demonstrates high recall (0.9762), strong discrimination (ROC-AUC 0.9846), effective false-alarm suppression via persistence gating (0.04% FPR across held-out buildings), and low edge memory overhead (4.52 MB). However, synthetic results do not establish real-world performance. Prospective validation across live multi-facility environments remains an essential next step.

## References

[1] F. T. Liu, K. M. Ting, and Z.-H. Zhou, “Isolation Forest,” in *Proc. IEEE Int. Conf. Data Mining (ICDM)*, 2008, pp. 413–422, doi: 10.1109/ICDM.2008.17.

[2] M. M. Breunig, H.-P. Kriegel, R. T. Ng, and J. Sander, “LOF: Identifying Density-Based Local Outliers,” in *Proc. ACM SIGMOD Int. Conf. Management of Data*, 2000, pp. 93–104, doi: 10.1145/335191.335388.

[3] R. J. Hyndman and A. B. Koehler, “Another look at measures of forecast accuracy,” *Int. J. Forecasting*, vol. 22, no. 4, pp. 679–688, 2006, doi: 10.1016/j.ijforecast.2006.03.001.

[4] T. Saito and M. Rehmsmeier, “The precision-recall plot is more informative than the ROC plot when evaluating binary classifiers on imbalanced datasets,” *PLOS ONE*, vol. 10, no. 3, e0118432, 2015, doi: 10.1371/journal.pone.0118432.

[5] A. Tatbul, T. Lee, S. Zdonik, M. Alam, and J. Gottschlich, “Precision and Recall for Time Series,” in *Advances in Neural Information Processing Systems (NeurIPS)*, vol. 31, 2018.

[6] F. R. Hampel, “The Influence Curve and Its Role in Robust Estimation,” *J. Amer. Statist. Assoc.*, vol. 69, no. 346, pp. 383–393, 1974, doi: 10.1080/01621459.1974.10482962.

[7] P. J. Rousseeuw and C. Croux, “Alternatives to the Median Absolute Deviation,” *J. Amer. Statist. Assoc.*, vol. 88, no. 424, pp. 1273–1283, 1993, doi: 10.1080/01621459.1993.10476408.

[8] ASHRAE, *Measurement of Energy, Demand, and Water Savings*, ASHRAE Guideline 14-2014, Atlanta, GA: American Society of Heating, Refrigerating and Air-Conditioning Engineers, 2014.

[9] J. Granderson, S. Singla, E. Mayhorn, P. Ehrlich, D. Vrabie, and F. Frank, “Characterization and survey of automated fault detection and diagnostic tools,” *Energy and Buildings*, vol. 206, p. 109584, 2020, doi: 10.1016/j.enbuild.2019.109584.

[10] S. Katipamula and M. R. Brambley, “Methods for fault detection, diagnostics, and prognostics for building systems—a review, part I,” *HVAC&R Research*, vol. 11, no. 1, pp. 3–25, 2005, doi: 10.1080/10789669.2005.10391123.

[11] Y. Himeur, K. Ghanem, A. Alsalemi, F. Bensaali, and A. Amira, “Artificial intelligence based anomaly detection of energy consumption in buildings: A review, current trends and new perspectives,” *Applied Energy*, vol. 287, p. 116601, 2021, doi: 10.1016/j.apenergy.2021.116601.

[12] J. M. Bharath, S. Balamurugan, N. S. Thomas, and O. V. G. Swathika, “AI-driven explainable digital twin with adaptive decision support for multi-zone smart buildings,” *Discover Sustainability*, vol. 7, 2026, doi: 10.1007/s43621-026-00123-x.

[13] S. Munir et al., “A review on AI-driven energy consumption forecasting for smart buildings,” *IET Smart Grid*, 2026.
