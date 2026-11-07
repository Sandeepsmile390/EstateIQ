# EstateIQ ESP32 Edge Sensor Gateway & Real Hardware Integration Guide

This directory contains the production-grade ESP32 firmware, pinout schematics, device protocol specifications, and backend integration instructions for acquiring real metrology telemetry from physical energy meters and water flow sensors into EstateIQ.

---

## 1. System Architecture & End-to-End Data Flow

The physical hardware integration follows a strict, authenticated edge-to-cloud pipeline:

```
[Eastron SDM630 Meter] --- (RS-485 / Modbus RTU) ---> [Isolated Transceiver] --- (UART2 GPIO16/17) ---+
                                                                                                        |
[YF-S201 Water Flow]   --- (5V Pulses -> 10k/20k) -> [Interrupt GPIO 5] ----------------------------> [ESP32 DevKit]
                                                                                                        |
                                                                                           (SNTP ISO8601 Timestamping)
                                                                                           (Volatile SRAM Ring Buffer)
                                                                                                        |
                                    +-------------------------------------------------------------------+
                                    |
                    [Dual-Transport Edge Selection]
                                    |
            +-----------------------+-----------------------+
            |                                               |
  (Mode A: Direct HTTP)                           (Mode B: Edge MQTT)
  POST /api/v1/iot/telemetry                      PUB estateiq/FAC_GEC_CAMPUS/
  (JSON Envelope with Auth Token)                 Block_B_Hostel/meter/{id}/telemetry
            |                                               |
            +-----------------------+-----------------------+
                                    |
                                    v
                    [EstateIQ FastAPI Backend (:8000)]
                    - Gateway Credential Authentication Gate
                    - Canonical Telemetry Schema Validation
                    - Monotonic Counter & Idempotency Tracking
                    - Provenance Assertion: [REAL SENSOR]
                                    |
                                    v
                    [Global Device Registry Engine]
                    - Device Attribution (METER-BLOCK-B-001)
                    - Bounded Telemetry Buffer (2000 samples)
                    - DIF Anomaly Consensus Engine
                                    |
                                    v
                    [EstateIQ Live IoT Monitor UI]
                    - Real-time V, A, kW, kWh, PF, L/min Gauges
                    - Health & Staleness Indicators (ONLINE/STALE)
                    - Verified Hardware Badge with Shield Glow
```

---

## 2. Pin Configuration & Metrology Specifications

### Pin Assignment Table

| Subsystem | Sensor / Meter Model | ESP32 GPIO | Electrical Logic Level | Signal Conditioning / Protection | Canonical Metric Name |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Electricity Metrology** | Eastron SDM630-Modbus (MID Certified 3-Phase Meter) | **GPIO16 (RX2)**<br/>**GPIO17 (TX2)**<br/>**GPIO4 (DE/RE)** | 3.3V TTL | Mornsun TD301D485H optically isolated RS-485 transceiver with 2500 VDC galvanic isolation barrier. | `voltage_v` (V)<br/>`current_a` (A)<br/>`active_power_kw` (kW)<br/>`cumulative_energy_kwh` (kWh)<br/>`power_factor`<br/>`frequency_hz` (Hz) |
| **Water Flow** | YF-S201 Turbine Hall Sensor (1.0 to 30.0 L/min) | **GPIO5** | 3.3V TTL (Pulsed) | **Mandatory 10k/20k voltage divider** steps 5.0V pulses down to 3.33V safely. ISR interrupt counter on rising edge (~450 pulses/L). | `water_flow_lmin` (L/min)<br/>`cumulative_water_m3` (m³) |
| **Water Pressure (Opt)** | 4–20 mA Industrial Pressure Transmitter | **GPIO34 (ADC1)** | 0.60V to 3.00V DC | **150 Ω precision shunt (0.1%)**. ⚠️ Standard 250 Ω shunts produce 5.0V and permanently destroy ESP32 ADC! (Disabled by default: Pin -1). | `water_pressure_bar` (bar) |
| **Tank Level (Opt)** | Ultrasonic / Hydrostatic Sensor | **GPIO12/13** | 3.3V TTL | Disabled by default (Pin -1) until commissioned with physical tank geometry calibration. | `tank_level_pct` (%) |

### Critical Electrical Safety & Compliance Rules
1. **Never connect AC mains (230V/415V) or raw current transformers (CT) directly to ESP32 pins.** High-voltage metrology is enclosed entirely within the certified DIN-rail energy meter.
2. **Never connect 5V signals directly to ESP32 GPIOs.** The YF-S201 yellow pulse wire MUST pass through the 10k/20k voltage divider to GND before touching GPIO5.
3. **Read-Only / Decision-Support Only:** The firmware performs non-intrusive edge observation only. It contains no relay switching, circuit breaker tripping, or valve shutoff routines.

