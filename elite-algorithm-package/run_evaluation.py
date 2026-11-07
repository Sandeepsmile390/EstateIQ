"""Run the corrected, deterministic Elite-DIF evaluation and export evidence."""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from elite_algo.complexity import COMPLEXITY_TABLE, EmpiricalComplexityBenchmark
from elite_algo.evaluator import PackageEvaluator
from elite_algo.visualizer import ChartGenerator

REPORTS_DIR = PACKAGE_ROOT / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def main() -> None:
    results = PackageEvaluator().evaluate_all()
    runtime = EmpiricalComplexityBenchmark.run_benchmark([100, 1000])
    ChartGenerator.generate_all_charts(results)

    summary = results["summary_df"]
    summary.to_csv(REPORTS_DIR / "metrics_summary.csv", index=False)
    serializable = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "facility_dataset/data/raw/energy_readings.csv (simulated/generated)",
        "energy": {k: v for k, v in results["energy_results"].items()
                   if k not in {"y_true", "y_pred_specialist", "y_pred_naive", "y_pred_mean"}},
        "anomaly": {k: v for k, v in results["anomaly_results"].items()
                    if k not in {"y_true", "y_score", "y_pred"}},
        "water": results["water_results"],
        "waste": results["waste_results"],
        "decision_layer": results["decision_results"],
        "complexity_model": COMPLEXITY_TABLE,
        "latency_benchmark": runtime,
    }
    (REPORTS_DIR / "evaluation_results.json").write_text(
        json.dumps(serializable, indent=2, allow_nan=False), encoding="utf-8")

    energy = results["energy_results"]
    anomaly = results["anomaly_results"]
    lines = [
        "# EstateIQ-DIF reproducible evaluation",
        "",
        f"Generated (UTC): {serializable['generated_at_utc']}",
        "",
        "> All source telemetry and anomaly injections in this evaluation are generated/simulated. These results are not evidence of production or real-facility performance.",
        "",
        "## Energy reference forecast",
        "",
        energy.get("evaluation_protocol", "NOT EVALUATED"),
        f"Test interval count: {energy.get('sample_count', 0):,}; test period: {energy.get('test_start')} to {energy.get('test_end')}.",
        "The seasonal-naive reference is not a trained Elite model. It uses the observed value one week earlier for a one-step rolling forecast.",
        "",
        "| Method | MAE (kWh/15 min) | RMSE | R² |",
        "|---|---:|---:|---:|",
        f"| 7-day seasonal naive | {energy['specialist_metrics']['mae']:.4f} | {energy['specialist_metrics']['rmse']:.4f} | {energy['specialist_metrics']['r2']:.4f} |",
        f"| 15-minute persistence | {energy['naive_metrics']['mae']:.4f} | {energy['naive_metrics']['rmse']:.4f} | {energy['naive_metrics']['r2']:.4f} |",
        f"| Training mean | {energy['mean_metrics']['mae']:.4f} | {energy['mean_metrics']['rmse']:.4f} | {energy['mean_metrics']['r2']:.4f} |",
        "",
        "![Chronological energy forecast references](../charts/energy_forecast_references.svg)",
        "",
        "## Anomaly episode evaluation",
        "",
        anomaly.get("evaluation_protocol", anomaly.get("reason", "NOT EVALUATED")),
        f"Sample count: {anomaly.get('sample_count', 0)}; positives: {anomaly.get('positive_count', 0)}; threshold: {anomaly.get('threshold', 'n/a')}.",
        f"Precision {anomaly.get('precision')}; recall {anomaly.get('recall')}; F1 {anomaly.get('f1_score')}; FPR {anomaly.get('false_positive_rate')}; ROC-AUC {anomaly.get('roc_auc')}; average precision {anomaly.get('average_precision')}.",
        "The score threshold was fixed before the evaluated labels. This event-window point metric does not measure event-level detection delay. The two generated episodes are too few to support generalization claims.",
        "",
        "![Observed confusion matrix](../charts/anomaly_confusion_matrix.svg)",
        "",
        "![Computed ROC and precision-recall curves](../charts/anomaly_roc_pr.svg)",
        "",
        "## Not evaluated",
        "",
        f"- Water specialist inference: {results['water_results']['reason']}",
        f"- Waste specialist inference: {results['waste_results']['reason']}",
        f"- Decision-level accuracy: {results['decision_results']['reason']}",
        "",
        "## Complexity model",
        "",
        "| Stage | Time | Space | Assumptions |",
        "|---|---|---|---|",
    ]
    for row in COMPLEXITY_TABLE:
        lines.append(f"| {row['stage']} | {row['time_complexity']} | {row['space_complexity']} | {row['assumptions']} |")
    lines += ["", "## Empirical runtime microbenchmark", ""]
    for row in runtime:
        lines.append(f"- N={row['sample_count']}: median {row['median_latency_ms']} ms, p95 {row['p95_latency_ms']} ms, p99 {row['p99_latency_ms']} ms, throughput {row['throughput_events_per_sec']} events/s ({row['environment']}).")
    lines += ["", "![Implemented decision path](../charts/dif_pipeline.svg)", ""]
    (REPORTS_DIR / "evaluation_report.md").write_text("\n".join(lines), encoding="utf-8")
    print(REPORTS_DIR / "evaluation_report.md")


if __name__ == "__main__":
    main()
