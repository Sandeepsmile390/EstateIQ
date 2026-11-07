/**
 * EstateIQ Standalone Resource Simulator UI Controller (resource-simulator-app/static/app.js)
 */

(function () {
    "use strict";

    const charts = {
        electricity: null,
        water: null,
        air: null,
        waste: null
    };

    let pollingTimer = null;
    let isGlobalRunning = true;

    // --- Chart Initialization ---
    function initCharts() {
        const commonOptions = {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 300 },
            plugins: {
                legend: {
                    display: true,
                    labels: { color: "#A3C9BE", font: { size: 10, family: "Inter" } }
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
                    ticks: { color: "#6A8C84", font: { size: 9 }, maxTicksLimit: 6 },
                    grid: { color: "rgba(255, 255, 255, 0.05)" }
                },
                y: {
                    ticks: { color: "#A3C9BE", font: { size: 9 } },
                    grid: { color: "rgba(255, 255, 255, 0.05)" }
                }
            }
        };

        // Electricity Chart
        const ctxElec = document.getElementById("chartElec");
        if (ctxElec) {
            charts.electricity = new Chart(ctxElec, {
                type: "line",
                data: {
                    labels: [],
                    datasets: [{
                        label: "Active Power (kW)",
                        data: [],
                        borderColor: "#00D09C",
                        backgroundColor: "rgba(0, 208, 156, 0.1)",
                        borderWidth: 2,
                        tension: 0.3,
                        fill: true,
                        pointRadius: 2
                    }]
                },
                options: commonOptions
            });
        }

        // Water Chart
        const ctxWater = document.getElementById("chartWater");
        if (ctxWater) {
            charts.water = new Chart(ctxWater, {
                type: "line",
                data: {
                    labels: [],
                    datasets: [
                        {
                            label: "Flow (L/min)",
                            data: [],
                            borderColor: "#38BDF8",
                            backgroundColor: "rgba(56, 189, 248, 0.1)",
                            borderWidth: 2,
                            tension: 0.3,
                            fill: true,
                            pointRadius: 2,
                            yAxisID: "y"
                        },
                        {
                            label: "Pressure (bar)",
                            data: [],
                            borderColor: "#F5C577",
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
                        y1: {
                            position: "right",
                            ticks: { color: "#F5C577", font: { size: 9 } },
                            grid: { drawOnChartArea: false }
                        }
                    }
                }
            });
        }

        // Air Quality Chart
        const ctxAir = document.getElementById("chartAir");
        if (ctxAir) {
            charts.air = new Chart(ctxAir, {
                type: "line",
                data: {
                    labels: [],
                    datasets: [
                        {
                            label: "CO2 (ppm)",
                            data: [],
                            borderColor: "#A78BFA",
                            backgroundColor: "rgba(167, 139, 250, 0.1)",
                            borderWidth: 2,
                            tension: 0.3,
                            fill: true,
                            pointRadius: 2,
                            yAxisID: "y"
                        },
                        {
                            label: "PM2.5 (µg/m³)",
                            data: [],
                            borderColor: "#F97316",
                            borderWidth: 1.5,
                            tension: 0.3,
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
                            ticks: { color: "#F97316", font: { size: 9 } },
                            grid: { drawOnChartArea: false }
                        }
                    }
                }
            });
        }

        // Waste Chart
        const ctxWaste = document.getElementById("chartWaste");
        if (ctxWaste) {
            charts.waste = new Chart(ctxWaste, {
                type: "line",
                data: {
                    labels: [],
                    datasets: [{
                        label: "Fill Level (%)",
                        data: [],
                        borderColor: "#F5C577",
                        backgroundColor: "rgba(245, 197, 119, 0.1)",
                        borderWidth: 2,
                        tension: 0.3,
                        fill: true,
                        pointRadius: 2
                    }]
                },
                options: {
                    ...commonOptions,
                    scales: {
                        ...commonOptions.scales,
                        y: { ...commonOptions.scales.y, min: 0, max: 100 }
                    }
                }
            });
        }
    }

    // --- State Polling & DOM Sync ---
    async function fetchStatus() {
        try {
            const resp = await fetch("/api/status");
            if (!resp.ok) return;
            const data = await resp.json();

            isGlobalRunning = data.global_running;
            setText("lblSamplesCount", data.samples_generated);
            if (data.last_sample_at) {
                const d = new Date(data.last_sample_at);
                setText("clockLastSample", d.toLocaleTimeString());
            }

            // Backend Status Badge
            const badge = document.getElementById("apiStatusBadge");
            const badgeText = document.getElementById("apiStatusText");
            if (data.backend_connected) {
                badge.style.borderColor = "var(--text-mint)";
                badge.style.color = "var(--text-mint)";
                badgeText.textContent = "ESTATEIQ BACKEND: SYNCED (8000)";
            } else {
                badge.style.borderColor = "var(--accent-gold)";
                badge.style.color = "var(--accent-gold)";
                badgeText.textContent = "STANDALONE MODE (API 8000 OFFLINE)";
            }

            // Sync Electricity
            const e = data.electricity;
            setText("valElecPower", `${e.active_power_kw.toFixed(1)} kW`);
            setText("valElecKwh", `${e.cumulative_energy_kwh.toFixed(2)} kWh`);
            setText("valElecVolt", `${e.voltage_v.toFixed(1)} V`);
            setText("valElecCurrent", `${e.current_a.toFixed(1)} A`);
            setText("valElecPf", e.power_factor.toFixed(2));
            setText("valElecFreq", `${e.frequency_hz.toFixed(2)} Hz`);
            setSelect("selElecScenario", e.scenario);
            setSlider("sldElecKw", e.baseline_kw);
            setText("lblElecKwVal", `${e.baseline_kw} kW`);
            setStatusBadge("badgeElecStatus", e.running);

            // Sync Water
            const w = data.water;
            setText("valWaterFlow", `${w.flow_rate_lmin.toFixed(1)} L/min`);
            setText("valWaterM3", `${w.cumulative_water_m3.toFixed(3)} m³`);
            setText("valWaterPressure", `${w.water_pressure_bar.toFixed(2)} bar`);
            setSelect("selWaterScenario", w.scenario);
            setSlider("sldWaterLmin", w.baseline_lmin);
            setText("lblWaterLminVal", `${w.baseline_lmin} L/min`);
            setStatusBadge("badgeWaterStatus", w.running);

            // Sync Air Quality
            const a = data.air;
            setText("valAirCo2", `${a.co2_ppm} ppm`);
            setText("valAirPm25", `${a.pm25.toFixed(1)} µg/m³`);
            setText("valAirPm10", `${a.pm10.toFixed(1)} µg/m³`);
            setText("valAirTemp", `${a.temperature_c.toFixed(1)} °C`);
            setText("valAirHum", `${a.humidity_pct.toFixed(1)} %`);
            setText("valAirAqi", `${a.air_quality_aqi} (${a.aqi_category})`);
            setSelect("selAirScenario", a.scenario);
            setSlider("sldAirOcc", a.baseline_occupancy);
            setText("lblAirOccVal", `${a.baseline_occupancy} people`);
            setStatusBadge("badgeAirStatus", a.running);

            // Sync Waste
            const wst = data.waste;
            setText("valWasteFill", `${wst.fill_level_percent.toFixed(1)} %`);
            setText("valWasteKg", `${wst.estimated_waste_kg.toFixed(1)} kg`);
            setText("valWasteRisk", wst.overflow_risk);
            setText("valWasteStatusTxt", wst.collection_status);
            setSelect("selWasteScenario", wst.scenario);
            setSlider("sldWasteRate", wst.accumulation_rate_pct);
            setText("lblWasteRateVal", `${wst.accumulation_rate_pct}% / step`);
            setStatusBadge("badgeWasteStatus", wst.running);

            // Update Progress Bar
            const pbar = document.getElementById("barWasteFill");
            if (pbar) {
                pbar.style.width = `${wst.fill_level_percent}%`;
                if (wst.fill_level_percent >= 90) pbar.style.background = "var(--accent-red)";
                else if (wst.fill_level_percent >= 75) pbar.style.background = "#F97316";
                else if (wst.fill_level_percent >= 50) pbar.style.background = "var(--accent-gold)";
                else pbar.style.background = "var(--text-mint)";
            }

        } catch (err) {
            console.error("Failed to poll simulator status:", err);
        }
    }

    async function fetchStream() {
        try {
            const resp = await fetch("/api/stream");
            if (!resp.ok) return;
            const data = await resp.json();
            const h = data.history;

            if (charts.electricity && h.electricity) {
                charts.electricity.data.labels = h.electricity.time;
                charts.electricity.data.datasets[0].data = h.electricity.power;
                charts.electricity.update("none");
            }
            if (charts.water && h.water) {
                charts.water.data.labels = h.water.time;
                charts.water.data.datasets[0].data = h.water.flow;
                charts.water.data.datasets[1].data = h.water.pressure;
                charts.water.update("none");
            }
            if (charts.air && h.air) {
                charts.air.data.labels = h.air.time;
                charts.air.data.datasets[0].data = h.air.co2;
                charts.air.data.datasets[1].data = h.air.pm25;
                charts.air.update("none");
            }
            if (charts.waste && h.waste) {
                charts.waste.data.labels = h.waste.time;
                charts.waste.data.datasets[0].data = h.waste.fill;
                charts.waste.update("none");
            }
        } catch (err) {
            console.error("Failed to poll stream history:", err);
        }
    }

    function setText(id, txt) {
        const el = document.getElementById(id);
        if (el) el.textContent = txt;
    }

    function setSelect(id, val) {
        const el = document.getElementById(id);
        if (el && document.activeElement !== el) el.value = val;
    }

    function setSlider(id, val) {
        const el = document.getElementById(id);
        if (el && document.activeElement !== el) el.value = val;
    }

    function setStatusBadge(id, isRunning) {
        const el = document.getElementById(id);
        if (!el) return;
        if (isRunning && isGlobalRunning) {
            el.textContent = "ACTIVE";
            el.style.background = "rgba(0, 208, 156, 0.15)";
            el.style.borderColor = "var(--text-mint)";
            el.style.color = "var(--text-mint)";
        } else {
            el.textContent = "PAUSED";
            el.style.background = "rgba(245, 197, 119, 0.15)";
            el.style.borderColor = "var(--accent-gold)";
            el.style.color = "var(--accent-gold)";
        }
    }

    // --- Actions Binding ---
    function bindEvents() {
        document.getElementById("btnStartAll")?.addEventListener("click", () => {
            fetch("/api/start", { method: "POST" }).then(fetchStatus);
        });

        document.getElementById("btnPauseAll")?.addEventListener("click", () => {
            fetch("/api/pause", { method: "POST" }).then(fetchStatus);
        });

        document.getElementById("btnStep")?.addEventListener("click", () => {
            fetch("/api/step", { method: "POST" }).then(() => {
                fetchStatus();
                fetchStream();
            });
        });

        document.getElementById("btnStopAll")?.addEventListener("click", () => {
            fetch("/api/stop", { method: "POST" }).then(fetchStatus);
        });

        document.getElementById("btnResetAll")?.addEventListener("click", () => {
            fetch("/api/reset", { method: "POST" }).then(() => {
                fetchStatus();
                fetchStream();
            });
        });

        document.getElementById("selectInterval")?.addEventListener("change", (e) => {
            fetch("/api/config/interval", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ interval_sec: parseFloat(e.target.value) })
            });
        });

        // Scenario selects
        const bindScenario = (selectId, utility) => {
            document.getElementById(selectId)?.addEventListener("change", (e) => {
                fetch("/api/scenario", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ utility: utility, scenario: e.target.value })
                }).then(fetchStatus);
            });
        };
        bindScenario("selElecScenario", "electricity");
        bindScenario("selWaterScenario", "water");
        bindScenario("selAirScenario", "air");
        bindScenario("selWasteScenario", "waste");

        // Baseline sliders
        const bindSlider = (sliderId, utility, labelId, unit) => {
            const el = document.getElementById(sliderId);
            if (el) {
                el.addEventListener("input", (e) => {
                    setText(labelId, `${e.target.value} ${unit}`);
                });
                el.addEventListener("change", (e) => {
                    fetch("/api/config/baseline", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ utility: utility, value: parseFloat(e.target.value) })
                    }).then(fetchStatus);
                });
            }
        };
        bindSlider("sldElecKw", "electricity", "lblElecKwVal", "kW");
        bindSlider("sldWaterLmin", "water", "lblWaterLminVal", "L/min");
        bindSlider("sldAirOcc", "air", "lblAirOccVal", "people");
        bindSlider("sldWasteRate", "waste", "lblWasteRateVal", "% / step");

        // Individual toggles & resets
        document.getElementById("btnToggleElec")?.addEventListener("click", () => {
            fetch("/api/pause?utility=electricity", { method: "POST" }).then(fetchStatus);
        });
        document.getElementById("btnResetElec")?.addEventListener("click", () => {
            fetch("/api/reset?utility=electricity", { method: "POST" }).then(fetchStatus);
        });

        document.getElementById("btnToggleWater")?.addEventListener("click", () => {
            fetch("/api/pause?utility=water", { method: "POST" }).then(fetchStatus);
        });
        document.getElementById("btnResetWater")?.addEventListener("click", () => {
            fetch("/api/reset?utility=water", { method: "POST" }).then(fetchStatus);
        });

        document.getElementById("btnToggleAir")?.addEventListener("click", () => {
            fetch("/api/pause?utility=air", { method: "POST" }).then(fetchStatus);
        });

        document.getElementById("btnToggleWaste")?.addEventListener("click", () => {
            fetch("/api/pause?utility=waste", { method: "POST" }).then(fetchStatus);
        });
        document.getElementById("btnResetWaste")?.addEventListener("click", () => {
            fetch("/api/reset?utility=waste", { method: "POST" }).then(fetchStatus);
        });

        // Subtabs
        const tabBtns = document.querySelectorAll(".tab-btn");
        const cards = {
            electricity: document.getElementById("cardElectricity"),
            water: document.getElementById("cardWater"),
            air: document.getElementById("cardAir"),
            waste: document.getElementById("cardWaste")
        };

        tabBtns.forEach(btn => {
            btn.addEventListener("click", (e) => {
                e.preventDefault();
                tabBtns.forEach(b => b.classList.remove("active"));
                btn.classList.add("active");
                const view = btn.getAttribute("data-view");

                if (view === "all") {
                    Object.values(cards).forEach(c => { if (c) c.style.display = "flex"; });
                } else {
                    Object.keys(cards).forEach(k => {
                        if (cards[k]) cards[k].style.display = (k === view) ? "flex" : "none";
                    });
                }
                setTimeout(() => {
                    Object.values(charts).forEach(c => { if (c) c.resize(); });
                }, 50);
            });
        });
    }

    // --- Init ---
    document.addEventListener("DOMContentLoaded", () => {
        initCharts();
        bindEvents();
        fetchStatus();
        fetchStream();
        pollingTimer = setInterval(() => {
            fetchStatus();
            fetchStream();
        }, 1200);
    });
})();

