from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch
from sklearn.metrics import precision_recall_curve, roc_curve, roc_auc_score, average_precision_score

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "elite-algorithm-package"))
from elite_algo.evaluator import PackageEvaluator


OUT = Path(__file__).resolve().parents[1] / "output" / "presentation"
OUT.mkdir(parents=True, exist_ok=True)

BG = "#e7f4ee"
TEAL = "#087e78"
DEEP = "#123d48"
MINT = "#d5eee4"
CARD = "#ffffff"
MUTED = "#557078"
GOLD = "#f2c96d"
RED = "#c85a52"
BLUE = "#57a6d8"


def canvas(title, subtitle, title_size=23):
    fig = plt.figure(figsize=(16, 9), dpi=160, facecolor=BG)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 16); ax.set_ylim(0, 9); ax.axis("off")
    ax.add_patch(FancyBboxPatch((5.0, 8.25), 6.0, .52, boxstyle="round,pad=0.03,rounding_size=.12", fc=TEAL, ec="none"))
    ax.text(8, 8.51, title, ha="center", va="center", color="white", fontsize=title_size, weight="bold")
    ax.text(8, 8.03, subtitle, ha="center", va="center", color=DEEP, fontsize=11.5, weight="medium")
    ax.text(15.55, 8.52, "BPUT HACKATHON\n2026", ha="right", va="center", color="#ef8a21", fontsize=12, weight="bold", linespacing=.9)
    return fig, ax


def card(ax, x, y, w, h, title, letter=None):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.035,rounding_size=.12", fc=CARD, ec="#c6ddd4", lw=1.2))
    if letter:
        ax.add_patch(plt.Circle((x+.32, y+h-.34), .20, color=TEAL))
        ax.text(x+.32, y+h-.34, letter, color="white", ha="center", va="center", fontsize=10, weight="bold")
        tx = x+.64
    else: tx = x+.22
    ax.text(tx, y+h-.34, title, color=DEEP, va="center", fontsize=12, weight="bold")


