/* ==========================================================================
   EstateIQ Facility Intelligence - Chart.js Initialization & Multi-Horizon Engine
   Supports 15 Min, 1 Hour, 24 Hours, 7 Days, 1 Month, 1 Year visualizations across:
   - Energy ML Load & Area Comparison
   - Water Consumption & Area Matrix
   - Waste Stream Fill Rate & Composition
   - Mobility Gate Flow & Air Quality (AQI)
   - Equipment Health & Vibration Anomaly Telemetry
   ========================================================================== */

let mainWaveChartInstance = null;
let miniBarChartInstance = null;
let scenarioChartInstance = null;

// Domain Specific Multi-Horizon Chart Instances
let energyTrendChartInstance = null;
let energyAreaChartInstance = null;
let waterTrendChartInstance = null;
let waterAreaChartInstance = null;
let wasteTrendChartInstance = null;
let wasteAreaChartInstance = null;
let mobilityTrendChartInstance = null;
let airTrendChartInstance = null;
let mobilityAreaChartInstance = null;
let equipmentVibrationChartInstance = null;
let equipmentAreaChartInstance = null;

document.addEventListener("DOMContentLoaded", () => {
    initWeeklyBarChart();
    initMainWaveChart();
    
    // Defer complex chart initializations slightly to ensure layout rendering
    setTimeout(() => {
        initEnergyTrendChart();
        initEnergyAreaChart();
        initWaterTrendChart();
        initWaterAreaChart();
        initWasteTrendChart();
        initWasteAreaChart();
        initMobilityTrendChart();
        initAirTrendChart();
        initMobilityAreaChart();
        initEquipmentVibrationChart();
        initEquipmentAreaChart();
        initScenarioComparisonChart();
        setupTimeHorizonListeners();
    }, 300);
});

/* ==========================================================================
   1. OVERVIEW & MINI CHARTS
   ========================================================================== */
function initWeeklyBarChart() {
    const ctx = document.getElementById("miniBarChart");
    if (!ctx) return;

    miniBarChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['M', 'T', 'W', 'T', 'F', 'S', 'S'],
            datasets: [
                {
                    label: 'Current Week',
                    data: [42, 65, 50, 58, 72, 38, 45],
                    backgroundColor: '#124B3E',
                    borderRadius: 4,
                    barPercentage: 0.5,
                    categoryPercentage: 0.7
                },
                {
                    label: 'Prior Week',
                    data: [35, 48, 55, 42, 60, 30, 38],
                    backgroundColor: '#88B9AC',
                    borderRadius: 4,
                    barPercentage: 0.5,
                    categoryPercentage: 0.7
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { display: false }, ticks: { color: '#9CA3AF', font: { family: 'Inter', size: 10, weight: '600' } } },
                y: { display: false, min: 0 }
            }
        }
    });
}

function initMainWaveChart() {
    const ctx = document.getElementById("mainWaveChart");
    if (!ctx) return;

    const labels = ['00:00', '03:00', '06:00', '09:00', '12:00', '15:00', '18:00', '21:00', '24:00'];

    mainWaveChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Energy (MWh)',
                    data: [4.2, 3.8, 5.1, 8.4, 9.2, 8.8, 7.42, 6.1, 4.9],
                    borderColor: '#124B3E',
                    borderWidth: 3.5,
                    tension: 0.45,
                    pointRadius: 0,
                    fill: false
                },
                {
                    label: 'Water (kL)',
                    data: [8.5, 7.2, 9.8, 14.1, 15.6, 13.9, 12.48, 11.2, 9.0],
                    borderColor: '#2BB49B',
                    borderWidth: 3.5,
                    tension: 0.45,
                    pointRadius: 0,
                    fill: false
                },
                {
                    label: 'Waste (kg)',
                    data: [2.1, 1.8, 3.2, 5.8, 6.4, 5.9, 5.42, 4.3, 3.1],
                    borderColor: '#D97706',
                    borderWidth: 3.5,
                    tension: 0.45,
                    pointRadius: 0,
                    fill: false
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, ticks: { color: '#6B7C77', font: { family: 'Inter', size: 12 } } },
                y: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, ticks: { color: '#6B7C77', font: { family: 'Inter', size: 12 } } }
            }
        }
    });
}

