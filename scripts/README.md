# EstateIQ Automation & Utility Scripts

This directory contains executable helper scripts, data seeders, model training workflows, validation scripts, and publication build utilities for **EstateIQ-DIF v2.0**.

---

## 🛠️ Key Scripts Reference

### 1. Demo & Data Operations
- **`seed_demo_data.py`**:
  ```bash
  python scripts/seed_demo_data.py
  ```
  Generates 14 days of deterministic hourly campus telemetry across 14 zones for Energy, Water, Air Quality, and Waste with 4 injected anomalies (`BLOCK_B` energy spike at 145.2 kWh, `BLOCK_B` overnight leak at 380 L/hr, `CANTEEN` waste overflow at 94%, and `BLOCK_A` PM2.5 surge at 142.5 µg/m³).
- **`reset_demo.py`**:
  ```bash
  python scripts/reset_demo.py
  ```
  Resets the local database, telemetry records, work orders, and runtime caches back to a clean initial baseline.

### 2. Machine Learning & Intelligence
- **`train_models.py`**:
  Trains and exports tabular machine learning models (energy, water, waste, air quality) to `models/`.
- **`evaluate_models.py`**:
  Computes regression metrics (MAE, RMSE, $R^2$, MAPE) and classification metrics on holdout test partitions.
- **`check_ai.py`**:
  Verifies Groq Cloud LPU API connectivity (`llama-3.3-70b-versatile`) and tests the offline deterministic fallback.

### 3. Academic Research & PDF Generation
- **`generate_ieee_paper_pdf.py`**:
  ```bash
  python scripts/generate_ieee_paper_pdf.py
  ```
  Executes the ReportLab academic typesetter (`research/ieee/build_ieee_paper.py`), generating the 7-page IEEE conference-style research paper PDF at `output/pdf/estateiq_elite_dif_ieee_research_paper.pdf`.

### 4. Code Quality & Encoding Validators
- **`scan_static_values.py`**: Scans codebase for hardcoded static values to ensure dynamic calculation integrity.
- **`validate-all.ps1` / `validate-all.sh`**: Runs complete repository validation suite.
- **`validate-encoding.ps1` / `validate-encoding.sh`**: Verifies UTF-8 encoding across all text and code files.
- **`validate-skills.ps1`**, **`validate-agents.ps1`**, **`validate-workflows.ps1`**: Validates agent, skill, and workflow YAML schemas.
