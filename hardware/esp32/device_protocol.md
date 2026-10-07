# EstateIQ Hardware & Device Protocol Specification
## MQTT / Modbus Telemetry Payload & Topic Architecture

---

## 1. MQTT TOPIC HIERARCHY

All IoT edge meters and sensor nodes publish to a structured topic tree:

```text
estateiq/{facility_id}/{building_id}/meter/{device_id}/telemetry
estateiq/{facility_id}/{building_id}/meter/{device_id}/status
estateiq/{facility_id}/{building_id}/meter/{device_id}/command
```

### Topic Example
`estateiq/FAC_GEC_CAMPUS/Block_B_Hostel/meter/METER-BLOCK-B-001/telemetry`

---

## 2. TELEMETRY JSON PAYLOAD SCHEMA

```json
{
  "device_id": "METER-BLOCK-B-001",
  "facility_id": "FAC_GEC_CAMPUS",
  "building_id": "Block B Hostel",
  "timestamp": "2026-10-07T10:30:00Z",
  "sequence": 124501,
  "measurements": {
    "voltage_v": 231.2,
    "current_a": 17.4,
    "power_kw": 3.82,
    "energy_kwh": 12452.32,
    "power_factor": 0.94,
    "frequency_hz": 50.01,
    "occupancy": 140,
    "temperature_c": 31.5
  },
  "quality": {
    "sensor_status": "OK",
    "calibrated": true
  },
  "provenance": "REAL_SENSOR"
}
```

---

## 3. DEVICE HEALTH STATES

- **`ONLINE`**: Active transmission received within last 60 seconds.
- **`DEGRADED`**: High sensor noise or power factor $< 0.80$.
- **`STALE`**: No transmission for $> 5$ minutes.
- **`OFFLINE`**: No transmission for $> 15$ minutes.
- **`ERROR`**: Hardware communication fault reported by Modbus transceiver.
