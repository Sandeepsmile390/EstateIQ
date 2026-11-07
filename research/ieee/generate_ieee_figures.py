"""Generate publication-grade figures for the IEEE EstateIQ-DIF research paper."""
import os
import tempfile
os.environ['MPLCONFIGDIR'] = tempfile.gettempdir()

import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

import sys
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / 'elite-algorithm-package') not in sys.path:
    sys.path.insert(0, str(ROOT / 'elite-algorithm-package'))

from elite_algo.evaluator import PackageEvaluator

FIG_DIR = ROOT / 'research/ieee/figures'
FIG_DIR.mkdir(parents=True, exist_ok=True)

# Publication style
plt.rcParams.update({
    'font.family': 'serif',
    'font.serif': ['Times New Roman', 'Times', 'DejaVu Serif'],
    'font.size': 8.5,
    'axes.labelsize': 8.5,
    'axes.titlesize': 9.0,
    'xtick.labelsize': 7.5,
    'ytick.labelsize': 7.5,
    'legend.fontsize': 7.5,
    'figure.titlesize': 9.5,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'axes.grid': True,
    'grid.alpha': 0.35,
    'grid.linestyle': '--',
    'axes.edgecolor': '#333333',
    'axes.linewidth': 0.7,
})

COLORS = {
    'primary': '#17324D',
    'teal': '#168C83',
    'coral': '#D9534F',
    'blue': '#2E6B9E',
    'amber': '#C78328',
    'gray': '#6B7C8A',
    'light_bg': '#F4F7F9',
}

# Load evaluation results
EVAL_PATH = ROOT / 'elite-algorithm-package/reports/evaluation_results.json'
EVAL_DATA = json.loads(EVAL_PATH.read_text(encoding='utf-8'))
ENERGY = EVAL_DATA['energy']
ANOMALY = EVAL_DATA['anomaly']
BENCH = EVAL_DATA['latency_benchmark']

# Load baseline profiles for Fig 2
BASELINE_PATH = ROOT / 'models/dif_baseline.json'
BASELINE_DATA = json.loads(BASELINE_PATH.read_text(encoding='utf-8'))


def plot_fig1_architecture():
    """Fig. 1: Architectural schematic of EstateIQ-DIF."""
    fig, ax = plt.subplots(figsize=(6.8, 2.4), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 42)
    ax.axis('off')

    # Boxes: (x, y, w, h, title, subtitle, color)
    boxes = [
        (2, 22, 13, 16, "1. Ingestion", "15-min Telemetry\n$x_t = (b, t, y_t, T_t)$", "#EAEFF4", "#17324D"),
        (18, 22, 15, 16, "2. Seasonal Baseline", "Group $G(b, s)$\n$m_{(b,s)}, \\sigma_{(b,s)}$", "#E6F4F1", "#168C83"),
        (36, 22, 16, 16, "3. Screening Filter", "Standardized $z_t$\nEarly exit: $|z_t|<1.875$", "#E6F4F1", "#168C83"),
        (55, 22, 15, 16, "4. Domain Rules", "Off-peak surge,\nHVAC, Power Factor", "#FFF3E6", "#C78328"),
        (73, 22, 12, 16, "5. Fusion", "Weighted score\n$S = 0.8C + 0.2R$", "#EAEFF4", "#17324D"),
        (88, 22, 10, 16, "6. Persistence", "Streak $\\geq 2$\nDebounce", "#FDF2E9", "#D35400"),
        (73, 2, 25, 14, "7. Decision Layer", "Surge kW, Avoidable Cost Scenario,\nCost of Inaction $\\Phi_{\\mathrm{annual}}$", "#F4F6F7", "#5D6D7E"),
    ]

    for x, y, w, h, t1, t2, bg, border in boxes:
        rect = matplotlib.patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.3", facecolor=bg, edgecolor=border, linewidth=1.1)
        ax.add_patch(rect)
        ax.text(x + w/2, y + h - 3.2, t1, ha='center', va='center', fontweight='bold', fontsize=7.2, color=border)
        ax.text(x + w/2, y + (h - 4)/2, t2, ha='center', va='center', fontsize=5.8, color='#2C3E50')

    # Arrows
    arrows = [
        (15, 30, 18, 30),
        (33, 30, 36, 30),
        (52, 30, 55, 30),
        (70, 30, 73, 30),
        (85, 30, 88, 30),
        (85, 22, 85, 16),
    ]
    for x1, y1, x2, y2 in arrows:
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="->", color="#17324D", lw=1.2))

    # Fast-path arrow from stage 3 to exit
    ax.annotate('', xy=(44, 12), xytext=(44, 22),
                arrowprops=dict(arrowstyle="->", color="#168C83", lw=1.0, ls="--"))
    ax.text(44, 8, "Fast Path A (Early Exit)\nNormal event; zero score", ha='center', va='center',
            fontsize=5.5, color='#168C83', style='italic',
            bbox=dict(boxstyle="square,pad=0.3", fc="#E8F8F5", ec="#168C83", lw=0.6))

    plt.tight_layout()
    fig.savefig(FIG_DIR / 'fig1_dif_architecture.png', dpi=300, bbox_inches='tight')
    plt.close(fig)
    print("Generated Fig 1: Architecture")