function updateChartTimeRange(range) {
    if (!mainWaveChartInstance) return;

    if (range === '7D') {
        mainWaveChartInstance.data.labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
        mainWaveChartInstance.data.datasets[0].data = [6.8, 7.9, 8.2, 7.42, 8.9, 5.4, 4.8];
        mainWaveChartInstance.data.datasets[1].data = [11.2, 13.5, 14.1, 12.48, 15.2, 9.1, 8.3];
        mainWaveChartInstance.data.datasets[2].data = [4.9, 5.8, 6.1, 5.42, 6.7, 3.8, 3.2];
    } else if (range === '30D') {
        mainWaveChartInstance.data.labels = ['Week 1', 'Week 2', 'Week 3', 'Week 4'];
        mainWaveChartInstance.data.datasets[0].data = [28.4, 31.2, 29.8, 27.5];
        mainWaveChartInstance.data.datasets[1].data = [48.1, 52.6, 50.2, 47.9];
        mainWaveChartInstance.data.datasets[2].data = [21.5, 23.8, 22.1, 20.4];
    } else { // 24H
        mainWaveChartInstance.data.labels = ['00:00', '03:00', '06:00', '09:00', '12:00', '15:00', '18:00', '21:00', '24:00'];
        mainWaveChartInstance.data.datasets[0].data = [4.2, 3.8, 5.1, 8.4, 9.2, 8.8, 7.42, 6.1, 4.9];
        mainWaveChartInstance.data.datasets[1].data = [8.5, 7.2, 9.8, 14.1, 15.6, 13.9, 12.48, 11.2, 9.0];
        mainWaveChartInstance.data.datasets[2].data = [2.1, 1.8, 3.2, 5.8, 6.4, 5.9, 5.42, 4.3, 3.1];
    }

    mainWaveChartInstance.update('active');
}

/* ==========================================================================
   2. ENERGY ML MULTI-HORIZON & AREA CHARTS
   ========================================================================== */
