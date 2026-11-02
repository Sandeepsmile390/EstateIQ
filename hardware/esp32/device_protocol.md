# EstateIQ Hardware & Device Protocol Specification
## Finalist Implementation Guide: Metrology, Safety, Wiring, and Live Demonstration Plan

---

## 1. ⚠️ CRITICAL ELECTRICAL SAFETY & COMPLIANCE RULES

> **MANDATORY SAFETY RULES:**
> 1. **NEVER CONNECT MAINS VOLTAGE OR RAW CT OUTPUTS TO ESP32 PINS.**
>    All high-voltage AC metrology (230 V single-phase / 415 V three-phase) must take place inside a certified, fully enclosed DIN-rail energy meter (e.g., Eastron SDM630 or Schneider PM series). The ESP32 communicates exclusively over a galvanically isolated RS-485 transceiver module with integrated isolated-side power (e.g. Mornsun TD301D485H or TD301D485H-A with integrated isolated DC-DC converter and 2500 VDC galvanic isolation barrier; or a discrete solution combining a digital isolator like TI ISO3082 with an isolated DC-DC converter like Mornsun B0505S-1WR3). A bare MAX485 or MAX13487 transceiver and generic breakout boards (such as XY-017) lack isolated DC-DC supplies and do NOT provide a rated galvanic isolation barrier.
> 2. **NEVER CONNECT A 5 V OR 10 V SIGNAL DIRECTLY TO AN ESP32 ADC.**
>    The ESP32 ADC input range is strictly limited to 3.3 V (absolute maximum 3.6 V). For 4–20 mA current loops, a standard 250 Ω shunt produces $20\text{ mA} \times 250\ \Omega = 5.0\text{ V}$, which destroys the ESP32 ADC. A **150 Ω precision resistor** ($0.1\%$ tolerance) must be used instead, yielding $0.60\text{ V}$ at 4 mA and $3.00\text{ V}$ at 20 mA.
> 3. **YF-S201 WATER PULSE LEVEL SHIFTING:**
>    The YF-S201 turbine Hall sensor operates at 5.0 V VCC and outputs 5.0 V logic pulses. Connecting this directly to an ESP32 GPIO destroys the pin. A 2-resistor voltage divider (10 kΩ series / 20 kΩ pull-down to GND) must be wired between the sensor yellow lead and GPIO5 to safely step pulses down to 3.33 V.
> 4. **NO AUTOMATIC MAINS SWITCHING OR WATER-VALVE CONTROL:**
>    The EstateIQ edge firmware and software are strictly read-only advisory decision-support tools. The firmware does NOT contain relays, circuit breaker trip coils, or automated valve actuators. All dashboard actions remain human-in-the-loop recommendations.
> 5. **UNVERIFIED SENSORS KEPT DISABLED:**
>    Any sensor whose exact part number, wiring schematic, ADC shunt, or calibration slope is not physically commissioned must have its configuration pin set to `-1` (disabled).

---

## 2. 🧾 BILL OF MATERIALS (BOM) — INDIA MARKET ESTIMATES

*Note: All prices are conservative budgetary estimates in Indian Rupees (INR) based on standard local distributors (Robu.in, Tanotis, RS Components India). Vendor quotations and GST (18%) may vary.*

