# EstateIQ Physical Hardware Wiring, Schematics & Pinout Guide
**ESP32 Edge Sensor Gateway Architecture (v3.0 Real-IoT Certified)**

---

## 1. Overview & Bill of Materials (BOM)

This reference design integrates 22 verified physical hardware parts into an industrial-grade EstateIQ Edge Gateway powered by the **ESP-32-WROOM-32** microcontroller. The gateway samples multi-modal submetering, hydraulics, air quality, climate, and diagnostics telemetry, locally renders metrics to a **0.96" SSD1306 OLED display**, and securely streams JSON packets over Wi-Fi/HTTP to the EstateIQ platform (`/api/v1/iot/telemetry`).

| Item # | Component Name | Electrical Interface | ESP32 Pin Allocation | Operating Voltage | Notes & Voltage Scaling |
|:---|:---|:---|:---|:---|:---|
| **1** | **Peacefair PZEM-004T 10A** | Modbus-RTU over UART2 | **RX2: GPIO 16, TX2: GPIO 17** | 5V Logic / 80-260V AC | Isolated optocoupler logic; CT coil on live load |
| **2** | **ZJ-S201 Water Flow Sensor** | Hall Pulse Interrupt | **GPIO 4 (Interrupt)** | 5V VCC, 3.3V Output | 10kΩ/22kΩ divider to protect GPIO 4 |
| **3** | **JSN-SR04T / AJ-SR04M** | Waterproof Ultrasonic Sonar | **Trig: GPIO 5, Echo: GPIO 18** | 5V VCC | 1kΩ/2.2kΩ divider on Echo line to GPIO 18 |
| **4** | **HC-SR04 Ultrasonic Sensor** | Benchtop Ultrasonic Sonar | **Trig: GPIO 5, Echo: GPIO 18** | 5V VCC | Pin-compatible alternative to JSN-SR04T |
| **5** | **DHT11 Climate Module** | 1-Wire Digital Bit-bang | **DATA: GPIO 23** | 3.3V VCC | 10kΩ pull-up to 3.3V; NOAA Heat Index computed |
| **6** | **MQ-135 Gas & Air Quality** | Analog Voltage (ADC1) | **AO: GPIO 34 (Analog In)** | 5V Heater VCC | 10kΩ/22kΩ divider to keep AO <= 3.3V |
| **7** | **0.96" I2C Blue OLED Module** | I2C (SSD1306 128x64) | **SDA: GPIO 21, SCL: GPIO 22** | 3.3V VCC | Built-in pull-ups; cycling 7-line local dashboard |
| **8-11**| **Carbon Film Resistors** | Passive Divider / Pull-up | *Across signal nets* | Up to 1/4 Watt | 1kΩ, 2.2kΩ, 10kΩ, 22kΩ (5% tolerance) |
| **12-15**| **Wires & Heat Shrink** | Wiring Harness & Sleeves | *Interconnects* | Industrial rating | 23SWG hookup, 7/36 cable, heat shrink, PVC tape |
| **16-17**| **DC 5.5x2.5mm Barrel Jacks** | Main 5V DC Power Input | **5V Bus & GND Bus** | 5.0V DC (2A minimum) | Regulated external 5V supply |
| **18-19**| **2-Pin & 3-Pin PBT Connectors**| Screw Terminal Blocks | *PCB Edge Ports* | 5mm pitch | Robust screw clamping for external sensor probes |
| **20-22**| **Veroboard & ESP32 Kits** | Main Carrier & Controller | **ESP32-WROOM-32** | 3.3V / 5V | 10x15cm proto board + 38-pin expansion socket |

---

## 2. Pin Conflict Resolution & GPIO Architecture

```
                    +------------------------------------+
                    |        ESP32-WROOM-32 MCU          |
                    +------------------------------------+
                                      |
       +------------------------------+------------------------------+
       |               |              |               |              |
   [GPIO 16/17]    [GPIO 4]       [GPIO 5/18]     [GPIO 23]      [GPIO 34]
    UART2 Serial  Hall Interrupt  Sonar Pulse   1-Wire Bus    ADC1 Analog
         |             |              |               |              |
    PZEM-004T 10A   ZJ-S201       JSN-SR04T /       DHT11          MQ-135
     Energy Meter  Flow Meter      HC-SR04       Temp & Hum      Gas Sensor
```