def plot_fig2_seasonal_baseline():
    """Fig. 2: 7-Day Diurnal Seasonal Baseline with MAD Scale Bands for BLD003."""
    bld3 = [p for p in BASELINE_DATA['profiles'] if p['building_id'] == 'BLD003']
    bld3 = sorted(bld3, key=lambda x: (x['day_of_week_utc'], x['hour_utc'], x['quarter_minute_utc']))

    x = np.arange(len(bld3))
    m = np.array([p['expected_kwh'] for p in bld3])
    s = np.array([p['scale_kwh'] for p in bld3])

    fig, ax = plt.subplots(figsize=(6.8, 2.2), dpi=300)
    ax.plot(x, m, color='#17324D', lw=1.2, label='Median Baseline $m_{(b,s)}$')
    ax.fill_between(x, m - s, m + s, color='#168C83', alpha=0.25, label='Robust Scale Band $\\pm 1.4826\\cdot\\mathrm{MAD}$')
    ax.fill_between(x, m - 2*s, m + 2*s, color='#168C83', alpha=0.10, label='Two-Scale Band $\\pm 2\\sigma$')

    days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    day_ticks = np.arange(0, 672, 96)
    ax.set_xticks(day_ticks + 48)
    ax.set_xticklabels(days, fontsize=7.5)
    for dt in day_ticks:
        ax.axvline(dt, color='#CCCCCC', lw=0.6, ls=':')

    ax.set_ylabel('Electricity (kWh / 15-min)', fontsize=7.8)
    ax.set_xlabel('Weekly Cycle Interval (UTC Slot $s \\in [0, 671]$)', fontsize=7.8)
    ax.set_xlim(0, 671)
    ax.set_ylim(bottom=0)
    ax.legend(loc='upper right', frameon=True, facecolor='white', framealpha=0.9, fontsize=6.8)

    plt.tight_layout()
    fig.savefig(FIG_DIR / 'fig2_seasonal_baseline.png', dpi=300, bbox_inches='tight')
    plt.close(fig)
    print("Generated Fig 2: Seasonal Baseline Profile")


def plot_fig3_forecast_comparison():
    """Fig. 3: Forecast reference comparison across 50,304 test intervals."""
    methods = ['7-Day Seasonal\nNaive ($y_{t-672}$)', '15-Minute\nPersistence ($y_{t-1}$)', 'Training Split\nMean ($\\bar{y}$)']
    maes = [ENERGY['specialist_metrics']['mae'], ENERGY['naive_metrics']['mae'], ENERGY['mean_metrics']['mae']]
    rmses = [ENERGY['specialist_metrics']['rmse'], ENERGY['naive_metrics']['rmse'], ENERGY['mean_metrics']['rmse']]
    r2s = [ENERGY['specialist_metrics']['r2'], ENERGY['naive_metrics']['r2'], ENERGY['mean_metrics']['r2']]

    x = np.arange(len(methods))
    w = 0.32

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(6.8, 2.1), dpi=300, gridspec_kw={'width_ratios': [1.3, 0.7]})

    # Subplot 1: MAE & RMSE
    r1 = ax1.bar(x - w/2, maes, w, label='MAE (kWh)', color='#168C83', edgecolor='#0E5C56', lw=0.6)
    r2 = ax1.bar(x + w/2, rmses, w, label='RMSE (kWh)', color='#2E6B9E', edgecolor='#1F486B', lw=0.6)
    ax1.set_xticks(x)
    ax1.set_xticklabels(methods, fontsize=6.8)
    ax1.set_ylabel('Error (kWh / 15-min interval)', fontsize=7.5)
    ax1.legend(loc='upper left', frameon=True, fontsize=6.8)
    ax1.set_ylim(0, 16.5)

    for r in r1 + r2:
        h = r.get_height()
        ax1.text(r.get_x() + r.get_width()/2., h + 0.35, f'{h:.2f}', ha='center', va='bottom', fontsize=6.2)

    # Subplot 2: R^2
    bars3 = ax2.bar(x, r2s, width=0.45, color=['#168C83', '#5B88A5', '#A9B7C0'], edgecolor='#333333', lw=0.6)
    ax2.set_xticks(x)
    ax2.set_xticklabels(['7-Day\nNaive', '15-min\nPersist', 'Train\nMean'], fontsize=6.8)
    ax2.set_ylabel('Coefficient of Determination ($R^2$)', fontsize=7.5)
    ax2.set_ylim(0, 1.15)
    for b in bars3:
        h = b.get_height()
        ax2.text(b.get_x() + b.get_width()/2., h + 0.02, f'{h:.4f}', ha='center', va='bottom', fontsize=6.2)

    plt.tight_layout()
    fig.savefig(FIG_DIR / 'fig3_forecast_comparison.png', dpi=300, bbox_inches='tight')
    plt.close(fig)
    print("Generated Fig 3: Forecast Comparison")


