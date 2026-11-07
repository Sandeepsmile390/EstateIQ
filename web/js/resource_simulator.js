/**
 * EstateIQ Dedicated Multi-Utility Resource Simulator (web/js/resource_simulator.js)
 *
 * Provides live, physics-based simulation and telemetry generation for:
 *  1. Electricity (Active Power, Cumulative Energy, Voltage, Current, Power Factor, Frequency)
 *  2. Water (Flow Rate, Cumulative Volume, Pressure)
 *  3. Air Quality (CO2, PM2.5, PM10, Temperature, Humidity, EPA AQI)
 *  4. Waste (Fill Level %, Estimated Mass kg, Overflow Risk, Collection Status)
 *
 * Features:
 *  - Independent controls per resource + Global Start/Pause/Stop/Reset
 *  - Physically plausible relationships (P = V * I * PF / 1000 single phase)
 *  - Monotonic totalizers for cumulative kWh and cumulative m³
 *  - Live Chart.js ring-buffer time-series visualization
 *  - Clean timer lifecycle management (pauses when tab inactive/navigated away)
 *  - Automated telemetry ingestion into POST /api/v1/iot/telemetry
 *  - Persistent, prominent [SIMULATED DATA] provenance badges
 */

(function () {
    "use strict";

    // --- Simulator Core State ---
    const simulatorState = {
        globalRunning: true,
        globalIntervalMs: 5000,
        activeTab: "all", // "all", "electricity", "water", "air", "waste"
        timerId: null,
        lastSampleTimestamp: null,
        apiConnected: true,
        apiLastResponseStatus: 200,
        apiConsecutiveErrors: 0,

        // 1. Electricity Meter (SIM-ELEC-01)
        electricity: {
            id: "SIM-ELEC-01",
            name: "Block B Main Power Submeter",
            facilityId: "FAC_GEC_CAMPUS",
            buildingId: "Block B Hostel",
            running: true,
            baselineKw: 55.0,
            scenario: "NORMAL", // NORMAL, PEAK_DEMAND, AFTER_HOURS_WASTE, VOLTAGE_INSTABILITY
            cumulativeKwh: 3420.5,
            latest: {
                activePowerKw: 55.0,
                cumulativeEnergyKwh: 3420.5,
                voltageV: 230.2,
                currentA: 251.5,
                powerFactor: 0.95,
                frequencyHz: 50.01
            },
            history: {
                labels: [],
                power: [],
                voltage: []
            }
        },

        // 2. Water Meter (SIM-WATER-01)
        water: {
            id: "SIM-WATER-01",
            name: "Block B Hydro Main Inflow",
            facilityId: "FAC_GEC_CAMPUS",
            buildingId: "Block B Hostel",
            running: true,
            baselineLmin: 35.0,
            scenario: "NORMAL", // NORMAL, SUSTAINED_LEAK, BURST_FLOW, LOW_FLOW
            cumulativeM3: 842.15,
            latest: {
                flowRateLmin: 35.0,
                cumulativeWaterM3: 842.15,
                pressureBar: 3.4
            },
            history: {
                labels: [],
                flow: [],
                pressure: []
            }
        },

        // 3. Air Quality Station (SIM-AIR-01)
        air: {
            id: "SIM-AIR-01",
            name: "Block B Environmental Quality Hub",
            facilityId: "FAC_GEC_CAMPUS",
            buildingId: "Block B Hostel",
            running: true,
            baselineOccupancy: 120,
            scenario: "NORMAL", // NORMAL, POOR_VENTILATION, PARTICULATE_SPIKE, SENSOR_FAULT
            latest: {
                co2Ppm: 625.0,
                pm25: 16.5,
                pm10: 27.0,
                temperatureC: 23.2,
                humidityPct: 48.5,
                aqi: 45,
                aqiCategory: "Good"
            },
            history: {
                labels: [],
                co2: [],
                pm25: [],
                aqi: []
            }
        },

        // 4. Waste Smart Bin (SIM-WASTE-01)
        waste: {
            id: "SIM-WASTE-01",
            name: "Block B Central Dumpster Bin #1",
            facilityId: "FAC_GEC_CAMPUS",
            buildingId: "Block B Hostel",
            running: true,
            accumulationRatePct: 2.5,
            scenario: "NORMAL", // NORMAL, EVENT_RAPID, BIN_FULL, RESET_EMPTIED
            fillLevelPct: 38.0,
            latest: {
                fillLevelPercent: 38.0,
                estimatedWasteKg: 62.7,
                overflowRisk: "LOW",
                overflowRiskScore: 0.38,
                collectionStatus: "Normal Operation"
            },
            history: {
                labels: [],
                fillLevel: [],
                wasteKg: []
            }
        }
    };

    // Chart.js Chart Instances
    const chartInstances = {
        electricity: null,
        water: null,
        air: null,
        waste: null
    };

    const MAX_HISTORY_POINTS = 25;

    // --- Helper Functions ---
    function clamp(val, min, max) {
        return Math.max(min, Math.min(max, val));
    }

    function gaussianRandom(mean = 0, stdev = 1) {
        let u = 1 - Math.random();
        let v = Math.random();
        let z = Math.sqrt(-2.0 * Math.log(u)) * Math.cos(2.0 * Math.PI * v);
        return z * stdev + mean;
    }

    function formatTime(dateObj = new Date()) {
        return dateObj.toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
    }

    function calculateEPA_AQI(pm25) {
        // EPA PM2.5 Breakpoints
        const breakpoints = [
            { cLow: 0.0, cHigh: 12.0, iLow: 0, iHigh: 50, cat: "Good" },
            { cLow: 12.1, cHigh: 35.4, iLow: 51, iHigh: 100, cat: "Moderate" },
            { cLow: 35.5, cHigh: 55.4, iLow: 101, iHigh: 150, cat: "Sensitive" },
            { cLow: 55.5, cHigh: 150.4, iLow: 151, iHigh: 200, cat: "Unhealthy" },
            { cLow: 150.5, cHigh: 250.4, iLow: 201, iHigh: 300, cat: "Very Unhealthy" },
            { cLow: 250.5, cHigh: 500.0, iLow: 301, iHigh: 500, cat: "Hazardous" }
        ];

        for (let bp of breakpoints) {
            if (pm25 >= bp.cLow && pm25 <= bp.cHigh) {
                let aqi = Math.round(((bp.iHigh - bp.iLow) / (bp.cHigh - bp.cLow)) * (pm25 - bp.cLow) + bp.iLow);
                return { aqi, category: bp.cat };
            }
        }
        if (pm25 > 500.0) return { aqi: 500, category: "Hazardous" };
        return { aqi: 25, category: "Good" };
    }

    // --- Physics-Based Telemetry Computation ---

    function tickElectricity(dtSec) {
        const e = simulatorState.electricity;
        if (!e.running || !simulatorState.globalRunning) return;

        let base = e.baselineKw;
        let pKw = base;
        let vVolt = 230.0;
        let pf = 0.95;
        let freq = 50.0;

        switch (e.scenario) {
            case "NORMAL":
                pKw = base * (1.0 + gaussianRandom(0, 0.025));
                vVolt = 230.0 + gaussianRandom(0, 1.2);
                pf = clamp(0.95 + gaussianRandom(0, 0.01), 0.88, 0.98);
                freq = 50.0 + gaussianRandom(0, 0.03);
                break;
            case "PEAK_DEMAND":
                // Chiller surge, concurrent elevator & lighting load
                pKw = base * (1.85 + gaussianRandom(0, 0.06));
                vVolt = 224.0 + gaussianRandom(0, 2.0); // slight voltage drop
                pf = clamp(0.91 + gaussianRandom(0, 0.015), 0.82, 0.94);
                freq = 49.88 + gaussianRandom(0, 0.05);
                break;
            case "AFTER_HOURS_WASTE":
                // Night waste: unoccupied baseline remains high
                pKw = base * (1.35 + gaussianRandom(0, 0.03));
                vVolt = 232.0 + gaussianRandom(0, 1.0);
                pf = clamp(0.89 + gaussianRandom(0, 0.015), 0.80, 0.93);
                freq = 50.02 + gaussianRandom(0, 0.03);
                break;
            case "VOLTAGE_INSTABILITY":
                // Voltage sag/swell and poor harmonic power factor
                pKw = base * (1.10 + gaussianRandom(0, 0.12));
                vVolt = clamp(230.0 + gaussianRandom(0, 14.0), 205.0, 255.0);
                pf = clamp(0.76 + gaussianRandom(0, 0.05), 0.62, 0.85);
                freq = clamp(50.0 + gaussianRandom(0, 0.35), 49.1, 50.9);
                break;
        }

        pKw = clamp(Math.round(pKw * 100) / 100, 1.0, 500.0);
        vVolt = clamp(Math.round(vVolt * 10) / 10, 180.0, 280.0);
        pf = clamp(Math.round(pf * 100) / 100, 0.50, 0.99);
        freq = clamp(Math.round(freq * 100) / 100, 48.0, 52.0);

        // Consistent electrical relationship: Current I = (1000 * P_kw) / (V * PF) for single phase
        let currentA = Math.round(((1000.0 * pKw) / (vVolt * pf)) * 10) / 10;

        // Monotonic cumulative energy: dKwh = P * dt / 3600
        let deltaKwh = (pKw * dtSec) / 3600.0;
        e.cumulativeKwh = Math.round((e.cumulativeKwh + deltaKwh) * 1000) / 1000;

        e.latest = {
            activePowerKw: pKw,
            cumulativeEnergyKwh: e.cumulativeKwh,
            voltageV: vVolt,
            currentA: currentA,
            powerFactor: pf,
            frequencyHz: freq
        };
    }

    function tickWater(dtSec) {
        const w = simulatorState.water;
        if (!w.running || !simulatorState.globalRunning) return;

        let base = w.baselineLmin;
        let flow = base;
        let pressure = 3.4;

        switch (w.scenario) {
            case "NORMAL":
                flow = base * clamp(1.0 + gaussianRandom(0, 0.08), 0.6, 1.4);
                pressure = clamp(3.4 + gaussianRandom(0, 0.12), 3.0, 3.8);
                break;
            case "SUSTAINED_LEAK":
                // Baseline leak: floor never drops below baseline + 25 L/min
                flow = base + 26.5 + gaussianRandom(0, 2.0);
                pressure = clamp(2.8 + gaussianRandom(0, 0.1), 2.4, 3.1);
                break;
            case "BURST_FLOW":
                // Catastrophic fracture: massive flow spike and severe pressure drop
                flow = base * clamp(4.2 + gaussianRandom(0, 0.3), 3.5, 5.2);
                pressure = clamp(1.4 + gaussianRandom(0, 0.2), 0.9, 1.9);
                break;
            case "LOW_FLOW":
                // Night shutoff or zero-consumption
                flow = clamp(0.5 + gaussianRandom(0, 0.3), 0.0, 1.5);
                pressure = clamp(1.8 + gaussianRandom(0, 0.2), 1.2, 2.4);
                break;
        }

        flow = clamp(Math.round(flow * 10) / 10, 0.0, 500.0);
        pressure = clamp(Math.round(pressure * 100) / 100, 0.2, 8.0);

        // Monotonic cumulative water in cubic meters: 1 m3 = 1000 Liters
        let deltaM3 = ((flow * (dtSec / 60.0)) / 1000.0);
        w.cumulativeM3 = Math.round((w.cumulativeM3 + deltaM3) * 10000) / 10000;

        w.latest = {
            flowRateLmin: flow,
            cumulativeWaterM3: w.cumulativeM3,
            pressureBar: pressure
        };
    }

    function tickAirQuality(dtSec) {
        const a = simulatorState.air;
        if (!a.running || !simulatorState.globalRunning) return;

        let occ = a.baselineOccupancy;
        let co2 = 410.0 + (occ * 1.8);
        let pm25 = 15.0;
        let pm10 = 24.0;
        let temp = 23.0;
        let hum = 50.0;

        switch (a.scenario) {
            case "NORMAL":
                co2 = clamp(410.0 + (occ * 1.8) + gaussianRandom(0, 15.0), 400.0, 1100.0);
                pm25 = clamp(15.0 + gaussianRandom(0, 2.5), 5.0, 28.0);
                pm10 = clamp(pm25 * 1.6 + gaussianRandom(0, 3.0), 10.0, 45.0);
                temp = clamp(23.0 + gaussianRandom(0, 0.3), 21.0, 25.0);
                hum = clamp(50.0 + gaussianRandom(0, 1.5), 42.0, 58.0);
                break;
            case "POOR_VENTILATION":
                // Fresh air makeup damper stuck, CO2 builds up rapidly
                co2 = clamp(1450.0 + (occ * 3.2) + gaussianRandom(0, 40.0), 1200.0, 3200.0);
                pm25 = clamp(36.0 + gaussianRandom(0, 4.0), 25.0, 55.0);
                pm10 = clamp(pm25 * 1.5 + gaussianRandom(0, 5.0), 38.0, 85.0);
                temp = clamp(25.6 + gaussianRandom(0, 0.4), 24.0, 27.5);
                hum = clamp(68.0 + gaussianRandom(0, 2.0), 60.0, 78.0);
                break;
            case "PARTICULATE_SPIKE":
                // External smoke/dust intrusion: massive PM spike
                co2 = clamp(620.0 + (occ * 1.5) + gaussianRandom(0, 20.0), 500.0, 1200.0);
                pm25 = clamp(125.0 + gaussianRandom(0, 20.0), 80.0, 220.0);
                pm10 = clamp(pm25 * 1.65 + gaussianRandom(0, 25.0), 130.0, 350.0);
                temp = clamp(24.2 + gaussianRandom(0, 0.5), 22.0, 26.5);
                hum = clamp(52.0 + gaussianRandom(0, 2.0), 45.0, 60.0);
                break;
            case "SENSOR_FAULT":
                // Erratic, drifting values
                co2 = clamp(1800.0 + gaussianRandom(0, 600.0), 300.0, 5000.0);
                pm25 = clamp(85.0 + gaussianRandom(0, 40.0), 0.0, 300.0);
                pm10 = clamp(140.0 + gaussianRandom(0, 60.0), 0.0, 450.0);
                temp = clamp(30.0 + gaussianRandom(0, 3.0), 15.0, 42.0);
                hum = clamp(35.0 + gaussianRandom(0, 12.0), 10.0, 95.0);
                break;
        }

        co2 = Math.round(co2);
        pm25 = Math.round(pm25 * 10) / 10;
        pm10 = Math.round(pm10 * 10) / 10;
        temp = Math.round(temp * 10) / 10;
        hum = Math.round(hum * 10) / 10;

        let aqiInfo = calculateEPA_AQI(pm25);

        a.latest = {
            co2Ppm: co2,
            pm25: pm25,
            pm10: pm10,
            temperatureC: temp,
            humidityPct: hum,
            aqi: aqiInfo.aqi,
            aqiCategory: aqiInfo.category
        };
    }

    function tickWaste(dtSec) {
        const wst = simulatorState.waste;
        if (!wst.running || !simulatorState.globalRunning) return;

        let rate = wst.accumulationRatePct;
        let currentFill = wst.fillLevelPct;

        switch (wst.scenario) {
            case "NORMAL":
                currentFill += (rate * (dtSec / 5.0)) + gaussianRandom(0, 0.2);
                break;
            case "EVENT_RAPID":
                // Campus event: banquet, move-in, festival
                currentFill += ((rate * 3.5) * (dtSec / 5.0)) + gaussianRandom(0, 0.5);
                break;
            case "BIN_FULL":
                // Pinned at capacity
                currentFill = clamp(94.0 + gaussianRandom(0, 1.5), 90.0, 99.5);
                break;
            case "RESET_EMPTIED":
                // Emptied by sanitation staff
                currentFill = clamp(4.0 + gaussianRandom(0, 0.5), 1.0, 8.0);
                // Return to normal scenario after explicit reset
                wst.scenario = "NORMAL";
                const scenSelect = document.getElementById("resSimWasteScenario");
                if (scenSelect) scenSelect.value = "NORMAL";
                break;
        }

        currentFill = clamp(Math.round(currentFill * 10) / 10, 0.0, 100.0);
        wst.fillLevelPct = currentFill;

        // Commercial 1100-liter bin with average uncompacted density ~0.15 kg/L => max ~165 kg
        let estKg = Math.round((currentFill / 100.0) * 165.0 * (0.95 + gaussianRandom(0, 0.03)) * 10) / 10;
        estKg = clamp(estKg, 1.0, 185.0);

        let risk = "LOW";
        let score = currentFill / 100.0;
        let colStatus = "Normal Operation";

        if (currentFill < 50.0) {
            risk = "LOW";
            colStatus = "Normal Operation";
        } else if (currentFill < 75.0) {
            risk = "MEDIUM";
            colStatus = "Approaching Capacity";
        } else if (currentFill < 90.0) {
            risk = "HIGH";
            colStatus = "Collection Recommended";
        } else {
            risk = "CRITICAL";
            colStatus = "Immediate Dispatch Required";
        }

        wst.latest = {
            fillLevelPercent: currentFill,
            estimatedWasteKg: estKg,
            overflowRisk: risk,
            overflowRiskScore: Math.round(score * 100) / 100,
            collectionStatus: colStatus
        };
    }

    // --- Master Simulation Step ---
    function stepSimulation() {
        const dtSec = simulatorState.globalIntervalMs / 1000.0;
        const now = new Date();
        const timeLabel = formatTime(now);
        simulatorState.lastSampleTimestamp = now.toISOString();

        // 1. Tick each utility physics model
        tickElectricity(dtSec);
        tickWater(dtSec);
        tickAirQuality(dtSec);
        tickWaste(dtSec);

        // 2. Append to history ring buffers
        appendHistory(timeLabel);

        // 3. Update DOM metrics
        updateMetricsDOM();

        // 4. Update Charts
        updateCharts();

        // 5. Ingest Telemetry to Backend
        sendTelemetryToBackend();
    }

    function appendHistory(timeLabel) {
        // Electricity
        const e = simulatorState.electricity;
        e.history.labels.push(timeLabel);
        e.history.power.push(e.latest.activePowerKw);
        e.history.voltage.push(e.latest.voltageV);
        if (e.history.labels.length > MAX_HISTORY_POINTS) {
            e.history.labels.shift();
            e.history.power.shift();
            e.history.voltage.shift();
        }

        // Water
        const w = simulatorState.water;
        w.history.labels.push(timeLabel);
        w.history.flow.push(w.latest.flowRateLmin);
        w.history.pressure.push(w.latest.pressureBar);
        if (w.history.labels.length > MAX_HISTORY_POINTS) {
            w.history.labels.shift();
            w.history.flow.shift();
            w.history.pressure.shift();
        }

        // Air
        const a = simulatorState.air;
        a.history.labels.push(timeLabel);
        a.history.co2.push(a.latest.co2Ppm);
        a.history.pm25.push(a.latest.pm25);
        a.history.aqi.push(a.latest.aqi);
        if (a.history.labels.length > MAX_HISTORY_POINTS) {
            a.history.labels.shift();
            a.history.co2.shift();
            a.history.pm25.shift();
            a.history.aqi.shift();
        }

        // Waste
        const wst = simulatorState.waste;
        wst.history.labels.push(timeLabel);
        wst.history.fillLevel.push(wst.latest.fillLevelPercent);
        wst.history.wasteKg.push(wst.latest.estimatedWasteKg);
        if (wst.history.labels.length > MAX_HISTORY_POINTS) {
            wst.history.labels.shift();
            wst.history.fillLevel.shift();
            wst.history.wasteKg.shift();
        }
    }

    // --- DOM Update Functions ---
    function updateMetricsDOM() {
        const now = new Date();
        const timeStr = formatTime(now);

        // Header time & state badge
        const timeEl = document.getElementById("resSimLastSampleTime");
        if (timeEl) timeEl.textContent = timeStr;

        const activeCount = [
            simulatorState.electricity.running,
            simulatorState.water.running,
            simulatorState.air.running,
            simulatorState.waste.running
        ].filter(Boolean).length;

        const globalStateBadge = document.getElementById("resSimGlobalStateBadge");
        if (globalStateBadge) {
            if (!simulatorState.globalRunning) {
                globalStateBadge.textContent = "SIMULATOR PAUSED";
                globalStateBadge.className = "badge-amber";
            } else if (activeCount === 0) {
                globalStateBadge.textContent = "ALL STOPPED";
                globalStateBadge.className = "badge-red";
            } else {
                globalStateBadge.textContent = `${activeCount}/4 UTILITIES ACTIVE`;
                globalStateBadge.className = "badge-mint";
            }
        }

        // 1. Electricity DOM
        const e = simulatorState.electricity;
        setText("resSimElecPower", `${e.latest.activePowerKw.toFixed(1)} kW`);
        setText("resSimElecKwh", `${e.latest.cumulativeEnergyKwh.toFixed(2)} kWh`);
        setText("resSimElecVolt", `${e.latest.voltageV.toFixed(1)} V`);
        setText("resSimElecCurrent", `${e.latest.currentA.toFixed(1)} A`);
        setText("resSimElecPf", `${e.latest.powerFactor.toFixed(2)}`);
        setText("resSimElecFreq", `${e.latest.frequencyHz.toFixed(2)} Hz`);
        updateResourceStatusBadge("resSimElecStatus", e.running);

        // 2. Water DOM
        const w = simulatorState.water;
        setText("resSimWaterFlow", `${w.latest.flowRateLmin.toFixed(1)} L/min`);
        setText("resSimWaterM3", `${w.latest.cumulativeWaterM3.toFixed(3)} m³`);
        setText("resSimWaterPressure", `${w.latest.pressureBar.toFixed(2)} bar`);
        updateResourceStatusBadge("resSimWaterStatus", w.running);

        // 3. Air Quality DOM
        const a = simulatorState.air;
        setText("resSimAirCo2", `${a.latest.co2Ppm} ppm`);
        setText("resSimAirPm25", `${a.latest.pm25.toFixed(1)} µg/m³`);
        setText("resSimAirPm10", `${a.latest.pm10.toFixed(1)} µg/m³`);
        setText("resSimAirTemp", `${a.latest.temperatureC.toFixed(1)} °C`);
        setText("resSimAirHum", `${a.latest.humidityPct.toFixed(1)} %`);
        setText("resSimAirAqi", `${a.latest.aqi} (${a.latest.aqiCategory})`);
        updateResourceStatusBadge("resSimAirStatus", a.running);

        // AQI color styling
        const aqiEl = document.getElementById("resSimAirAqi");
        if (aqiEl) {
            if (a.latest.aqi <= 50) aqiEl.style.color = "#00D09C";
            else if (a.latest.aqi <= 100) aqiEl.style.color = "#F5C577";
            else if (a.latest.aqi <= 150) aqiEl.style.color = "#F97316";
            else aqiEl.style.color = "#EF4444";
        }

        // 4. Waste DOM
        const wst = simulatorState.waste;
        setText("resSimWasteFill", `${wst.latest.fillLevelPercent.toFixed(1)} %`);
        setText("resSimWasteKg", `${wst.latest.estimatedWasteKg.toFixed(1)} kg`);
        setText("resSimWasteRisk", `${wst.latest.overflowRisk}`);
        setText("resSimWasteStatusTxt", `${wst.latest.collectionStatus}`);
        updateResourceStatusBadge("resSimWasteStatus", wst.running);

        // Waste Fill Visual Bar
        const fillBar = document.getElementById("resSimWasteFillBar");
        if (fillBar) {
            fillBar.style.width = `${wst.latest.fillLevelPercent}%`;
            if (wst.latest.fillLevelPercent >= 90) {
                fillBar.style.background = "#EF4444";
            } else if (wst.latest.fillLevelPercent >= 75) {
                fillBar.style.background = "#F97316";
            } else if (wst.latest.fillLevelPercent >= 50) {
                fillBar.style.background = "#F5C577";
            } else {
                fillBar.style.background = "#00D09C";
            }
        }

        // Overflow Risk Badge color
        const riskEl = document.getElementById("resSimWasteRisk");
        if (riskEl) {
            if (wst.latest.overflowRisk === "LOW") riskEl.style.color = "#00D09C";
            else if (wst.latest.overflowRisk === "MEDIUM") riskEl.style.color = "#F5C577";
            else if (wst.latest.overflowRisk === "HIGH") riskEl.style.color = "#F97316";
            else riskEl.style.color = "#EF4444";
        }
    }

    function setText(id, text) {
        const el = document.getElementById(id);
        if (el) el.textContent = text;
    }

    function updateResourceStatusBadge(elemId, isRunning) {
        const el = document.getElementById(elemId);
        if (!el) return;
        if (!simulatorState.globalRunning || !isRunning) {
            el.textContent = "PAUSED";
            el.className = "badge-amber";
            el.style.background = "rgba(245, 197, 119, 0.15)";
            el.style.color = "#F5C577";
            el.style.border = "1px solid rgba(245, 197, 119, 0.4)";
        } else {
            el.textContent = "ACTIVE";
            el.className = "badge-mint";
            el.style.background = "rgba(0, 208, 156, 0.15)";
            el.style.color = "#00D09C";
            el.style.border = "1px solid rgba(0, 208, 156, 0.4)";
        }
    }

    // --- Chart.js Initialization & Updates ---
    function initCharts() {
        if (typeof Chart === "undefined") {
            console.warn("Chart.js is not loaded yet. Retrying in 250ms...");
            setTimeout(initCharts, 250);
            return;
        }

        const commonOptions = {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 350 },
            plugins: {
                legend: {
                    display: true,
                    labels: { color: "#A3C9BE", font: { size: 11, family: "Inter" } }
                },
                tooltip: {
                    backgroundColor: "rgba(10, 46, 38, 0.95)",
                    borderColor: "rgba(0, 208, 156, 0.4)",
                    borderWidth: 1,
                    titleColor: "#FFF",
                    bodyColor: "#A3C9BE"
                }
            },
            scales: {
                x: {
                    ticks: { color: "#6A8C84", font: { size: 10 }, maxRotation: 0, autoSkip: true, maxTicksLimit: 6 },
                    grid: { color: "rgba(255, 255, 255, 0.05)" }
                },
                y: {
                    ticks: { color: "#A3C9BE", font: { size: 10 } },
                    grid: { color: "rgba(255, 255, 255, 0.05)" }
                }
            }
        };

        // 1. Electricity Chart
        const ctxElec = document.getElementById("canvasResSimElec");
        if (ctxElec && !chartInstances.electricity) {
            chartInstances.electricity = new Chart(ctxElec, {
                type: "line",
                data: {
                    labels: simulatorState.electricity.history.labels,
                    datasets: [
                        {
                            label: "Active Power (kW)",
                            data: simulatorState.electricity.history.power,
                            borderColor: "#00D09C",
                            backgroundColor: "rgba(0, 208, 156, 0.1)",
                            borderWidth: 2,
                            tension: 0.35,
                            fill: true,
                            pointRadius: 2,
                            yAxisID: "y"
                        }
                    ]
                },
                options: commonOptions
            });
        }

        // 2. Water Chart
        const ctxWater = document.getElementById("canvasResSimWater");
        if (ctxWater && !chartInstances.water) {
            chartInstances.water = new Chart(ctxWater, {
                type: "line",
                data: {
                    labels: simulatorState.water.history.labels,
                    datasets: [
                        {
                            label: "Flow Rate (L/min)",
                            data: simulatorState.water.history.flow,
                            borderColor: "#38BDF8",
                            backgroundColor: "rgba(56, 189, 248, 0.1)",
                            borderWidth: 2,
                            tension: 0.35,
                            fill: true,
                            pointRadius: 2,
                            yAxisID: "y"
                        },
                        {
                            label: "Pressure (bar)",
                            data: simulatorState.water.history.pressure,
                            borderColor: "#F5C577",
                            borderWidth: 1.5,
                            tension: 0.3,
                            borderDash: [4, 4],
                            pointRadius: 1,
                            yAxisID: "y1"
                        }
                    ]
                },
                options: {
                    ...commonOptions,
                    scales: {
                        ...commonOptions.scales,
                        y1: {
                            position: "right",
                            ticks: { color: "#F5C577", font: { size: 10 } },
                            grid: { drawOnChartArea: false }
                        }
                    }
                }
            });
        }

        // 3. Air Quality Chart
        const ctxAir = document.getElementById("canvasResSimAir");
        if (ctxAir && !chartInstances.air) {
            chartInstances.air = new Chart(ctxAir, {
                type: "line",
                data: {
                    labels: simulatorState.air.history.labels,
                    datasets: [
                        {
                            label: "CO2 (ppm)",
                            data: simulatorState.air.history.co2,
                            borderColor: "#A78BFA",
                            backgroundColor: "rgba(167, 139, 250, 0.1)",
                            borderWidth: 2,
                            tension: 0.35,
                            fill: true,
                            pointRadius: 2,
                            yAxisID: "y"
                        },
                        {
                            label: "PM2.5 (µg/m³)",
                            data: simulatorState.air.history.pm25,
                            borderColor: "#F97316",
                            borderWidth: 1.5,
                            tension: 0.35,
                            pointRadius: 2,
                            yAxisID: "y1"
                        }
                    ]
                },
                options: {
                    ...commonOptions,
                    scales: {
                        ...commonOptions.scales,
                        y1: {
                            position: "right",
                            ticks: { color: "#F97316", font: { size: 10 } },
                            grid: { drawOnChartArea: false }
                        }
                    }
                }
            });
        }

        // 4. Waste Chart
        const ctxWaste = document.getElementById("canvasResSimWaste");
        if (ctxWaste && !chartInstances.waste) {
            chartInstances.waste = new Chart(ctxWaste, {
                type: "line",
                data: {
                    labels: simulatorState.waste.history.labels,
                    datasets: [
                        {
                            label: "Fill Level (%)",
                            data: simulatorState.waste.history.fillLevel,
                            borderColor: "#34D399",
                            backgroundColor: "rgba(52, 211, 153, 0.1)",
                            borderWidth: 2,
                            tension: 0.3,
                            fill: true,
                            pointRadius: 2,
                            yAxisID: "y"
                        },
                        {
                            label: "Est. Mass (kg)",
                            data: simulatorState.waste.history.wasteKg,
                            borderColor: "#FBBF24",
                            borderWidth: 1.5,
                            tension: 0.3,
                            borderDash: [3, 3],
                            pointRadius: 1,
                            yAxisID: "y1"
                        }
                    ]
                },
                options: {
                    ...commonOptions,
                    scales: {
                        ...commonOptions.scales,
                        y: {
                            ...commonOptions.scales.y,
                            min: 0,
                            max: 100
                        },
                        y1: {
                            position: "right",
                            ticks: { color: "#FBBF24", font: { size: 10 } },
                            grid: { drawOnChartArea: false }
                        }
                    }
                }
            });
        }
    }

    function updateCharts() {
        if (chartInstances.electricity) {
            chartInstances.electricity.data.labels = simulatorState.electricity.history.labels;
            chartInstances.electricity.data.datasets[0].data = simulatorState.electricity.history.power;
            chartInstances.electricity.update("none");
        }
        if (chartInstances.water) {
            chartInstances.water.data.labels = simulatorState.water.history.labels;
            chartInstances.water.data.datasets[0].data = simulatorState.water.history.flow;
            chartInstances.water.data.datasets[1].data = simulatorState.water.history.pressure;
            chartInstances.water.update("none");
        }
        if (chartInstances.air) {
            chartInstances.air.data.labels = simulatorState.air.history.labels;
            chartInstances.air.data.datasets[0].data = simulatorState.air.history.co2;
            chartInstances.air.data.datasets[1].data = simulatorState.air.history.pm25;
            chartInstances.air.update("none");
        }
        if (chartInstances.waste) {
            chartInstances.waste.data.labels = simulatorState.waste.history.labels;
            chartInstances.waste.data.datasets[0].data = simulatorState.waste.history.fillLevel;
            chartInstances.waste.data.datasets[1].data = simulatorState.waste.history.wasteKg;
            chartInstances.waste.update("none");
        }
    }

    // --- Backend Telemetry Ingestion ---
    async function sendTelemetryToBackend() {
        if (!simulatorState.globalRunning) return;

        const nowIso = new Date().toISOString();
        const packets = [];

        // 1. Electricity Packet
        if (simulatorState.electricity.running) {
            const e = simulatorState.electricity;
            packets.push({
                message_id: `MSG_SIM_ELEC_${Date.now()}_${Math.floor(Math.random() * 1000)}`,
                simulator_id: "SIM_RESOURCE_DEMO_01",
                device_id: e.id,
                device_name: e.name,
                facility_id: e.facilityId,
                building_id: e.buildingId,
                source_type: "simulated_iot",
                is_verified_hardware: false,
                data_source_badge: "[SIMULATED IoT]",
                event_timestamp: nowIso,
                measurements: {
                    active_power_kw: e.latest.activePowerKw,
                    cumulative_energy_kwh: e.latest.cumulativeEnergyKwh,
                    voltage_v: e.latest.voltageV,
                    current_a: e.latest.currentA,
                    power_factor: e.latest.powerFactor,
                    frequency_hz: e.latest.frequencyHz
                }
            });
        }

        // 2. Water Packet
        if (simulatorState.water.running) {
            const w = simulatorState.water;
            packets.push({
                message_id: `MSG_SIM_WATER_${Date.now()}_${Math.floor(Math.random() * 1000)}`,
                simulator_id: "SIM_RESOURCE_DEMO_01",
                device_id: w.id,
                device_name: w.name,
                facility_id: w.facilityId,
                building_id: w.buildingId,
                source_type: "simulated_iot",
                is_verified_hardware: false,
                data_source_badge: "[SIMULATED IoT]",
                event_timestamp: nowIso,
                measurements: {
                    water_flow_lmin: w.latest.flowRateLmin,
                    cumulative_water_m3: w.latest.cumulativeWaterM3,
                    water_pressure_bar: w.latest.pressureBar
                }
            });
        }

        // 3. Air Quality Packet
        if (simulatorState.air.running) {
            const a = simulatorState.air;
            packets.push({
                message_id: `MSG_SIM_AIR_${Date.now()}_${Math.floor(Math.random() * 1000)}`,
                simulator_id: "SIM_RESOURCE_DEMO_01",
                device_id: a.id,
                device_name: a.name,
                facility_id: a.facilityId,
                building_id: a.buildingId,
                source_type: "simulated_iot",
                is_verified_hardware: false,
                data_source_badge: "[SIMULATED IoT]",
                event_timestamp: nowIso,
                measurements: {
                    co2_ppm: a.latest.co2Ppm,
                    pm25: a.latest.pm25,
                    pm10: a.latest.pm10,
                    temperature_c: a.latest.temperatureC,
                    humidity_pct: a.latest.humidityPct,
                    air_quality_aqi: a.latest.aqi
                }
            });
        }

        // 4. Waste Packet
        if (simulatorState.waste.running) {
            const wst = simulatorState.waste;
            packets.push({
                message_id: `MSG_SIM_WASTE_${Date.now()}_${Math.floor(Math.random() * 1000)}`,
                simulator_id: "SIM_RESOURCE_DEMO_01",
                device_id: wst.id,
                device_name: wst.name,
                facility_id: wst.facilityId,
                building_id: wst.buildingId,
                source_type: "simulated_iot",
                is_verified_hardware: false,
                data_source_badge: "[SIMULATED IoT]",
                event_timestamp: nowIso,
                measurements: {
                    fill_level_percent: wst.latest.fillLevelPercent,
                    estimated_waste_kg: wst.latest.estimatedWasteKg
                }
            });
        }

        if (packets.length === 0) return;

        // Post each packet to /api/v1/iot/telemetry
        for (const pkt of packets) {
            try {
                const resp = await fetch("/api/v1/iot/telemetry", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(pkt)
                });

                if (resp.ok) {
                    simulatorState.apiConnected = true;
                    simulatorState.apiConsecutiveErrors = 0;
                    simulatorState.apiLastResponseStatus = resp.status;
                } else {
                    simulatorState.apiConsecutiveErrors++;
                    simulatorState.apiLastResponseStatus = resp.status;
                }
            } catch (err) {
                // If API is unreachable (e.g. running in offline/static preview)
                simulatorState.apiConsecutiveErrors++;
                simulatorState.apiConnected = false;
            }
        }

        updateApiStatusBadge();
    }

    function updateApiStatusBadge() {
        const badge = document.getElementById("resSimApiBadge");
        const text = document.getElementById("resSimApiText");
        if (!badge || !text) return;

        if (simulatorState.apiConnected && simulatorState.apiConsecutiveErrors === 0) {
            badge.style.background = "rgba(0, 208, 156, 0.15)";
            badge.style.border = "1px solid #00D09C";
            badge.style.color = "#00D09C";
            text.textContent = "INGESTION: /api/v1/iot/telemetry (ACTIVE 200 OK)";
        } else {
            badge.style.background = "rgba(245, 197, 119, 0.15)";
            badge.style.border = "1px solid #F5C577";
            badge.style.color = "#F5C577";
            text.textContent = "LOCAL SIMULATION (API OFFLINE / STANDALONE)";
        }
    }

    // --- Lifecycle & Timer Management ---
    function startTimer() {
        stopTimer();
        // Run first step immediately
        stepSimulation();
        simulatorState.timerId = setInterval(stepSimulation, simulatorState.globalIntervalMs);
    }

    function stopTimer() {
        if (simulatorState.timerId) {
            clearInterval(simulatorState.timerId);
            simulatorState.timerId = null;
        }
    }

    function pauseAll() {
        simulatorState.globalRunning = false;
        updateMetricsDOM();
    }

    function resumeAll() {
        simulatorState.globalRunning = true;
        updateMetricsDOM();
    }

    function stopAll() {
        simulatorState.globalRunning = false;
        simulatorState.electricity.running = false;
        simulatorState.water.running = false;
        simulatorState.air.running = false;
        simulatorState.waste.running = false;
        updateMetricsDOM();
    }

    function startAll() {
        simulatorState.globalRunning = true;
        simulatorState.electricity.running = true;
        simulatorState.water.running = true;
        simulatorState.air.running = true;
        simulatorState.waste.running = true;
        updateMetricsDOM();
        if (!simulatorState.timerId) startTimer();
    }

    function resetToDefaults() {
        // Electricity
        simulatorState.electricity.baselineKw = 55.0;
        simulatorState.electricity.scenario = "NORMAL";
        simulatorState.electricity.cumulativeKwh = 3420.5;
        simulatorState.electricity.running = true;

        // Water
        simulatorState.water.baselineLmin = 35.0;
        simulatorState.water.scenario = "NORMAL";
        simulatorState.water.cumulativeM3 = 842.15;
        simulatorState.water.running = true;

        // Air
        simulatorState.air.baselineOccupancy = 120;
        simulatorState.air.scenario = "NORMAL";
        simulatorState.air.running = true;

        // Waste
        simulatorState.waste.accumulationRatePct = 2.5;
        simulatorState.waste.scenario = "NORMAL";
        simulatorState.waste.fillLevelPct = 38.0;
        simulatorState.waste.running = true;

        // Sync slider and select elements
        syncInputsWithState();
        stepSimulation();
    }

    function syncInputsWithState() {
        setVal("resSimElecSlider", simulatorState.electricity.baselineKw);
        setText("resSimElecSliderVal", `${simulatorState.electricity.baselineKw} kW`);
        setVal("resSimElecScenario", simulatorState.electricity.scenario);

        setVal("resSimWaterSlider", simulatorState.water.baselineLmin);
        setText("resSimWaterSliderVal", `${simulatorState.water.baselineLmin} L/min`);
        setVal("resSimWaterScenario", simulatorState.water.scenario);

        setVal("resSimAirSlider", simulatorState.air.baselineOccupancy);
        setText("resSimAirSliderVal", `${simulatorState.air.baselineOccupancy} people`);
        setVal("resSimAirScenario", simulatorState.air.scenario);

        setVal("resSimWasteSlider", simulatorState.waste.accumulationRatePct);
        setText("resSimWasteSliderVal", `${simulatorState.waste.accumulationRatePct}% / step`);
        setVal("resSimWasteScenario", simulatorState.waste.scenario);
    }

    function setVal(id, val) {
        const el = document.getElementById(id);
        if (el) el.value = val;
    }

    // --- Tab Filtering for Grid vs Individual Views ---
    function switchUtilityView(viewId) {
        simulatorState.activeTab = viewId;
        const navBtns = document.querySelectorAll(".res-sim-subtab");
        navBtns.forEach(btn => {
            if (btn.getAttribute("data-res-view") === viewId) {
                btn.classList.add("active");
                btn.style.background = "#00D09C";
                btn.style.color = "#0E3D32";
            } else {
                btn.classList.remove("active");
                btn.style.background = "rgba(255, 255, 255, 0.05)";
                btn.style.color = "#A3C9BE";
            }
        });

        const cards = {
            electricity: document.getElementById("resSimCardElectricity"),
            water: document.getElementById("resSimCardWater"),
            air: document.getElementById("resSimCardAir"),
            waste: document.getElementById("resSimCardWaste")
        };

        if (viewId === "all") {
            Object.values(cards).forEach(c => { if (c) c.style.display = "flex"; });
        } else {
            Object.keys(cards).forEach(key => {
                if (cards[key]) {
                    cards[key].style.display = (key === viewId) ? "flex" : "none";
                }
            });
        }

        // Trigger chart resize
        setTimeout(() => {
            Object.values(chartInstances).forEach(chart => {
                if (chart) chart.resize();
            });
        }, 60);
    }

    // --- DOM Event Listeners Binding ---
    function bindEventListeners() {
        // Global Controls
        const btnStartAll = document.getElementById("resSimBtnStartAll");
        if (btnStartAll) btnStartAll.addEventListener("click", startAll);

        const btnPauseAll = document.getElementById("resSimBtnPauseAll");
        if (btnPauseAll) {
            btnPauseAll.addEventListener("click", () => {
                if (simulatorState.globalRunning) {
                    pauseAll();
                    btnPauseAll.innerHTML = '<i class="fa-solid fa-play"></i> Resume All';
                } else {
                    resumeAll();
                    btnPauseAll.innerHTML = '<i class="fa-solid fa-pause"></i> Pause All';
                }
            });
        }

        const btnStopAll = document.getElementById("resSimBtnStopAll");
        if (btnStopAll) btnStopAll.addEventListener("click", stopAll);

        const btnResetAll = document.getElementById("resSimBtnResetAll");
        if (btnResetAll) btnResetAll.addEventListener("click", resetToDefaults);

        // Global Interval
        const selectInterval = document.getElementById("resSimGlobalInterval");
        if (selectInterval) {
            selectInterval.addEventListener("change", (e) => {
                const val = parseInt(e.target.value, 10);
                if (val >= 500 && val <= 60000) {
                    simulatorState.globalIntervalMs = val;
                    startTimer();
                }
            });
        }

        // Subtabs
        const subtabs = document.querySelectorAll(".res-sim-subtab");
        subtabs.forEach(btn => {
            btn.addEventListener("click", (e) => {
                e.preventDefault();
                const view = btn.getAttribute("data-res-view");
                if (view) switchUtilityView(view);
            });
        });

        // 1. Electricity Controls
        bindResourceControls({
            resKey: "electricity",
            toggleBtnId: "resSimBtnElecToggle",
            resetBtnId: "resSimBtnElecReset",
            scenarioSelectId: "resSimElecScenario",
            sliderId: "resSimElecSlider",
            sliderValId: "resSimElecSliderVal",
            sliderUnit: "kW",
            onReset: () => {
                simulatorState.electricity.cumulativeKwh = 3420.5;
            }
        });

        // 2. Water Controls
        bindResourceControls({
            resKey: "water",
            toggleBtnId: "resSimBtnWaterToggle",
            resetBtnId: "resSimBtnWaterReset",
            scenarioSelectId: "resSimWaterScenario",
            sliderId: "resSimWaterSlider",
            sliderValId: "resSimWaterSliderVal",
            sliderUnit: "L/min",
            onReset: () => {
                simulatorState.water.cumulativeM3 = 842.15;
            }
        });

        // 3. Air Quality Controls
        bindResourceControls({
            resKey: "air",
            toggleBtnId: "resSimBtnAirToggle",
            resetBtnId: "resSimBtnAirReset",
            scenarioSelectId: "resSimAirScenario",
            sliderId: "resSimAirSlider",
            sliderValId: "resSimAirSliderVal",
            sliderUnit: "people",
            onReset: () => {
                simulatorState.air.baselineOccupancy = 120;
            }
        });

        // 4. Waste Controls
        bindResourceControls({
            resKey: "waste",
            toggleBtnId: "resSimBtnWasteToggle",
            resetBtnId: "resSimBtnWasteReset",
            scenarioSelectId: "resSimWasteScenario",
            sliderId: "resSimWasteSlider",
            sliderValId: "resSimWasteSliderVal",
            sliderUnit: "% / step",
            onReset: () => {
                // Emptied dump scenario: reset to 4.0%
                simulatorState.waste.scenario = "RESET_EMPTIED";
                const scenSelect = document.getElementById("resSimWasteScenario");
                if (scenSelect) scenSelect.value = "RESET_EMPTIED";
                stepSimulation();
            }
        });

        // Page Visibility API & Tab Unmount Cleanup
        document.addEventListener("visibilitychange", () => {
            if (document.hidden) {
                stopTimer();
            } else {
                if (simulatorState.globalRunning) startTimer();
            }
        });

        window.addEventListener("beforeunload", () => {
            stopTimer();
        });
    }

    function bindResourceControls(cfg) {
        const res = simulatorState[cfg.resKey];
        if (!res) return;

        const toggleBtn = document.getElementById(cfg.toggleBtnId);
        if (toggleBtn) {
            toggleBtn.addEventListener("click", () => {
                res.running = !res.running;
                toggleBtn.innerHTML = res.running ? '<i class="fa-solid fa-pause"></i> Pause' : '<i class="fa-solid fa-play"></i> Run';
                updateMetricsDOM();
            });
        }

        const resetBtn = document.getElementById(cfg.resetBtnId);
        if (resetBtn) {
            resetBtn.addEventListener("click", () => {
                if (cfg.onReset) cfg.onReset();
                stepSimulation();
            });
        }

        const scenSelect = document.getElementById(cfg.scenarioSelectId);
        if (scenSelect) {
            scenSelect.addEventListener("change", (e) => {
                res.scenario = e.target.value;
                stepSimulation();
            });
        }

        const slider = document.getElementById(cfg.sliderId);
        const sliderVal = document.getElementById(cfg.sliderValId);
        if (slider) {
            slider.addEventListener("input", (e) => {
                const val = parseFloat(e.target.value);
                if (cfg.resKey === "electricity") res.baselineKw = val;
                else if (cfg.resKey === "water") res.baselineLmin = val;
                else if (cfg.resKey === "air") res.baselineOccupancy = parseInt(val, 10);
                else if (cfg.resKey === "waste") res.accumulationRatePct = val;

                if (sliderVal) sliderVal.textContent = `${val} ${cfg.sliderUnit}`;
                stepSimulation();
            });
        }
    }

    // --- Public Module Interface ---
    window.EstateIQResourceSimulator = {
        init: function () {
            console.log("[ResourceSimulator] Initializing EstateIQ Resource Simulator Engine...");
            bindEventListeners();
            initCharts();
            syncInputsWithState();
            startTimer();
        },
        getState: function () {
            return simulatorState;
        },
        step: function () {
            stepSimulation();
        },
        start: startAll,
        pause: pauseAll,
        resume: resumeAll,
        stop: stopAll,
        reset: resetToDefaults,
        destroy: function () {
            stopTimer();
            Object.values(chartInstances).forEach(c => { if (c) c.destroy(); });
        }
    };

    // Auto-init on DOMContentLoaded or immediate if document is ready
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", () => {
            window.EstateIQResourceSimulator.init();
        });
    } else {
        window.EstateIQResourceSimulator.init();
    }
})();

