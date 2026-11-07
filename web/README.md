# EstateIQ Liquid Glass Web UI

This directory contains the lightweight, zero-build Liquid Glass web client for the **EstateIQ Facility Decision Intelligence Platform**.

---

## 🎨 Design Philosophy & Features

- **Liquid Glass Aesthetic**: Dark forest green theme (`#081c15`, `#1b4332`), translucent glassmorphic card panels (`rgba(255, 255, 255, 0.05)` with `backdrop-filter: blur(12px)`), and crisp emerald green accents (`#52b788`).
- **Zero-Build Architecture**: Implemented in clean, modern vanilla JavaScript (ES6+), HTML5, and CSS3. Requires no npm build, webpack bundling, or node runtime to render.
- **Live Server-Sent Events (SSE)**: Connects directly to `GET /api/v1/iot/telemetry/stream` for sub-second, real-time push updates without polling.
- **Dynamic Live IoT Monitor**:
  - Live meter readings for Active Power, Energy, Voltage, Current, Power Factor, Frequency, and Water Flow.
  - Automatic provenance badging: displays an emerald green **`[REAL SENSOR]`** badge when data arrives from physical hardware (`ESP32_EDGE_GATEWAY_01` with `is_verified_hardware: true`), and amber **`[SIMULATED DATA]`** badge for virtual simulators.
- **Multi-Utility Resource Simulator Integration**: Quick-launch buttons and status indicators connecting to the dedicated Port 8503 Resource Simulator.

---

## 📁 Directory Structure

```text
web/
├── index.html                   # Master single-page application layout
├── css/
│   └── styles.css               # Translucent glassmorphic design system styles
├── js/
│   ├── app.js                   # State manager, SSE subscriber, tab router
│   └── resource_simulator.js    # Multi-utility simulator controller logic
└── README.md                    # Web client documentation
```

---

## 🚀 How to View & Access

1. **Via FastAPI Static Hosting**:
   When the FastAPI backend is running (`uvicorn api.main:app --port 8000`), the web client is accessible at:
   - [http://localhost:8000/](http://localhost:8000/) or [http://localhost:8000/web/index.html](http://localhost:8000/web/index.html)

2. **Direct Browser Execution**:
   You can also open `web/index.html` directly in any modern browser (Chrome, Edge, Firefox, Safari).

---

## 📡 Live Telemetry Data Flow

```text
ESP32 Gateway / Simulator ➔ FastAPI (Port 8000) ➔ SSE (/api/v1/iot/telemetry/stream) ➔ web/js/app.js ➔ DOM Update
```