function getMultiHorizonData(domain, timeframe) {
    const horizons = {
        '15m': {
            labels: ['12:00', '12:15', '12:30', '12:45', '13:00', '13:15', '13:30', '13:45'],
            energyActual: [112, 118, 124, 135, 142, 145, 138, 132],
            energyPredicted: [110, 115, 122, 130, 138, 140, 135, 130],
            waterActual: [410, 425, 460, 520, 580, 540, 490, 470],
            waterPredicted: [400, 420, 450, 500, 550, 520, 480, 460],
            wasteFill: [62, 64, 68, 72, 78, 82, 84, 86],
            mobilityFlow: [45, 52, 68, 88, 94, 82, 70, 60],
            airAqi: [82, 85, 88, 94, 110, 108, 98, 92],
            equipVib: [2.1, 2.3, 2.8, 3.9, 4.2, 3.8, 3.1, 2.6]
        },
        '1h': {
            labels: ['12:00', '12:10', '12:20', '12:30', '12:40', '12:50', '13:00'],
            energyActual: [105, 112, 120, 128, 135, 142, 145],
            energyPredicted: [102, 110, 118, 125, 132, 138, 140],
            waterActual: [380, 410, 440, 470, 510, 560, 580],
            waterPredicted: [370, 400, 430, 460, 490, 540, 550],
            wasteFill: [58, 62, 66, 70, 75, 79, 83],
            mobilityFlow: [40, 48, 62, 78, 90, 96, 88],
            airAqi: [78, 82, 86, 92, 102, 110, 106],
            equipVib: [1.8, 2.0, 2.4, 3.1, 3.8, 4.1, 3.9]
        },
        '24h': {
            labels: ['00:00', '03:00', '06:00', '09:00', '12:00', '15:00', '18:00', '21:00'],
            energyActual: [65, 58, 82, 135, 145, 155, 128, 95],
            energyPredicted: [62, 55, 78, 128, 138, 148, 122, 90],
            waterActual: [220, 180, 340, 680, 750, 620, 490, 310],
            waterPredicted: [210, 175, 320, 640, 710, 590, 470, 300],
            wasteFill: [20, 22, 28, 45, 78, 88, 92, 54],
            mobilityFlow: [12, 8, 35, 145, 95, 110, 160, 65],
            airAqi: [54, 48, 65, 98, 110, 125, 115, 78],
            equipVib: [1.2, 1.1, 1.8, 3.2, 4.1, 4.3, 3.5, 2.1]
        },
        '7d': {
            labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
            energyActual: [138, 142, 145, 139, 151, 88, 76],
            energyPredicted: [135, 140, 142, 136, 147, 85, 72],
            waterActual: [680, 710, 750, 690, 740, 420, 380],
            waterPredicted: [660, 690, 720, 670, 710, 400, 360],
            wasteFill: [72, 78, 85, 80, 92, 55, 42],
            mobilityFlow: [140, 148, 155, 142, 162, 75, 58],
            airAqi: [98, 105, 112, 102, 120, 72, 65],
            equipVib: [3.4, 3.6, 4.1, 3.8, 4.3, 2.1, 1.8]
        },
        '1m': {
            labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
            energyActual: [940, 1020, 980, 910],
            energyPredicted: [920, 990, 950, 890],
            waterActual: [4800, 5200, 4950, 4600],
            waterPredicted: [4650, 5000, 4800, 4450],
            wasteFill: [75, 82, 78, 70],
            mobilityFlow: [980, 1050, 1010, 940],
            airAqi: [92, 108, 96, 88],
            equipVib: [3.2, 3.8, 3.5, 2.9]
        },
        '1y': {
            labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
            energyActual: [820, 850, 980, 1150, 1320, 1450, 1420, 1380, 1210, 1050, 890, 810],
            energyPredicted: [800, 830, 950, 1120, 1280, 1400, 1380, 1340, 1180, 1020, 860, 790],
            waterActual: [4100, 4300, 5100, 6200, 7100, 7800, 7600, 7200, 6400, 5300, 4400, 4000],
            waterPredicted: [3950, 4150, 4900, 6000, 6800, 7500, 7300, 6900, 6100, 5100, 4200, 3850],
            wasteFill: [62, 65, 72, 80, 88, 94, 91, 86, 78, 71, 64, 60],
            mobilityFlow: [850, 880, 990, 1120, 1250, 1310, 1280, 1220, 1150, 1040, 910, 830],
            airAqi: [115, 122, 108, 95, 88, 82, 75, 78, 89, 105, 130, 142],
            equipVib: [2.5, 2.7, 3.1, 3.8, 4.2, 4.6, 4.4, 4.1, 3.6, 3.0, 2.6, 2.4]
        }
    };
    return horizons[timeframe] || horizons['24h'];
}

function initEnergyTrendChart() {
    const ctx = document.getElementById("energyTrendChartCanvas");
    if (!ctx) return;

    const data = getMultiHorizonData('energy', '24h');

    energyTrendChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.labels,
            datasets: [
                {
                    label: 'Actual Telemetry Load (kWh)',
                    data: data.energyActual,
                    borderColor: '#EAB308',
                    backgroundColor: 'rgba(234, 179, 8, 0.15)',
                    borderWidth: 3,
                    tension: 0.35,
                    fill: true
                },
                {
                    label: 'CatBoost ML Forecast (kWh)',
                    data: data.energyPredicted,
                    borderColor: '#10B981',
                    borderWidth: 2.5,
                    borderDash: [5, 5],
                    tension: 0.35,
                    fill: false
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: true, labels: { color: '#94A3B8', font: { family: 'Inter', size: 11 } } },
                tooltip: { backgroundColor: '#0F172A', padding: 10 }
            },
            scales: {
                x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94A3B8' } },
                y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94A3B8' } }
            }
        }
    });
}