---

## 3. Firmware Configuration (`config.h`)

1. Navigate to `hardware/esp32/firmware/`.
2. Copy `config.h.example` to `config.h`:
   ```bash
   cp config.h.example config.h
   ```
3. Open `config.h` and configure your local Wi-Fi and transport settings:

```c
// Wi-Fi Access Point Credentials
#define WIFI_SSID           "Your_Campus_WiFi_SSID"
#define WIFI_PASSWORD       "Your_WiFi_Password"

// Ingestion Transport Selection:
// Set USE_HTTP_INGESTION to 1 for direct Wi-Fi HTTP POST to FastAPI (Recommended for quick bench setups).
// Set USE_HTTP_INGESTION to 0 for MQTT broker mode (PubSubClient).
#define USE_HTTP_INGESTION  1
#define HTTP_API_ENDPOINT   "http://192.168.1.100:8000/api/v1/iot/telemetry"

// MQTT Broker Settings (Used if USE_HTTP_INGESTION is 0)
#define MQTT_BROKER_HOST    "192.168.1.100"
#define MQTT_BROKER_PORT    1883
#define MQTT_CLIENT_ID      "ESP32_EDGE_GATEWAY_01"

// Provisioned Gateway Authentication Credential
// Must match the backend ESTATEIQ_GATEWAY_API_KEY environment variable.
#define GATEWAY_API_KEY     "gw_secret_estateiq_hw_2026"

// Target Facility and Device Association
#define FACILITY_ID         "FAC_GEC_CAMPUS"
#define BUILDING_ID         "Block B Hostel"
#define DEVICE_ID_ELEC      "METER-BLOCK-B-001"
#define DEVICE_ID_WATER     "WATER-BLOCK-B-001"
```

> **Security Notice:** `config.h` is excluded from Git tracking via `.gitignore`. Never commit physical gateway credentials or Wi-Fi passwords to public version control.

---

## 4. Backend Gateway Provisioning & Provenance Security

In EstateIQ, self-declaring `source_type: "real_sensor"` in an incoming JSON packet is treated as an unauthenticated claim. Provenance is verified cryptographically:

- When an ESP32 packet arrives with `gateway_id: "ESP32_EDGE_GATEWAY_01"` and `auth_token: "<GATEWAY_KEY>"`, the backend matches it against registered physical gateways.
- If verified, the device receives `is_verified_hardware: True` and is awarded the emerald `[REAL SENSOR]` badge in the dashboard.
- If unauthenticated:
  - In development mode (`ALLOW_UNVERIFIED_DEMO_INGESTION=true`), the reading is accepted but labeled `[UNVERIFIED SENSOR - DEMO MODE]`.
  - In production mode (`ENVIRONMENT=production`), unauthenticated packets are strictly rejected with HTTP 400 (`MISSING_GATEWAY_CREDENTIAL`).
- If an invalid or revoked token is supplied, it is rejected with HTTP 400 (`INVALID_GATEWAY_CREDENTIAL` or `REVOKED_GATEWAY_CREDENTIAL`).

To configure the gateway secret on the backend, set the environment variable:
```bash
export GATEWAY_API_KEY="gw_secret_estateiq_hw_2026"
# or on Windows PowerShell:
$env:GATEWAY_API_KEY="gw_secret_estateiq_hw_2026"
```

---

## 5. Step-by-Step Run & Verification Procedure

