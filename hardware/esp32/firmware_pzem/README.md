# EstateIQ ESP32 Dedicated PZEM-004T Metrology Gateway (Node #2)

This directory contains the production Arduino firmware for the 2nd dedicated ESP32 edge microcontroller measuring electrical metrology via the Peacefair PZEM-004T (v3.0 / v4.0).

---

## 1. Hardware Pinout & Wiring

| PZEM-004T Pin | ESP32 GPIO | Description |
| :--- | :--- | :--- |
| **5V (VCC)** | 5V / VIN | Power for PZEM optical isolation (5V DC) |
| **GND** | GND | Common ground |
| **TX** | **GPIO16 (RX2)** | PZEM Serial Transmit -> ESP32 HardwareSerial(2) Receive |
| **RX** | **GPIO17 (TX2)** | PZEM Serial Receive <- ESP32 HardwareSerial(2) Transmit |

* **High Voltage AC side:** Connected to AC mains / test load circuit.
* **Current Transformer (CT):** Clamped around the live (phase) conductor only.

---

## 2. Capabilities & Dual-Output Pipeline

1. **Embedded Local Web Dashboard:**
   * Browsing to `http://<ESP32_IP>/` on your phone or laptop loads a live dark-mode web dashboard showing real-time Volts, Amps, Watts, kWh, Hz, PF, and Cloud Sync state.
2. **EstateIQ Cloud REST Ingestion:**
   * Dispatches canonical telemetry packets directly to `POST http://<HOST>:8000/api/v1/iot/telemetry`.
   * Maps to `METER-BLOCK-B-001` in the EstateIQ Global Device Registry.
   * Authenticated with `GATEWAY_API_KEY` for verified hardware badge `[REAL SENSOR]` on the EstateIQ dashboard.

---

## 3. How to Flash

1. Open **Arduino IDE**.
2. Go to **File -> Open** and select:
   `hardware/esp32/firmware_pzem/main/main.ino`
3. Install required libraries via Library Manager:
   * **PZEM004Tv30** by Mandar Joshi
   * **ArduinoJson** by Benoit Blanchon (version 6.x)
4. Check or edit settings in `config.h` (Wi-Fi SSID, password, Backend IP).
5. Select Board: **ESP32 Dev Module**, select COM Port, and click **Upload**.

