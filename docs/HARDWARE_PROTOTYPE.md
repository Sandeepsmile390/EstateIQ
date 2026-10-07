# EstateIQ Hardware Gateway & Low-Voltage PCB Specification

---

## 1. RECOMMENDED HARDWARE COMPONENTS

1. **Smart Energy Meter**: Multi-function digital energy meter with RS-485 Modbus RTU interface (measures Voltage, Current, Power, Power Factor, Frequency, kWh).
2. **Current Transformer (CT)**: Split-core isolated Current Transformer for non-intrusive current sampling.
3. **Edge Microcontroller / Gateway**: ESP32-S3 or Industrial IoT Gateway with WiFi/Ethernet and hardware RS-485 transceiver (MAX485 / SP3485).
4. **Power Supply**: 5V/2A DC isolated power module.

---

## 2. LOW-VOLTAGE PCB ARCHITECTURE

```text
┌─────────────────┐
│ Smart Meter     │
└────────┬────────┘
         │ RS-485
┌────────▼────────┐
│ Isolated RS485  │ (Optocoupler Isolation)
└────────┬────────┘
         │ UART
┌────────▼────────┐
│ ESP32 Gateway   │ (3.3V DC Logic)
└────────┬────────┘
         │ WiFi / MQTT
┌────────▼────────┐
│ EstateIQ Server │
└─────────────────┘
```

---

## 3. ELECTRICAL SAFETY MANDATE

- **No Mains Switching on PCB**: The gateway PCB operates strictly at **3.3V/5V DC low-voltage logic**.
- **No Direct Mains Exposure**: Never connect 230V/415V AC mains directly to microcontrollers.
- **Galvanic Isolation**: Use optocoupled RS-485 transceivers and isolated DC-DC converters to prevent ground loops.
- **Qualified Installation**: All high-voltage metering installations must be conducted by certified electricians using proper enclosures and fuses.
