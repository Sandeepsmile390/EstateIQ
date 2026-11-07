# EstateIQ Hardware Gateway & Edge Metrology Specification

This specification documents the physical hardware architecture, edge microcontroller firmware, galvanic isolation barriers, sensor conditioning circuits, and protocol interfaces for the **EstateIQ Sustainable Facility & Estate Intelligence Platform**.

For complete step-by-step flashing, wiring pinouts, and Arduino IDE instructions, refer to the [ESP32 Hardware & Firmware Guide](../hardware/esp32/README.md).

---

## 1. Edge Hardware Profile & Bill of Materials (BOM)

| Component | Exact Model / Specification | Purpose / Subsystem | Interface & Signal Level | Safety / Isolation Requirement |
| :--- | :--- | :--- | :--- | :--- |
| **Microcontroller Node** | ESP32-WROOM-32D / ESP32-S3 DevKit (Dual-core 240MHz, 2.4GHz Wi-Fi) | Edge acquisition node, SNTP UTC clock, Modbus master, pulse ISR, dual HTTP/MQTT streaming | 3.3V DC Logic | Powered by regulated 5V USB-C power supply with star ground |
| **Certified Energy Meter** | Eastron SDM630-Modbus (MID Certified Three-Phase DIN Rail Meter) | AC mains metrology ($V, A, kW, kWh, PF, Hz$) | RS-485 Modbus RTU (9600 8N1, Slave ID 1, Function 0x04 Input Registers) | **Enclosed High-Voltage Metrology:** Never connect AC mains or bare CT leads directly to microcontroller pins! |
| **Isolated RS-485 Transceiver** | Mornsun TD301D485H / TD301D485H-A module with integrated DC-DC supply | Bidirectional differential bus interface between meter and ESP32 UART2 | 3.3V TTL (RO/DI/CON) to ESP32 GPIO16 (RX), GPIO17 (TX), GPIO4 (DE/RE) | **2500 VDC Galvanic Isolation Barrier:** Integrated isolated-side power prevents dangerous ground loops between AC panel and DC logic. |
| **Water Flow Turbine Sensor** | YF-S201 1/2" Hall-Effect Flow Meter (1.0 to 30.0 L/min, ~450 pulses/L) | Interrupt-driven flow velocity and volumetric accumulator | 5.0V VCC / Pulsed Output | **Mandatory 10k/20k Voltage Divider:** Steps 5.0V pulses down to 3.33V safely at GPIO5. |
| **Pressure Transmitter (Opt)** | 4–20 mA Industrial Pressure Transmitter (0–10 bar) | Riser hydrostatic pressure monitoring | 4–20 mA current loop | **150 Ω 0.1% Precision Shunt Resistor:** Produces 0.60V at 4mA and 3.00V at 20mA. ⚠️ Standard 250 Ω shunts produce 5.0V and destroy ESP32 ADC! (Kept disabled at Pin -1 by default). |

---

## 2. Low-Voltage Edge Architecture Schematic

```text
  [230V / 415V AC Mains]
            │
  ┌─────────▼─────────┐
  │ Eastron SDM630    │ (Certified Enclosed Metrology)
  │ Modbus Meter      │
  └─────────┬─────────┘
            │ Modbus RTU (Terminals 8:A, 9:B)
  ══════════╪═════════════════════════════════════════════════════════
  [ 2500 VDC Galvanic Isolation Barrier — Mornsun TD301D485H Module ]
  ══════════╪═════════════════════════════════════════════════════════
            │ Isolated 3.3V UART (RX: GPIO16, TX: GPIO17, DE/RE: GPIO4)
  ┌─────────▼─────────┐             ┌─────────────────────────┐
  │ ESP32 Edge Node   │<──[GPIO 5]──┤ YF-S201 Water Turbine   │
  │ (3.3V DC Logic)   │             │ (via 10k/20k Divider)   │
  └─────────┬─────────┘             └─────────────────────────┘
            │
            │ Wi-Fi 2.4 GHz (SNTP Synchronized ISO8601 Timestamps)
            │
            ├─── Mode A: Direct HTTP REST ───> POST /api/v1/iot/telemetry
            └─── Mode B: Edge MQTT Broker ───> PUB estateiq/FAC_GEC_CAMPUS/...
            │
  ┌─────────▼─────────┐
  │ EstateIQ Backend  │ (FastAPI Port 8000: Gateway Authentication Gate)
  └───────────────────┘
```

---

## 3. Mandatory Electrical Safety & Regulatory Rules

1. **Strictly Read-Only Observation:** The gateway operates as an edge monitoring sensor node only. The firmware and software contain **no mechanical relays, circuit breaker trip coils, or automated valve actuators**. All platform outputs are advisory decision-support recommendations requiring human authorization.
2. **No Direct Mains Exposure:** Never connect 230V or 415V AC conductors, current transformers, or unconditioned analog voltages directly to the ESP32.
3. **Galvanic Isolation Barrier:** Always use an industrially rated, manufacturer-tested isolated transceiver module (such as Mornsun TD301D485H) with an integrated isolated DC-DC converter. Bare MAX485 or XY-017 breakout boards lack isolated power and do not provide rated protection.
4. **Current Loop Resistor Selection:** Standard 250 Ω shunts produce 5.0V at 20mA, which will permanently destroy the ESP32 ADC. A **150 Ω precision resistor (0.1% tolerance)** must be installed across the loop return to GND.
5. **Level-Shifting for Hall Pulses:** The YF-S201 operates at 5V and outputs 5V logic pulses. A 2-resistor divider (10 kΩ series / 20 kΩ pull-down) steps pulses down to 3.33V before entering GPIO5.

---

## 4. Software & Firmware References

- **Firmware Implementation:** [hardware/esp32/firmware/main.ino](../hardware/esp32/firmware/main.ino)
- **Configuration Template:** [hardware/esp32/firmware/config.h.example](../hardware/esp32/firmware/config.h.example)
- **Device Protocol & Envelope Schema:** [hardware/esp32/device_protocol.md](../hardware/esp32/device_protocol.md)
- **Backend Registry Engine:** [src/registry/device_registry.py](../src/registry/device_registry.py)
- **MQTT Consumer Client:** [src/data/mqtt_consumer.py](../src/data/mqtt_consumer.py)
- **Integration Test Suite:** [tests/test_hardware_integration.py](../tests/test_hardware_integration.py)