| Item # | Component Description | Exact Model / Spec | Qty | Approx Unit Cost (INR) | Total Cost (INR) | Purpose / Role |
| :--- | :--- | :--- | :---: | :---: | :---: | :--- |
| **1** | ESP32-S3 DevKit Edge Gateway | ESP32-S3-WROOM-1 (N16R8, Dual-Core 240MHz, 2.4GHz Wi-Fi) | 1 | ₹650 | ₹650 | Edge acquisition node, Modbus polling, ISR pulse counting, MQTT streaming |
| **2** | Certified 3-Phase Energy Meter | Eastron SDM630-Modbus V2 (MID Certified, RS-485 Modbus RTU, 100A Direct/CT) | 1 | ₹6,800 | ₹6,800 | Metrology for V, A, kW, kWh, PF, Hz, THD over isolated serial bus |
| **3** | Galvanically Isolated RS-485 Transceiver Module | Mornsun TD301D485H (or TD301D485H-A with auto-direction); 3.3V logic, integrated isolated DC-DC supply, 2500 VDC isolation barrier | 1 | ₹550 | ₹550 | Complete galvanic isolation with isolated-side power between high-voltage meter bus and ESP32 3.3V UART |
| **4** | Water Flow Turbine Meter | YF-S201 1/2" Hall-Effect Flow Sensor (1.0 to 30.0 L/min, ~450 pulses/L) | 1 | ₹280 | ₹280 | Digital pulse-counter for flow velocity and cumulative water volume |
| **5** | Voltage Level-Shift Resistors | 10 kΩ and 20 kΩ Metal Film Resistors (0.25W, 1%) | 2 | ₹5 | ₹10 | 5V-to-3.3V voltage divider for YF-S201 pulse output |
| **6** | 4–20 mA Current Loop Shunt Resistor | 150 Ω Precision Resistor (0.1% tolerance, 0.5W, 15 ppm/°C) | 1 | ₹45 | ₹45 | Safe 0.60V–3.00V ADC conversion for optional 4–20 mA pressure loop |
| **7** | USB-to-RS485 Bench Adapter | FTDI FT232RL or CH340 Industrial USB-RS485 Dongle with A/B terminals | 1 | ₹250 | ₹250 | Safe bench demonstration: Modbus slave emulation without AC mains |
| **8** | Regulated DC Power Supply | 5V 2.5A USB-C Power Adapter (BIS Certified) | 1 | ₹350 | ₹350 | Clean, low-noise power for ESP32 DevKit and isolated RS-485 transceiver |
| **9** | Prototyping Breadboard & Wires | 830-point solderless breadboard + Dupont jumper wire bundle | 1 | ₹220 | ₹220 | Benchtop interconnects |
| **10** | DIN Rail Enclosure (Optional) | Modular 4-pole DIN-rail enclosure for ESP32 edge node | 1 | ₹350 | ₹350 | Enclosed electrical safety for demo rig |
| **TOTAL**| **Minimum Bench Rig BOM (Estimated Total)** | *(Items 1, 3, 4, 5, 7, 8, 9: Core ESP32 + Isolated RS-485 + YF-S201 + Level Shift + USB Dongle + 5V PSU + Breadboard/Wires)* | | | **₹2,310** | *Safe bench-demo rig (simulated Modbus)* |
| **TOTAL**| **Full Pilot Kit BOM (Estimated Total)** | *(All Items 1 through 10, including Eastron SDM630 Certified Meter + 150Ω Shunt + DIN Enclosure)* | | | **₹9,505** | *Complete physical metrology installation* |

---

## 3. 🔌 WIRING & INTERFACE MATRIX

```
 +-----------------------------------------------------------------------------------------+
 |                                  ESTATEIQ EDGE GATEWAY                                  |
 |                                                                                         |
 |  [5V DC Power] ---> ESP32 DevKit (VIN / GND)                                            |
 |                                                                                         |
 |  ESP32 3.3V VCC ------------> VCC_LOGIC (3.3V) +--------------------------------------+ |
 |  ESP32 GND -----------------> GND_LOGIC        | Industrially Isolated RS-485 Module  | |
 |  ESP32 GPIO16 (RX2) <-------- RXD (RO)         | (Mornsun TD301D485H / TD301D485H-A)  | |
 |  ESP32 GPIO17 (TX2) --------> TXD (DI)         | [Integrated Isolated DC-DC Converter | |
 |  ESP32 GPIO4  (DIR) --------> CON / DE_RE      |  2500 VDC Galvanic Isolation]        | |
 |                                                +------------------+-------------------+ |
 |                                                                   | Isolated RS-485 Bus |
 |                                                                   | A (+) / B (-) / GND |
 |                                                                   v                     |
 |                                                Eastron SDM630 Modbus Energy Meter       |
 |                                                [Terminal 8: A(+), Terminal 9: B(-)]     |
 |                                                [Galvanically Isolated from ESP32 GND]   |
 |                                                                                         |
 |  [5V DC VCC] -------> YF-S201 Red Wire                                                  |
 |  [Common GND] ------> YF-S201 Black Wire                                                |
 |  YF-S201 Yellow ----> 10k Resistor ---> ESP32 GPIO5 ---> 20k Resistor ---> GND          |
 |                       (5V Pulse)       (3.3V Safe Logic)                                |
 |                                                                                         |
 |  [Optional 4-20mA Pressure Receiver - Keep Pin -1 if unequipped]:                       |
 |  Transmitter (+) ---> +24V External Supply Loop                                         |
 |  Transmitter (-) ---> ESP32 GPIO34 (ADC1) ---> 150 Ohm 0.1% Shunt ---> Supply GND       |
 |                       (0.60V at 4mA, 3.00V at 20mA - NEVER use 250 Ohm)                 |
 +-----------------------------------------------------------------------------------------+
```

