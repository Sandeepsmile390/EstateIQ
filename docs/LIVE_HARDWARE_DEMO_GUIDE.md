# EstateIQ Live Hardware Demo & Evaluation Runbook
**ESP32 Edge Gateway & Physical Sensor Integration**

---

## Executive Overview & Data Path Architecture

This runbook guides presenters, evaluators, and engineers through conducting a live, repeatable hardware demonstration of **EstateIQ** using an **ESP32 development board** and connected physical sensors.

### End-to-End Data Flow

```
+-------------------------------------------------------------+
|                     PHYSICAL HARDWARE BENCH                 |
|                                                             |
|  [MQ-135 Air Quality]    [YF-S201 Water Flow]    [Power CT]  |
|  (Analog Pin on ADC1)    (Pulse Interrupt GPIO)  (UART / CT) |
|           |                        |                  |      |
|           +------------------------+------------------+      |
|                                    v                         |
|                    [ESP32 Microcontroller Node]              |
|                    - 12-bit ADC Sampling (ADC1)              |
|                    - Hardware Pulse Interrupt Counter        |
|                    - Canonical JSON Envelope Serialization   |
+-------------------------------------------------------------+
               |                                   |
    (USB Cable: 5V DC Power,                       | (Wi-Fi 802.11 b/g/n:
     Flashing, & 115200 Baud                       |  Local Network Telemetry)
     Serial Diagnostics)                           |
               |                                   v
+-----------------------+        +------------------------------------+
|  Laptop USB Port      |        |  EstateIQ FastAPI Backend (:8000)  |
|  - Arduino Serial Mon |        |  - Gateway Auth: ESP32_EDGE_GW_01  |
|  - 115200 Baud Output |        |  - Canonical Schema Validation     |
+-----------------------+        |  - Provenance: [LIVE HARDWARE]     |
                                 +------------------------------------+
                                                   |
                                                   v
                                 +------------------------------------+
                                 |  EstateIQ Live Interfaces          |
                                 |  - Streamlit: "Live Hardware" Tab  |
                                 |  - Web UI: Live Sparklines & Stream|
                                 +------------------------------------+
```

> [!IMPORTANT]
> **Data Transport Clarification:**
> The USB cable between the laptop and the ESP32 serves **solely for regulated 5V DC power, Arduino firmware flashing, and 115200 baud serial diagnostics**. Telemetry data does **not** travel over a serial COM port bridge; it is transmitted wirelessly over **Wi-Fi** directly to the laptop-hosted EstateIQ backend (`POST /api/v1/iot/telemetry`). This architecture proves genuine network-layer IoT edge communication without operating system driver dependencies.

---

## 1. Hardware Bill of Materials & Wiring

| Sensor / Module | Function | ESP32 GPIO Pin | Required Signal Conditioning / Protection |
| :--- | :--- | :--- | :--- |
| **AJ-SR04M Ultrasonic Sensor** | Water Tank Level & Surface Distance Ranging | **Trig: GPIO5**<br/>**Echo: GPIO18** | Connect VCC to 5V (or 3.3V) and GND to GND. In 5V mode, Echo pulse can be fed directly or through a 1k series resistor to ESP32 3.3V GPIO. |
| **MQ-135 Gas Sensor** | Indoor Air Quality / Relative Exhalation Indicator | **GPIO34 (ADC1_CH6)** | **Mandatory 10k / 20k Voltage Divider** on Analog Out (AO) stepping 5.0V signal down to 3.33V maximum to protect ESP32 ADC. |
| **YF-S201 Flow Sensor** *(optional)* | Potable Water Consumption & Flow Rate | **GPIO19 (or GPIO5)** | 10k pull-up resistor to 3.3V (or 10k/20k divider on 5V pulse output). |
| **PZEM-004T / CT** *(optional)* | Active Power, Voltage, Current, kWh | **GPIO16 (RX2) & GPIO17 (TX2)** | UART Serial2 communication. |
| **ESP32 DevKit V1** | Microcontroller Edge Gateway | Micro-USB | Plugged into host laptop USB 3.0 port. |