def plot_fig4_roc_pr():
    """Fig. 4: ROC and Precision-Recall Curves."""
    res = PackageEvaluator().evaluate_anomaly_detection()
    y = list(map(int, res['y_true']))
    scores = list(map(float, res['y_score']))
    ordered = sorted(zip(scores, y), reverse=True)
    positives = sum(y)
    negatives = len(y) - positives

    fprs, tprs, precisions, recalls = [0.0], [0.0], [1.0], [0.0]
    tp = fp = 0
    i = 0
    while i < len(ordered):
        thresh = ordered[i][0]
        while i < len(ordered) and ordered[i][0] == thresh:
            if ordered[i][1] == 1:
                tp += 1
            else:
                fp += 1
            i += 1
        tpr = tp / max(positives, 1)
        fpr = fp / max(negatives, 1)
        prec = tp / max(tp + fp, 1)
        fprs.append(fpr)
        tprs.append(tpr)
        precisions.append(prec)
        recalls.append(tpr)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(6.8, 2.3), dpi=300)

    # Panel (a): ROC
    ax1.plot(fprs, tprs, color='#168C83', lw=1.6, label=f'DIF Score (AUC = {ANOMALY["roc_auc"]:.4f})')
    ax1.plot([0, 1], [0, 1], color='#888888', lw=0.9, ls='--', label='Random Classifier')
    # Mark threshold 55 operating point (FPR=0.0443, TPR=0.9762)
    ax1.plot(0.0443, 0.9762, 'o', color='#D9534F', markersize=4.5, label='Operating Point ($S \\geq 55$)')
    ax1.set_xlabel('False Positive Rate (1 - Specificity)', fontsize=7.5)
    ax1.set_ylabel('True Positive Rate (Recall)', fontsize=7.5)
    ax1.set_title('(a) Receiver Operating Characteristic (ROC)', fontsize=8.0, fontweight='bold')
    ax1.legend(loc='lower right', frameon=True, fontsize=6.5)
    ax1.set_xlim(-0.02, 1.02)
    ax1.set_ylim(-0.02, 1.05)

    # Panel (b): Precision-Recall
    ax2.plot(recalls, precisions, color='#C78328', lw=1.6, label=f'DIF Score (AP = {ANOMALY["average_precision"]:.4f})')
    base_rate = positives / len(y)
    ax2.axhline(base_rate, color='#888888', lw=0.9, ls='--', label=f'Base Rate ($P={base_rate:.3f}$)')
    # Mark operating point
    ax2.plot(0.9762, 0.7069, 'o', color='#D9534F', markersize=4.5, label='Operating Point ($S \\geq 55$)')
    ax2.set_xlabel('Recall (True Positive Rate)', fontsize=7.5)
    ax2.set_ylabel('Precision (Positive Predictive Value)', fontsize=7.5)
    ax2.set_title('(b) Precision–Recall Characteristic', fontsize=8.0, fontweight='bold')
    ax2.legend(loc='lower left', frameon=True, fontsize=6.5)
    ax2.set_xlim(-0.02, 1.02)
    ax2.set_ylim(-0.02, 1.05)

    plt.tight_layout()
    fig.savefig(FIG_DIR / 'fig4_roc_pr_curves.png', dpi=300, bbox_inches='tight')
    plt.close(fig)
    print("Generated Fig 4: ROC and PR Curves")


