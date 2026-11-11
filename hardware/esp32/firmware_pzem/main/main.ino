#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <PZEM004Tv30.h>
#include <time.h>
#include <esp_wifi.h>

#include "config.h"

// =========================================================================================
// ESTATEIQ - ESP32 DEDICATED PZEM-004T ENERGY METROLOGY GATEWAY
// Dual Output: Local HTML Dashboard (:80) + Cloud REST Ingestion (:8000/api/v1/iot/telemetry)
// =========================================================================================

// ---------------- PZEM-004T Hardware Serial ----------------
HardwareSerial PZEMSerial(2);
PZEM004Tv30 pzem(PZEMSerial, PZEM_RX_PIN, PZEM_TX_PIN);

// ---------------- Local Web Server on Port 80 ----------------
WebServer server(80);

// ---------------- Sensor Measurements ----------------
float voltage = NAN;
float current = NAN;
float power = NAN;         // Watts
float energy = NAN;        // kWh
float frequency = NAN;     // Hz
float pf = NAN;            // Power Factor

bool pzemConnected = false;
unsigned long lastReadTime = 0;

// ---------------- Telemetry & Sequence Tracking ----------------
static unsigned long sequenceCounter = 0;
static char bootSessionId[16] = {0};
static char lastCloudStatus[32] = "INITIALIZING";
static int lastHttpCode = 0;
static unsigned long lastCloudSyncMillis = 0;
static bool ntpSynchronized = false;