def metrics_page(results):
    energy = results["energy_results"]
    anomaly = results["anomaly_results"]
    y, scores = np.asarray(anomaly["y_true"], dtype=int), np.asarray(anomaly["y_score"], dtype=float)
    fpr, tpr, _ = roc_curve(y, scores)
    precision, recall, _ = precision_recall_curve(y, scores)
    auc, ap = roc_auc_score(y, scores), average_precision_score(y, scores)
    fig, ax = canvas("ALGORITHM METRICS", "EstateIQ-DIF | Reproducible evaluation on generated telemetry")

    card(ax, .45, 4.75, 7.25, 2.9, "Forecast reference comparison (kWh / 15-min interval)", "A")
    p = fig.add_axes([.095, .61, .39, .16], facecolor="white")
    names = ["7-day seasonal\nnaive reference", "15-min\npersistence", "Training split\nmean"]
    groups = [energy["specialist_metrics"], energy["naive_metrics"], energy["mean_metrics"]]
    xx = np.arange(3); width = .32
    p.bar(xx-width/2, [g["mae"] for g in groups], width, color="#42b9bd", label="MAE")
    p.bar(xx+width/2, [g["rmse"] for g in groups], width, color="#75a9ee", label="RMSE")
    for i, g in enumerate(groups):
        p.text(i-width/2, g["mae"]+.25, f"{g['mae']:.2f}", ha="center", fontsize=7)
        p.text(i+width/2, g["rmse"]+.25, f"{g['rmse']:.2f}", ha="center", fontsize=7)
    p.set_xticks(xx, names, fontsize=8); p.set_ylabel("Error (kWh)", fontsize=8)
    p.tick_params(axis="y", labelsize=8); p.grid(axis="y", alpha=.2); p.legend(frameon=False, ncol=2, fontsize=8)
    p.spines[["top", "right"]].set_visible(False)
    ax.text(.75, 4.96, "7-day seasonal naive is a reference baseline, not a trained Elite model.", color=MUTED, fontsize=8.5)

    card(ax, 7.9, 4.75, 7.65, 2.9, "Anomaly ranking curves", "B")
    r = fig.add_axes([.53, .58, .195, .20], facecolor="white")
    r.plot(fpr, tpr, color="#189d8b", lw=2.4, label=f"ROC AUC = {auc:.4f}")
    r.plot([0, 1], [0, 1], color="#8ca0a5", ls="--", lw=1, label="Random")
    r.set(xlim=(0, 1), ylim=(0, 1.02), xlabel="False positive rate", ylabel="True positive rate")
    r.tick_params(labelsize=6); r.xaxis.label.set_size(7); r.yaxis.label.set_size(7); r.grid(alpha=.18); r.legend(frameon=False, fontsize=6, loc="lower right")
    r.spines[["top", "right"]].set_visible(False)
    q = fig.add_axes([.755, .58, .195, .20], facecolor="white")
    q.plot(recall, precision, color="#3699e5", lw=2.4, label=f"Average precision = {ap:.4f}")
    q.axhline(y.mean(), color="#8ca0a5", ls="--", lw=1, label=f"Prevalence = {y.mean():.3f}")
    q.set(xlim=(0, 1), ylim=(0, 1.02), xlabel="Recall", ylabel="Precision")
    q.tick_params(labelsize=6); q.xaxis.label.set_size(7); q.yaxis.label.set_size(7); q.grid(alpha=.18); q.legend(frameon=False, fontsize=6, loc="lower left")
    q.spines[["top", "right"]].set_visible(False)

    card(ax, .45, 1.54, 7.25, 2.86, "Fixed operating point | score threshold 55/100", "C")
    vals = [f"Precision   {anomaly['precision']:.3f}", f"Recall        {anomaly['recall']:.3f}", f"F1 score     {anomaly['f1_score']:.3f}", f"False alarm rate   {anomaly['false_positive_rate']:.3f}"]
    for i, txt in enumerate(vals):
        ax.text(.85, 3.52-i*.42, txt, color=DEEP, fontsize=14, family="DejaVu Sans Mono", weight="bold" if i == 2 else "normal")
    cm = anomaly["confusion_matrix"]
    ax.text(4.5, 3.56, f"{anomaly['sample_count']} labeled windows", color=TEAL, fontsize=14, weight="bold")
    ax.text(4.5, 3.13, f"TP {cm['tp']}     FP {cm['fp']}", color=DEEP, fontsize=12)
    ax.text(4.5, 2.76, f"FN {cm['fn']}      TN {cm['tn']}", color=DEEP, fontsize=12)
    ax.text(4.5, 2.12, "Threshold fixed in config; not tuned on these test labels.", color=MUTED, fontsize=9)

    card(ax, 7.9, 1.54, 7.65, 2.86, "What this evaluation does and does not establish", "D")
    facts = [
        "Energy: 50,304 chronological rolling-origin holdout intervals across 10 generated buildings.",
        "Anomaly: 426 windows around 2 injected episodes; training history precedes each episode.",
        "Electricity only. Water, waste, and operator decisions have no independent held-out evaluation.",
        "These are internal synthetic-data results; they do not establish real-facility accuracy.",
    ]
    for i, t in enumerate(facts):
        ax.text(8.28, 3.55-i*.48, "• " + t, color=DEEP, fontsize=10.2, va="center", wrap=True)
    ax.add_patch(FancyBboxPatch((.45, .63), 15.1, .57, boxstyle="round,pad=.02,rounding_size=.1", fc="#f6e8b7", ec="none"))
    ax.text(8, .91, "BENCHMARK CAVEAT  |  Generated telemetry and injected labels • not validated on live buildings • scores describe this test set only", ha="center", va="center", color="#584b25", fontsize=10, weight="bold")
    ax.text(.5, .27, "ESTATEIQ • FACILITY INTELLIGENCE", color=DEEP, fontsize=8, weight="bold")
    fig.savefig(OUT / "estateiq_algorithm_metrics.png", dpi=160, facecolor=BG)
    plt.close(fig)