### Critical Pin Safeguards:
1. **Flow Interrupt vs. Ultrasonic Trig Separation:**
   - In earlier prototypes, flow interrupt was inadvertently mapped to GPIO 5, conflicting with Sonar Trig.
   - **Resolved Architecture:** Flow interrupt is permanently assigned to **GPIO 4**, completely isolating high-frequency Hall pulses from the ultrasonic 10 µs trigger pulse on **GPIO 5**.
2. **Wi-Fi ADC Conflict Prevention:**
   - On the ESP32, ADC2 cannot be used while Wi-Fi is active.
   - **Resolved Architecture:** The MQ-135 analog output connects to **GPIO 34**, which belongs strictly to **ADC1**, guaranteeing noise-free 12-bit analog sampling with simultaneous Wi-Fi transmission.
3. **Dedicated I2C Hardware Bus:**
   - Hardware I2C is bound to default pins **SDA: GPIO 21** and **SCL: GPIO 22**, providing robust 400 kHz communication to the SSD1306 128x64 OLED.

---

## 3. Voltage Divider & Logic Protection Calculations

ESP32 GPIO pins are **not 5V tolerant**. Keep input signals within the ESP32 3.3V operating range; do not use the absolute-maximum rating as a design target. Verify the actual module output voltage and output type before wiring. A passive divider is only appropriate for a push-pull output when its source impedance and pulse rate are compatible with the divider.

### A. Sonar Echo Line (JSN-SR04T / HC-SR04 -> GPIO 18)
- **Example divider for a verified 5V push-pull Echo output:** $R_1 = 2.2\text{ k}\Omega$ in series and $R_2 = 3.3\text{ k}\Omega$ from input node to GND.

$$V_{\text{in(ESP32)}} = V_{\text{sonar}} \times \frac{R_2}{R_1 + R_2} = 5.0\text{ V} \times \frac{3300}{2200 + 3300} = 3.0\text{ V}$$

Do not use the former 1kΩ/2.2kΩ pair: at a 5V source it yields about 3.44V, which is above the 3.3V operating range. Confirm the divider output with a multimeter before connecting GPIO. This example is not a substitute for checking the exact sonar module documentation.

### B. Water Flow Pulse (ZJ-S201 -> GPIO 4)
- For a verified 5V push-pull output, one example is $R_1 = 2.2\text{ k}\Omega$ series and $R_2 = 3.3\text{ k}\Omega$ to GND. If the sensor output is open-collector/open-drain, use a pull-up to 3.3V instead, if supported by the sensor documentation; do not assume its output topology.

$$V_{\text{in(ESP32)}} = 5.0\text{ V} \times \frac{3300}{2200 + 3300} = 3.0\text{ V}$$

### C. MQ-135 Analog Voltage Scaling (AO -> GPIO 34 / ADC1)
- Use a verified divider that keeps the maximum analog output below 3.3V. For a 0–5V module output, an example is $R_1 = 10\text{ k}\Omega$ series and $R_2 = 15\text{ k}\Omega$ to GND.

$$V_{\text{ADC}} = V_{\text{sensor}} \times \frac{15000}{10000 + 15000} = \frac{V_{\text{sensor}}}{1.6667}$$

If this divider is used, configure `MQ135_VOLTAGE_DIVIDER_RATIO` as approximately `1.6667f` and confirm the measured ADC voltage before use. The local firmware config and physical resistor values must agree. The previously listed 10kΩ/22kΩ pair can produce about 3.44V from a 5V output and must not be treated as safe for a 3.3V ESP32 input.

> [!WARNING]
> **Metrological Disclaimer on MQ-135 Air Quality Sensor:**
> The MQ-135 module is an unheated/uncalibrated metal-oxide semiconductor sensor sensitive to a broad range of gases (ammonia, benzene, smoke, sulfides). Its output is an **indicative analog signal (12-bit ADC raw count)**.
> **DO NOT claim or present MQ-135 data as certified CO₂, certified AQI, or particulate matter (PM2.5/PM10).** Certified audits require calibrated Non-Dispersive Infrared (NDIR) sensors for CO₂ and optical laser scattering counters for PM.

> [!CAUTION]
> **High-Voltage Mains Safety Warning (PZEM-004T AC Electricity Meter):**
> Measuring 80–260V AC carries severe electrocution hazard. High-voltage wiring must only be carried out under qualified supervision. All 230V terminals must be enclosed inside a protective, touch-safe ABS enclosure. Never route AC lines on proto-boards.

