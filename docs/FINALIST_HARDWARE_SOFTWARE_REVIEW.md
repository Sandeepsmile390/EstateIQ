# EstateIQ finalist review: hardware, telemetry, and software readiness

**Scope.** This review compares the EstateIQ finalist deck with the current repository and recommends a practical electricity and water sensing kit. The deck is treated as a description of the proposed product; statements in it are not treated as evidence that physical sensing, savings verification, or control has already been implemented.

## 1. What EstateIQ is

EstateIQ is a facility decision-support platform for campuses, hospitals, offices, and estates. It combines facility data, contextual baselines, forecasts, anomaly scoring, explanations, financial impact, what-if scenarios, recommendations, and post-action outcome tracking. The repository already contains:

- A web dashboard and FastAPI API, plus a Streamlit dashboard.
- Energy, water, air, waste, equipment, mobility, and safety data/model modules; a synthetic campus data generator; saved ML models; and an interactive IoT simulator.
- A decision/intelligence layer for contextual baselines, anomaly consensus, confidence, recommendations, impact, and outcome verification.
- An IoT device registry and ingestion APIs, MQTT consumer, ESP32 firmware stub, and device protocol documentation.

The product's strongest finalist story is **observe → contextualize → explain → prioritize → recommend → verify**. Keep physical actuation out of the core claim unless an actual device and safety interlock are demonstrated. A meter proves what was measured; it does not prove which appliance caused the deviation.

## 2. Current project versus the deck

The repository and presentation are not fully aligned yet:

1. **The physical firmware is still a telemetry mock.** `hardware/esp32/firmware/main.ino` publishes fixed voltage, current, power, energy, power factor, occupancy, and temperature values. It does not read Modbus, a CT, a water sensor, or a pressure/level sensor. It also lacks an event timestamp and durable offline queue.
2. **Gateway choice conflicts.** Slide 9 names Raspberry Pi; the implementation and hardware docs name ESP32. Slide 11 shows an Ubuntu local server and Wi-Fi router. These can coexist if responsibilities are stated clearly: ESP32 = sensor/Modbus edge node; Raspberry Pi/Ubuntu = optional local broker/API/database host. For the finalist prototype, an ESP32 and existing laptop/server are sufficient.
3. **The documented hardware protocol and backend envelope differ.** `hardware/esp32/device_protocol.md` uses `measurements` and `timestamp`; `/api/v1/iot/telemetry` expects the registry envelope with `metrics`, `event_timestamp`, `sent_timestamp`, `simulator_id`, and `sequence_number` (some fields receive defaults). The current `mqtt_consumer.py` subscribes to `estateiq/telemetry/#`, while the firmware publishes under `estateiq/{facility}/{building}/meter/{device}/telemetry`.
4. **Real data can be mislabeled as simulated.** The device registry currently records telemetry with `source_type: simulated_iot` and `[SIMULATED IoT]` regardless of the incoming source. This must be fixed before a physical demo so observed and simulated values are visibly distinct.
5. **The deck already includes the right water sensors.** Slide 12 identifies flow, pressure, and tank level. The code simulator also has water flow, cumulative volume, pressure, and tank level controls. Those should become the physical water fields.
6. **Claims need a validation boundary.** Slide 8 shows perfect ROC AUC and F1 values in one chart. The deck's own fine print says evaluations need validation on the current dataset. Present these as synthetic/benchmark results, then state that a campus pilot and time/site-separated holdout are needed before claiming real-world performance. The research-slide citations and financial comparison also need a bibliography and evidence behind them.

## 3. Minimum hardware that can demonstrate useful anomalies

### Electricity

Use **one certified DIN-rail energy meter with RS-485 Modbus RTU**, matched to the demo circuit (single phase for a safe, simple load demo; three phase for the campus feeder story). The meter performs the metrology; the ESP32 reads its registers. Do not build a mains voltage/current measurement circuit from loose CTs for the finalist demo.

Capture, at minimum:

| Field | Unit | Why EstateIQ needs it |
|---|---:|---|
| Cumulative imported active energy, phase and total | kWh | Billing-period/interval consumption and savings verification |
| Active power, phase and total | kW | Immediate load spike and off-hours detection |
| RMS voltage and current, phase by phase | V, A | Supply/load context, phase imbalance, missing phase |
| Power factor, phase and total | ratio | Low-PF/power-factor penalty and load-quality context |
| Frequency | Hz | Grid condition/context |
| Maximum demand or demand-window value | kW or kVA | Peak demand alerts and cost analysis |
| Voltage/current THD and phase unbalance, when supported | %, % | Power-quality anomaly screening |
| Meter status, timestamp, sequence, quality flag | — | Stale data, communication faults, ordering and trust |

An Eastron SDM630 Modbus is one example of a meter family whose Modbus variants report kWh, W, V, A, PF, THD, frequency, maximum demand, and import/export registers. Check the exact variant, current rating, CT/direct connection type, register map, and local availability before purchase; do not assume every SDM630 variant exposes the same fields. [Manufacturer datasheet](https://www.eastroneurope.com/images/uploads/products/cad-drawings/SDM630_series_Datasheet_May22.pdf), [manufacturer register map](https://www.eastroneurope.com/images/uploads/products/protocol/SDM630_MODBUS_Protocol.pdf).

**When is a separate CT needed?** Only when the chosen meter is CT-operated or you need circuit-level submetering. Select CT ratio and meter input together; clamp one insulated conductor per CT. A CT-only reading gives current, not reliable real energy or power factor without synchronized voltage measurement and phase calibration. An integrated Modbus energy meter avoids that complexity for this prototype. For power-quality events such as short sags/swells or waveform distortion, use a meter explicitly rated for those event measurements; slow polling of ordinary registers will miss transients. Analog Devices' metering IC documentation illustrates the distinct voltage/current sampling and metrology required for RMS, active/reactive/apparent power, and PF. [ADE9153A product information](https://www.analog.com/en/products/ade9153a.html).

### Water

Use **an inline flow meter sized for the actual pipe and expected flow**, with a pulse output or Modbus/4–20 mA output. For an operational pilot, use an industrial meter with a documented calibration/accuracy and suitable water-contact/pressure rating. For a tabletop hackathon rig, a Hall-effect turbine flow sensor is inexpensive and easy to count, but label it as a demonstrator and calibrate it with a known-volume bucket; low-cost pulse sensors can vary with pressure, flow, orientation, and wear. [Adafruit pulse sensor description and limitations](https://www.adafruit.com/product/833), [DFRobot flow sensor examples and ratings](https://wiki.dfrobot.com/sen0550).

Measure:

| Field | Unit | Why EstateIQ needs it |
|---|---:|---|
| Instantaneous flow rate | L/min or m³/h | Continuous-flow-at-night, burst, and unusual draw alerts |
| Monotonic cumulative volume totalizer | L or m³ | Consumption totals and interval volume derived from deltas |
| Upstream pressure (optionally downstream too) | bar or kPa | Pressure drop/burst clues and flow-pressure context |
| Tank level | % plus raw distance | Overflow, empty-tank, pump cycling, and supply context |
| Sensor status, pulse count, timestamp, quality | — | No-flow versus disconnected sensor, duplicate/gap detection |

Pressure is a strong second signal for burst/leak diagnosis, but it is not mandatory for a basic high-flow alert. Use a pressure transmitter matched to the pipe range and water chemistry; industrial 4–20 mA or Modbus is easier to transmit robustly than a bare analog sensor. ifm documents water pressure sensors with 4–20 mA / 0–10 V outputs. [ifm India water-pressure sensor overview](https://www.ifm.com/in/en/shared/products/pressure/application/pressure-sensors-for-water-based-media).

For tank level, an overhead ultrasonic sensor is adequate for a clear, static tank surface. Install it away from inlet turbulence, foam, internal obstructions, and the tank wall. Convert measured distance to percent using the commissioned empty/full geometry, and retain the raw distance and sensor validity. The inexpensive DFRobot SEN0208 is a short-range demonstrator; an industrial 4–20 mA/HART level transmitter is more appropriate for a real tank. [DFRobot SEN0208 specs](https://wiki.dfrobot.com/sen0208/), [Pepperl+Fuchs LUC-M20 product data](https://files.pepperl-fuchs.com/webcat/navi/productInfo/pds/272182_eng.pdf?v=20240111020138).

### Edge and communications

For a finalist prototype, use:

- ESP32-S3 development board.
- Isolated RS-485 transceiver for the meter's Modbus RTU bus.
- Pulse input with interrupt/debounce and a level-shift/opto-isolated input as required by the flow meter output.
- Industrial 4–20 mA receiver/isolator (or a Modbus pressure/level transmitter); never connect a 24 V loop directly to an ESP32 ADC.
- Isolated, regulated low-voltage supply, fused enclosed terminals, strain relief, and DIN/bench enclosure.
- Wi-Fi MQTT or HTTPS to the existing EstateIQ server. Add a local queue (LittleFS/SD) and retry with sequence IDs; do not hold the main firmware in an endless Wi-Fi/MQTT reconnect loop.

ESP32-S3 has UART peripherals and 2.4 GHz Wi-Fi, making it suitable as a low-cost Modbus-to-IP edge node. Use an isolated RS-485 interface and a documented Modbus serial implementation. [Espressif ESP32-S3 datasheet](https://documentation.espressif.com/esp32_s3_datasheet_en.pdf), [Modbus serial-line specifications](https://www.modbus.org/modbus-specifications).

**Minimum demo bill of materials:** 1 ESP32-S3; 1 Modbus energy meter; 1 isolated RS-485 interface; 1 pulse-output water flow meter; 1 pressure sensor if showing leak/burst context; 1 tank-level sensor if showing tank/pump behavior; isolated low-voltage supply and enclosure. Temperature/relative humidity and privacy-preserving occupancy counts are useful context features, but are not required to prove the basic electricity/water anomaly path. Use schedules or building booking data for occupancy if available; avoid collecting identifiable camera data.

For any connection to a building panel, 230/415 V supply, CTs, or pressurized plumbing, use a qualified electrician/plumber and appropriately rated meter, protection, enclosure, and fittings. Keep the student-built gateway on isolated low-voltage interfaces. Do not demo an ESP32 relay switching building mains.

## 4. Sampling and anomaly rules

Keep the native sample interval and the analysis interval separate:

| Signal | Read at edge | Send/aggregate for dashboard | Example rules |
|---|---:|---:|---|
| Meter registers | 1–5 s where meter supports it | 15 s or 1 min; roll up to 15 min | kW above contextual baseline; nonzero overnight load; low PF; phase voltage/current imbalance; meter stale |
| Water pulse count / flow | Count continuously; compute over 1–5 s window | 15 s or 1 min; roll up to 15 min/hour | sustained flow during known closed hours; minimum-flow leak; abrupt high flow; flow with low pressure; flow while tank/pump state is inconsistent |
| Pressure | 1–5 s | 15 s or 1 min | sudden pressure loss, pressure outside commissioned range, flow/pressure disagreement |
| Tank level | 5–30 s | 1 min | high-high/low-low, overflow trend, tank level not rising while inlet flow is present |
| Occupancy/schedule/weather | 1–15 min / source cadence | align by event time | contextualize expected demand and reduce false alerts |

Use **interval energy = current cumulative kWh minus prior cumulative kWh**, and **interval water = current totalizer minus prior totalizer**. Reject or flag negative deltas, counter resets/rollovers, duplicate sequence numbers, impossible rates, stale timestamps, and unit changes. Preserve raw meter readings and quality flags; do not silently interpolate a suspected leak or outage into an apparently observed value.

The 15-minute historical ML dataset is useful for forecasts and trend analysis, but it can hide a short leak or electrical event. Keep high-rate raw/current measurements for alerting, and aggregate them into the 15-minute format used by existing models.

## 5. Telemetry contract to implement

Normalize physical values to the repository's device registry envelope. Example:

```json
{
  "schema_version": "1.0",
  "message_id": "meter-01-00001234",
  "simulator_id": "EDGE_CAMPUS_01",
  "device_id": "METER_BLOCK_B_MAIN",
  "facility_id": "FAC_GEC_CAMPUS",
  "building_id": "Block B Hostel",
  "source_type": "real_sensor",
  "event_timestamp": "2026-10-23T10:30:00Z",
  "sent_timestamp": "2026-10-23T10:30:01Z",
  "sequence_number": 1234,
  "metrics": [
    {"metric": "active_power_kw", "value": 4.21, "unit": "kW", "quality": "good"},
    {"metric": "energy_import_kwh", "value": 12452.32, "unit": "kWh", "quality": "good"},
    {"metric": "voltage_l1_v", "value": 231.2, "unit": "V", "quality": "good"},
    {"metric": "current_l1_a", "value": 17.4, "unit": "A", "quality": "good"},
    {"metric": "power_factor_total", "value": 0.94, "unit": "ratio", "quality": "good"},
    {"metric": "water_flow_lpm", "value": 3.2, "unit": "L/min", "quality": "good"},
    {"metric": "water_total_m3", "value": 12.432, "unit": "m3", "quality": "good"},
    {"metric": "water_pressure_bar", "value": 3.1, "unit": "bar", "quality": "good"},
    {"metric": "tank_level_pct", "value": 78.0, "unit": "%", "quality": "good"}
  ]
}
```

Choose and document one canonical name per metric. Existing code alternates between `active_power_kw`/`active_power`, `water_flow_lmin`/`water_flow_lpm`/`flow_rate_lmin`, and `tank_level_pct`/`tank_level_percent`; energy appears as both interval kWh and cumulative kWh. Keep unit and semantics in the schema. Set source provenance at ingestion and carry it through history, API responses, dashboard badges, and model evidence.

## 6. Highest-value software corrections before the final round

### P0 — make the live hardware path truthful and end-to-end

1. Replace hardcoded values in `hardware/esp32/firmware/main.ino` with Modbus reads and real pulse/analog/digital inputs. Include UTC event time, sequence number, source type, sensor health, units, and the meter register map/version.
2. Align the firmware JSON, MQTT topic, `src/data/mqtt_consumer.py`, and `/api/v1/iot/telemetry` schema. There are duplicate `/api/v1/iot/telemetry` and batch route definitions in `api/main.py`; consolidate each route and ensure the intended implementation is registered once.
3. Persist `real_sensor`/`simulated_iot` provenance correctly. Registry currently hardcodes simulated provenance in stored telemetry; demo badges must say `[REAL SENSOR]` only for actual hardware and retain `[SIMULATED IoT]` for the simulator.
4. Add device authentication and facility/device authorization to physical ingestion. The current registry has pairing concepts, but the telemetry ingest path should not accept an arbitrary device identity as proof of authorization. For a local hackathon bench demo, use a scoped device token and a broker/API restricted to the demo LAN; do not expose an unauthenticated MQTT broker publicly.
5. Add reconnect backoff, QoS 1 or acknowledged HTTPS, bounded flash/SD buffering, retry, duplicate idempotency by `message_id`, clock sync, and a visible `last_seen`/stale state. The current firmware's blocking reconnect loop and MQTT default QoS 0 can freeze sampling and lose packets.

### P1 — make anomaly outputs defensible

1. Separate **observed**, **derived**, **predicted**, and **simulated** fields. Example: totalizer delta is derived from observed counters; a baseline is predicted; a what-if saving is simulated.
2. Add a sensor health/data quality gate before anomaly inference: stale, missing, frozen, out-of-range, implausible delta, counter reset, and Modbus exception should create a sensor fault or low-confidence state, not a resource anomaly.
3. Build water rules from flow + time/schedule + totalizer, then add pressure and tank/pump states to distinguish possible leak, burst, overflow, empty tank, and sensor fault. Keep alerts phrased as “possible” until validated.
4. Make attribution claims careful. SHAP explains which model inputs influenced its output; it does not prove an appliance caused excess consumption. Add meter topology (main → building → HVAC/pump submeter) before attributing savings to equipment.
5. Tune and evaluate with a held-out building/time period, real labeled pilot anomalies, precision/recall, false alarms per device-day, detection delay, and missed-event review. Report synthetic data results separately from real pilot results. Avoid a perfect AUC claim without a leakage audit and independent test split.
6. Verify savings against a weather/occupancy-adjusted baseline and a clearly defined pre/post window. Separate “recommended,” “approved,” “action recorded,” and “measured/verified”; do not say an MQTT relay physically changed equipment if it only logged a simulation.

### P2 — sharpen the product and presentation

- Choose one consistent architecture picture: ESP32 sensor node → isolated Modbus/pulse/4–20 mA → MQTT/HTTPS → EstateIQ API; optional Pi/Ubuntu host for local broker/server/offline mode; cloud as optional sync. Explain which device runs which service.
- Replace generic “electricity/water anomaly” with 2 live scenarios: (1) after-hours kW stays above baseline while occupancy is zero; (2) water flow persists overnight or jumps while pressure drops. Show raw reading → baseline → alert → confidence/data quality → recommended inspection → measured resolution.
- Add a hardware proof slide with actual meter/sensors, wiring at block level, measured fields, rates, calibration check, and a provenance badge. Show the serial/Modbus register values beside the dashboard to prove the path is physical.
- Add a limitations/validation slide: current demo sensor count, synthetic vs physical data boundary, installation requirements, pilot plan, and what remains advisory. Cite research papers in a references slide and show dataset, split, sample size, and metric definitions next to reported model results.
- Reword broad comparative/business claims (“first,” “others stop at data,” “low cost”) as evidence-based differentiators unless you have sources and a costed bill of materials.
- The demo deck page 1/4 contains “TEAM”/sector text that may be placeholders or duplicated in extraction; visually verify the final export and ensure the actual team name and claims read cleanly.

## 7. Suggested finalist demo build and story

1. Use a low-risk bench rig: meter a controlled, enclosed demo load through an appropriately rated certified meter; run water through a recirculating bucket/pump and pulse flow meter. Keep all mains-panel work with a qualified electrician.
2. Start the dashboard with simulation clearly labeled, then switch to a separate device whose badge says `[REAL SENSOR]` only after actual readings arrive.
3. Show meter register values and flow pulse counts at the edge, then show the same timestamped values in the API and dashboard. Demonstrate a short outage and buffered replay if implemented.
4. Trigger a repeatable high-load/after-hours scenario and a sustained water flow scenario. Show data-quality checks and threshold/baseline reasoning, not only an AI narrative.
5. Finish with one recommendation and measured recovery. State whether the result is a bench test, simulation, or field-verified savings.

## 8. Reference sources

- Eastron, [SDM630 series data sheet](https://www.eastroneurope.com/images/uploads/products/cad-drawings/SDM630_series_Datasheet_May22.pdf) and [Modbus register map](https://www.eastroneurope.com/images/uploads/products/protocol/SDM630_MODBUS_Protocol.pdf).
- Espressif, [ESP32-S3 datasheet](https://documentation.espressif.com/esp32_s3_datasheet_en.pdf).
- Modbus Organization, [Modbus specifications and serial-line guide](https://www.modbus.org/modbus-specifications).
- Analog Devices, [ADE9153A metering IC product information and datasheet](https://www.analog.com/en/products/ade9153a.html).
- DFRobot, [SEN0550 pulse flow sensor specs](https://wiki.dfrobot.com/sen0550) and [SEN0208 ultrasonic distance specs](https://wiki.dfrobot.com/sen0208/).
- ifm, [water pressure sensor options](https://www.ifm.com/in/en/shared/products/pressure/application/pressure-sensors-for-water-based-media).
- Pepperl+Fuchs, [LUC-M20 ultrasonic level transmitter data sheet](https://files.pepperl-fuchs.com/webcat/navi/productInfo/pds/272182_eng.pdf?v=20240111020138).
