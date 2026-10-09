# EstateIQ Standalone Multi-Device IoT Telemetry Simulator

An independent, local multi-device physics IoT telemetry generator & LAN streaming application for the **EstateIQ Facility Intelligence Platform** (BPUT Hackathon 2026).

---

## Features

- **Standalone Execution:** Runs as an independent process served on port `8502`. Does not require starting EstateIQ frontend on the simulator laptop.
- **LAN Networking:** Discovers EstateIQ server over Wi-Fi / Local Area Network using one-time single-use pairing codes.
- **12 Virtual Device Profiles:** Electricity meters, building submeters, transformers, diesel generators, HVAC units, occupancy counters, ambient sensors, water meters, water tank level sensors, AQI monitors, lighting controllers, and multi-sensors.
- **14 Physics & Anomaly Presets:** Normal operation, peak HVAC surge, water leaks, off-peak setback, equipment vibration, transformer overloading, DG active, etc.
- **Offline Resiliency Buffer:** Automatically queues generated telemetry packets locally (`data/buffer.json`) if EstateIQ server is temporarily unreachable and flushes upon reconnection with backoff.
- **Interactive Control Web UI:** Adjust real-time sensor readings (active power, temperature, HVAC load, water flow) using sliders and watch telemetry stream in real time.

---

## Quick Start Guide

### 1. Requirements
- Python 3.9+
- Network connection to EstateIQ host laptop (same Wi-Fi / LAN)

### 2. Startup Commands

#### Windows
```cmd
run_windows.bat
```

#### Linux / macOS
```bash
chmod +x run_linux_mac.sh
./run_linux_mac.sh
```

#### Manual Python Execution
```bash
pip install -r requirements.txt
python run.py
```

Open the web UI at: **`http://localhost:8502`**

---

## Pairing with EstateIQ Server

1. Start EstateIQ main server on Host Laptop A (`http://<LAPTOP_A_IP>:8000`).
2. Open EstateIQ IoT Devices tab to get/generate pairing code (e.g. `IQ-DEMO`).
3. In the Standalone Simulator UI (`http://localhost:8502`):
   - Enter **EstateIQ Server LAN URL** (e.g. `http://192.168.1.20:8000`).
   - Enter **Pairing Code** (`IQ-DEMO`).
   - Click **Pair & Discover**.
4. The simulator will pair, receive a scoped auth credential, register its virtual devices, and begin heartbeat dispatches.
