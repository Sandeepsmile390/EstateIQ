# EstateIQ Telemetry Protocol & Payload Specification

## Overview

EstateIQ uses a standardized JSON telemetry envelope (`version 1.0`) for ingesting sensor readings from simulator instances and physical IoT edge nodes.

---

## Telemetry Envelope Schema

```json
{
  "schema_version": "1.0",
  "message_id": "MSG_METER-BLOCK-A-001_1710001234000",
  "simulator_id": "SIM_LAPTOP_A1B2C3",
  "device_id": "METER-BLOCK-A-001",
  "facility_id": "FAC_GEC_CAMPUS",
  "building_id": "Block B Hostel",
  "source_type": "simulated_iot",
  "event_timestamp": "2026-10-09T14:30:00.000000",
  "sent_timestamp": "2026-10-09T14:30:00.150000",
  "sequence_number": 1042,
  "metrics": [
    {
      "metric": "active_power",
      "value": 145.2,
      "unit": "kW",
      "quality": "good"
    },
    {
      "metric": "energy_kwh",
      "value": 36.3,
      "unit": "kWh",
      "quality": "good"
    },
    {
      "metric": "voltage_v",
      "value": 415.0,
      "unit": "V",
      "quality": "good"
    }
  ]
}
```

---

## API Endpoints

- `POST /api/v1/iot/pair` -> Exchange pairing code for scoped auth token.
- `POST /api/v1/iot/simulators/register` -> Register simulator instance metadata.
- `POST /api/v1/iot/simulators/{instance_id}/heartbeat` -> Send operational heartbeat.
- `POST /api/v1/iot/telemetry` -> Ingest single telemetry packet.
- `POST /api/v1/iot/telemetry/batch` -> Ingest batch of buffered telemetry packets.
