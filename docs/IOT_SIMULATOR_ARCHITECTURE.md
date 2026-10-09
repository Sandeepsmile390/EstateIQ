# EstateIQ Standalone IoT Simulator Architecture

## System Overview

The **EstateIQ IoT Simulator** is designed as a standalone, decoupled micro-application that generates physics-grounded telemetry for 12 virtual device profiles across enterprise campus environments.

```
+------------------------------------+           LAN Network (HTTP / REST)           +----------------------------------+
|   Laptop B: IoT Simulator App      | --------------------------------------------> |   Laptop A: EstateIQ Main Server |
|   (Port 8502 Web UI + Engine)      | <-------------------------------------------- |   (Port 8000 FastAPI Backend)    |
+------------------------------------+                                               +----------------------------------+
   |                                                                                    |
   +-- Device Manager (12 Profiles)                                                     +-- Device Registry Engine
   +-- Scenario Engine (14 Presets)                                                     +-- EstateIQ-DIF Engine
   +-- Offline Buffer Queue (Buffer.json)                                                +-- Historical CSV Repository
   +-- LAN Client & Heartbeat Engine                                                    +-- AI Copilot Context Builder
```

---

## Architectural Principles

1. **Isolation & Independence:** The simulator runs entirely in its own directory (`iot-simulator-app/`) with standalone dependencies. It does not import internal modules from EstateIQ via relative paths.
2. **Grounded Physics Coupling:** Telemetry readings follow physically realistic dependencies. For example, HVAC load correlates with total energy consumption, occupancy influences environmental conditions, and water flow increases cumulative water usage.
3. **LAN Resilience & Bounded Queueing:** In the event of network disruption, telemetry samples are buffered locally (`data/buffer.json`) up to a configurable limit (default: 500 records) and retried sequentially upon connection recovery.
4. **Data Provenance Separation:** All generated telemetry packets are explicitly tagged with `source_type: "simulated_iot"`, ensuring historical CSV baselines are never mutated or corrupted.