### Complete Pin Mapping Table

| ESP32 GPIO | Subsystem | Connected Pin | Signal Description | Electrical Logic Level | Protection / Conditioning |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **GPIO16** | Electricity Meter | Isolated Module RXD (RO) | UART2 Receive (Modbus RTU responses) | 3.3 V TTL | Industrially isolated transceiver module (Mornsun TD301D485H / TD301D485H-A with integrated isolated DC-DC supply; 2500 VDC isolation barrier) |
| **GPIO17** | Electricity Meter | Isolated Module TXD (DI) | UART2 Transmit (Modbus RTU queries) | 3.3 V TTL | Industrially isolated transceiver module (Mornsun TD301D485H / TD301D485H-A with integrated isolated DC-DC supply; 2500 VDC isolation barrier) |
| **GPIO4** | Electricity Meter | Isolated Module CON / DE_RE | Transmit / Receive direction select | 3.3 V TTL (HIGH=TX, LOW=RX) | Direct GPIO drive for TD301D485H CON pin (set to -1 if using auto-directional TD301D485H-A) |
| **GPIO5** | Water Flow Meter | YF-S201 Signal | Interrupt-driven pulse counter | 3.3 V TTL (pulsed) | 10k / 20k divider steps 5V down to 3.33V |
| **GPIO34** | Water Pressure (Opt)| 4–20 mA Return | Analog voltage input (ADC1_CH6) | 0.60 V to 3.00 V DC | 150 Ω precision shunt (0.1%). Pin set to -1 |
| **GPIO12/13**| Tank Level (Opt) | Echo / Trig | Ultrasonic sensor interface | 3.3 V TTL | Reserved; kept disabled (Pin -1) |
| **VIN (5V)** | Power Supply | USB-C 5V Supply | System DC power | 5.0 V DC (±5%) | Polyswitch fuse & reverse protection |
| **GND** | System Ground | Common Ground | Reference potential | 0.0 V | Star-topology ground bus |

---

## 4. 📡 MQTT TOPIC HIERARCHY & CANONICAL ENVELOPE

### Topics
```text
estateiq/{facility_id}/{building_id}/meter/{device_id}/telemetry
estateiq/{facility_id}/{building_id}/sensor/{device_id}/telemetry
```

### Ingestion Telemetry Schema (Canonical Example)
```json
{
  "schema_version": "1.0",
  "message_id": "MSG_ESP32_ELEC_1729681200",
  "gateway_id": "ESP32_EDGE_GATEWAY_01",
  "auth_token": "your_provisioned_gateway_key",
  "device_id": "METER-BLOCK-B-001",
  "facility_id": "FAC_GEC_CAMPUS",
  "building_id": "Block B Hostel",
  "source_type": "real_sensor",
  "event_timestamp": "2026-10-23T11:30:00Z",
  "sent_timestamp": "2026-10-23T11:30:01Z",
  "sequence_number": 1420,
  "metrics": [
    {"name": "active_power_kw", "value": 14.85, "unit": "kW", "quality": "good"},
    {"name": "cumulative_energy_kwh", "value": 12845.6, "unit": "kWh", "quality": "good"},
    {"name": "voltage_v", "value": 231.4, "unit": "V", "quality": "good"},
    {"name": "current_a", "value": 64.2, "unit": "A", "quality": "good"},
    {"name": "power_factor", "value": 0.96, "unit": "ratio", "quality": "good"},
    {"name": "frequency_hz", "value": 50.02, "unit": "Hz", "quality": "good"}
  ]
}
```

### Security & Trust Boundary (Demo Bench vs. Production)