### D. DHT11 1-Wire Pull-Up
- $R_{\text{pullup}} = 10\text{ k}\Omega$ between **DHT11 DATA (GPIO 23)** and **3.3V VCC**.

---

## 4. Comprehensive Sensor Interconnect Schematic

### Connector 1: PZEM-004T 10A AC Energy Meter
```
PZEM-004T (Low Voltage Side)          ESP32 Carrier Board
-----------------------------          -------------------
Pin 1: VCC (5V)       -------------->  5V Power Rail
Pin 2: RX             -------------->  GPIO 17 (TX2)
Pin 3: TX             -------------->  GPIO 16 (RX2)
Pin 4: GND            -------------->  Common GND Rail

PZEM-004T (High Voltage Side - CAUTION: 230V AC MAINS)
------------------------------------------------------
Terminal L (Line In):      230V AC Mains Phase
Terminal N (Neutral In):   230V AC Mains Neutral
Terminal CT 1:             CT Coil Blue Wire
Terminal CT 2:             CT Coil Black Wire
*NOTE: Pass only ONE single live wire through the center hole of the CT coil.*
```

### Connector 2: ZJ-S201 Water Flow Sensor
```
ZJ-S201 Turbine                     ESP32 Carrier Board
---------------                     -------------------
Red Wire:   VCC (5V)  ------------> 5V Power Rail
Black Wire: GND       ------------> Common GND Rail
Yellow Wire: Pulse    ----[2.2kΩ]--+----> GPIO 4 (Pulse Interrupt)
                                    |
                                  [3.3kΩ]
                                    |
                                   GND
```

### Connector 3: JSN-SR04T / HC-SR04 Ultrasonic Sonar
```
Ultrasonic Module                   ESP32 Carrier Board
-----------------                   -------------------
VCC (5V)              ------------> 5V Power Rail
GND                   ------------> Common GND Rail
Trig                  ------------> GPIO 5 (Direct Output)
Echo                  ----[2.2kΩ]---+----> GPIO 18 (Echo Input)
                                    |
                                 [3.3kΩ]
                                    |
                                   GND
```

### Connector 4: DHT11 Temperature & Humidity Sensor
```
DHT11 Module                        ESP32 Carrier Board
------------                        -------------------
Pin 1: VCC (3.3V)     ------------> 3.3V Power Rail
Pin 2: DATA           ------+-----> GPIO 23 (1-Wire Digital)
                            |
                         [10kΩ] (Pull-up)
                            |
                          3.3V
Pin 3: NC (Not Used)
Pin 4: GND            ------------> Common GND Rail
```

### Connector 5: MQ-135 Gas & Air Quality Sensor
```
MQ-135 Module                       ESP32 Carrier Board
-------------                       -------------------
VCC (5V for Heater)   ------------> 5V Power Rail
GND                   ------------> Common GND Rail
DO (Digital Out)      ------------> Not Connected
AO (Analog Out)       ----[10kΩ]----+----> GPIO 34 (ADC1 Channel 6)
                                    |
                                  [15kΩ]
                                    |
                                   GND
```

### Connector 6: 0.96" SSD1306 Blue OLED Display
```
SSD1306 4-Pin OLED                  ESP32 Carrier Board
------------------                  -------------------
GND                   ------------> Common GND Rail
VCC                   ------------> 3.3V Power Rail
SCL                   ------------> GPIO 22 (Hardware I2C SCL)
SDA                   ------------> GPIO 21 (Hardware I2C SDA)
```

---

## 5. Veroboard Prototype Layout & Terminal Block Mapping

On your **10x15 cm Veroboard**, organize the board into three distinct electrical zones:

```
+-------------------------------------------------------------------------+
| [J1: 5V DC IN]   [5V Bus Rail] =======================                  |
| [2-Pin PBT]      [GND Bus Rail] ======================                  |
|                                                                         |
|  +------------------------+      +-----------------------------------+  |
|  |   ESP32-WROOM-32       |      |   OLED 0.96" SSD1306 Display      |  |
|  |   38-Pin Socket        |      |   Mounted Flush Front             |  |
|  +------------------------+      +-----------------------------------+  |
|                                                                         |
|  ZONE A: 5V Logic Sensors        ZONE B: Voltage Dividers (Resistors)   |
|  -------------------------       ------------------------------------   |
|  [TB1: PZEM UART] (3-Pin PBT)    - 1kΩ / 2.2kΩ Echo Divider             |
|  [TB2: Sonar Trig/Echo] (3-Pin)  - 10kΩ / 22kΩ Flow Divider             |
|  [TB3: ZJ-S201 Flow] (3-Pin PBT) - 10kΩ / 22kΩ MQ-135 Divider          |
|  [TB4: MQ-135 Gas] (2-Pin PBT)   - 10kΩ DHT11 Pull-up Resistor          |
|  [TB5: DHT11 Climate] (2-Pin)                                           |
|                                                                         |
|  ZONE C: High Voltage Barrier (PHYSICALLY SEPARATED BY 20MM ROUTING)   |
|  -------------------------------------------------------------------   |
|  PZEM AC Mains Terminals & CT Clamp (No AC tracks on Veroboard)         |
+-------------------------------------------------------------------------+
```

### Safety & Soldering Best Practices:
1. **Never bring 230V AC lines onto the Veroboard!** Connect mains wires directly into the isolated screw terminals of the PZEM-004T module inside an enclosed ABS junction box.
2. **Heat Shrink Sleeves:** Slide the included 20cm heat shrink sleeves over all resistor solder joints and wire splices before applying a heat gun or flame.
3. **Common Ground:** Tie the ESP32 GND, PZEM-004T GND, 5V DC power supply GND, and sensor GNDs to a single, continuous solder bridge line along the bottom of the Veroboard.

---

## 6. End-to-End Verification Runbook

### Step 1: Flashing Firmware to ESP32
1. Open Arduino IDE or PlatformIO.
2. Open `hardware/esp32/firmware/main/main.ino`.
3. Verify settings in `hardware/esp32/firmware/main/config.h`:
   ```cpp
   #define WIFI_SSID             "YOUR_WIFI_SSID"
   #define WIFI_PASSWORD         "YOUR_WIFI_PASSWORD"
   #define HTTP_SERVER_ENDPOINT  "http://YOUR_SERVER_IP:8000/api/v1/iot/telemetry"
   ```
4. Select Board: **ESP32 Dev Module**, Flash Frequency: **80MHz**, Upload Speed: **921600**.
5. Upload firmware.

### Step 2: Observing Serial Monitor (Baud 115200)
Verify the startup sequence:
```
========================================================
EstateIQ ESP32 Edge Sensor Gateway Firmware v3.0-RealIoT
========================================================
[CONFIG] Gateway ID: ESP32_EDGE_GATEWAY_01 | Facility: FAC_GEC_CAMPUS
[PZEM-004T] Initialized on RX:16, TX:17, Baud:9600
[ZJ-S201] Flow interrupt attached on GPIO 4
[AJ-SR04M] Ultrasonic initialized: Trig=GPIO5, Echo=GPIO18
[DHT11] Climate sensor armed on GPIO 23
[MQ-135] Gas sensor initialized on ADC1 GPIO 34
[OLED] SSD1306 128x64 display active on SDA:21, SCL:22
[WIFI] Connected! Assigned IP: 172.16.222.83
[HTTP] Telemetry POST accepted (HTTP 200)
```

### Step 3: Verifying EstateIQ Web Dashboard
1. Navigate to: `http://localhost:8000/static/index.html#iot-monitor`
2. Inspect the **Hardware Metrology & Sensor Status Matrix**:
   - All 6 physical sensors show **`LIVE MEASURED [REAL HARDWARE]`** in solid emerald `#00F0B5` badges.
   - Background is solid pitch dark `#081D17` and `#0C3328` headers with maximum contrast.
3. Verify the **6 Real-Time Sensor Gauges**:
   - **PZEM-004T:** Live Active Power (kW), Voltage (V), Current (A), Energy (kWh).
   - **Water Riser & Tank:** Tank Level (%), Sonar Clearance (cm), Flow Rate (L/min), Cumulative ($m^3$).
   - **MQ-135:** Raw ADC Counts, Sensor Voltage (V), Indicative CO₂/Gas (ppm).
   - **DHT11:** Temperature (°C), Humidity (% RH), NOAA Heat Index (°C).
   - **OLED & Diagnostics:** SSD1306 State, I2C/UART2 Bus Health.
   - **Resource Simulator:** Virtual node on Port 8503 (when running).
4. Verify **Anomaly Engine**:
   - Real-time physics engine evaluates all 12 rules across fused telemetry with zero demo data.

