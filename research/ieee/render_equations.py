"""
Render all 30 display equations for the EstateIQ-DIF research paper into crisp 300 DPI figures.
Replaces raw LaTeX typography with publication-grade mathematical typesetting.
"""
import os
from pathlib import Path
os.environ["MPLCONFIGDIR"] = "C:/Users/SANDEE~1/AppData/Local/Temp/matplotlib_cache"

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
EQ_DIR = ROOT / "research/ieee/equations"
EQ_DIR.mkdir(parents=True, exist_ok=True)

# Mathtext configurations: use STIX (designed for IEEE Times-like math typography)
plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "DejaVu Serif", "STIXGeneral"],
    "mathtext.fontset": "stix",  # Complete IEEE math symbol coverage
})

def render_equation_image(filename: str, latex_str: str, tag_num: int, width_in: float = 3.59, height_in: float = 0.38, fontsize: float = 8.5):
    """Render a single centered display equation with a right-aligned tag number."""
    fig = plt.figure(figsize=(width_in, height_in), dpi=300)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")
    
    # Equation centered
    ax.text(0.48, 0.5, f"${latex_str}$", fontsize=fontsize, ha="center", va="center")
    # Tag right-aligned
    ax.text(0.985, 0.5, f"({tag_num})", fontsize=fontsize - 0.5, ha="right", va="center", family="serif")
    
    out_path = EQ_DIR / filename
    fig.savefig(out_path, dpi=300, transparent=True)
    plt.close(fig)
    return out_path

def render_piecewise_10():
    """Eq (10): HVAC base piecewise function."""
    fig = plt.figure(figsize=(3.59, 0.50), dpi=300)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")
    ax.text(0.18, 0.50, r"$\mathrm{HVAC}_{\mathrm{base}} = $", fontsize=8.2, ha="right", va="center")
    ax.text(0.20, 0.50, "{", fontsize=23, ha="left", va="center", fontname="Times New Roman")
    ax.text(0.25, 0.70, r"$35.0, \quad \mathrm{if } \; 8 \leq \mathrm{hour}_t \leq 18$", fontsize=7.6, ha="left", va="center")
    ax.text(0.25, 0.30, r"$15.0, \quad \mathrm{otherwise}$", fontsize=7.6, ha="left", va="center")
    ax.text(0.985, 0.50, "(10)", fontsize=8.0, ha="right", va="center", family="serif")
    fig.savefig(EQ_DIR / "eq_10.png", dpi=300, transparent=True)
    plt.close(fig)

def render_piecewise_19():
    """Eq (19): Rule score piecewise function."""
    fig = plt.figure(figsize=(3.59, 0.46), dpi=300)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")
    ax.text(0.26, 0.50, r"$R_t = $", fontsize=8.2, ha="right", va="center")
    ax.text(0.28, 0.50, "{", fontsize=22, ha="left", va="center", fontname="Times New Roman")
    ax.text(0.33, 0.70, r"$100.0, \quad \mathrm{if } \; \mathcal{R}_t = 1$", fontsize=7.6, ha="left", va="center")
    ax.text(0.33, 0.30, r"$0.0, \quad \; \mathrm{otherwise}$", fontsize=7.6, ha="left", va="center")
    ax.text(0.985, 0.50, "(19)", fontsize=8.0, ha="right", va="center", family="serif")
    fig.savefig(EQ_DIR / "eq_19.png", dpi=300, transparent=True)
    plt.close(fig)

def render_piecewise_21():
    """Eq (21): Persistence streak tracking piecewise function."""
    fig = plt.figure(figsize=(3.59, 0.68), dpi=300)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")
    ax.text(0.10, 0.50, r"$n_t = $", fontsize=8.2, ha="right", va="center")
    ax.text(0.12, 0.50, "{", fontsize=34, ha="left", va="center", fontname="Times New Roman")
    ax.text(0.17, 0.77, r"$n_{t-1} + 1, \quad \mathrm{if } \; S_t \geq 55.0 \;\wedge\; 0 < (t - t_{\mathrm{last}}) \leq 60.0\mathrm{\,min}$", fontsize=7.0, ha="left", va="center")
    ax.text(0.17, 0.50, r"$1, \quad\quad\quad\; \mathrm{if } \; S_t \geq 55.0 \;\wedge\; (\mathrm{initial} \;\vee\; (t - t_{\mathrm{last}}) > 60.0\mathrm{\,min})$", fontsize=7.0, ha="left", va="center")
    ax.text(0.17, 0.23, r"$0, \quad\quad\quad\; \mathrm{if } \; S_t < 55.0 \;\wedge\; 0 < (t - t_{\mathrm{last}}) \leq 60.0\mathrm{\,min}$", fontsize=7.0, ha="left", va="center")
    ax.text(0.985, 0.50, "(21)", fontsize=8.0, ha="right", va="center", family="serif")
    fig.savefig(EQ_DIR / "eq_21.png", dpi=300, transparent=True)
    plt.close(fig)