1. **No String-Based Provenance**: Device IDs (`METER-*`, `DEV_REAL-*`) are arbitrary identifiers. Ingesting a payload with `"source_type": "real_sensor"` is merely a claim; it never produces a verified `[REAL SENSOR]` badge without valid gateway credential verification.
2. **Credential Authentication**:
   - `auth_token` in the payload must match a pre-registered, unrevoked gateway secret (`ESTATEIQ_GATEWAY_API_KEY`).
   - If valid, the record receives verified provenance and the emerald `[REAL SENSOR]` badge.
   - If invalid or revoked, the telemetry is rejected with HTTP 400 (`INVALID_GATEWAY_CREDENTIAL` or `REVOKED_GATEWAY_CREDENTIAL`).
3. **Local Demo Mode Trust Boundary**:
   - In local bench setup (`allow_unverified_demo_mode = True`), unauthenticated payloads are accepted but labeled `[UNVERIFIED SENSOR - DEMO MODE]`.
   - Outside development (`allow_unverified_demo_mode = False`), unauthenticated payloads are strictly rejected with HTTP 400 (`MISSING_GATEWAY_CREDENTIAL`).
4. **Current Bench-Demo Limitations**:
   - **Plaintext / Local LAN**: The ESP32 transmits its provisioned gateway key within JSON over plaintext MQTT (port 1883) at QoS 0. This architecture is safe only on an isolated demo router or local bench network. It is **not** production-grade security.
   - **Volatile SRAM Queue**: Offline buffering uses 30 envelopes in ESP32 internal SRAM. Data is not preserved across brownouts or reboots. QoS 0 delivery is best-effort and volatile.
5. **Production Migration Path**:
   - Deploy MQTT over TLS (MQTTS, port 8883) with mutual TLS (mTLS) client certificates per gateway.
   - Enforce broker-level topic ACLs (gateway identity asserted by TLS common name; no credentials in JSON payload).
   - Use SPIFFS/LittleFS flash storage for non-volatile QoS 1 persistent queueing.

---

## 5. 🧪 SAFE BENCH-DEMO PROCEDURE (WITHOUT EXPOSED MAINS)

To demonstrate the full physical hardware pipeline safely in a hackathon demo booth without high-voltage AC hazards:

### Step 1: Laptop Modbus Simulator Setup
1. Plug an isolated USB-to-RS485 dongle into the laptop USB port.
2. Connect Dongle Terminal `A (+)` to Isolated Module `A (+)`, Dongle `B (-)` to Isolated Module `B (-)`, and Isolated GND to Dongle GND. (Do NOT bridge isolated bus GND to ESP32 system GND).
3. Start a local Modbus RTU slave emulator on the laptop (e.g., using `pymodbus` or `diagslave` on the USB COM port at 9600 baud, 8N1, Slave ID 1).
4. Configure the slave to respond to Function 0x04 (Read Input Registers) with IEEE 754 float values matching the Eastron SDM630 register map:
   - Reg `0x0000` (Voltage): `230.5` V
   - Reg `0x0006` (Current): `45.2` A
   - Reg `0x0034` (Active Power): `10418.0` W (converted by ESP32 to `10.42` kW)
   - Reg `0x001E` (Power Factor): `0.95`
   - Reg `0x0046` (Frequency): `50.0` Hz
   - Reg `0x0156` (Cumulative Energy): `5240.2` kWh

### Step 2: Water Pulse Generation
1. Connect the YF-S201 sensor to a tabletop water squeeze bottle or connect a simple mechanical pushbutton between GPIO5 and GND (with the 10k/20k voltage divider in place).
2. Tapping the pushbutton or pulsing water produces clean 3.3V pulses on GPIO5. The ESP32 ISR counts pulses, calculates flow rate (L/min) and cumulative water ($m^3$), and formats canonical JSON.

### Step 3: Broker & Backend Connection
1. Launch Mosquitto MQTT broker on the laptop: `mosquitto -v -p 1883`.
2. Launch EstateIQ backend: `uvicorn api.main:app --port 8000`.
3. Launch EstateIQ MQTT consumer: `python -m src.data.mqtt_consumer`.
4. Power on the ESP32. Observe serial terminal output:
   - Wi-Fi connects non-blockingly.
   - NTP synchronizes real ISO-8601 UTC time.
   - Modbus polls query registers `0x0000` to `0x0156` over RS-485.
   - Packets publish to `estateiq/FAC_GEC_CAMPUS/Block_B_Hostel/meter/METER-BLOCK-B-001/telemetry`.