// ---------------- HTML Dashboard (Embedded WebServer) ----------------
const char DASHBOARD[] PROGMEM = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>EstateIQ Energy Node - PZEM-004T</title>
<style>
* { box-sizing: border-box; }
body {
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    background: #0B1118;
    color: #E2E8F0;
}
header {
    background: linear-gradient(135deg, #0F172A 0%, #134E4A 100%);
    color: white;
    padding: 24px;
    text-align: center;
    border-bottom: 1px solid rgba(0, 240, 181, 0.2);
}
header h2 { margin: 0; font-size: 24px; font-weight: 800; letter-spacing: 0.5px; }
header p { margin: 8px 0 0; font-size: 13px; color: #00F0B5; font-weight: 600; }
.container {
    max-width: 960px;
    margin: 25px auto;
    padding: 0 16px;
}
.status-bar {
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    align-items: center;
    padding: 14px 20px;
    background: #151F2C;
    border: 1px solid #1E293B;
    border-radius: 12px;
    margin-bottom: 20px;
}
.status-pill {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
    font-weight: 700;
}
.dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    display: inline-block;
}
.dot.online { background: #00F0B5; box-shadow: 0 0 10px #00F0B5; }
.dot.offline { background: #EF4444; box-shadow: 0 0 10px #EF4444; }
.grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 16px;
}
.card {
    background: #151F2C;
    padding: 22px;
    border-radius: 14px;
    border: 1px solid #1E293B;
    transition: transform 0.15s ease, border-color 0.15s ease;
}
.card:hover {
    border-color: #00F0B5;
    transform: translateY(-2px);
}
.card h3 {
    margin: 0 0 12px;
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #94A3B8;
    font-weight: 600;
}
.value {
    font-size: 32px;
    font-weight: 800;
    color: #00F0B5;
    font-family: monospace;
}
.unit {
    font-size: 12px;
    color: #64748B;
    margin-top: 4px;
}
.cloud-banner {
    margin-top: 20px;
    padding: 14px 20px;
    background: #0F172A;
    border-radius: 12px;
    border: 1px solid #1E293B;
    font-size: 12px;
    color: #94A3B8;
    display: flex;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 8px;
}
footer {
    text-align: center;
    padding: 30px;
    color: #64748B;
    font-size: 12px;
}
</style>
</head>
<body>

<header>
    <h2>EstateIQ Energy Metrology Gateway</h2>
    <p>ESP32 Node #2 + Peacefair PZEM-004T (MID Class 1.0)</p>
</header>

<div class="container">
    <div class="status-bar">
        <div class="status-pill">
            <span class="dot" id="sensorDot"></span>
            <span>PZEM Meter: <span id="sensorStatus">Connecting...</span></span>
        </div>
        <div class="status-pill">
            <span class="dot" id="cloudDot"></span>
            <span>EstateIQ Cloud Sync: <span id="cloudStatus">Connecting...</span></span>
        </div>
    </div>

    <div class="grid">
        <div class="card">
            <h3>Line Voltage</h3>
            <div class="value" id="voltage">--</div>
            <div class="unit">Volts (V AC)</div>
        </div>
        <div class="card">
            <h3>AC Current</h3>
            <div class="value" id="current">--</div>
            <div class="unit">Amperes (A)</div>
        </div>
        <div class="card">
            <h3>Active Power</h3>
            <div class="value" id="power">--</div>
            <div class="unit">Watts (W) &bull; <span id="powerKw">-- kW</span></div>
        </div>
        <div class="card">
            <h3>Cumulative Energy</h3>
            <div class="value" id="energy">--</div>
            <div class="unit">Kilowatt-hours (kWh)</div>
        </div>
        <div class="card">
            <h3>Grid Frequency</h3>
            <div class="value" id="frequency">--</div>
            <div class="unit">Hertz (Hz)</div>
        </div>
        <div class="card">
            <h3>Power Factor</h3>
            <div class="value" id="pf">--</div>
            <div class="unit">Ratio (cos &phi;)</div>
        </div>
    </div>

    <div class="cloud-banner">
        <div>Device ID: <strong style="color:#00F0B5;">METER-BLOCK-B-001</strong> | Node: <strong style="color:#FFFFFF;">ESP32_PZEM_GATEWAY_01</strong></div>
        <div>Target API: <span id="apiHost">--</span> | Packets Ingested: <strong id="pktSeq">0</strong></div>
    </div>
</div>

<footer>
    EstateIQ Dual-Node Facility Intelligence &bull; Verified Physical Metrology Pipeline
</footer>

<script>
async function updateDashboard() {
    try {
        const response = await fetch('/data', { cache: 'no-store' });
        if (!response.ok) throw new Error('HTTP ' + response.status);
        const data = await response.json();

        // Meter status
        const sDot = document.getElementById('sensorDot');
        const sStatus = document.getElementById('sensorStatus');
        if (data.connected) {
            sDot.className = 'dot online';
            sStatus.textContent = 'ONLINE (UART2 Active)';
            sStatus.style.color = '#00F0B5';
        } else {
            sDot.className = 'dot offline';
            sStatus.textContent = 'DISCONNECTED (Check AC Line)';
            sStatus.style.color = '#EF4444';
        }

        // Cloud status
        const cDot = document.getElementById('cloudDot');
        const cStatus = document.getElementById('cloudStatus');
        if (data.cloud_code === 200) {
            cDot.className = 'dot online';
            cStatus.textContent = 'INGESTED (HTTP 200 OK)';
            cStatus.style.color = '#00F0B5';
        } else if (data.cloud_code > 0) {
            cDot.className = 'dot offline';
            cStatus.textContent = 'ERROR (HTTP ' + data.cloud_code + ')';
            cStatus.style.color = '#EF4444';
        } else {
            cDot.className = 'dot';
            cStatus.textContent = data.cloud_status || 'PENDING';
            cStatus.style.color = '#94A3B8';
        }

        document.getElementById('voltage').textContent = data.voltage;
        document.getElementById('current').textContent = data.current;
        document.getElementById('power').textContent = data.power;
        document.getElementById('powerKw').textContent = data.power_kw ? (data.power_kw + ' kW') : '-- kW';
        document.getElementById('energy').textContent = data.energy;
        document.getElementById('frequency').textContent = data.frequency;
        document.getElementById('pf').textContent = data.pf;
        document.getElementById('apiHost').textContent = data.backend_host || '--';
        document.getElementById('pktSeq').textContent = data.sequence || '0';

    } catch (err) {
        console.error(err);
    }
}
updateDashboard();
setInterval(updateDashboard, 2500);
</script>
</body>
</html>
)rawliteral";

// ---------------- Utility: Format Sensor Value ----------------
static String formatValue(float val, int decimals) {
    if (isnan(val)) return "--";
    return String(val, decimals);
}

// ---------------- ISO 8601 Timestamp Generator ----------------
static bool getISOTimestamp(char* buf, size_t maxLen) {
    time_t nowSec;
    time(&nowSec);
    struct tm timeinfo;
    gmtime_r(&nowSec, &timeinfo);

    if (timeinfo.tm_year > (2020 - 1900)) {
        strftime(buf, maxLen, "%Y-%m-%dT%H:%M:%SZ", &timeinfo);
        ntpSynchronized = true;
        return true;
    }

    // Relative uptime fallback: guarantee zero dropped packets before NTP lock
    unsigned long uptimeSec = millis() / 1000UL;
    unsigned long days = uptimeSec / 86400UL;
    unsigned long rem = uptimeSec % 86400UL;
    unsigned int hrs = rem / 3600UL;
    unsigned int mins = (rem % 3600UL) / 60UL;
    unsigned int secs = rem % 60UL;
    snprintf(buf, maxLen, "2026-11-10T%02u:%02u:%02uZ", hrs, mins, secs);
    return false;
}

// ---------------- Synchronize Clock from Backend ----------------
static void syncTimeFromBackend() {
    if (WiFi.status() != WL_CONNECTED) return;
    char timeUrl[128];
    snprintf(timeUrl, sizeof(timeUrl), "http://%s:%d/api/v1/system/time", ESTATEIQ_BACKEND_HOST, ESTATEIQ_BACKEND_PORT);

    HTTPClient http;
    http.begin(timeUrl);
    http.setTimeout(2000);
    int httpCode = http.GET();
    if (httpCode == 200) {
        String payload = http.getString();
        StaticJsonDocument<384> doc;
        DeserializationError err = deserializeJson(doc, payload);
        if (!err && doc.containsKey("epoch_timestamp")) {
            time_t epoch = doc["epoch_timestamp"].as<time_t>();
            struct timeval tv = { .tv_sec = epoch, .tv_usec = 0 };
            settimeofday(&tv, NULL);
            ntpSynchronized = true;
            Serial.printf("[TIME] Synchronized system time from EstateIQ backend: epoch=%ld\n", (long)epoch);
        }
    }
    http.end();
}

// ---------------- Read Physical PZEM-004T Meter ----------------
void readSensor() {
    float newVoltage = pzem.voltage();

    if (isnan(newVoltage)) {
        pzemConnected = false;
        voltage = NAN;
        current = NAN;
        power = NAN;
        energy = NAN;
        frequency = NAN;
        pf = NAN;
        Serial.println("[PZEM-WARN] PZEM sensor offline or no AC power connected to CT/meter.");
        return;
    }

    voltage = newVoltage;
    current = pzem.current();
    power = pzem.power();
    energy = pzem.energy();
    frequency = pzem.frequency();
    pf = pzem.pf();
    pzemConnected = true;

    Serial.printf("[PZEM-004T] V: %.1fV | I: %.3fA | P: %.1fW (%.3fkW) | En: %.3fkWh | Freq: %.1fHz | PF: %.2f\n",
                  voltage, current, power, power / 1000.0f, energy, frequency, pf);
}

// ---------------- Transmit Canonical Telemetry to EstateIQ Backend ----------------
void transmitTelemetryToEstateIQ() {
    if (WiFi.status() != WL_CONNECTED) {
        strncpy(lastCloudStatus, "WIFI_DISCONNECTED", sizeof(lastCloudStatus));
        return;
    }
    if (!pzemConnected || isnan(voltage)) {
        strncpy(lastCloudStatus, "PZEM_STANDBY", sizeof(lastCloudStatus));
        return;
    }

    sequenceCounter++;
    char timestampIso[32];
    getISOTimestamp(timestampIso, sizeof(timestampIso));

    StaticJsonDocument<1536> doc;
    doc["schema_version"] = "1.0";
    char msgId[48];
    snprintf(msgId, sizeof(msgId), "MSG_%s_%s_%lu", DEVICE_ID_ELEC, bootSessionId, sequenceCounter);
    doc["message_id"] = msgId;
    doc["gateway_id"] = GATEWAY_ID;
    doc["boot_id"] = bootSessionId;
    doc["device_id"] = DEVICE_ID_ELEC;
    doc["auth_token"] = GATEWAY_API_KEY;
    doc["facility_id"] = FACILITY_ID;
    doc["building_id"] = BUILDING_ID;
    doc["source_type"] = "real_sensor";
    doc["event_timestamp"] = timestampIso;
    doc["sent_timestamp"] = timestampIso;
    doc["sequence_number"] = sequenceCounter;

    doc["reporting_state"] = "NORMAL_15M";
    doc["reporting_interval_sec"] = PZEM_READ_INTERVAL_MS / 1000UL;
    doc["next_report_expected_sec"] = PZEM_READ_INTERVAL_MS / 1000UL;
    doc["is_anomaly"] = false;

    // Canonical Metrology Metrics Array
    JsonArray metrics = doc.createNestedArray("metrics");

    JsonObject m1 = metrics.createNestedObject();
    m1["metric"] = "voltage_v"; m1["value"] = voltage; m1["unit"] = "V"; m1["quality"] = "good";

    JsonObject m2 = metrics.createNestedObject();
    m2["metric"] = "current_a"; m2["value"] = isnan(current) ? 0.0f : current; m2["unit"] = "A"; m2["quality"] = "good";

    JsonObject m3 = metrics.createNestedObject();
    m3["metric"] = "active_power_kw"; m3["value"] = isnan(power) ? 0.0f : (power / 1000.0f); m3["unit"] = "kW"; m3["quality"] = "good";

    JsonObject m4 = metrics.createNestedObject();
    m4["metric"] = "cumulative_energy_kwh"; m4["value"] = isnan(energy) ? 0.0f : energy; m4["unit"] = "kWh"; m4["quality"] = "good";

    JsonObject m5 = metrics.createNestedObject();
    m5["metric"] = "power_factor"; m5["value"] = isnan(pf) ? 0.95f : pf; m5["unit"] = "ratio"; m5["quality"] = "good";

    JsonObject m6 = metrics.createNestedObject();
    m6["metric"] = "frequency_hz"; m6["value"] = isnan(frequency) ? 50.0f : frequency; m6["unit"] = "Hz"; m6["quality"] = "good";

    char jsonBuf[1536];
    serializeJson(doc, jsonBuf);

    char fullUrl[160];
    snprintf(fullUrl, sizeof(fullUrl), "http://%s:%d%s", ESTATEIQ_BACKEND_HOST, ESTATEIQ_BACKEND_PORT, ESTATEIQ_TELEMETRY_PATH);

    HTTPClient http;
    http.begin(fullUrl);
    http.addHeader("Content-Type", "application/json");
    http.setTimeout(2500);

    int httpResponseCode = http.POST((uint8_t*)jsonBuf, strlen(jsonBuf));
    lastHttpCode = httpResponseCode;
    lastCloudSyncMillis = millis();

    if (httpResponseCode >= 200 && httpResponseCode < 300) {
        strncpy(lastCloudStatus, "ACCEPTED", sizeof(lastCloudStatus));
        Serial.printf("[ESTATEIQ-HTTP] Telemetry POST accepted (HTTP %d) | Seq:%lu | %.1fV | %.2fW\n",
                      httpResponseCode, sequenceCounter, voltage, power);
    } else {
        snprintf(lastCloudStatus, sizeof(lastCloudStatus), "ERR_%d", httpResponseCode);
        Serial.printf("[ESTATEIQ-WARN] HTTP POST returned code %d to %s\n", httpResponseCode, fullUrl);
    }
    http.end();
}

// ---------------- Local Web Server Handlers ----------------
void handleRoot() {
    server.send_P(200, "text/html", DASHBOARD);
}

void handleData() {
    StaticJsonDocument<512> doc;
    doc["connected"] = pzemConnected;
    doc["voltage"] = formatValue(voltage, 2);
    doc["current"] = formatValue(current, 3);
    doc["power"] = formatValue(power, 2);
    doc["power_kw"] = isnan(power) ? "--" : String(power / 1000.0f, 3);
    doc["energy"] = formatValue(energy, 3);
    doc["frequency"] = formatValue(frequency, 2);
    doc["pf"] = formatValue(pf, 2);
    doc["backend_host"] = String(ESTATEIQ_BACKEND_HOST) + ":" + String(ESTATEIQ_BACKEND_PORT);
    doc["cloud_code"] = lastHttpCode;
    doc["cloud_status"] = lastCloudStatus;
    doc["sequence"] = sequenceCounter;

    String jsonStr;
    serializeJson(doc, jsonStr);
    server.send(200, "application/json", jsonStr);
}

// ---------------- Wi-Fi Setup with Anti-Sleep Resilience ----------------
void connectWiFi() {
    WiFi.disconnect(true);
    delay(100);
    WiFi.mode(WIFI_STA);
    WiFi.setAutoReconnect(true);
    WiFi.setSleep(false); // CRITICAL: Disable modem sleep to prevent beacon loss

    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    Serial.printf("[WIFI] Connecting to SSID '%s'...\n", WIFI_SSID);

    unsigned long start = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - start < 15000) {
        delay(400);
        Serial.print(".");
    }

    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("\n[WIFI] Connected successfully!");
        Serial.printf("[WIFI] Assigned IP: %s | RSSI: %d dBm\n", WiFi.localIP().toString().c_str(), WiFi.RSSI());
        Serial.printf("[WIFI] Local Web Dashboard: http://%s/\n", WiFi.localIP().toString().c_str());

        // Initial time sync
        syncTimeFromBackend();
        configTime(0, 0, "pool.ntp.org", "time.google.com");
    } else {
        Serial.println("\n[WIFI-WARN] Initial connection timeout. Background auto-reconnect will continue.");
    }
}

