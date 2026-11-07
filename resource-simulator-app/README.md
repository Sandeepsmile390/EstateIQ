# EstateIQ Standalone Multi-Utility Resource Simulator Application

A dedicated, isolated standalone web controller and physics-based telemetry generator for the four campus utility streams:
1. **Electricity** (`SIM-ELEC-01`)
2. **Water** (`SIM-WATER-01`)
3. **Air Quality** (`SIM-AIR-01`)
4. **Waste Dumpster** (`SIM-WASTE-01`)

---

## Highlights

- **Completely Separate Folder**: Resides in `resource-simulator-app/` with its own launcher, server, engine, and frontend.
- **Dedicated Port `8503`**: Runs independently on port 8503 so it never conflicts with port 8000 (EstateIQ API), port 8501 (Streamlit), or port 8502 (`iot-simulator-app`).
- **Live Physics Models**: Dynamic Ohm's law ($P = V \cdot I \cdot \text{PF} / 1000$), hydraulic head loss/burst flow, indoor human $\text{CO}_2$ respiration, EPA AQI derivation, and dumpster volume-to-mass ($0.15\text{ kg/L}$).
- **Automatic Ingestion**: Dispatches canonical telemetry packets directly to `POST http://localhost:8000/api/v1/iot/telemetry`.
- **Standalone Offline Mode**: If the EstateIQ backend is stopped, the simulator seamlessly continues generating data and plotting charts locally.
- **Mandatory Provenance**: Every reading is tagged `[SIMULATED DATA]` with `source_type: "simulated_iot"` and `is_verified_hardware: False`.

---

## Quick Start

### Windows (1-Click)
Double-click `run_windows.bat` inside this folder, or run from the repo root:
```cmd
run_resource_simulator.bat
```

### Command Line
```bash
cd resource-simulator-app
python run.py
```
Open **`http://localhost:8503`** in your browser.

---

## Architecture

```
resource-simulator-app/
├── README.md               # User & API manual
├── requirements.txt        # Lightweight dependencies
├── run.py                  # Standalone launcher on port 8503
├── run_windows.bat         # 1-click Windows runner
├── run_linux_mac.sh        # Unix launch script
├── server.py               # FastAPI standalone server & REST API
├── engine/
│   ├── models.py           # Pydantic schemas & state models
│   ├── physics.py          # Differential physics equations & monotonic totalizers
│   └── client.py           # Telemetry builder & HTTP ingestion client
├── static/
│   ├── index.html          # Web controller UI
│   ├── styles.css          # EstateIQ Dark Forest Green & Mint styling
│   └── app.js              # Real-time state polling & Chart.js management
└── tests/
    └── test_standalone.py  # Standalone unit & integration tests
```

---

## REST API Endpoints

- `GET /health`: Health check (`{"status": "ok", "port": 8503}`)
- `GET /api/status`: Full state of all 4 utilities and backend connectivity
- `POST /api/start`: Resume all or specific utility (`?utility=electricity`)
- `POST /api/pause`: Toggle pause/resume
- `POST /api/step`: Trigger single manual step
- `POST /api/stop`: Stop all simulators
- `POST /api/reset`: Reset totalizers or restore default baselines
- `POST /api/scenario`: Change scenario preset (`{"utility": "water", "scenario": "BURST_FLOW"}`)
- `POST /api/config/baseline`: Set baseline load, flow, occupants, or fill rate
- `POST /api/config/interval`: Set reporting frequency (`{"interval_sec": 2.0}`)
- `GET /api/stream`: 30-sample rolling history buffer for live charts
- Interactive Swagger docs: **`http://localhost:8503/docs`**

---

## Automated Tests

Run standalone tests:
```bash
pytest tests/test_standalone.py -v
```