function initEnergyAreaChart() {
    const ctx = document.getElementById("energyAreaChartCanvas");
    if (!ctx) return;

    energyAreaChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Chiller Plant', 'AHUs & HVAC', 'Server / IT', 'Campus Lighting', 'Auxiliary Loads'],
            datasets: [{
                label: 'Sub-meter Load (kWh)',
                data: [65.4, 42.8, 24.5, 14.2, 8.3],
                backgroundColor: ['#124B3E', '#1E7A68', '#2BB49B', '#D97706', '#94A3B8'],
                borderRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { display: false }, ticks: { color: '#94A3B8', font: { family: 'Inter', size: 11 } } },
                y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94A3B8' } }
            }
        }
    });
}

/* ==========================================================================
   3. WATER MODULE MULTI-HORIZON & AREA CHARTS
   ========================================================================== */
function initWaterTrendChart() {
    const ctx = document.getElementById("waterTrendChartCanvas");
    if (!ctx) return;

    const data = getMultiHorizonData('water', '24h');

    waterTrendChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.labels,
            datasets: [
                {
                    label: 'Actual Water Demand (L/min)',
                    data: data.waterActual,
                    borderColor: '#06B6D4',
                    backgroundColor: 'rgba(6, 182, 212, 0.15)',
                    borderWidth: 3,
                    tension: 0.35,
                    fill: true
                },
                {
                    label: 'Predicted Demand (L/min)',
                    data: data.waterPredicted,
                    borderColor: '#10B981',
                    borderWidth: 2.5,
                    borderDash: [4, 4],
                    tension: 0.35,
                    fill: false
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: true, labels: { color: '#94A3B8' } } },
            scales: {
                x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94A3B8' } },
                y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94A3B8' } }
            }
        }
    });
}

function initWaterAreaChart() {
    const ctx = document.getElementById("waterAreaChartCanvas");
    if (!ctx) return;

    waterAreaChartInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Block B Hostel', 'Hostel A', 'Central Cafeteria', 'Admin Complex', 'Landscaping'],
            datasets: [{
                data: [42, 28, 18, 8, 4],
                backgroundColor: ['#06B6D4', '#1E7A68', '#D97706', '#10B981', '#64748B'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { position: 'right', labels: { color: '#94A3B8', font: { family: 'Inter', size: 11 } } } }
        }
    });
}

/* ==========================================================================
   4. WASTE MODULE MULTI-HORIZON & COMPOSITION CHARTS
   ========================================================================== */
function initWasteTrendChart() {
    const ctx = document.getElementById("wasteTrendChartCanvas");
    if (!ctx) return;

    const data = getMultiHorizonData('waste', '24h');

    wasteTrendChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.labels,
            datasets: [
                {
                    label: 'Avg Bin Fill Capacity (%)',
                    data: data.wasteFill,
                    borderColor: '#F59E0B',
                    backgroundColor: 'rgba(245, 158, 11, 0.15)',
                    borderWidth: 3,
                    tension: 0.35,
                    fill: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: true, labels: { color: '#94A3B8' } } },
            scales: {
                x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94A3B8' } },
                y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94A3B8' }, max: 100 }
            }
        }
    });
}

function initWasteAreaChart() {
    const ctx = document.getElementById("wasteAreaChartCanvas");
    if (!ctx) return;

    wasteAreaChartInstance = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: ['Organic / Wet', 'Dry Recyclables', 'Plastic & Packaging', 'Hazardous / E-Waste'],
            datasets: [{
                data: [45, 32, 18, 5],
                backgroundColor: ['#10B981', '#F59E0B', '#06B6D4', '#EF4444'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { position: 'right', labels: { color: '#94A3B8', font: { family: 'Inter', size: 11 } } } }
        }
    });
}

/* ==========================================================================
   5. MOBILITY, AIR QUALITY & EQUIPMENT CHARTS
   ========================================================================== */