### Critical ESP32 ADC1 Rule
> [!CAUTION]
> **Wi-Fi and ADC2 Incompatibility:**
> The ESP32's internal Wi-Fi driver uses the `ADC2` peripheral. Therefore, **analog read operations on ADC2 pins (GPIO0, 2, 4, 12, 13, 14, 15, 25, 26, 27) fail or cause system crashes while Wi-Fi is active**. All analog sensors (including the MQ-135) **MUST** be connected exclusively to **ADC1 pins (GPIO32, 33, 34, 35, 36, or 39)**.

---

## 2. Workstation & Arduino IDE Setup

### Step 2.1: Arduino IDE Configuration
1. Install **Arduino IDE** (v2.0 or later).
2. Add ESP32 Board Support:
   - Navigate to **File &rarr; Preferences**.
   - In *Additional Board Manager URLs*, add:
     `https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json`
   - Open **Tools &rarr; Board &rarr; Boards Manager**, search for **esp32** by *Espressif Systems*, and install.
3. Install Required Libraries via **Tools &rarr; Manage Libraries**:
   - `ArduinoJson` (v6.21.x or later)
   - `WiFi` (built into ESP32 core)
   - `HTTPClient` (built into ESP32 core)
   - `PubSubClient` (v2.8 or later, by Nick O'Leary)

### Step 2.2: Identify Laptop LAN IP Address
The ESP32 needs to send HTTP requests to your laptop's IP address on the local network (or phone hotspot).

- **Windows:**
  Open PowerShell or Command Prompt and run:
  ```powershell
  ipconfig
  ```
  Look for your active Wi-Fi adapter's **IPv4 Address** (e.g., `192.168.1.45` or `192.168.137.1`).
- **macOS / Linux:**
  ```bash
  ifconfig | grep "inet "
  ```

---

## 3. Firmware Configuration & Flashing

### Step 3.1: Create `config.h`
In `hardware/esp32/firmware/`, copy `config.h.example` to `config.h`:

```bash
cd hardware/esp32/firmware
cp config.h.example config.h
```

Open `hardware/esp32/firmware/config.h` in your editor and configure:

```c
// 1. Wi-Fi Configuration
#define WIFI_SSID           "Your_WiFi_Or_Hotspot_Name"
#define WIFI_PASSWORD       "Your_WiFi_Password"

// 2. EstateIQ Backend Endpoint
// Replace with your laptop's actual IP from Step 2.2
#define API_SERVER_HOST     "192.168.1.45"
#define API_SERVER_PORT     8000
#define API_TELEMETRY_PATH  "/api/v1/iot/telemetry"

// 3. Gateway Identity & Security Key
#define GATEWAY_ID          "ESP32_EDGE_GATEWAY_01"
#define GATEWAY_API_KEY     "gw_secret_estateiq_hw_2026"

// 4. Hardware Node Sub-Devices
#define DEVICE_ID_ENV       "ENV-BLOCK-B-001"
#define DEVICE_ID_ENERGY    "METER-BLOCK-B-001"
#define DEVICE_ID_WATER     "WATER-BLOCK-B-001"

// 5. Analog & Sensor Pin Definitions
#define MQ135_ANALOG_PIN            34     // GPIO34 (ADC1_CH6) - MUST BE ADC1!
#define MQ135_VOLTAGE_DIVIDER_RATIO 1.5f   // 10k / 20k resistor divider ratio
#define MQ135_WARMUP_PERIOD_SEC     180    // MOS heater warm-up duration

// 6. Transport Mode (HTTP Direct Ingestion)
#define USE_MQTT            false
```

### Step 3.2: Flash the Firmware
1. Connect the ESP32 to your laptop using a data-capable Micro-USB cable.
2. In Arduino IDE:
   - Select Board: **ESP32 Dev Module** (or your specific ESP32 board).
   - Select Port: (e.g. `COM3` on Windows, `/dev/ttyUSB0` on Linux).
   - Open `hardware/esp32/firmware/main.ino`.
   - Click **Upload** (Ctrl+U).
3. Once upload completes, open **Tools &rarr; Serial Monitor** and set baud rate to **115200 baud**.

---

## 4. Starting the EstateIQ Backend & UI

In a terminal on your laptop, ensure the EstateIQ backend binds to all network interfaces (`0.0.0.0`) so the ESP32 can communicate with it:

### Step 4.1: Start FastAPI Ingestion Backend
```powershell
cd D:\Hackathon\Model
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

> [!NOTE]
> If prompted by Windows Defender Firewall, click **"Allow access"** for private and public networks on port 8000.

### Step 4.2: Start Streamlit Dashboard (In a New Terminal)
```powershell
cd D:\Hackathon\Model
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

### Step 4.3: Open Web IoT Monitor (Alternative Web Console)
Open `web/index.html` in your browser (or serve via local static server).

---

## 5. Verifying the End-to-End Pipeline

### Step 5.1: Inspect ESP32 Serial Diagnostics
In the Arduino IDE Serial Monitor (115200 baud), observe the startup log:

```text
[INIT] EstateIQ ESP32 Edge Gateway Booting...
[INIT] Firmware Build: 2026.11
[ADC] MQ-135 Configured on ADC1 GPIO34 (12-bit, 0-3.3V)
[WIFI] Connecting to Your_WiFi_Or_Hotspot_Name...
[WIFI] Connected! Assigned IP: 192.168.1.112 | RSSI: -58 dBm
[SNTP] Synchronizing Network Time...
[SNTP] Time synchronized: 2026-11-07T11:15:20Z

--- Beginning Sensor Sampling Loop ---
[SENSOR-MQ135] Raw ADC: 1248 | Voltage: 1.01V | Warm-up: OK | Est: 612 ppm
[HTTP] Transmitting canonical payload for ENV-BLOCK-B-001...
[HTTP] Response code: 200 | Payload accepted by EstateIQ backend!
```

### Step 5.2: Verify Streamlit Dashboard
1. In the Streamlit sidebar, select **"Live Hardware (ESP32)"**.
2. Notice the top banner:
   - Emerald badge: **`[LIVE HARDWARE]`**
   - Node Connection State: **`ONLINE`** (Freshness: `< 15.0s ago`)
3. Select **`ENV-BLOCK-B-001`** from the device dropdown:
   - **Raw ADC Signal:** e.g. `1,248 count`
   - **Sensor Voltage:** e.g. `1.01 V`
   - **Indicative Gas Est.:** e.g. `612 ppm (est)`
   - **Heater Status:** `STABILIZED`
4. Observe the real-time **Sensor History Chart** updating every 15 seconds.

### Step 5.3: Verify Web Dashboard (`web/index.html`)
1. In `web/index.html`, navigate to the **Live IoT Stream & Hardware Sensor Nodes** section.
2. In the **Sensor Hardware & Metrology Matrix**, inspect the **Indoor Air Quality (MQ-135)** row:
   - Status indicates `RAW ADC MEASURED`.
3. In **Card 4 (Block B Environmental Node)**:
   - Live metrics display ADC counts, voltage, and indicative gas estimates.
   - The sparkline canvas draws real-time data points received from the backend stream.

---

## 6. Safe Sensor Stimulus Demonstration Procedures

During an evaluation or hackathon presentation, demonstrate physical responsiveness using these safe procedures:

### Test A: MQ-135 Air Quality Sensor (Exhalation Stimulus)
1. **Initial Baseline:** Observe the steady-state raw ADC reading in clean room air (typically **1,050 to 1,300 counts**, voltage **~0.85V to 1.05V**).
2. **Apply Stimulus:**
   - Bring your mouth approximately 5 cm from the MQ-135 metal protective mesh.
   - Gently exhale 2–3 steady breaths across the sensor.
3. **Observed Response:**
   - Exhaled human breath contains ~40,000 ppm CO₂ along with water vapor (elevated humidity).
   - The SnO₂ metal-oxide semiconductor surface resistance drops rapidly.
   - In the next sampling interval, the Serial Monitor and EstateIQ UI show the **Raw ADC jump to 2,000–2,900+ counts**, and the voltage rises to **1.6V–2.3V**.
4. **Recovery:** Within 30–60 seconds, ambient room air disperses the exhaled breath and values decline toward baseline.

### Test B: YF-S201 Water Flow Sensor (Turbine Stimulus)
1. **Initial Baseline:** With no air or water movement, flow is **0.0 L/min**.
2. **Apply Stimulus:**
   - Gently blow air into the flow meter nozzle (or pour a small cup of water through it over a container).
3. **Observed Response:**
   - The internal plastic turbine wheel spins; the embedded magnet passes the Hall effect sensor.
   - Hardware interrupt triggers pulse accumulation on the GPIO pin.
   - EstateIQ UI immediately displays active flow rate (e.g. **8.4 to 15.2 L/min**) and increments cumulative m³.

> [!CAUTION]
> **Electrical Safety Notice:**
> Never connect bare 120V / 230V AC mains electrical wires to the ESP32. AC metrology must strictly use galvanic isolation (e.g. split-core Current Transformer clamps or optically isolated RS-485 Modbus transceivers).

---

## 7. Scientific Disclosure: MQ-135 Calibration & Selectivity

EstateIQ enforces strict scientific transparency regarding low-cost metal-oxide sensors:

1. **Broad-Spectrum Cross-Sensitivity:**
   The MQ-135 utilizes a Tin Dioxide ($\text{SnO}_2$) sensing layer that responds non-specifically to carbon dioxide ($\text{CO}_2$), ammonia ($\text{NH}_3$), ethanol ($\text{C}_2\text{H}_5\text{OH}$), benzene ($\text{C}_6\text{H}_6$), and smoke. It also exhibits substantial temperature and relative humidity cross-sensitivity.
2. **Indicative Estimate Only:**
   The displayed ppm value is calculated via standard logarithmic load-resistance curve approximation. It serves as an **indicative qualitative indicator** of room ventilation changes.
3. **Regulatory Non-Equivalence:**
   MQ-135 readings **must never** be cited as certified laboratory NDIR $\text{CO}_2$ concentration, $\text{PM}_{2.5} / \text{PM}_{10}$ optical particle counter mass, or official US EPA / European Air Quality Index (AQI) values.

---

## 8. Comprehensive Troubleshooting Matrix

| Symptom / Error | Root Cause | Resolution |
| :--- | :--- | :--- |
| **ESP32 Serial shows `[WIFI] Connection Failed!`** | Incorrect SSID, password, or 5GHz-only Wi-Fi band. | ESP32 only supports 2.4 GHz 802.11 b/g/n. Ensure your router or mobile hotspot broadcasts on 2.4 GHz. Verify credentials in `config.h`. |
| **`[HTTP] Response code: -1` or Connection Timeout** | Laptop firewall blocking port 8000, or wrong IP address in `config.h`. | 1. Re-check laptop IP using `ipconfig`.<br/>2. Verify FastAPI is running with `--host 0.0.0.0` (not `127.0.0.1`).<br/>3. Allow inbound connections on port 8000 in Windows Firewall. |
| **`[HTTP] Response code: 401 Unauthorized`** | Gateway API key mismatch. | Ensure `GATEWAY_API_KEY` in `config.h` matches `src/registry/device_registry.py` (`gw_secret_estateiq_hw_2026` or `ESTATEIQ_GATEWAY_API_KEY` env var). |
| **`[HTTP] Response code: 422 Unprocessable Entity`** | Telemetry payload violates canonical range bounds. | Check `src/data/telemetry_schema.py`. Ensure metrics are within realistic physical bounds (e.g., `mq135_raw_adc` between 0 and 4095). |
| **ESP32 crashes or reboots when reading analog pin** | Analog pin assigned to `ADC2` while Wi-Fi is active. | Move analog sensor to **ADC1** (`GPIO32`, `33`, `34`, `35`, `36`, or `39`). Update pin definition in `config.h`. |
| **MQ-135 ADC reads constantly 4095 (railed high)** | Missing voltage divider; 5V AO is saturating 3.3V ADC. | Install 10k series / 20k pull-down resistor divider between MQ-135 AO and ESP32 GPIO. |
| **Dashboard displays `[SIMULATED IoT]` instead of `[LIVE HARDWARE]`** | Telemetry payload was ingested without authenticated gateway key or with `source_type: "simulated_iot"`. | Verify payload was signed with `gateway_id: "ESP32_EDGE_GATEWAY_01"` and valid `gateway_api_key`. |
| **Device Freshness shows `STALE` or `OFFLINE`** | Time elapsed since last sample exceeds threshold (45s for Stale, 300s for Offline). | Increase sample frequency in firmware or check serial monitor to confirm continuous transmissions. |