def render_piecewise_26():
    """Eq (26): Adaptive Reporting Cadence State Machine."""
    fig = plt.figure(figsize=(3.59, 0.68), dpi=300)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")
    ax.text(0.10, 0.50, r"$\Theta_t = $", fontsize=8.2, ha="right", va="center")
    ax.text(0.12, 0.50, "{", fontsize=34, ha="left", va="center", fontname="Times New Roman")
    ax.text(0.17, 0.77, r"$\mathrm{ANOMALY\_5M}, \quad\;\;\; \mathrm{if } \; A_t = 1 \;\vee\; \mathcal{A}_{\mathrm{edge}} = 1$", fontsize=7.0, ha="left", va="center")
    ax.text(0.17, 0.50, r"$\mathrm{NORMAL\_15M}, \quad\;\;\;\; \mathrm{if } \; A_t = 0 \;\wedge\; c_{\mathrm{rec}}(t) \geq M$", fontsize=7.0, ha="left", va="center")
    ax.text(0.17, 0.23, r"$\mathrm{RECOVERY\_5M}, \quad\;\;\; \mathrm{if } \; A_t = 0 \;\wedge\; 1 \leq c_{\mathrm{rec}}(t) < M$", fontsize=7.0, ha="left", va="center")
    ax.text(0.985, 0.50, "(26)", fontsize=8.0, ha="right", va="center", family="serif")
    fig.savefig(EQ_DIR / "eq_26.png", dpi=300, transparent=True)
    plt.close(fig)

def render_piecewise_27():
    """Eq (27): Reporting Interval and Next Deadline."""
    fig = plt.figure(figsize=(3.59, 0.50), dpi=300)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")
    ax.text(0.15, 0.50, r"$T_{\mathrm{rep}}(\Theta_t) = $", fontsize=8.2, ha="right", va="center")
    ax.text(0.17, 0.50, "{", fontsize=23, ha="left", va="center", fontname="Times New Roman")
    ax.text(0.22, 0.70, r"$900\mathrm{\,s} \; (15\mathrm{\,min}), \quad \mathrm{if } \; \Theta_t = \mathrm{NORMAL\_15M}$", fontsize=7.3, ha="left", va="center")
    ax.text(0.22, 0.30, r"$300\mathrm{\,s} \; (5\mathrm{\,min}), \quad\;\; \mathrm{if } \; \Theta_t \in \{\mathrm{ANOMALY\_5M}, \mathrm{RECOVERY\_5M}\}$", fontsize=7.3, ha="left", va="center")
    ax.text(0.985, 0.50, "(27)", fontsize=8.0, ha="right", va="center", family="serif")
    fig.savefig(EQ_DIR / "eq_27.png", dpi=300, transparent=True)
    plt.close(fig)

