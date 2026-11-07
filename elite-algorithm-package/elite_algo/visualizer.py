"""Dependency-free SVG plots drawn only from measured evaluation results."""

from html import escape
from pathlib import Path
from typing import Any, Dict, List, Tuple

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
CHARTS_DIR = PACKAGE_ROOT / "charts"
CHARTS_DIR.mkdir(parents=True, exist_ok=True)


def _svg(width: int, height: int, body: str) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}"><rect width="100%" height="100%" fill="white"/>'
            f'<style>text{{font-family:Arial,sans-serif;fill:#243746}} .muted{{fill:#627583}}</style>{body}</svg>')


class ChartGenerator:
    @staticmethod
    def generate_all_charts(results: Dict[str, Any]) -> None:
        ChartGenerator.plot_forecast_comparison(results["energy_results"])
        if results["anomaly_results"].get("status") == "EVALUATED":
            ChartGenerator.plot_anomaly_confusion(results["anomaly_results"])
            ChartGenerator.plot_roc_pr(results["anomaly_results"])
        ChartGenerator.plot_pipeline()

    @staticmethod
    def plot_forecast_comparison(result: Dict[str, Any]) -> None:
        methods = [("7-day seasonal naive", result["specialist_metrics"]["mae"], "#168c83"),
                   ("15-minute persistence", result["naive_metrics"]["mae"], "#5b88a5"),
                   ("Training mean", result["mean_metrics"]["mae"], "#9eabb4")]
        x0, chartw = 190, 380
        maxv = max(v for _, v, _ in methods) * 1.12
        body = '<text x="24" y="28" font-size="16" font-weight="bold">Chronological energy forecast references</text>'
        for tick in range(5):
            x = x0 + chartw * tick / 4
            body += f'<line x1="{x}" y1="52" x2="{x}" y2="180" stroke="#d8e1e6"/><text x="{x}" y="197" text-anchor="middle" class="muted" font-size="10">{maxv*tick/4:.1f}</text>'
        for i, (label, value, color) in enumerate(methods):
            y = 68 + i * 39
            body += f'<text x="{x0-10}" y="{y+15}" text-anchor="end" font-size="11">{escape(label)}</text>'
            body += f'<rect x="{x0}" y="{y}" width="{chartw*value/maxv}" height="22" rx="4" fill="{color}"/>'
            body += f'<text x="{x0+chartw*value/maxv+7}" y="{y+15}" font-size="10">{value:.3f} kWh</text>'
        body += '<text x="380" y="222" text-anchor="middle" class="muted" font-size="10">MAE (kWh per 15-minute interval)</text>'
        body += '<text x="24" y="247" class="muted" font-size="10">Generated telemetry; final chronological 15% holdout; baseline only, not a fitted Elite model.</text>'
        (CHARTS_DIR / "energy_forecast_references.svg").write_text(_svg(650, 265, body), encoding="utf-8")

    @staticmethod
    def plot_anomaly_confusion(result: Dict[str, Any]) -> None:
        cm = result["confusion_matrix"]
        cells = [[cm["tn"], cm["fp"]], [cm["fn"], cm["tp"]]]
        labels = [["True normal / pred normal", "True normal / pred anomaly"],
                  ["True anomaly / pred normal", "True anomaly / pred anomaly"]]
        body = '<text x="20" y="27" font-size="16" font-weight="bold">Injected anomaly windows: point-level confusion</text>'
        for row in range(2):
            for col in range(2):
                x, y = 34 + col * 275, 54 + row * 93
                body += f'<rect x="{x}" y="{y}" width="252" height="76" rx="5" fill="#eaf5f3" stroke="#168c83"/>'
                body += f'<text x="{x+126}" y="{y+28}" text-anchor="middle" class="muted" font-size="10">{labels[row][col]}</text>'
                body += f'<text x="{x+126}" y="{y+60}" text-anchor="middle" font-size="22" font-weight="bold">{cells[row][col]}</text>'
        body += f'<text x="20" y="258" class="muted" font-size="10">N={result["sample_count"]}; positives={result["positive_count"]}; threshold=55/100; two generated episodes.</text>'
        (CHARTS_DIR / "anomaly_confusion_matrix.svg").write_text(_svg(600, 278, body), encoding="utf-8")

    @staticmethod
    def plot_roc_pr(result: Dict[str, Any]) -> None:
        y = list(map(int, result["y_true"])); score = list(map(float, result["y_score"]))
        ordered = sorted(zip(score, y), reverse=True)
        positives = sum(y); negatives = len(y) - positives
        tp = fp = 0; points: List[Tuple[float, float, float]] = [(0.0, 0.0, 1.0)]
        i = 0
        while i < len(ordered):
            threshold = ordered[i][0]
            while i < len(ordered) and ordered[i][0] == threshold:
                tp += ordered[i][1]; fp += 1 - ordered[i][1]; i += 1
            points.append((fp / max(negatives, 1), tp / max(positives, 1), tp / max(tp + fp, 1)))
        def xy(point, x0, y0, size):
            return (x0 + point[0] * size, y0 + (1.0 - point[1]) * size)
        def path(points_to_plot, x0, y0, size, x_idx, y_idx):
            commands=[]
            for j,p in enumerate(points_to_plot):
                xx=x0+p[x_idx]*size; yy=y0+(1-p[y_idx])*size
                commands.append(("M" if j==0 else "L")+f"{xx:.2f},{yy:.2f}")
            return " ".join(commands)
        body = '<text x="20" y="24" font-size="15" font-weight="bold">Curves computed from measured anomaly scores and held-out labels</text>'
        for x0, title, color, xidx, yidx in [(55,"ROC", "#168c83",0,1),(350,"Precision–Recall", "#c78328",1,2)]:
            y0, size = 58, 190
            body += f'<text x="{x0+size/2}" y="45" text-anchor="middle" font-size="12" font-weight="bold">{title}</text>'
            body += f'<rect x="{x0}" y="{y0}" width="{size}" height="{size}" fill="none" stroke="#a9bbc5"/>'
            for tick in range(5):
                v=tick/4; xx=x0+v*size; yy=y0+(1-v)*size
                body += f'<line x1="{xx}" y1="{y0}" x2="{xx}" y2="{y0+size}" stroke="#e4eaee"/>'
                body += f'<line x1="{x0}" y1="{yy}" x2="{x0+size}" y2="{yy}" stroke="#e4eaee"/>'
            if title == "ROC":
                body += f'<path d="M{x0},{y0+size} L{x0+size},{y0}" fill="none" stroke="#82929c" stroke-dasharray="4 4"/>'
            pts=path(points,x0,y0,size,xidx,yidx)
            body += f'<path d="{pts}" fill="none" stroke="{color}" stroke-width="2.5"/>'
        body += f'<text x="20" y="274" class="muted" font-size="10">ROC-AUC={result["roc_auc"]:.4f}; average precision={result["average_precision"]:.4f}; point-based, two generated episodes.</text>'
        (CHARTS_DIR / "anomaly_roc_pr.svg").write_text(_svg(620, 292, body), encoding="utf-8")

    @staticmethod
    def plot_pipeline() -> None:
        nodes = [(30, 68, "Telemetry", "validated input"), (225, 68, "Baseline", "seasonal median/MAD"),
                 (420, 68, "Evidence", "residual + rules"), (420, 176, "Temporal", "bounded persistence"),
                 (225, 176, "Impact", "interval scenario"), (30, 176, "Triage", "priority, advisory")]
        body = '<text x="24" y="28" font-size="16" font-weight="bold">Current Elite-DIF processing path</text>'
        for x, y, title, subtitle in nodes:
            body += f'<rect x="{x}" y="{y}" width="158" height="60" rx="6" fill="#eaf5f3" stroke="#168c83"/>'
            body += f'<text x="{x+79}" y="{y+24}" text-anchor="middle" font-size="12" font-weight="bold">{title}</text>'
            body += f'<text x="{x+79}" y="{y+43}" text-anchor="middle" class="muted" font-size="9">{subtitle}</text>'
        arrows = [(188,98,218,98),(383,98,413,98),(499,132,499,166),(413,206,383,206),(218,206,188,206)]
        for x1,y1,x2,y2 in arrows:
            body += f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#526d7a" stroke-width="1.5" marker-end="url(#arrow)"/>'
        body = '<defs><marker id="arrow" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto"><path d="M0,0 L7,3.5 L0,7 z" fill="#526d7a"/></marker></defs>' + body
        (CHARTS_DIR / "dif_pipeline.svg").write_text(_svg(610, 250, body), encoding="utf-8")