def plot_fig5_confusion_matrix():
    """Fig. 5: Confusion matrix heatmap at score threshold 55."""
    cm = ANOMALY['confusion_matrix']
    matrix = np.array([[cm['tn'], cm['fp']], [cm['fn'], cm['tp']]])

    fig, ax = plt.subplots(figsize=(3.2, 2.2), dpi=300)
    cax = ax.matshow(matrix, cmap='Blues', alpha=0.7)

    for i in range(2):
        for j in range(2):
            val = matrix[i, j]
            pct = val / 426.0 * 100.0
            tag = ['TN', 'FP'][j] if i == 0 else ['FN', 'TP'][j]
            color = 'white' if val > 150 else '#17324D'
            ax.text(j, i, f"{val}\n({pct:.1f}%)\n{tag}", ha='center', va='center',
                    fontsize=7.0, fontweight='bold', color=color)

    ax.set_xticks([0, 1])
    ax.set_yticks([0, 1])
    ax.set_xticklabels(['Normal (0)', 'Anomaly (1)'], fontsize=7.2)
    ax.set_yticklabels(['Normal (0)', 'Anomaly (1)'], fontsize=7.2)
    ax.set_xlabel('Predicted Label ($S \\geq 55.0$)', fontsize=7.5, labelpad=5)
    ax.set_ylabel('Actual Ground Truth', fontsize=7.5)
    ax.tick_params(top=True, bottom=False, labeltop=True, labelbottom=False)
    ax.grid(False)

    plt.tight_layout()
    fig.savefig(FIG_DIR / 'fig5_confusion_matrix.png', dpi=300, bbox_inches='tight')
    plt.close(fig)
    print("Generated Fig 5: Confusion Matrix")


def plot_fig6_ablation():
    """Fig. 6: Component Ablation across 4 verified configurations."""
    variants = [
        'Full DIF\n($w_c=0.8, w_r=0.2$)',
        'Residual Only\n($w_c=1.0, w_r=0.0$)',
        'Rules Only\n($w_c=0.0, w_r=1.0$)',
        'Persistence-Gated\n($S\\geq 55 \\wedge n\\geq 2$)'
    ]
    precision = [0.7069, 0.5616, 1.0000, 0.9512]
    recall = [0.9762, 0.9762, 0.3810, 0.9286]
    f1 = [0.8200, 0.7130, 0.5517, 0.9398]

    x = np.arange(len(variants))
    w = 0.25

    fig, ax = plt.subplots(figsize=(6.8, 2.2), dpi=300)
    b1 = ax.bar(x - w, precision, w, label='Precision', color='#168C83', edgecolor='#0E5C56', lw=0.6)
    b2 = ax.bar(x, recall, w, label='Recall', color='#2E6B9E', edgecolor='#1F486B', lw=0.6)
    b3 = ax.bar(x + w, f1, w, label='F1-Score', color='#C78328', edgecolor='#8A5B1C', lw=0.6)

    ax.set_xticks(x)
    ax.set_xticklabels(variants, fontsize=6.8)
    ax.set_ylabel('Metric Score', fontsize=7.5)
    ax.set_ylim(0, 1.18)
    ax.legend(loc='upper right', frameon=True, fontsize=6.8, ncol=3)

    for bars in [b1, b2, b3]:
        for b in bars:
            h = b.get_height()
            ax.text(b.get_x() + b.get_width()/2., h + 0.02, f'{h:.2f}', ha='center', va='bottom', fontsize=5.8)

    plt.tight_layout()
    fig.savefig(FIG_DIR / 'fig6_ablation_study.png', dpi=300, bbox_inches='tight')
    plt.close(fig)
    print("Generated Fig 6: Ablation Study")


def plot_fig7_benchmarks():
    """Fig. 7: Empirical microbenchmark latency percentiles and throughput."""
    ns = [b['sample_count'] for b in BENCH]
    medians = [b['median_latency_ms'] * 1000.0 for b in BENCH]  # to microseconds
    p95s = [b['p95_latency_ms'] * 1000.0 for b in BENCH]
    p99s = [b['p99_latency_ms'] * 1000.0 for b in BENCH]
    tputs = [b['throughput_events_per_sec'] for b in BENCH]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(6.8, 2.0), dpi=300)

    # Latencies in microseconds
    x = np.arange(len(ns))
    w = 0.25
    ax1.bar(x - w, medians, w, label='Median', color='#168C83')
    ax1.bar(x, p95s, w, label='p95', color='#2E6B9E')
    ax1.bar(x + w, p99s, w, label='p99', color='#D9534F')
    ax1.set_xticks(x)
    ax1.set_xticklabels([f'$N={n}$' for n in ns], fontsize=7.2)
    ax1.set_ylabel('Latency ($\\mu$s / event)', fontsize=7.5)
    ax1.set_title('(a) Processing Latency Distribution', fontsize=8.0, fontweight='bold')
    ax1.legend(loc='upper left', frameon=True, fontsize=6.5)

    # Throughput
    ax2.bar(x, tputs, width=0.45, color=['#5B88A5', '#267A73'], edgecolor='#333333', lw=0.6)
    ax2.set_xticks(x)
    ax2.set_xticklabels([f'$N={n}$' for n in ns], fontsize=7.2)
    ax2.set_ylabel('Throughput (events / sec)', fontsize=7.5)
    ax2.set_title('(b) Sustained Single-Thread Throughput', fontsize=8.0, fontweight='bold')
    for i, t in enumerate(tputs):
        ax2.text(i, t + 800, f'{t:.0f} ev/s', ha='center', va='bottom', fontsize=6.5)
    ax2.set_ylim(0, max(tputs) * 1.22)

    plt.tight_layout()
    fig.savefig(FIG_DIR / 'fig7_latency_scaling.png', dpi=300, bbox_inches='tight')
    plt.close(fig)
    print("Generated Fig 7: Latency & Throughput Scaling")