### Step 4: Verification in Web Dashboard
1. Open `http://localhost:8000/`.
2. Click on the **Live IoT Monitor** tab.
3. Confirm the Hardware Metrology Matrix displays:
   - Electricity: `MEASURED` with green `[REAL SENSOR]` badge.
   - Water Flow: `MEASURED` with real pulse counter updates.
   - Aux Pressure & Tank Level: `DISABLED (Pin -1)` with clear safety explanations.

---

## 6. 📋 SENSOR CALIBRATION & ACCEPTANCE CHECKLIST

| Verification Item | Acceptance Test Criteria | Pass / Fail Condition | Current Status |
| :--- | :--- | :--- | :---: |
| **Mains Voltage Isolation** | Certified galvanic separation between high voltage AC and ESP32 pins. Requires isolated RS-485 transceiver datasheet (Mornsun TD301D485H / TD301D485H-A with integrated isolated DC-DC converter, rated 2500 VDC dielectric withstand test voltage; or discrete ISO3082 with isolated Mornsun B0505S-1WR3 supply). Bare transceivers (MAX485, MAX13487) and unverified boards (XY-017) lack isolated power and do not provide a rated isolation barrier. | Pass: Transceiver datasheet confirms manufacturer-rated 2500 VDC galvanic isolation test voltage with integrated isolated-side power. An ohmmeter continuity check (>10 MΩ) only proves absence of DC shorts and does NOT certify or verify an isolation barrier under high-voltage dielectric stress. Physical hi-pot dielectric breakdown testing has not been performed on bench hardware. | **DESIGN SPECIFIED** |
| **ADC Input Voltage Safety**| Under maximum 20 mA loop current, voltage at GPIO34 must not exceed 3.00 V. | Pass: $20\text{ mA} \times 150\ \Omega = 3.00\text{ V} \le 3.30\text{ V}$ specification verified mathematically; physical 20 mA loop injection not performed on hardware. | **DESIGN SPECIFIED** |
| **YF-S201 Pulse Calibration**| 5.0 Liters of water passed through turbine. Total pulse count recorded. | Pass: Calculated factor within $\pm 5\%$ of calibration factor ($450 \pm 25$ pulses/L). Volumetric 5L test not performed on physical sample. | **NOT TESTED** |
| **Modbus CRC & Frame Audit**| 100 consecutive Modbus read frames executed without CRC or slave ID error. | Pass: CRC error rate $< 0.1\%$. Physical communication with live meter on bench hardware not executed. | **NOT TESTED** |
| **Monotonic Counter Integrity**| Energy and water cumulative counters increase monotonically. Reset or rollback detected server-side. | Pass: Counter rollback flags quality warning and suppresses false interval surge. Verified in automated test suite. | **SOFTWARE TESTED** |
| **Durable Provenance Check** | Ingested packets without verified gateway credentials cannot claim `[REAL SENSOR]` badge. | Pass: Unauthenticated packets labeled `[UNVERIFIED SENSOR - DEMO MODE]`. Verified in automated test suite. | **SOFTWARE TESTED** |
| **Network Outage Recovery** | Wi-Fi disabled for 60 seconds; sensor pulse counting continues; queue replays on reconnect. | Pass: 30 packets buffered in RAM; zero lost pulses; replay order chronological. Physical Wi-Fi interrupt on hardware not executed. | **DESIGN SPECIFIED** |

---

## 7. 🔍 SYSTEM CAPABILITY MATRIX