def render_all_equations():
    print("Rendering publication-quality equation figures...")
    
    # Eq 1-25
    render_equation_image("eq_1.png", r"\mathrm{MAD} = \mathrm{median}\left(\left|y_i - \mathrm{median}(y)\right|\right)", 1, height_in=0.34)
    render_equation_image("eq_2.png", r"k = \frac{1}{\Phi^{-1}(0.75)} \approx 1.4826", 2, height_in=0.38)
    render_equation_image("eq_3.png", r"x_t = \left(b, t, y_t, \mathrm{hour}_t, \mathrm{dow}_t, \mathrm{quarter}_t, \mathrm{occ}_t, T_t, \mathrm{hvac}_t, \mathrm{PF}_t, \Delta t\right)", 3, height_in=0.34, fontsize=7.5)
    render_equation_image("eq_4.png", r"s(t) = (\mathrm{dow}_{\mathrm{UTC}} \times 96) + (\mathrm{hour}_{\mathrm{UTC}} \times 4) + \left\lfloor \frac{\mathrm{minute}_{\mathrm{UTC}}}{15} \right\rfloor", 4, height_in=0.40, fontsize=7.8)
    render_equation_image("eq_5.png", r"A_t = \mathbf{1}\left(S_t \geq \theta_{\mathrm{anom}}\right)", 5, height_in=0.34)
    render_equation_image("eq_6.png", r"m_{(b, s)} = \mathrm{median}\left(\left\{y_i \mid i \in G(b, s)\right\}\right)", 6, height_in=0.36)
    render_equation_image("eq_7.png", r"\mathrm{MAD}_{(b, s)} = \mathrm{median}\left(\left\{\left|y_i - m_{(b, s)}\right| \;\middle|\; i \in G(b, s)\right\}\right)", 7, height_in=0.36, fontsize=8.0)
    render_equation_image("eq_8.png", r"\sigma_{(b, s)} = \max\left(1.4826 \cdot \mathrm{MAD}_{(b, s)},\, \rho |m_{(b, s)}|,\, \sigma_{\mathrm{abs}}\right)", 8, height_in=0.36, fontsize=8.0)
    render_equation_image("eq_9.png", r"m_0(x_t) = 45.0 + \mathrm{HVAC}_{\mathrm{base}} + 0.12 \cdot \mathrm{occ}_t + 2.5 \cdot \max(0, T_t - 24.0)", 9, height_in=0.34, fontsize=7.6)
    render_piecewise_10()
    render_equation_image("eq_11.png", r"\sigma_0(x_t) = \max\left(0.08 \cdot m_0(x_t),\, \epsilon\right)", 11, height_in=0.34)
    render_equation_image("eq_12.png", r"d_t = 100 \cdot \frac{r_t}{\max(|m_{(b, s)}|,\, \epsilon)}", 12, height_in=0.40)
    render_equation_image("eq_13.png", r"z_t = \frac{r_t}{\max\left(\sigma_{(b, s)},\, \epsilon\right)}", 13, height_in=0.40)
    render_equation_image("eq_14.png", r"\mathcal{E}_t = \mathbf{1}\left(|d_t| < 15.0\% \;\wedge\; |z_t| < 1.875 \;\wedge\; \neg \mathcal{R}_t\right)", 14, height_in=0.34, fontsize=7.8)
    render_equation_image("eq_15.png", r"C(z_t) = 100 \left(1 - \exp\left(-\frac{|z_t|}{3.0}\right)\right)", 15, height_in=0.40)
    render_equation_image("eq_16.png", r"\psi_{\mathrm{surge}}(x_t) = \mathbf{1}\left((\mathrm{hour}_t \geq 20 \vee \mathrm{hour}_t \leq 5) \;\wedge\; y_t \geq 1.8 \cdot \max(m_{(b, s)}, 10^{-9})\right)", 16, height_in=0.36, fontsize=7.3)
    render_equation_image("eq_17.png", r"\psi_{\mathrm{hvac}}(x_t) = \mathbf{1}\left((T_t > 30.0^\circ\mathrm{C} \wedge \mathrm{hvac}_t < 10\%) \vee (T_t < 20.0^\circ\mathrm{C} \wedge \mathrm{hvac}_t > 80\%)\right)", 17, height_in=0.36, fontsize=7.2)
    render_equation_image("eq_18.png", r"\psi_{\mathrm{pf}}(x_t) = \mathbf{1}\left(\mathrm{PF}_t \mathrm{\;is\;present} \;\wedge\; 0.0 < \mathrm{PF}_t < 0.82\right)", 18, height_in=0.34, fontsize=7.8)
    render_piecewise_19()
    render_equation_image("eq_20.png", r"S_t = \mathrm{round}\left(w_c \cdot C(z_t) + w_r \cdot R_t,\, 1\right)", 20, height_in=0.34)
    render_piecewise_21()
    render_equation_image("eq_22.png", r"e_t = \frac{\max(0, r_t)}{\Delta t} \quad (\mathrm{kW})", 22, height_in=0.40)
    render_equation_image("eq_23.png", r"\Phi_{\mathrm{hr}} = e_t \times \mathrm{Tariff} \quad (\mathrm{INR/hour})", 23, height_in=0.34)
    render_equation_image("eq_24.png", r"\Phi_{\mathrm{annual}} = e_t \times \mathrm{Tariff} \times 8760 \quad (\mathrm{INR/year})", 24, height_in=0.34)
    render_equation_image("eq_25.png", r"E_{\mathrm{annual}} = e_t \times \gamma_{\mathrm{grid}} \times \frac{8760}{1000} \quad (\mathrm{Metric\ Tons\ }\mathrm{CO}_2\mathrm{/year})", 25, height_in=0.40, fontsize=7.5)

    # New Equations: Adaptive Cadence & Edge Metrology (Eq 26-30)
    render_piecewise_26()
    render_piecewise_27()
    render_equation_image("eq_28.png", r"\eta_{\mathrm{tx}} = 1 - \frac{N_{\mathrm{adaptive}}}{N_{\mathrm{fixed\_5m}}} = 1 - \frac{96\mathrm{\,packets/day}}{288\mathrm{\,packets/day}} = 66.7\%", 28, height_in=0.40, fontsize=7.4)
    render_equation_image("eq_29.png", r"D = \frac{v_{\mathrm{sound}}(T) \cdot \Delta t_{\mathrm{echo}}}{2}, \quad L_{\mathrm{pct}} = \max\left(0, \min\left(100, \frac{H_{\mathrm{tank}} - D}{H_{\mathrm{tank}} - D_{\mathrm{blind}}} \times 100\right)\right)", 29, height_in=0.42, fontsize=7.3)
    render_equation_image("eq_30.png", r"V_{\mathrm{ADC}} = V_{\mathrm{sensor}} \times \frac{R_2}{R_1 + R_2} = 5.0\mathrm{\,V} \times \frac{3.3\mathrm{\,k}\Omega}{2.2\mathrm{\,k}\Omega + 3.3\mathrm{\,k}\Omega} = 3.00\mathrm{\,V} \leq 3.30\mathrm{\,V}", 30, height_in=0.40, fontsize=7.3)

    print(f"Successfully generated all 30 equation images in {EQ_DIR}")

if __name__ == "__main__":
    render_all_equations()