function initMobilityTrendChart() {
    const ctx = document.getElementById("mobilityTrendChartCanvas");
    if (!ctx) return;

    const data = getMultiHorizonData('mobility', '24h');

    mobilityTrendChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.labels,
            datasets: [
                {
                    label: 'Campus Gate Entry Rate (Vehicles/hr)',
                    data: data.mobilityFlow,
                    borderColor: '#10B981',
                    backgroundColor: 'rgba(16, 185, 129, 0.15)',
                    borderWidth: 3,
                    tension: 0.35,
                    fill: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: true, labels: { color: '#94A3B8' } } },
            scales: {
                x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94A3B8' } },
                y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94A3B8' } }
            }
        }
    });
}

function initAirTrendChart() {
    const ctx = document.getElementById("airTrendChartCanvas");
    if (!ctx) return;

    const data = getMultiHorizonData('air', '24h');

    airTrendChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.labels,
            datasets: [
                {
                    label: 'Air Quality Index (AQI)',
                    data: data.airAqi,
                    borderColor: '#F59E0B',
                    borderWidth: 2.5,
                    tension: 0.35,
                    fill: false
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: true, labels: { color: '#94A3B8' } } },
            scales: {
                x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94A3B8' } },
                y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94A3B8' } }
            }
        }
    });
}

function initMobilityAreaChart() {
    const ctx = document.getElementById("mobilityAreaChartCanvas");
    if (!ctx) return;

    mobilityAreaChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['North Gate', 'South Gate', 'Multi-Story Deck', 'EV Charging Hub'],
            datasets: [{
                label: 'Occupancy Rate (%)',
                data: [78, 52, 64, 85],
                backgroundColor: ['#06B6D4', '#10B981', '#F59E0B', '#8B5CF6'],
                borderRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { display: false }, ticks: { color: '#94A3B8' } },
                y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94A3B8' }, max: 100 }
            }
        }
    });
}

function initEquipmentVibrationChart() {
    const ctx = document.getElementById("equipmentVibrationChartCanvas");
    if (!ctx) return;

    const data = getMultiHorizonData('equip', '24h');

    equipmentVibrationChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.labels,
            datasets: [
                {
                    label: 'AST_CHILLER_01 Vibration (mm/s)',
                    data: data.equipVib,
                    borderColor: '#EF4444',
                    backgroundColor: 'rgba(239, 68, 68, 0.15)',
                    borderWidth: 3,
                    tension: 0.4,
                    fill: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: true, labels: { color: '#94A3B8' } } },
            scales: {
                x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94A3B8' } },
                y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94A3B8' } }
            }
        }
    });
}

function initEquipmentAreaChart() {
    const ctx = document.getElementById("equipmentAreaChartCanvas");
    if (!ctx) return;

    equipmentAreaChartInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Optimal Health', 'Minor Wear', 'Maintenance Warning', 'Critical Alert'],
            datasets: [{
                data: [26, 6, 2, 1],
                backgroundColor: ['#10B981', '#06B6D4', '#F59E0B', '#EF4444'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { position: 'right', labels: { color: '#94A3B8', font: { family: 'Inter', size: 11 } } } }
        }
    });
}

/* ==========================================================================
   6. TIME HORIZON BUTTON CLICK EVENT HANDLERS ENGINE
   ========================================================================== */
function setupTimeHorizonListeners() {
    document.querySelectorAll(".time-horizon-bar").forEach(bar => {
        const target = bar.getAttribute("data-chart-target");
        bar.querySelectorAll(".th-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                bar.querySelectorAll(".th-btn").forEach(b => b.classList.remove("active"));
                btn.classList.add("active");

                const timeframe = btn.getAttribute("data-timeframe");
                updateChartHorizon(target, timeframe);
            });
        });
    });
}