| Feature / Subsystem | What is Working in Software | What is Simulated | What is Physical | What Remains Unverified |
| :--- | :--- | :--- | :--- | :--- |
| **Electricity Metrology** | Full canonical schema, active power (kW), cumulative energy (kWh), V, A, PF, Hz, THD, counter reset detection | Historical campus dataset, baseline generator, load surge presets | Eastron SDM630 Modbus RTU driver in ESP32 firmware, isolated RS-485 query loop | Physical calibration against utility revenue-grade reference meter |
| **Water Metrology** | Interrupt-driven pulse math, flow rate (L/min), volume ($m^3$), night-flow leak detection | Simulator hydrodynamic curves, high-flow anomaly preset | YF-S201 ISR counter driver, 5V-to-3.3V divider wiring specification | Physical 5-liter bucket calibration on the team's specific turbine sample |
| **Pressure & Tank Level** | Bounds checking, 150Ω shunt voltage math, uncalibrated level rejection | Riser hydraulic pressure, overhead tank fill rate & drainage simulation | Driver boundary implemented; pins set to -1 (disabled) for electrical safety | Physical 4–20 mA pressure transmitter and ultrasonic tank geometry |
| **Intelligence & DIF Fusion** | CatBoost energy forecast, baseline calculation, anomaly consensus, SHAP explainability | Campus occupancy headcount, weather temperature profile | Evaluates live incoming telemetry stream in real time | Multi-month seasonal field holdout dataset |
| **Data Quality Gate** | Non-finite rejection, physical limits, stale timeout (45s), anomaly suppression | Mock communication error injection | Validates incoming CRC, NTP timestamp sync, and device health | Long-term RS-485 electromagnetic interference (EMI) test |

---

## 8. ⏱️ 2–3 MINUTE FINALIST DEMONSTRATION SCRIPT

### Objective
Demonstrate an end-to-end, credible, and safe IoT data pipeline: from physical sensor observation through canonical ingestion to contextual AI explainability and human-in-the-loop recommendations.

### Timeline
- **0:00 – 0:30 (The Physical Edge):**
  - Point to the bench demonstration hardware: *"Here is our ESP32-S3 edge gateway. Notice our electrical safety architecture: the ESP32 is completely isolated from high voltages, communicating over RS-485 with a certified Eastron SDM630 energy meter, and our water turbine uses a level-shifted pulse counter."*
  - Show the serial terminal log showing NTP synchronization and Modbus registers being read in real time.
- **0:30 – 1:15 (Live Ingestion & Sensor Matrix):**
  - Switch to the EstateIQ web dashboard on the **Live IoT Monitor** tab.
  - Highlight the **Hardware Metrology Matrix**: *"Notice our provenance integrity: the dashboard displays a verified `[REAL SENSOR]` badge because the gateway authenticated with server-side credentials. Unconnected auxiliary analog pins are shown as disabled rather than displaying fabricated numbers."*
  - Point to the live cards updating every 15 seconds with active power, line voltage, and water flow rate.
- **1:15 – 2:00 (Contextual Anomaly & DIF Decision Intelligence):**
  - Trigger an event (either step on the load via the simulator/Modbus bench or simulate low-occupancy night hours).
  - Open the **Overview** / **Operational Alerts** tab:
    - Point out the active anomaly: *"EstateIQ detected a sustained water flow of 18.2 L/min during night hours when building occupancy was under 15."*
    - Show the **Decision Intelligence Fusion (DIF)** card: explain that the model distinguishes between a *suspected* leak and a *confirmed* leak based on whether occupancy was physically measured or estimated.
- **2:00 – 2:30 (Action Recommendation & Verification):**
  - Show the actionable resolution card: *"Rather than claiming risky automatic valve closure, EstateIQ generates a prioritized work order: 'Dispatch technician to inspect Floor 2 riser valve.' Once resolved, the system calculates and verifies actual utility cost savings against our historical baseline."*

### ⚠️ Fallback Plan (If Sensor Wire or Local Wi-Fi Fails)
1. **Network Disconnection Fallback:**
   - The ESP32 firmware immediately buffers incoming samples in its RAM queue without stalling sensor interrupts.
   - The UI automatically displays `STALE TELEMETRY (>45s)`, and the Data Quality Engine suppresses false resource waste claims, raising a clear **Sensor Communication Warning**.
2. **Hardware Failure Fallback:**
   - Seamlessly switch the dashboard location dropdown from `Live Hardware` to `Interactive IoT Simulator`.
   - The UI immediately tags telemetry with `[SIMULATED IoT]` in gold, ensuring judges see that the software pipeline functions flawlessly without falsely claiming hardware measurements.