def flow_page():
    fig, ax = canvas("ESTATEIQ-DIF | ALGORITHM FLOW", "Measured signals → contextual comparison → evidence score → cadence-aware reporting", title_size=19)
    cards = [
        ("01  INPUTS", ["PZEM-004T: V, A, kW, kWh, PF, Hz", "Water flow: L/min, pulse total", "Ultrasonic: tank/bin distance & fill", "DHT11: temperature, humidity", "MQ-135: raw ADC & sensor voltage", "Simulator and ESP32 share telemetry path"]),
        ("02  DATA QUALITY", ["Validate event fields and ranges", "Check sensor validity / freshness", "Reject or flag unusable readings", "Keep device, timestamp & provenance", "Low quality can halt deeper analysis"]),
        ("03  CONTEXT BASELINE", ["Building + weekday + 15-min slot", "Historical median as expected kWh", "Scale = 1.4826 × MAD (with floors)", "Residual = actual − expected", "Cold-start fallback where profile absent"]),
        ("04  ANOMALY EVIDENCE", ["Context score from |residual / scale|", "Domain-rule signal: 0 or 100", "Score = 0.80 × context + 0.20 × rules", "Default trigger: score ≥ 55 / 100", "Explain evidence and score inputs"]),
        ("05  DECISION & EXPLANATION", ["Fast path for ordinary events", "Escalate larger deviations", "Confidence includes data quality", "AI should explain supplied evidence", "No trained IF / LOF / SHAP in this path"]),
    ]
    x0, gap, w, y, h = .45, .18, 2.88, 4.18, 2.75
    for i, (head, lines) in enumerate(cards):
        x = x0 + i*(w+gap)
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=.035,rounding_size=.12", fc=CARD, ec="#bfd8cf", lw=1.3))
        ax.add_patch(FancyBboxPatch((x, y+h-.55), w, .55, boxstyle="round,pad=.03,rounding_size=.1", fc=TEAL if i in (0, 3) else MINT, ec="none"))
        ax.text(x+.15, y+h-.28, head, color="white" if i in (0, 3) else DEEP, fontsize=10.2, weight="bold", va="center")
        for j, line in enumerate(lines):
            ax.text(x+.16, y+h-.88-j*.34, "• " + line, color=DEEP, fontsize=8.15, va="top", wrap=True)
        if i < len(cards)-1:
            ax.annotate("", xy=(x+w+gap-.03, y+1.35), xytext=(x+w+.02, y+1.35), arrowprops=dict(arrowstyle="-|>", lw=1.6, color="#6b8790"))

    ax.add_patch(FancyBboxPatch((.6, 1.35), 14.8, 1.42, boxstyle="round,pad=.04,rounding_size=.12", fc="#f7faf8", ec="#b9d9cf", lw=1.2))
    ax.text(.9, 2.48, "EDGE REPORTING CADENCE (ESP32)", color=TEAL, fontsize=12, weight="bold")
    stages = [("NORMAL", "15 min reports"), ("ANOMALY", "immediate trigger + 5 min reports"), ("RECOVERY", "5 min reports; 3 normal confirmations"), ("NORMAL", "return to 15 min")]
    centers = [2.35, 6.15, 10.0, 13.65]
    for i, ((a, b), cx) in enumerate(zip(stages, centers)):
        ax.text(cx, 1.99, a, ha="center", color=DEEP, fontsize=11, weight="bold")
        ax.text(cx, 1.64, b, ha="center", color=MUTED, fontsize=8.8)
        if i < 3:
            ax.annotate("", xy=(centers[i+1]-1.05, 1.94), xytext=(cx+1.1, 1.94), arrowprops=dict(arrowstyle="-|>", lw=1.4, color=TEAL))
    ax.text(8, 1.46, "Internal sensor acquisition continues independently of these network reporting intervals.", ha="center", color="#576f69", fontsize=8)

    ax.add_patch(FancyBboxPatch((.6, .52), 14.8, .56, boxstyle="round,pad=.02,rounding_size=.1", fc="#f6e8b7", ec="none"))
    ax.text(8, .8, "SENSOR LIMITS  |  MQ-135 is raw / cross-sensitive response, not certified CO₂, AQI, or PM measurement. Water and waste forecasting are not independently evaluated.", ha="center", va="center", color="#584b25", fontsize=9.2, weight="bold")
    ax.text(.5, .25, "ESTATEIQ • ALGORITHM OVERVIEW", color=DEEP, fontsize=8, weight="bold")
    fig.savefig(OUT / "estateiq_algorithm_architecture.png", dpi=160, facecolor=BG)
    plt.close(fig)


if __name__ == "__main__":
    evaluation = PackageEvaluator().evaluate_all()
    metrics_page(evaluation)
    flow_page()
    print(f"Created: {OUT / 'estateiq_algorithm_metrics.png'}")
    print(f"Created: {OUT / 'estateiq_algorithm_architecture.png'}")
