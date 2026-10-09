# Two-Laptop LAN Setup & Deployment Guide

This guide details the procedure for deploying EstateIQ across two separate laptops connected over a Local Area Network (Wi-Fi or Ethernet switch).

---

## Laptop A: EstateIQ Main Server Host

1. **Connect Laptop A to the local network.**
2. **Find Laptop A's LAN IP address:**
   - **Windows:** Open Command Prompt and run `ipconfig` (e.g. `192.168.1.20`).
   - **Linux/macOS:** Run `ifconfig` or `ip a`.
3. **Start the EstateIQ FastAPI Backend:**
   ```bash
   cd Model
   python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
   ```
4. **Verify Health Endpoint:**
   Open browser at `http://localhost:8000/api/v1/ai/health` to confirm server startup.
5. **Ensure Windows Firewall allows inbound connections on Port 8000.**

---

## Laptop B: Standalone IoT Simulator Host

1. **Connect Laptop B to the same local network.**
2. **Open the simulator folder:**
   ```bash
   cd Model/iot-simulator-app
   ```
3. **Start the Standalone Simulator:**
   - **Windows:** `run_windows.bat`
   - **Linux/macOS:** `./run_linux_mac.sh`
4. **Access Simulator Local Interface:**
   Open browser on Laptop B at `http://localhost:8502`.
5. **Pair with Laptop A:**
   - Set **EstateIQ Server LAN URL** to `http://192.168.1.20:8000` (replacing with Laptop A's actual IP).
   - Enter Pairing Code: `IQ-DEMO`.
   - Click **Pair & Discover**.
6. **Verify Streaming:**
   - Confirm status badge changes to `Registered` and `Streaming`.
   - Verify EstateIQ dashboard on Laptop A displays live simulator metrics and telemetry under the **IoT Devices** tab.
