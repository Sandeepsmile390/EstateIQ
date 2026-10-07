# EstateIQ ESP32 Edge Sensor Gateway Firmware

This directory contains the ESP32 firmware and device protocol specifications for connecting physical energy meters and environmental sensors to EstateIQ via MQTT.

## Directory Structure
- `firmware/main.ino`: Arduino/ESP32 C++ firmware source code.
- `device_protocol.md`: Telemetry payload schema and MQTT topic hierarchy.

## Safety Instructions
- **Low-Voltage / Isolated Only**: The ESP32 interface operates strictly at 3.3V/5V DC logic levels.
- **Modbus / CT Metering**: Mains power (230V/415V AC) must be sampled using galvanically isolated Current Transformers (CT) or certified Modbus energy meters.
- **No Direct Mains Exposure**: Never connect mains AC voltage directly to ESP32 GPIO pins.