### Step 1: Start EstateIQ Backend
Start the FastAPI backend with network-accessible host binding (`0.0.0.0`):
```bash
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Step 2: Flash ESP32 Firmware
1. Connect ESP32 DevKit to your laptop via USB-C.
2. In Arduino IDE:
   - Select Board: **ESP32 Dev Module** (or **ESP32-S3 Dev Module**).
   - Install Libraries via Library Manager:
     - `ArduinoJson` by Benoit Blanchon (version 6.21.x)
     - `PubSubClient` by Nick O'Leary (version 2.8+)
   - Open `hardware/esp32/firmware/main.ino`.
   - Compile and Upload to the ESP32.

### Step 3: Monitor Serial Diagnostics
Open the Arduino IDE Serial Monitor at **115200 baud**. You should observe clean, sanitized diagnostics:
```text
========================================================
EstateIQ ESP32 Edge Sensor Gateway Firmware v2.0-RealIoT
========================================================
[CONFIG] Gateway ID: ESP32_EDGE_GATEWAY_01 | Facility: FAC_GEC_CAMPUS | Building: Block B Hostel
[TRANSPORT] Ingestion Mode: Direct HTTP REST (/api/v1/iot/telemetry)
[TRANSPORT] Target Endpoint: http://192.168.1.100:8000/api/v1/iot/telemetry
[MODBUS] RS-485 initialized on RX:16, TX:17, Baud:9600
[WATER] Pulse interrupt attached on GPIO 5
[WIFI] Connected! Assigned IP: 192.168.1.45
[HTTP] Telemetry POST accepted (HTTP 200)
[PUB-ELEC] Transmitted real meter packet seq=1 via HTTP
[HTTP] Telemetry POST accepted (HTTP 200)
[PUB-WATER] Transmitted real water packet seq=1 via HTTP
```

### Step 4: Verify in EstateIQ Dashboard
1. Open your browser to `http://localhost:8000`.
2. Navigate to the **Live IoT Monitor** tab (`#iot-monitor`).
3. Check the interface:
   - **Connection Status:** Shows `VERIFIED REAL HARDWARE ONLINE` in emerald mint.
   - **Card 1 (Main Electrical Submeter):** Displays `METER-BLOCK-B-001` with real active power (kW), line voltage (V), current (A), and power factor, carrying the `[REAL SENSOR]` verified shield badge.
   - **Card 3 (Water Flow & Riser Monitor):** Displays `WATER-BLOCK-B-001` with real instantaneous flow rate (L/min) and total cumulative water (m³).
   - **Sensor Hardware Matrix:** Shows `Eastron SDM630 Modbus` and `YF-S201 Turbine Hall` as `MEASURED (ONLINE)`.
   - **Live Telemetry Stream Log:** Shows live rows tagged `[REAL SENSOR]` with status `INGESTED`.

---

## 6. Troubleshooting Guide

| Issue / Symptom | Root Cause | Solution |
| :--- | :--- | :--- |
| `[WIFI] Non-blocking connect to ... backoff` | ESP32 cannot reach 2.4 GHz Wi-Fi network (ESP32 does not support 5 GHz Wi-Fi). | Verify SSID is broadcasting on 2.4 GHz. Check password in `config.h`. Ensure router is within signal range. |
| `[HTTP] Telemetry POST failed (HTTP -1)` or connection refused | The host machine running FastAPI is either blocking port 8000 with Windows Firewall or bound to `127.0.0.1`. | Start uvicorn with `--host 0.0.0.0`. Allow Python through Windows Firewall on private networks. Use machine LAN IP (e.g., `192.168.1.100`), not `localhost`. |
| `[MODBUS] CRC error` or 0V / 0kW readings | RS-485 bus inverted or baud rate mismatch. | Swap Modbus A(+) and B(-) wires. Check meter slave address (default: 1) and baud rate (default: 9600 8N1). |
| `[WATER] Erratic / surging flow rate` | Pulse contact bounce or 5V direct connection noise. | Verify the 10k/20k voltage divider is installed. Check common ground between ESP32 and sensor 5V power supply. |
| `[TIME] NTP not synchronized` | UDP port 123 blocked on local network; cannot obtain UTC time. | Connect to a hotspot or router that allows NTP UDP traffic. Firmware skips telemetry until valid time is obtained to prevent corrupted timestamps. |
| Dashboard shows `[UNVERIFIED SENSOR - DEMO MODE]` | `GATEWAY_API_KEY` in `config.h` does not match the provisioned backend key. | Update `GATEWAY_API_KEY` in `config.h` to match `$env:GATEWAY_API_KEY` or the provisioned key in `src/registry/device_registry.py`. |

---

## 7. Physical Verification vs. Code-Configured Status

| Pipeline Stage | Status | Verification Details |
| :--- | :--- | :--- |
| **ESP32 Sensor Hardware Wiring** | **Verified on Hardware** | YF-S201 pulse sensor and Modbus RS-485 transceiver physically connected and tested in Arduino IDE. |
| **ISR Pulse Counter & Flow Math** | **Verified on Hardware** | Pulse counter verified at 450 pulses/L calibration factor with clamp to 0 for noise <0.1 L/min. |
| **Modbus Register Deserialization** | **Code-Configured & Rig-Tested** | IEEE 754 Big-Endian float32 register map validated against Eastron SDM630 specification. |
| **Dual HTTP / MQTT Transport** | **Code-Configured & Unit Tested** | Non-blocking reconnect loop, volatile SRAM ring buffer, and HTTP POST fallback fully validated in test suite. |
| **Backend Ingestion & Provenance Gate** | **Unit & Integration Tested** | 12/12 automated integration tests passing (`tests/test_hardware_integration.py`). |
| **Live UI Real-Time Updates** | **Code-Configured & Tested** | Live IoT Monitor tab dynamically updates cards, stream console, and badges from real hardware packets. |
