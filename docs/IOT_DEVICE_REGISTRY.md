# EstateIQ Device Registry & Discovery Engine

## Overview

The `DeviceRegistryEngine` (`src/registry/device_registry.py`) serves as the central backend authority managing connected IoT simulator instances, virtual devices, heartbeat tracking, and telemetry buffers.

---

## Key Data Models

### 1. SimulatorInstance
- `instance_id`: Unique identifier (e.g. `SIM_LAPTOP_A1B2C3`)
- `name`: Human-readable name (e.g. `Campus-Simulator-01`)
- `facility_id`: Scoped facility ID
- `building_id`: Scoped building ID
- `ip_address`: Discovered LAN IP address
- `status`: `CONNECTED`, `STREAMING`, `STALE`, `OFFLINE`, `REVOKED`
- `last_heartbeat_at`: ISO timestamp of latest heartbeat
- `active_devices_count`: Number of active streaming devices

### 2. VirtualDevice
- `device_id`: Unique device ID (e.g. `METER-BLOCK-A-001`)
- `name`: Display name (e.g. `Block A Energy Submeter`)
- `profile`: Sensor profile type (e.g. `Electricity Meter`, `HVAC Monitor`)
- `status`: `ONLINE`, `STREAMING`, `STALE`, `OFFLINE`, `DISABLED`
- `last_telemetry_sample`: Latest received metric payload

---

## State Transition Lifecycle

```
[ Unregistered ] ---> (Pairing Code) ---> [ Registered ]
                                               |
                                        (Heartbeat Received)
                                               |
                                               v
                                        [ Connected / Streaming ]
                                               |
                                     (Missed > 30s Heartbeat)
                                               |
                                               v
                                          [ Stale ]
                                               |
                                     (Missed > 120s Heartbeat)
                                               |
                                               v
                                         [ Offline ]
```