function updateChartHorizon(target, timeframe) {
    const data = getMultiHorizonData(target, timeframe);

    if (target === 'energyTrend' && energyTrendChartInstance) {
        energyTrendChartInstance.data.labels = data.labels;
        energyTrendChartInstance.data.datasets[0].data = data.energyActual;
        energyTrendChartInstance.data.datasets[1].data = data.energyPredicted;
        energyTrendChartInstance.update('active');
    } else if (target === 'waterTrend' && waterTrendChartInstance) {
        waterTrendChartInstance.data.labels = data.labels;
        waterTrendChartInstance.data.datasets[0].data = data.waterActual;
        waterTrendChartInstance.data.datasets[1].data = data.waterPredicted;
        waterTrendChartInstance.update('active');
    } else if (target === 'wasteTrend' && wasteTrendChartInstance) {
        wasteTrendChartInstance.data.labels = data.labels;
        wasteTrendChartInstance.data.datasets[0].data = data.wasteFill;
        wasteTrendChartInstance.update('active');
    } else if (target === 'mobilityTrend' && mobilityTrendChartInstance) {
        mobilityTrendChartInstance.data.labels = data.labels;
        mobilityTrendChartInstance.data.datasets[0].data = data.mobilityFlow;
        mobilityTrendChartInstance.update('active');
    } else if (target === 'airTrend' && airTrendChartInstance) {
        airTrendChartInstance.data.labels = data.labels;
        airTrendChartInstance.data.datasets[0].data = data.airAqi;
        airTrendChartInstance.update('active');
    } else if (target === 'equipmentTrend' && equipmentVibrationChartInstance) {
        equipmentVibrationChartInstance.data.labels = data.labels;
        equipmentVibrationChartInstance.data.datasets[0].data = data.equipVib;
        equipmentVibrationChartInstance.update('active');
    }
}

/* ==========================================================================
   7. WHAT-IF SCENARIO COMPARISON ENGINE
   ========================================================================== */
function initScenarioComparisonChart(baselineData = [], targetData = []) {
    const ctx = document.getElementById("scenarioComparisonChart");
    if (!ctx) return;

    const hours = Array.from({ length: 24 }, (_, i) => `${String(i).padStart(2, '0')}:00`);
    const defaultBaseline = baselineData.length ? baselineData : [85, 80, 78, 75, 82, 98, 125, 142, 155, 160, 158, 150, 145, 148, 152, 140, 130, 120, 115, 110, 105, 98, 92, 88];
    const defaultTarget = targetData.length ? targetData : [72, 68, 65, 62, 68, 82, 102, 118, 128, 132, 130, 124, 120, 122, 125, 116, 108, 98, 94, 90, 85, 80, 75, 72];

    if (scenarioChartInstance) {
        scenarioChartInstance.destroy();
    }

    scenarioChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: hours,
            datasets: [
                {
                    label: 'Baseline Demand (kWh)',
                    data: defaultBaseline,
                    borderColor: '#EF4444',
                    borderWidth: 2.5,
                    borderDash: [5, 5],
                    tension: 0.35,
                    pointRadius: 0,
                    fill: false
                },
                {
                    label: 'Simulated Target Load (kWh)',
                    data: defaultTarget,
                    borderColor: '#10B981',
                    backgroundColor: 'rgba(16, 185, 129, 0.12)',
                    borderWidth: 3,
                    tension: 0.35,
                    pointRadius: 2,
                    fill: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: true, position: 'top', labels: { color: '#94A3B8' } },
                tooltip: { backgroundColor: '#0E3D32', padding: 10 }
            },
            scales: {
                x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94A3B8' } },
                y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94A3B8' } }
            }
        }
    });
}

function updateScenarioChartData(baseLoadMultiplier, solarKwOffset) {
    if (!scenarioChartInstance) {
        initScenarioComparisonChart();
    }
    if (!scenarioChartInstance) return;

    const baseCurve = [85, 80, 78, 75, 82, 98, 125, 142, 155, 160, 158, 150, 145, 148, 152, 140, 130, 120, 115, 110, 105, 98, 92, 88];
    const solarCurve = [0, 0, 0, 0, 5, 25, 60, 95, 130, 145, 150, 145, 135, 110, 75, 40, 15, 0, 0, 0, 0, 0, 0, 0];

    const targetCurve = baseCurve.map((val, i) => {
        const hvacAdjusted = val * baseLoadMultiplier;
        const solarOffset = (solarCurve[i] / 150) * (solarKwOffset * 0.15);
        return Math.max(15, Math.round(hvacAdjusted - solarOffset));
    });

    scenarioChartInstance.data.datasets[1].data = targetCurve;
    scenarioChartInstance.update('active');
}