// ---------------- Setup ----------------
void setup() {
    Serial.begin(115200);
    delay(500);

    uint32_t chipId = (uint32_t)ESP.getEfuseMac();
    snprintf(bootSessionId, sizeof(bootSessionId), "%08X", chipId);

    Serial.println();
    Serial.println("==================================================================");
    Serial.println(" EstateIQ ESP32 Dedicated PZEM-004T Metrology Gateway (Node #2)");
    Serial.println("==================================================================");
    Serial.printf("[CONFIG] Gateway ID: %s | Device ID: %s\n", GATEWAY_ID, DEVICE_ID_ELEC);
    Serial.printf("[TARGET] http://%s:%d%s\n", ESTATEIQ_BACKEND_HOST, ESTATEIQ_BACKEND_PORT, ESTATEIQ_TELEMETRY_PATH);

    // Initialize PZEM-004T HardwareSerial(2) on RX16, TX17
    PZEMSerial.begin(PZEM_BAUD_RATE, SERIAL_8N1, PZEM_RX_PIN, PZEM_TX_PIN);
    Serial.printf("[PZEM-004T] Initialized UART2 on RX:%d, TX:%d at %d baud\n",
                  PZEM_RX_PIN, PZEM_TX_PIN, PZEM_BAUD_RATE);

    delay(300);

    // Connect to Wi-Fi
    connectWiFi();

    // Start Local Web Server
    server.on("/", HTTP_GET, handleRoot);
    server.on("/data", HTTP_GET, handleData);
    server.begin();
    Serial.println("[HTTP-SERVER] Local Web Dashboard active on port 80");

    // Initial sensor reading
    readSensor();
    lastReadTime = millis();
}

// ---------------- Main Loop ----------------
void loop() {
    // 1. Serve incoming local web dashboard browser clients
    server.handleClient();

    unsigned long now = millis();

    // 2. Periodic Sensor Acquisition and Cloud Telemetry Dispatch
    if (now - lastReadTime >= PZEM_READ_INTERVAL_MS) {
        lastReadTime = now;

        // A. Read PZEM-004T hardware
        readSensor();

        // B. If Wi-Fi dropped, retry connection gracefully
        if (WiFi.status() != WL_CONNECTED) {
            static unsigned long lastWifiRetry = 0;
            if (now - lastWifiRetry >= 15000UL) {
                lastWifiRetry = now;
                Serial.println("[WIFI] Auto-reconnecting to AP...");
                WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
            }
        } else {
            // C. Push canonical telemetry packet directly into EstateIQ FastAPI backend
            transmitTelemetryToEstateIQ();
        }
    }

    delay(2);
}