def plot_fig8_sensitivity_and_baselines():
    ext_path = ROOT / 'research/ieee/extended_experiment_results.json'
    if not ext_path.exists():
        print("Skipping Fig 8: extended_experiment_results.json not found")
        return
    data = json.loads(ext_path.read_text(encoding='utf-8'))
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.1, 2.5), dpi=300)
    
    # Panel (a): Threshold sensitivity
    ts = data['threshold_sensitivity']
    thetas = [x['threshold'] for x in ts]
    precs = [x['precision'] for x in ts]
    recs = [x['recall'] for x in ts]
    f1s = [x['f1'] for x in ts]
    
    ax1.plot(thetas, precs, 'o-', color='#168C83', lw=1.5, ms=4, label='Precision')
    ax1.plot(thetas, recs, 's-', color='#2E6B9E', lw=1.5, ms=4, label='Recall')
    ax1.plot(thetas, f1s, '^-', color='#D9534F', lw=1.5, ms=4, label='F1-Score')
    ax1.axvline(55.0, color='#6B7C8A', ls='--', lw=1.0, alpha=0.8, label=r'Operating $\theta=55$')
    ax1.set_xlabel('Anomaly Score Threshold ($\\theta$)', fontsize=8.0)
    ax1.set_ylabel('Metric Value', fontsize=8.0)
    ax1.set_title('(a) Threshold Sensitivity ($\\theta \\in [30, 80]$)', fontsize=8.5, fontweight='bold')
    ax1.set_ylim(0.2, 1.05)
    ax1.legend(loc='lower left', frameon=True, fontsize=6.8)
    
    # Panel (b): Baseline comparisons
    bc = data['baselines_comparison']
    models = ['EstateIQ-DIF', 'Gaussian Seasonal', 'Rolling Z-Score', 'Static P99']
    keys = ['EstateIQ-DIF (Proposed)', 'Seasonal Mean + Std (Gaussian Non-Robust)', 'Rolling 7-Day Z-Score (z >= 3.0)', 'Static Historical P99 Threshold']
    b_precs = [bc[k]['precision'] for k in keys]
    b_recs = [bc[k]['recall'] for k in keys]
    b_f1s = [bc[k]['f1'] for k in keys]
    
    x = np.arange(len(models))
    w = 0.25
    ax2.bar(x - w, b_precs, w, label='Precision', color='#168C83')
    ax2.bar(x, b_recs, w, label='Recall', color='#2E6B9E')
    ax2.bar(x + w, b_f1s, w, label='F1-Score', color='#D9534F')
    ax2.set_xticks(x)
    ax2.set_xticklabels(models, fontsize=6.5, rotation=10)
    ax2.set_ylabel('Score', fontsize=8.0)
    ax2.set_title('(b) Baseline Comparison on Same Windows', fontsize=8.5, fontweight='bold')
    ax2.set_ylim(0.0, 1.15)
    ax2.legend(loc='upper right', frameon=True, fontsize=6.8)
    
    plt.tight_layout()
    fig.savefig(FIG_DIR / 'fig8_sensitivity_and_baselines.png', dpi=300, bbox_inches='tight')
    plt.close(fig)
    print("Generated Fig 8: Sensitivity & Baselines Comparison")


def main():
    plot_fig1_architecture()
    plot_fig2_seasonal_baseline()
    plot_fig3_forecast_comparison()
    plot_fig4_roc_pr()
    plot_fig5_confusion_matrix()
    plot_fig6_ablation()
    plot_fig7_benchmarks()
    plot_fig8_sensitivity_and_baselines()
    print("All 8 IEEE publication figures successfully generated in:", FIG_DIR)


if __name__ == '__main__':
    main()
