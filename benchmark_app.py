"""EstateIQ Algorithm Benchmark Application.

A comprehensive, scientific evaluation app comparing the EstateIQ-DIF algorithm
against reference baselines for energy forecasting, anomaly detection, and
computational complexity on facility datasets.
"""

from __future__ import annotations

import json
from pathlib import Path
import time
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.benchmarks.dataset_loader import DatasetLoader, DatasetMetadata
from src.benchmarks.forecasting_bench import EnergyForecastingBenchmark, ForecastingBenchResult
from src.benchmarks.anomaly_bench import AnomalyDetectionBenchmark, AnomalyBenchResult
from src.benchmarks.complexity_bench import ComplexityBenchmark

# -----------------------------------------------------------------------------
# Streamlit Page Configuration & Styling
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="EstateIQ Algorithm Benchmark Suite",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    /* Dark EstateIQ Theme */
    .stApp {
        background-color: #0B1118;
        color: #E2E8F0;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    .metric-card {
        background: #151F2C;
        border: 1px solid #1E293B;
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
    }
    .metric-title {
        color: #94A3B8;
        font-size: 13px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-weight: 600;
        margin-bottom: 6px;
    }
    .metric-value {
        color: #00F0B5;
        font-size: 26px;
        font-weight: 800;
        font-family: monospace;
    }
    .metric-sub {
        color: #64748B;
        font-size: 12px;
        margin-top: 4px;
    }
    .badge-synthetic {
        background: rgba(245, 158, 11, 0.15);
        color: #F59E0B;
        border: 1px solid rgba(245, 158, 11, 0.4);
        padding: 4px 10px;
        border-radius: 8px;
        font-size: 11px;
        font-weight: 700;
        display: inline-block;
        letter-spacing: 0.5px;
    }
    .badge-verified {
        background: rgba(0, 240, 181, 0.15);
        color: #00F0B5;
        border: 1px solid rgba(0, 240, 181, 0.4);
        padding: 4px 10px;
        border-radius: 8px;
        font-size: 11px;
        font-weight: 700;
        display: inline-block;
    }
    .callout-box {
        background: #0F172A;
        border-left: 4px solid #00F0B5;
        padding: 14px 18px;
        border-radius: 0 8px 8px 0;
        margin: 16px 0;
        font-size: 13px;
        color: #CBD5E1;
    }
    .callout-warning {
        background: #18120B;
        border-left: 4px solid #F59E0B;
        padding: 14px 18px;
        border-radius: 0 8px 8px 0;
        margin: 16px 0;
        font-size: 13px;
        color: #FDE68A;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner="Loading and verifying dataset integrity...")
def get_cached_dataset(file_path: Optional[str] = None):
    loader = DatasetLoader()
    return loader.load_dataset(file_path)


def main():
    # Header Banner
    col_hdr1, col_hdr2 = st.columns([3, 1])
    with col_hdr1:
        st.title("⚡ EstateIQ-DIF Algorithm Benchmark Suite")
        st.caption("Scientific evaluation of EstateIQ Dynamic Intelligence Fusion against standard reference baselines")
    with col_hdr2:
        st.write("")
        st.markdown(
            '<div style="text-align: right;"><span class="badge-synthetic">SYNTHETIC BENCHMARK DATASET</span><br>'
            '<span style="font-size: 11px; color: #64748B;">Not Measured Live Sensor Data</span></div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # -------------------------------------------------------------------------
    # Sidebar Controls
    # -------------------------------------------------------------------------
    st.sidebar.header("📁 Dataset Source")
    data_option = st.sidebar.radio(
        "Select Telemetry Source:",
        ["Repository Benchmark Dataset", "Upload Custom CSV"],
        index=0,
    )

    uploaded_file = None
    custom_df = None
    dataset_path_str = None

    if data_option == "Upload Custom CSV":
        uploaded_file = st.sidebar.file_uploader("Upload facility CSV:", type=["csv"])
        if uploaded_file is None:
            st.info("Please upload a CSV dataset containing 'timestamp' and 'electricity_kwh' (or 'energy_kwh').")
            st.stop()
        try:
            loader = DatasetLoader()
            df, meta = loader.load_dataset(uploaded_file)
        except Exception as e:
            st.error(f"Error parsing uploaded file: {e}")
            st.stop()
    else:
        try:
            df, meta = get_cached_dataset(None)
        except Exception as e:
            st.error(f"Could not load repository dataset: {e}")
            st.stop()

    # Sidebar Filter Controls
    st.sidebar.markdown("---")
    st.sidebar.header("⚙️ Evaluation Parameters")

    all_buildings = meta.buildings
    selected_buildings = st.sidebar.multiselect(
        "Filter Buildings:",
        options=all_buildings,
        default=all_buildings[:3] if len(all_buildings) > 3 else all_buildings,
    )
    if not selected_buildings:
        selected_buildings = all_buildings

    st.sidebar.subheader("Forecasting Split")
    train_ratio = st.sidebar.slider("Training Ratio (%):", min_value=50, max_value=85, value=70, step=5) / 100.0
    val_ratio = 0.15
    test_ratio = round(1.0 - train_ratio - val_ratio, 2)
    st.sidebar.caption(f"Split: {int(train_ratio*100)}% Train / {int(val_ratio*100)}% Val / {int(test_ratio*100)}% Test")

    st.sidebar.subheader("Anomaly Detection")
    anomaly_mode = st.sidebar.radio(
        "Anomaly Evaluation Mode:",
        ["Injected Episodes (±24h Buffer)", "Full Chronological Test Split"],
        index=0,
    )
    dif_threshold = st.sidebar.slider("EstateIQ-DIF Anomaly Threshold:", min_value=30.0, max_value=85.0, value=55.0, step=1.0)
    enable_persistence = st.sidebar.checkbox("Enable Persistence Gating (n ≥ 2)", value=True)
    enable_ablations = st.sidebar.checkbox("Run DIF Ablations (Residual / Rules)", value=True)

    # -------------------------------------------------------------------------
    # Main Tabs
    # -------------------------------------------------------------------------
    tab_overview, tab_forecast, tab_anomaly, tab_runtime, tab_repro = st.tabs([
        "📋 Overview & Provenance",
        "📈 Energy Forecasting",
        "🚨 Anomaly Detection",
        "⏱️ Complexity & Runtime",
        "💾 Reproducibility & Export",
    ])

    # =========================================================================
    # TAB 1: DATASET AUDIT & PROVENANCE
    # =========================================================================
    with tab_overview:
        st.subheader("Facility Dataset Audit & Reproducibility Fingerprint")

        st.markdown(
            f"""
            <div class="callout-box">
                <strong>Provenance Guarantee:</strong> {meta.provenance_notes}<br>
                <strong>Evaluation Integrity:</strong> Ground-truth anomaly flags are used strictly for post-hoc validation.
                All baseline fitting, scaling, and thresholding steps observe chronological boundaries with <strong>zero future data leakage</strong>.
            </div>
            """,
            unsafe_allow_html=True,
        )

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">Total Records</div>
                <div class="metric-value">{meta.total_rows:,}</div>
                <div class="metric-sub">{len(meta.buildings)} Monitored Buildings</div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">Sampling Interval</div>
                <div class="metric-value">{meta.sampling_interval_minutes:.0f} min</div>
                <div class="metric-sub">Quarter-Hourly Resolution</div>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">Missing Values</div>
                <div class="metric-value">{meta.missing_energy_pct:.2f}%</div>
                <div class="metric-sub">{meta.missing_energy_rows:,} Missing Intervals</div>
            </div>
            """, unsafe_allow_html=True)
        with col4:
            anom_count = meta.anomaly_counts.get("anomaly", 0)
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">Labeled Anomalies</div>
                <div class="metric-value">{anom_count:,}</div>
                <div class="metric-sub">{meta.anomaly_prevalence_pct:.4f}% Class Prevalence</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("#### Chronological Split Timeline & Leakage Prevention")
        st.markdown(
            """
            ```mermaid
            flowchart LR
                A["Training Split (0% - 70%)<br>Fitted: Seasonal Baselines & P99 Thresholds<br>Labels: Ignored"] --> B["Validation Split (70% - 85%)<br>Hyperparameter tuning & gates"]
                B --> C["Test Split (85% - 100%)<br>Strictly Out-of-Sample<br>Zero Future Telemetry Leakage"]
                style A fill:#1E293B,stroke:#00F0B5,stroke-width:2px,color:#E2E8F0
                style B fill:#1E293B,stroke:#38BDF8,stroke-width:2px,color:#E2E8F0
                style C fill:#1E293B,stroke:#F59E0B,stroke-width:2px,color:#E2E8F0
            ```
            """
        )

        st.markdown("#### Dataset Metadata Specification")
        audit_data = [
            {"Property": "Dataset File Path", "Value": meta.file_path},
            {"Property": "SHA-256 Checksum", "Value": meta.sha256_fingerprint},
            {"Property": "Date Range", "Value": f"{meta.date_start} to {meta.date_end}"},
            {"Property": "Buildings Available", "Value": ", ".join(meta.buildings)},
            {"Property": "Ground-Truth Labels Present", "Value": "Yes (anomaly_flag)" if meta.has_ground_truth_labels else "No (Unlabeled Dataset)"},
            {"Property": "Labeled Anomaly Types", "Value": str(meta.anomaly_types) if meta.anomaly_types else "None"},
            {"Property": "Available Columns", "Value": ", ".join(meta.available_columns)},
        ]
        st.dataframe(pd.DataFrame(audit_data), use_container_width=True, hide_index=True)

    # =========================================================================
    # TAB 2: ENERGY FORECASTING BENCHMARK
    # =========================================================================
    with tab_forecast:
        st.subheader("Energy Forecasting Regression Benchmark")
        st.caption("Compares 15-minute rolling horizon predictions using identical chronological training and evaluation windows.")

        run_forecast_btn = st.button("🚀 Run Energy Forecasting Benchmark", key="btn_forecast")

        if run_forecast_btn or "forecast_result" in st.session_state:
            if run_forecast_btn:
                with st.spinner("Executing chronological energy forecasting models..."):
                    fc_bench = EnergyForecastingBenchmark(
                        train_ratio=train_ratio,
                        val_ratio=val_ratio,
                        test_ratio=test_ratio,
                    )
                    res_fc = fc_bench.run(df, selected_buildings=selected_buildings, max_test_samples_per_building=1000)
                    st.session_state["forecast_result"] = res_fc
            else:
                res_fc = st.session_state["forecast_result"]

            st.markdown(f"**Evaluated Test Samples:** `{res_fc.sample_count:,}` across `{len(selected_buildings)}` buildings.")
            st.markdown(f"**Chronological Boundary:** Train End: `{res_fc.train_end_timestamp}` | Test Start: `{res_fc.test_start_timestamp}`")

            # Metrics Table
            st.markdown("#### Comparative Regression Metrics")
            st.dataframe(
                res_fc.metrics_table.style.format({
                    "MAE (kWh)": "{:.3f}",
                    "RMSE (kWh)": "{:.3f}",
                    "R² Score": "{:.4f}",
                    "MAPE (%)": "{:.2f}%",
                    "Max Absolute Error (kWh)": "{:.2f}",
                    "Evaluation Samples": "{:,}",
                }).highlight_min(subset=["MAE (kWh)", "RMSE (kWh)", "MAPE (%)"], color="rgba(0, 240, 181, 0.25)")
                .highlight_max(subset=["R² Score"], color="rgba(0, 240, 181, 0.25)"),
                use_container_width=True,
                hide_index=True,
            )

            col_fc1, col_fc2 = st.columns(2)
            with col_fc1:
                st.markdown("#### Actual vs Predicted Energy Load")
                plot_samples = min(200, len(res_fc.y_true))
                plot_df = pd.DataFrame({
                    "Timestamp": res_fc.timestamps[:plot_samples],
                    "Actual (kWh)": res_fc.y_true[:plot_samples],
                })
                for m_name, p_vals in res_fc.predictions.items():
                    plot_df[m_name] = p_vals[:plot_samples]

                fig_fc = px.line(
                    plot_df, x="Timestamp", y=plot_df.columns[1:],
                    title="Chronological Telemetry vs Predictions (First 200 Test Intervals)",
                    color_discrete_sequence=["#FFFFFF", "#00F0B5", "#38BDF8", "#F59E0B", "#A855F7"],
                )
                fig_fc.update_layout(
                    template="plotly_dark",
                    plot_bgcolor="#0B1118",
                    paper_bgcolor="#151F2C",
                    margin=dict(l=20, r=20, t=40, b=20),
                    legend=dict(orientation="h", yanchor="bottom", y=-0.4, xanchor="center", x=0.5),
                )
                st.plotly_chart(fig_fc, use_container_width=True)

            with col_fc2:
                st.markdown("#### Forecast Residual Error Distributions")
                res_df = pd.DataFrame({
                    "Seasonal-Naive Residual": res_fc.y_true - res_fc.predictions["7-Day Seasonal-Naive (Lag 672)"],
                    "Persistence Residual": res_fc.y_true - res_fc.predictions["Previous-Interval Persistence (Lag 1)"],
                    "DIF Baseline Residual": res_fc.y_true - res_fc.predictions["EstateIQ Seasonal Baseline Profile"],
                })
                fig_res = px.histogram(
                    res_df, barmode="overlay", nbins=50,
                    title="Error Residuals: (Actual - Predicted) in kWh",
                    color_discrete_sequence=["#38BDF8", "#F59E0B", "#00F0B5"],
                )
                fig_res.update_layout(
                    template="plotly_dark",
                    plot_bgcolor="#0B1118",
                    paper_bgcolor="#151F2C",
                    margin=dict(l=20, r=20, t=40, b=20),
                    legend=dict(orientation="h", yanchor="bottom", y=-0.4, xanchor="center", x=0.5),
                )
                st.plotly_chart(fig_res, use_container_width=True)

            if not res_fc.per_building_metrics.empty:
                st.markdown("#### Per-Building Breakdown")
                st.dataframe(res_fc.per_building_metrics, use_container_width=True, hide_index=True)

            st.info(f"ℹ️ **Horizon & Protocol:** {res_fc.horizon_description}")

    # =========================================================================
    # TAB 3: ANOMALY DETECTION BENCHMARK
    # =========================================================================
    with tab_anomaly:
        st.subheader("Anomaly Detection & Classification Benchmark")
        st.caption("Evaluates candidate detectors on labeled facility anomaly events. Emphasizes Precision, Recall, and F1 because anomalies represent <0.1% of intervals.")

        if not meta.has_ground_truth_labels:
            st.warning("⚠️ The current dataset does not contain ground-truth anomaly labels (`anomaly_flag`). Classification metrics cannot be computed.")
            st.stop()

        run_anom_btn = st.button("🚀 Run Anomaly Detection Benchmark", key="btn_anom")

        if run_anom_btn or "anomaly_result" in st.session_state:
            if run_anom_btn:
                with st.spinner("Executing anomaly detectors across candidate models..."):
                    bench_mode = "episodes" if "Episodes" in anomaly_mode else "full_test"
                    anom_bench = AnomalyDetectionBenchmark(
                        default_threshold=dif_threshold,
                        min_persistence_streak=2 if enable_persistence else 1,
                    )
                    res_anom = anom_bench.run(
                        df,
                        mode=bench_mode,
                        selected_buildings=selected_buildings,
                        threshold=dif_threshold,
                        enable_ablations=enable_ablations,
                    )
                    st.session_state["anomaly_result"] = res_anom
            else:
                res_anom = st.session_state["anomaly_result"]

            st.markdown(
                f"""
                <div class="callout-box">
                    <strong>Evaluation Mode:</strong> <code>{res_anom.evaluation_mode}</code> &bull;
                    <strong>Threshold:</strong> <code>{res_anom.threshold_used}/100</code> &bull;
                    <strong>Total Samples:</strong> <code>{res_anom.sample_count:,}</code> &bull;
                    <strong>Positive Anomaly Intervals:</strong> <code>{res_anom.positive_count}</code><br>
                    <em>Note on Class Imbalance:</em> Because normal facility telemetry exceeds 99% of readings, 
                    <strong>Precision, Recall (Sensitivity), F1-Score, and PR-AUC</strong> are the decisive evaluation metrics. 
                    Raw accuracy alone is misleading (predicting all-zero trivially achieves >99% accuracy).
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Main Anomaly Detection Metrics Table
            st.markdown("#### Comparative Anomaly Classification Table")
            st.dataframe(
                res_anom.metrics_table.style.format({
                    "Precision": "{:.4f}",
                    "Recall (Sensitivity)": "{:.4f}",
                    "F1-Score": "{:.4f}",
                    "Balanced Accuracy": "{:.4f}",
                    "ROC-AUC": lambda x: f"{x:.4f}" if pd.notna(x) else "N/A",
                    "PR-AUC": lambda x: f"{x:.4f}" if pd.notna(x) else "N/A",
                    "False-Positive Rate": "{:.4f}",
                    "Raw Accuracy": "{:.4f}",
                    "Event Detection Rate": lambda x: f"{x*100:.1f}%" if pd.notna(x) else "N/A",
                    "Mean Delay (min)": lambda x: f"{x:.1f}m" if pd.notna(x) else "N/A",
                    "TP": "{:,}", "FP": "{:,}", "TN": "{:,}", "FN": "{:,}",
                }).highlight_max(subset=["Precision", "Recall (Sensitivity)", "F1-Score", "Balanced Accuracy"], color="rgba(0, 240, 181, 0.25)")
                .highlight_min(subset=["False-Positive Rate", "FP"], color="rgba(0, 240, 181, 0.25)"),
                use_container_width=True,
                hide_index=True,
            )

            # Confusion Matrix Visualizations
            st.markdown("#### Confusion Matrices (Interval Level)")
            cm_cols = st.columns(min(3, len(res_anom.algorithm_outputs)))
            for i, (algo_name, algo_out) in enumerate(res_anom.algorithm_outputs.items()):
                with cm_cols[i % len(cm_cols)]:
                    cm = algo_out.metrics["confusion_matrix"]
                    cm_matrix = [[cm["tn"], cm["fp"]], [cm["fn"], cm["tp"]]]
                    fig_cm = px.imshow(
                        cm_matrix,
                        text_auto=True,
                        labels=dict(x="Predicted Class", y="Actual Class", color="Count"),
                        x=["Normal (0)", "Anomaly (1)"],
                        y=["Normal (0)", "Anomaly (1)"],
                        title=f"{algo_name[:28]}...",
                        color_continuous_scale="Tealgrn",
                    )
                    fig_cm.update_layout(
                        height=240,
                        margin=dict(l=10, r=10, t=35, b=10),
                        template="plotly_dark",
                        paper_bgcolor="#151F2C",
                    )
                    st.plotly_chart(fig_cm, use_container_width=True)

            # ROC & PR Curves
            st.markdown("#### ROC Curves & Precision-Recall Curves")
            roc_col1, roc_col2 = st.columns(2)
            with roc_col1:
                fig_roc = go.Figure()
                fig_roc.add_shape(type="line", line=dict(dash="dash", color="#64748B"), x0=0, x1=1, y0=0, y1=1)
                for a_name, a_out in res_anom.algorithm_outputs.items():
                    if a_out.y_scores is not None and np.any(res_anom.y_true == 1):
                        fprs = [0.0, a_out.metrics["false_positive_rate"], 1.0]
                        tprs = [0.0, a_out.metrics["recall"], 1.0]
                        fig_roc.add_trace(go.Scatter(x=fprs, y=tprs, mode="lines+markers", name=f"{a_name[:24]} (AUC={a_out.metrics.get('roc_auc') or 0:.3f})"))
                fig_roc.update_layout(
                    title="Receiver Operating Characteristic (ROC)",
                    xaxis_title="False Positive Rate",
                    yaxis_title="True Positive Rate (Recall)",
                    template="plotly_dark",
                    plot_bgcolor="#0B1118",
                    paper_bgcolor="#151F2C",
                    margin=dict(l=20, r=20, t=40, b=20),
                    legend=dict(orientation="h", yanchor="bottom", y=-0.4, xanchor="center", x=0.5),
                )
                st.plotly_chart(fig_roc, use_container_width=True)

            with roc_col2:
                fig_pr = go.Figure()
                for a_name, a_out in res_anom.algorithm_outputs.items():
                    if a_out.y_scores is not None and np.any(res_anom.y_true == 1):
                        recalls = [0.0, a_out.metrics["recall"], 1.0]
                        precs = [1.0, a_out.metrics["precision"], a_out.metrics["positive_count"]/a_out.metrics["sample_count"]]
                        fig_pr.add_trace(go.Scatter(x=recalls, y=precs, mode="lines+markers", name=f"{a_name[:24]} (AP={a_out.metrics.get('pr_auc') or 0:.3f})"))
                fig_pr.update_layout(
                    title="Precision-Recall Curve (PR)",
                    xaxis_title="Recall (Sensitivity)",
                    yaxis_title="Precision",
                    template="plotly_dark",
                    plot_bgcolor="#0B1118",
                    paper_bgcolor="#151F2C",
                    margin=dict(l=20, r=20, t=40, b=20),
                    legend=dict(orientation="h", yanchor="bottom", y=-0.4, xanchor="center", x=0.5),
                )
                st.plotly_chart(fig_pr, use_container_width=True)

    # =========================================================================
    # TAB 4: COMPLEXITY & RUNTIME BENCHMARK
    # =========================================================================
    with tab_runtime:
        st.subheader("Computational Complexity & Runtime Benchmarking")
        st.caption("Distinguishes theoretical Big-O asymptotic complexity from measured wall-clock hardware latency.")

        st.markdown(
            """
            <div class="callout-warning">
                <strong>⚠️ Scientific Rigor Notice (Big-O vs Empirical Runtime):</strong><br>
                Theoretical Big-O describes the asymptotic resource scaling of an algorithm as input size <code>N → ∞</code>.
                Empirical runtime (microseconds / milliseconds) measures wall-clock execution on a specific CPU architecture,
                subject to Python interpreter overhead, cache locality, and OS thread scheduling.
                <strong>An empirical runtime measurement on one machine must never be presented as proof of asymptotic Big-O complexity.</strong>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("#### 1. Audited Theoretical Complexity Table (Derived from Code)")
        spec_list = ComplexityBenchmark.get_theoretical_specifications()
        spec_df = pd.DataFrame([
            {
                "Algorithm": s.algorithm_name,
                "Stage": s.stage,
                "Offline Fit Time": s.offline_fit_time,
                "Online Scoring Time": s.online_inference_time,
                "Fitted State Space": s.fitted_state_space,
                "Working Memory": s.per_event_working_memory,
                "Key Implementation Assumptions": s.key_assumptions,
            }
            for s in spec_list
        ])
        st.dataframe(spec_df, use_container_width=True, hide_index=True)

        st.markdown("#### 2. Empirical Latency & Throughput Benchmark")
        emp_sample_size = st.slider("Benchmark Sample Count:", min_value=500, max_value=10000, value=2000, step=500)
        run_runtime_btn = st.button("⚡ Measure Runtime & Scaling on This Machine", key="btn_runtime")

        if run_runtime_btn or "runtime_results" in st.session_state:
            if run_runtime_btn:
                with st.spinner("Executing isolated high-resolution timing harnesses..."):
                    c_bench = ComplexityBenchmark()
                    emp_res = c_bench.run_empirical_benchmark(df, sample_size=emp_sample_size, warmup_count=50)
                    scale_res = c_bench.run_scaling_experiment(df, sample_sizes=[500, 1000, 2500, 5000])
                    st.session_state["runtime_results"] = emp_res
                    st.session_state["scaling_results"] = scale_res
            else:
                emp_res = st.session_state["runtime_results"]
                scale_res = st.session_state["scaling_results"]

            emp_df = pd.DataFrame([
                {
                    "Algorithm": r.algorithm_name,
                    "Fit Time (ms)": r.fit_duration_ms,
                    "Total Inference (ms)": r.total_inference_ms,
                    "Median Latency (μs)": r.median_latency_us,
                    "p95 Latency (μs)": r.p95_latency_us,
                    "p99 Latency (μs)": r.p99_latency_us,
                    "Throughput (events/sec)": r.throughput_events_per_sec,
                    "Peak Memory (KB)": r.peak_memory_kb,
                    "Timed Samples": r.sample_count,
                }
                for r in emp_res
            ])

            st.dataframe(
                emp_df.style.format({
                    "Fit Time (ms)": "{:.2f} ms",
                    "Total Inference (ms)": "{:.2f} ms",
                    "Median Latency (μs)": "{:.1f} μs",
                    "p95 Latency (μs)": "{:.1f} μs",
                    "p99 Latency (μs)": "{:.1f} μs",
                    "Throughput (events/sec)": "{:,.1f}",
                    "Peak Memory (KB)": "{:.1f} KB",
                    "Timed Samples": "{:,}",
                }).highlight_max(subset=["Throughput (events/sec)"], color="rgba(0, 240, 181, 0.25)")
                .highlight_min(subset=["Median Latency (μs)", "p95 Latency (μs)"], color="rgba(0, 240, 181, 0.25)"),
                use_container_width=True,
                hide_index=True,
            )

            # Empirical Scaling Plots
            st.markdown("#### 3. Empirical Scaling Curves (Input Size N vs Execution Time & Memory)")
            col_sc1, col_sc2 = st.columns(2)
            with col_sc1:
                sc_time_df = pd.DataFrame(scale_res.results_by_algorithm)
                sc_time_df["Dataset Size (N)"] = scale_res.sizes
                fig_scale_time = px.line(
                    sc_time_df, x="Dataset Size (N)", y=list(scale_res.results_by_algorithm.keys()),
                    title="Dataset Size (N) vs Total Fitting & Scoring Time (ms)",
                    markers=True,
                    color_discrete_sequence=["#00F0B5", "#38BDF8", "#F59E0B", "#A855F7"],
                )
                fig_scale_time.update_layout(
                    template="plotly_dark",
                    plot_bgcolor="#0B1118",
                    paper_bgcolor="#151F2C",
                    margin=dict(l=20, r=20, t=40, b=20),
                    yaxis_title="Execution Time (ms)",
                    legend=dict(orientation="h", yanchor="bottom", y=-0.4, xanchor="center", x=0.5),
                )
                st.plotly_chart(fig_scale_time, use_container_width=True)

            with col_sc2:
                sc_mem_df = pd.DataFrame(scale_res.memory_by_algorithm)
                sc_mem_df["Dataset Size (N)"] = scale_res.sizes
                fig_scale_mem = px.line(
                    sc_mem_df, x="Dataset Size (N)", y=list(scale_res.memory_by_algorithm.keys()),
                    title="Dataset Size (N) vs Peak Working Memory (KB)",
                    markers=True,
                    color_discrete_sequence=["#00F0B5", "#38BDF8", "#F59E0B", "#A855F7"],
                )
                fig_scale_mem.update_layout(
                    template="plotly_dark",
                    plot_bgcolor="#0B1118",
                    paper_bgcolor="#151F2C",
                    margin=dict(l=20, r=20, t=40, b=20),
                    yaxis_title="Peak Memory (KB)",
                    legend=dict(orientation="h", yanchor="bottom", y=-0.4, xanchor="center", x=0.5),
                )
                st.plotly_chart(fig_scale_mem, use_container_width=True)

    # =========================================================================
    # TAB 5: REPRODUCIBILITY & EXPORT
    # =========================================================================
    with tab_repro:
        st.subheader("Benchmark Artifact Export & Reproducibility Audit")
        st.caption("Export exact audit configurations, metric tables, and environmental specifications.")

        env_info = ComplexityBenchmark.get_system_environment_info()
        repro_dict = {
            "execution_timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "dataset_file": meta.file_path,
            "dataset_sha256": meta.sha256_fingerprint,
            "dataset_total_rows": meta.total_rows,
            "sampling_interval_min": meta.sampling_interval_minutes,
            "provenance": meta.provenance_badge,
            "parameters": {
                "train_ratio": train_ratio,
                "val_ratio": val_ratio,
                "test_ratio": test_ratio,
                "anomaly_threshold": dif_threshold,
                "persistence_gated": enable_persistence,
                "selected_buildings": selected_buildings,
            },
            "environment": env_info,
        }

        col_exp1, col_exp2 = st.columns(2)
        with col_exp1:
            st.markdown("#### JSON Audit Manifest")
            st.json(repro_dict)
            json_str = json.dumps(repro_dict, indent=2)
            st.download_button(
                label="📥 Download Benchmark Audit Config (JSON)",
                data=json_str,
                file_name="estateiq_benchmark_config.json",
                mime="application/json",
            )

        with col_exp2:
            st.markdown("#### Metrics Tables Export")
            if "forecast_result" in st.session_state:
                csv_fc = st.session_state["forecast_result"].metrics_table.to_csv(index=False)
                st.download_button(
                    label="📥 Download Forecasting Metrics (CSV)",
                    data=csv_fc,
                    file_name="estateiq_forecasting_metrics.csv",
                    mime="text/csv",
                )
            if "anomaly_result" in st.session_state:
                csv_anom = st.session_state["anomaly_result"].metrics_table.to_csv(index=False)
                st.download_button(
                    label="📥 Download Anomaly Detection Metrics (CSV)",
                    data=csv_anom,
                    file_name="estateiq_anomaly_metrics.csv",
                    mime="text/csv",
                )
            if "runtime_results" in st.session_state:
                emp_list = [
                    {
                        "Algorithm": r.algorithm_name,
                        "Fit_ms": r.fit_duration_ms,
                        "Inference_ms": r.total_inference_ms,
                        "Median_Latency_us": r.median_latency_us,
                        "p95_Latency_us": r.p95_latency_us,
                        "p99_Latency_us": r.p99_latency_us,
                        "Throughput_eps": r.throughput_events_per_sec,
                        "Peak_Memory_KB": r.peak_memory_kb,
                    }
                    for r in st.session_state["runtime_results"]
                ]
                csv_rt = pd.DataFrame(emp_list).to_csv(index=False)
                st.download_button(
                    label="📥 Download Complexity & Runtime Metrics (CSV)",
                    data=csv_rt,
                    file_name="estateiq_complexity_metrics.csv",
                    mime="text/csv",
                )


if __name__ == "__main__":
    main()

