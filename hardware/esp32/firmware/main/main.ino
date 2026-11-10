/*
 * EstateIQ ESP32 Edge Sensor Gateway Firmware v3.0-ProductionIoT
 * =========================================================================================
 * Full Hardware Support for Multi-Modal Facility Intelligence:
 * 1. Peacefair PZEM-004T 10A / 100A AC Metrology Monitor (UART2: GPIO16/17)
 * 2. ZJ-S201 / YF-S201 Water Flow Sensor (Interrupt Pulse Counter: GPIO4)
 * 3. JSN-SR04T / AJ-SR04M / HC-SR04 Waterproof Ultrasonic Sonar (Trig: GPIO5, Echo: GPIO18)
 * 4. DHT11 Digital Temperature & Humidity Module (1-Wire: GPIO23)
 * 5. MQ-135 Gas / Air Quality Detector Module (ADC1: GPIO34)
 * 6. 0.96 Inch I2C SSD1306 128x64 OLED Display (SDA: GPIO21, SCL: GPIO22)
 *
 * Transports:
 * - Direct HTTP REST Ingestion to EstateIQ Backend (/api/v1/iot/telemetry)
 * - Volatile Ring-Buffer Offline Fallback Queue
 * - Non-blocking Wi-Fi State Machine with Auto-Reconnect
 * =========================================================================================
 */

#include <WiFi.h>
#include <WiFiClient.h>
#include <HTTPClient.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <time.h>
#include <esp_wifi.h>

#include "config.h"

// Keep older local config.h files buildable. Set SYSTEM_TIME_ENDPOINT in config.h
// to the backend's LAN URL to enable backend clock sync for your demo network.
#ifndef SYSTEM_TIME_ENDPOINT
#define SYSTEM_TIME_ENDPOINT ""
#endif

// --- Global Client Instances ---
WiFiClient espClient;
PubSubClient mqttClient(espClient);
HardwareSerial MeterSerial(2); // UART2: RX=GPIO16, TX=GPIO17

// --- Device State Trackers ---
static unsigned long sequenceCounter = 0;
static char bootId[9] = "00000000";
static unsigned long lastSampleMillis = 0;
static unsigned long lastWifiConnectAttempt = 0;
static unsigned long lastMqttAttempt = 0;
static unsigned long mqttBackoffMs = 2000;
static const unsigned long maxMqttBackoffMs = 60000;
static bool wifiReportedConnected = false;
static bool timeIsSynchronized = false;
static unsigned long gatewayBootTimeUtc = 0;

// --- Adaptive Telemetry Reporting State Machine ---
enum GatewayReportingState {
    REPORT_STATE_NORMAL_15M = 0,
    REPORT_STATE_ANOMALY_5M = 1,
    REPORT_STATE_RECOVERY_5M = 2
};

struct EdgeAnomalyState {
    bool is_active = false;
    char metric[32] = "";
    float observed_value = 0.0f;
    float threshold_value = 0.0f;
    char reason[128] = "";
    char device_id[32] = "";
    unsigned long first_detected_ms = 0;
    int persistence_counter = 0;
};

static GatewayReportingState currentReportingState = REPORT_STATE_NORMAL_15M;
static EdgeAnomalyState g_edgeAnomaly;
static unsigned long lastAcquisitionMillis = 0;
static unsigned long lastReportMillis = 0;
static int recoveryConfirmationCount = 0;
static bool triggerImmediateAnomalyReport = false;

// --- Telemetry Readings Structs ---
struct ElectricityReadings {
    bool valid = false;
    float voltage_v = 0.0f;
    float current_a = 0.0f;
    float active_power_kw = 0.0f;
    float cumulative_energy_kwh = 0.0f;
    float power_factor = 0.95f;
    float frequency_hz = 50.0f;
    const char* meter_type = "PZEM-004T";
};

struct WaterReadings {
    bool flow_valid = false;
    float water_flow_lmin = 0.0f;
    float cumulative_water_m3 = 0.0f;
    float cumulative_liters = 0.0f;
    unsigned long pulse_count_total = 0;

    bool tank_valid = false;
    float tank_distance_cm = 0.0f;
    float tank_level_pct = 0.0f;

    bool pressure_valid = false;
    float water_pressure_bar = 0.0f;
};

struct EnvironmentalReadings {
    bool gas_valid = false;
    int raw_adc = 0;
    float sensor_voltage_v = 0.0f;
    float co2_estimate_ppm = 400.0f;
    bool warming_up = false;

    bool dht_valid = false;
    float temperature_c = 0.0f;
    float humidity_pct = 0.0f;
    float heat_index_c = 0.0f;
};

struct WasteReadings {
    bool bin_valid = false;
    float bin_distance_cm = 0.0f;
    float fill_level_percent = 0.0f;
    int echo_pin_used = -1;
};

// Forward function declarations
bool readPZEM004TMeter(ElectricityReadings &out);
bool readWaterFlowSensor(WaterReadings &out);
bool readUltrasonicSensor(WaterReadings &out);
bool readDHT11Sensor(EnvironmentalReadings &out);
bool readMQ135GasSensor(EnvironmentalReadings &out);
bool readWasteUltrasonicSensor(WasteReadings &out, const WaterReadings &water);

// --- Edge Anomaly Evaluation Logic ---
static bool evaluateEdgeAnomalies(const ElectricityReadings& elec, const WaterReadings& water, const EnvironmentalReadings& env, const WasteReadings& waste, EdgeAnomalyState& outAnomaly) {
    // A. Electrical Anomaly Checks (PZEM-004T / Modbus)
    if (elec.valid) {
        if (elec.voltage_v > 0.0f && (elec.voltage_v < EDGE_ANOMALY_ELEC_VOLTAGE_MIN || elec.voltage_v > EDGE_ANOMALY_ELEC_VOLTAGE_MAX)) {
            outAnomaly.is_active = true;
            strncpy(outAnomaly.metric, "voltage_v", sizeof(outAnomaly.metric));
            outAnomaly.observed_value = elec.voltage_v;
            outAnomaly.threshold_value = (elec.voltage_v < EDGE_ANOMALY_ELEC_VOLTAGE_MIN) ? EDGE_ANOMALY_ELEC_VOLTAGE_MIN : EDGE_ANOMALY_ELEC_VOLTAGE_MAX;
            snprintf(outAnomaly.reason, sizeof(outAnomaly.reason), "Grid voltage %.1fV out of nominal safety window (%.0f-%.0fV)", elec.voltage_v, EDGE_ANOMALY_ELEC_VOLTAGE_MIN, EDGE_ANOMALY_ELEC_VOLTAGE_MAX);
            strncpy(outAnomaly.device_id, DEVICE_ID_ELEC, sizeof(outAnomaly.device_id));
            return true;
        }
        if (elec.active_power_kw > EDGE_ANOMALY_ELEC_POWER_MAX) {
            outAnomaly.is_active = true;
            strncpy(outAnomaly.metric, "active_power_kw", sizeof(outAnomaly.metric));
            outAnomaly.observed_value = elec.active_power_kw;
            outAnomaly.threshold_value = EDGE_ANOMALY_ELEC_POWER_MAX;
            snprintf(outAnomaly.reason, sizeof(outAnomaly.reason), "Active power %.2fkW exceeds maximum bench safety limit (%.1fkW)", elec.active_power_kw, EDGE_ANOMALY_ELEC_POWER_MAX);
            strncpy(outAnomaly.device_id, DEVICE_ID_ELEC, sizeof(outAnomaly.device_id));
            return true;
        }
    }

    // B. Water Flow & Tank Anomaly Checks (ZJ-S201 & Ultrasonic)
    if (water.flow_valid && water.water_flow_lmin > EDGE_ANOMALY_WATER_FLOW_MAX) {
        outAnomaly.is_active = true;
        strncpy(outAnomaly.metric, "water_flow_lmin", sizeof(outAnomaly.metric));
        outAnomaly.observed_value = water.water_flow_lmin;
        outAnomaly.threshold_value = EDGE_ANOMALY_WATER_FLOW_MAX;
        snprintf(outAnomaly.reason, sizeof(outAnomaly.reason), "High flow rate %.1fL/min exceeded pipe burst threshold (%.1fL/min)", water.water_flow_lmin, EDGE_ANOMALY_WATER_FLOW_MAX);
        strncpy(outAnomaly.device_id, DEVICE_ID_WATER, sizeof(outAnomaly.device_id));
        return true;
    }
    if (water.tank_valid && water.tank_distance_cm > 0.0f) {
        if (water.tank_distance_cm < EDGE_ANOMALY_TANK_DIST_MIN) {
            outAnomaly.is_active = true;
            strncpy(outAnomaly.metric, "tank_distance_cm", sizeof(outAnomaly.metric));
            outAnomaly.observed_value = water.tank_distance_cm;
            outAnomaly.threshold_value = EDGE_ANOMALY_TANK_DIST_MIN;
            snprintf(outAnomaly.reason, sizeof(outAnomaly.reason), "Water tank level near overflow clearance (%.1fcm < %.0fcm)", water.tank_distance_cm, EDGE_ANOMALY_TANK_DIST_MIN);
            strncpy(outAnomaly.device_id, DEVICE_ID_WATER, sizeof(outAnomaly.device_id));
            return true;
        } else if (water.tank_distance_cm > EDGE_ANOMALY_TANK_DIST_MAX) {
            outAnomaly.is_active = true;
            strncpy(outAnomaly.metric, "tank_distance_cm", sizeof(outAnomaly.metric));
            outAnomaly.observed_value = water.tank_distance_cm;
            outAnomaly.threshold_value = EDGE_ANOMALY_TANK_DIST_MAX;
            snprintf(outAnomaly.reason, sizeof(outAnomaly.reason), "Water tank low/empty: clearance exceeds dry limit (%.1fcm > %.0fcm)", water.tank_distance_cm, EDGE_ANOMALY_TANK_DIST_MAX);
            strncpy(outAnomaly.device_id, DEVICE_ID_WATER, sizeof(outAnomaly.device_id));
            return true;
        }
    }

    // C. Environmental Anomaly Checks (DHT11 & MQ-135)
    if (env.dht_valid && env.temperature_c > EDGE_ANOMALY_TEMP_MAX) {
        outAnomaly.is_active = true;
        strncpy(outAnomaly.metric, "temperature_c", sizeof(outAnomaly.metric));
        outAnomaly.observed_value = env.temperature_c;
        outAnomaly.threshold_value = EDGE_ANOMALY_TEMP_MAX;
        snprintf(outAnomaly.reason, sizeof(outAnomaly.reason), "Ambient temperature %.1fC exceeds safety threshold (%.0fC)", env.temperature_c, EDGE_ANOMALY_TEMP_MAX);
        strncpy(outAnomaly.device_id, DEVICE_ID_ENV, sizeof(outAnomaly.device_id));
        return true;
    }
    if (env.gas_valid && !env.warming_up && env.raw_adc > EDGE_ANOMALY_GAS_ADC_MAX) {
        outAnomaly.is_active = true;
        strncpy(outAnomaly.metric, "mq135_raw_adc", sizeof(outAnomaly.metric));
        outAnomaly.observed_value = (float)env.raw_adc;
        outAnomaly.threshold_value = (float)EDGE_ANOMALY_GAS_ADC_MAX;
        snprintf(outAnomaly.reason, sizeof(outAnomaly.reason), "MQ-135 raw ADC count (%d) indicates elevated reducing gas / smoke presence", env.raw_adc);
        strncpy(outAnomaly.device_id, DEVICE_ID_ENV, sizeof(outAnomaly.device_id));
        return true;
    }

    // D. Smart Waste Bin Anomaly Checks (HC-SR04)
    if (waste.bin_valid && waste.fill_level_percent >= EDGE_ANOMALY_BIN_FILL_MAX) {
        outAnomaly.is_active = true;
        strncpy(outAnomaly.metric, "fill_level_percent", sizeof(outAnomaly.metric));
        outAnomaly.observed_value = waste.fill_level_percent;
        outAnomaly.threshold_value = EDGE_ANOMALY_BIN_FILL_MAX;
        snprintf(outAnomaly.reason, sizeof(outAnomaly.reason), "Smart waste bin near capacity (%.1f%% >= %.0f%%) - collection dispatch required", waste.fill_level_percent, EDGE_ANOMALY_BIN_FILL_MAX);
        strncpy(outAnomaly.device_id, DEVICE_ID_WASTE, sizeof(outAnomaly.device_id));
        return true;
    }

    outAnomaly.is_active = false;
    return false;
}

// --- Water Flow Pulse Counter State ---
static volatile unsigned long isrWaterPulseCount = 0;
static unsigned long lastWaterPulseSnap = 0;
static unsigned long lastWaterCalcMillis = 0;
static float cumulativeWaterVolumeM3 = 0.0f;
static float cumulativeWaterLiters = 0.0f;

// --- Offline Telemetry Queue (Ring Buffer) ---
struct OfflinePacket {
    char topic[96];
    char payload[1536];
    bool in_use = false;
};
static OfflinePacket offlineQueue[OFFLINE_QUEUE_SIZE];
static int queueHead = 0;
static int queueTail = 0;
static int queueCount = 0;



// Global cache for OLED display rendering
static ElectricityReadings g_lastElec;
static WaterReadings g_lastWater;
static EnvironmentalReadings g_lastEnv;
static WasteReadings g_lastWaste;
static const char* g_lastIngestionStatus = "INIT";

// =========================================================================================
// OLED SSD1306 MICRO-DRIVER (Zero External Library Required)
// =========================================================================================
#if defined(OLED_ENABLED) && (OLED_ENABLED == 1)

// Standard 5x7 ASCII Font Table
static const uint8_t font5x7[] PROGMEM = {
    0x00, 0x00, 0x00, 0x00, 0x00, // (space)
    0x00, 0x00, 0x5F, 0x00, 0x00, // !
    0x00, 0x07, 0x00, 0x07, 0x00, // "
    0x14, 0x7F, 0x14, 0x7F, 0x14, // #
    0x24, 0x2A, 0x7F, 0x2A, 0x12, // $
    0x23, 0x13, 0x08, 0x64, 0x62, // %
    0x36, 0x49, 0x55, 0x22, 0x50, // &
    0x00, 0x05, 0x03, 0x00, 0x00, // '
    0x00, 0x1C, 0x22, 0x41, 0x00, // (
    0x00, 0x41, 0x22, 0x1C, 0x00, // )
    0x14, 0x08, 0x3E, 0x08, 0x14, // *
    0x08, 0x08, 0x3E, 0x08, 0x08, // +
    0x00, 0x50, 0x30, 0x00, 0x00, // ,
    0x08, 0x08, 0x08, 0x08, 0x08, // -
    0x00, 0x60, 0x60, 0x00, 0x00, // .
    0x20, 0x10, 0x08, 0x04, 0x02, // /
    0x3E, 0x51, 0x49, 0x45, 0x3E, // 0
    0x00, 0x42, 0x7F, 0x40, 0x00, // 1
    0x42, 0x61, 0x51, 0x49, 0x46, // 2
    0x21, 0x41, 0x45, 0x4B, 0x31, // 3
    0x18, 0x14, 0x12, 0x7F, 0x10, // 4
    0x27, 0x45, 0x45, 0x45, 0x39, // 5
    0x3C, 0x4A, 0x49, 0x49, 0x30, // 6
    0x01, 0x71, 0x09, 0x05, 0x03, // 7
    0x36, 0x49, 0x49, 0x49, 0x36, // 8
    0x06, 0x49, 0x49, 0x29, 0x1E, // 9
    0x00, 0x36, 0x36, 0x00, 0x00, // :
    0x00, 0x56, 0x36, 0x00, 0x00, // ;
    0x08, 0x14, 0x22, 0x41, 0x00, // <
    0x14, 0x14, 0x14, 0x14, 0x14, // =
    0x00, 0x41, 0x22, 0x14, 0x08, // >
    0x02, 0x01, 0x51, 0x09, 0x06, // ?
    0x32, 0x49, 0x79, 0x41, 0x3E, // @
    0x7E, 0x11, 0x11, 0x11, 0x7E, // A
    0x7F, 0x49, 0x49, 0x49, 0x36, // B
    0x3E, 0x41, 0x41, 0x41, 0x22, // C
    0x7F, 0x41, 0x41, 0x22, 0x1C, // D
    0x7F, 0x49, 0x49, 0x49, 0x41, // E
    0x7F, 0x09, 0x09, 0x09, 0x01, // F
    0x3E, 0x41, 0x49, 0x49, 0x7A, // G
    0x7F, 0x08, 0x08, 0x08, 0x7F, // H
    0x00, 0x41, 0x7F, 0x41, 0x00, // I
    0x20, 0x40, 0x41, 0x3F, 0x01, // J
    0x7F, 0x08, 0x14, 0x22, 0x41, // K
    0x7F, 0x40, 0x40, 0x40, 0x40, // L
    0x7F, 0x02, 0x0C, 0x02, 0x7F, // M
    0x7F, 0x04, 0x08, 0x10, 0x7F, // N
    0x3E, 0x41, 0x41, 0x41, 0x3E, // O
    0x7F, 0x09, 0x09, 0x09, 0x06, // P
    0x3E, 0x41, 0x51, 0x21, 0x5E, // Q
    0x7F, 0x09, 0x19, 0x29, 0x46, // R
    0x46, 0x49, 0x49, 0x49, 0x31, // S
    0x01, 0x01, 0x7F, 0x01, 0x01, // T
    0x3F, 0x40, 0x40, 0x40, 0x3F, // U
    0x1F, 0x20, 0x40, 0x20, 0x1F, // V
    0x7F, 0x20, 0x18, 0x20, 0x7F, // W
    0x63, 0x14, 0x08, 0x14, 0x63, // X
    0x07, 0x08, 0x70, 0x08, 0x07, // Y
    0x61, 0x51, 0x49, 0x45, 0x43, // Z
    0x00, 0x7F, 0x41, 0x41, 0x00, // [
    0x02, 0x04, 0x08, 0x10, 0x20, // backslash
    0x00, 0x41, 0x41, 0x7F, 0x00, // ]
    0x04, 0x02, 0x01, 0x02, 0x04, // ^
    0x40, 0x40, 0x40, 0x40, 0x40, // _
    0x00, 0x01, 0x02, 0x04, 0x00, // `
    0x20, 0x54, 0x54, 0x54, 0x78, // a
    0x7F, 0x48, 0x44, 0x44, 0x38, // b
    0x38, 0x44, 0x44, 0x44, 0x20, // c
    0x38, 0x44, 0x44, 0x48, 0x7F, // d
    0x38, 0x54, 0x54, 0x54, 0x18, // e
    0x08, 0x7E, 0x09, 0x01, 0x02, // f
    0x0C, 0x52, 0x52, 0x52, 0x3E, // g
    0x7F, 0x08, 0x04, 0x04, 0x78, // h
    0x00, 0x44, 0x7D, 0x40, 0x00, // i
    0x20, 0x40, 0x44, 0x3D, 0x00, // j
    0x7F, 0x10, 0x28, 0x44, 0x00, // k
    0x00, 0x41, 0x7F, 0x40, 0x00, // l
    0x7C, 0x04, 0x18, 0x04, 0x78, // m
    0x7C, 0x08, 0x04, 0x04, 0x78, // n
    0x38, 0x44, 0x44, 0x44, 0x38, // o
    0x7C, 0x14, 0x14, 0x14, 0x08, // p
    0x08, 0x14, 0x14, 0x18, 0x7C, // q
    0x7C, 0x08, 0x04, 0x04, 0x08, // r
    0x48, 0x54, 0x54, 0x54, 0x20, // s
    0x04, 0x3F, 0x44, 0x40, 0x20, // t
    0x3C, 0x40, 0x40, 0x20, 0x7C, // u
    0x1C, 0x20, 0x40, 0x20, 0x1C, // v
    0x3C, 0x40, 0x30, 0x40, 0x3C, // w
    0x44, 0x28, 0x10, 0x28, 0x44, // x
    0x0C, 0x50, 0x50, 0x50, 0x3C, // y
    0x44, 0x64, 0x54, 0x4C, 0x44  // z
};

static uint8_t oledBuffer[128 * 8]; // 128x64 display buffer (1024 bytes)
static bool oledInitialized = false;

static void oledCommand(uint8_t cmd) {
    Wire.beginTransmission(OLED_I2C_ADDRESS);
    Wire.write(0x00); // Command stream
    Wire.write(cmd);
    Wire.endTransmission();
}

static void oledInitDisplay() {
    Wire.begin(OLED_SDA_PIN, OLED_SCL_PIN);
    Wire.setClock(400000); // 400 kHz Fast I2C

    // Probe I2C address
    Wire.beginTransmission(OLED_I2C_ADDRESS);
    if (Wire.endTransmission() != 0) {
        Serial.printf("[OLED] SSD1306 not detected at 0x%02X; skipping screen init.\n", OLED_I2C_ADDRESS);
        oledInitialized = false;
        return;
    }

    // SSD1306 Initialization Sequence
    oledCommand(0xAE); // Display OFF
    oledCommand(0xD5); oledCommand(0x80); // Display clock divide ratio
    oledCommand(0xA8); oledCommand(0x3F); // Multiplex ratio (64)
    oledCommand(0xD3); oledCommand(0x00); // Display offset (0)
    oledCommand(0x40); // Start line 0
    oledCommand(0x8D); oledCommand(0x14); // Enable charge pump
    oledCommand(0x20); oledCommand(0x00); // Horizontal addressing mode
    oledCommand(0xA1); // Segment re-map (A0/A1)
    oledCommand(0xC8); // COM Output scan direction
    oledCommand(0xDA); oledCommand(0x12); // COM pins hardware config
    oledCommand(0x81); oledCommand(0xCF); // Contrast control
    oledCommand(0xD9); oledCommand(0xF1); // Pre-charge period
    oledCommand(0xDB); oledCommand(0x40); // VCOMH deselect level
    oledCommand(0xA4); // Output follows RAM
    oledCommand(0xA6); // Normal display
    oledCommand(0xAF); // Display ON

    memset(oledBuffer, 0x00, sizeof(oledBuffer));
    oledInitialized = true;
    Serial.println("[OLED] 0.96 Inch SSD1306 Display initialized on I2C GPIO21/GPIO22");
}

static void oledClear() {
    if (!oledInitialized) return;
    memset(oledBuffer, 0x00, sizeof(oledBuffer));
}

static void oledDrawChar(int x, int page, char c) {
    if (!oledInitialized || page < 0 || page >= 8 || x < 0 || x > 122) return;
    if (c < 32 || c > 122) c = ' ';
    int fontIndex = (c - 32) * 5;
    for (int i = 0; i < 5; i++) {
        oledBuffer[page * 128 + x + i] = pgm_read_byte(&font5x7[fontIndex + i]);
    }
    oledBuffer[page * 128 + x + 5] = 0x00; // 1px space between characters
}

static void oledDrawString(int x, int page, const char* str) {
    if (!oledInitialized) return;
    int curX = x;
    while (*str && curX <= 122) {
        oledDrawChar(curX, page, *str);
        curX += 6;
        str++;
    }
}

static void oledRender() {
    if (!oledInitialized) return;
    oledCommand(0x21); oledCommand(0); oledCommand(127); // Column 0-127
    oledCommand(0x22); oledCommand(0); oledCommand(7);   // Page 0-7

    for (int i = 0; i < 1024; i += 16) {
        Wire.beginTransmission(OLED_I2C_ADDRESS);
        Wire.write(0x40); // Data stream
        for (int j = 0; j < 16; j++) {
            Wire.write(oledBuffer[i + j]);
        }
        Wire.endTransmission();
    }
}

static void oledUpdateDashboard() {
    if (!oledInitialized) return;
    oledClear();

    // Line 0: Header
    oledDrawString(0, 0, "EstateIQ Edge Gateway");

    // Line 1: Adaptive Reporting Mode & Wi-Fi IP
    char bufLine1[32];
    const char* stateAbbr = (currentReportingState == REPORT_STATE_NORMAL_15M) ? "NORM-15m" :
                            (currentReportingState == REPORT_STATE_ANOMALY_5M) ? "!ANOM-5m!" : "RECOV-5m";
    if (WiFi.status() == WL_CONNECTED) {
        snprintf(bufLine1, sizeof(bufLine1), "%s IP:%s", stateAbbr, WiFi.localIP().toString().c_str());
    } else {
        snprintf(bufLine1, sizeof(bufLine1), "%s WiFi:NoConn", stateAbbr);
    }
    oledDrawString(0, 1, bufLine1);

    // Line 2: AC Electrical Power (PZEM-004T)
    char bufLine2[32];
    if (g_lastElec.valid) {
        snprintf(bufLine2, sizeof(bufLine2), "Pwr:%.2fkW En:%.1fkWh", g_lastElec.active_power_kw, g_lastElec.cumulative_energy_kwh);
    } else {
        snprintf(bufLine2, sizeof(bufLine2), "Pwr: Standby (PZEM)");
    }
    oledDrawString(0, 2, bufLine2);

    // Line 3: Live Ultrasonic Distance / Bin Fill (HC-SR04 / AJ-SR04M)
    char bufLine3[32];
    if (g_lastWaste.bin_valid) {
        snprintf(bufLine3, sizeof(bufLine3), "Bin:%.1fcm (%.0f%%)", g_lastWaste.bin_distance_cm, g_lastWaste.fill_level_percent);
    } else if (g_lastWater.tank_valid) {
        snprintf(bufLine3, sizeof(bufLine3), "Tank:%.1fcm (%.0f%%)", g_lastWater.tank_distance_cm, g_lastWater.tank_level_pct);
    } else {
        snprintf(bufLine3, sizeof(bufLine3), "Sonar: Awaiting Echo");
    }
    oledDrawString(0, 3, bufLine3);

    // Line 4: Water Flow Rate (ZJ-S201)
    char bufLine4[32];
    if (g_lastWater.flow_valid && g_lastWater.water_flow_lmin > 0.0f) {
        snprintf(bufLine4, sizeof(bufLine4), "Flow:%.1fL/m V:%.1fm3", g_lastWater.water_flow_lmin, g_lastWater.cumulative_water_m3);
    } else {
        snprintf(bufLine4, sizeof(bufLine4), "Flow: Standby");
    }
    oledDrawString(0, 4, bufLine4);

    // Line 5: Climate Temp & Humidity (DHT11)
    char bufLine5[32];
    if (g_lastEnv.dht_valid) {
        snprintf(bufLine5, sizeof(bufLine5), "T:%.1fC H:%.0f%% HI:%.1f", g_lastEnv.temperature_c, g_lastEnv.humidity_pct, g_lastEnv.heat_index_c);
    } else {
        snprintf(bufLine5, sizeof(bufLine5), "DHT11: Standby");
    }
    oledDrawString(0, 5, bufLine5);

    // Line 6: Gas & Air Quality (MQ-135)
    char bufLine6[32];
    if (g_lastEnv.gas_valid && g_lastEnv.raw_adc >= 80) {
        snprintf(bufLine6, sizeof(bufLine6), "Gas:%d ADC (%.0fppm)", g_lastEnv.raw_adc, g_lastEnv.co2_estimate_ppm);
    } else {
        snprintf(bufLine6, sizeof(bufLine6), "MQ135: Standby");
    }
    oledDrawString(0, 6, bufLine6);

    // Line 7: Cloud Ingestion Status
    char bufLine7[32];
    snprintf(bufLine7, sizeof(bufLine7), "Cloud: %s [Seq:%lu]", g_lastIngestionStatus, sequenceCounter);
    oledDrawString(0, 7, bufLine7);

    oledRender();
}

#endif // OLED_ENABLED

// =========================================================================================
// WATER FLOW INTERRUPT SERVICE ROUTINE (ZJ-S201 / YF-S201)
// =========================================================================================
void IRAM_ATTR onWaterPulseISR() {
    isrWaterPulseCount++;
}

// =========================================================================================
// TIME SYNCHRONIZATION (Backend REST + NTP Fallback)
// =========================================================================================
bool syncTimeFromBackend() {
    if (WiFi.status() != WL_CONNECTED) return false;
    if (SYSTEM_TIME_ENDPOINT[0] == '\0') return false;
    HTTPClient http;
    http.begin(SYSTEM_TIME_ENDPOINT);
    http.setTimeout(3000);
    int httpCode = http.GET();
    if (httpCode == HTTP_CODE_OK) {
        String payload = http.getString();
        StaticJsonDocument<256> doc;
        DeserializationError err = deserializeJson(doc, payload);
        if (!err && doc.containsKey("utc_timestamp")) {
            const char* ts = doc["utc_timestamp"];
            struct tm t = {0};
            if (sscanf(ts, "%d-%d-%dT%d:%d:%d",
                       &t.tm_year, &t.tm_mon, &t.tm_mday,
                       &t.tm_hour, &t.tm_min, &t.tm_sec) >= 6) {
                t.tm_year -= 1900;
                t.tm_mon -= 1;
                time_t epochTime = mktime(&t);
                struct timeval tv = { .tv_sec = epochTime, .tv_usec = 0 };
                settimeofday(&tv, NULL);
                gatewayBootTimeUtc = epochTime - (millis() / 1000);
                timeIsSynchronized = true;
                Serial.printf("[TIME] Synced UTC clock from EstateIQ backend: %s\n", ts);
                http.end();
                return true;
            }
        }
    }
    http.end();
    return false;
}

bool getISOTimestamp(char* outBuf, size_t bufSize) {
    time_t now = time(nullptr);
    if (now > 1700000000) {
        timeIsSynchronized = true;
        struct tm* timeinfo = gmtime(&now);
        strftime(outBuf, bufSize, "%Y-%m-%dT%H:%M:%SZ", timeinfo);
        return true;
    }
    if (timeIsSynchronized && gatewayBootTimeUtc > 0) {
        time_t calculatedUtc = gatewayBootTimeUtc + (millis() / 1000);
        struct tm* timeinfo = gmtime(&calculatedUtc);
        strftime(outBuf, bufSize, "%Y-%m-%dT%H:%M:%SZ", timeinfo);
        return true;
    }
    return false;
}

// =========================================================================================
// VOLATILE OFFLINE QUEUE MANAGER
// =========================================================================================
void enqueueTelemetry(const char* topic, const char* payload) {
    int index = queueHead;
    strncpy(offlineQueue[index].topic, topic, sizeof(offlineQueue[index].topic) - 1);
    offlineQueue[index].topic[sizeof(offlineQueue[index].topic) - 1] = '\0';
    strncpy(offlineQueue[index].payload, payload, sizeof(offlineQueue[index].payload) - 1);
    offlineQueue[index].payload[sizeof(offlineQueue[index].payload) - 1] = '\0';
    offlineQueue[index].in_use = true;

    queueHead = (queueHead + 1) % OFFLINE_QUEUE_SIZE;
    if (queueCount < OFFLINE_QUEUE_SIZE) {
        queueCount++;
    } else {
        queueTail = (queueTail + 1) % OFFLINE_QUEUE_SIZE; // Drop oldest
    }
    Serial.printf("[QUEUE] Stored packet offline (queue depth: %d/%d)\n", queueCount, OFFLINE_QUEUE_SIZE);
}

bool sendHttpTelemetry(const char* payload) {
    if (WiFi.status() != WL_CONNECTED) return false;
    HTTPClient http;
    http.begin(HTTP_API_ENDPOINT);
    http.addHeader("Content-Type", "application/json");
    http.addHeader("X-Gateway-Key", GATEWAY_API_KEY);
    http.setTimeout(HTTP_REQUEST_TIMEOUT_MS);

    int httpResponseCode = http.POST(payload);
    bool success = false;
    if (httpResponseCode == 200 || httpResponseCode == 201) {
        Serial.printf("[HTTP] Telemetry POST accepted (HTTP %d)\n", httpResponseCode);
        g_lastIngestionStatus = "200 OK";
        success = true;
    } else {
        Serial.printf("[HTTP] Telemetry POST failed (HTTP %d: %s)\n",
                      httpResponseCode, http.errorToString(httpResponseCode).c_str());
        g_lastIngestionStatus = "POST ERR";
    }
    http.end();
    return success;
}

void drainOfflineQueue() {
    if (queueCount == 0) return;
    Serial.printf("[QUEUE] Draining %d buffered offline packets...\n", queueCount);
    while (queueCount > 0) {
        OfflinePacket &item = offlineQueue[queueTail];
        if (item.in_use) {
#if defined(USE_HTTP_INGESTION) && (USE_HTTP_INGESTION == 1)
            bool ok = sendHttpTelemetry(item.payload);
#else
            bool ok = mqttClient.publish(item.topic, item.payload, false);
#endif
            item.in_use = false;
            queueTail = (queueTail + 1) % OFFLINE_QUEUE_SIZE;
            queueCount--;
            if (!ok && WiFi.status() != WL_CONNECTED) {
                Serial.println("[QUEUE] Network interrupted during drain; pausing.");
                break;
            }
            delay(50);
        } else {
            queueTail = (queueTail + 1) % OFFLINE_QUEUE_SIZE;
            queueCount--;
        }
    }
}

// =========================================================================================
// ROBUST WI-FI & NETWORK STATE MACHINE
// =========================================================================================
void onWiFiEvent(WiFiEvent_t event, WiFiEventInfo_t info) {
    if (event != ARDUINO_EVENT_WIFI_STA_DISCONNECTED) return;
    const uint8_t reason = info.wifi_sta_disconnected.reason;
    Serial.printf("[WIFI] Disconnect event reason %u\n", reason);
}

void maintainWiFi() {
    if (WiFi.status() == WL_CONNECTED) {
        if (!wifiReportedConnected) {
            wifiReportedConnected = true;
            Serial.println("========================================================");
            Serial.printf("[WIFI] Connected! Assigned IP: %s | RSSI: %d dBm\n", WiFi.localIP().toString().c_str(), WiFi.RSSI());
            Serial.println("========================================================");
            syncTimeFromBackend();
            configTime(0, 0, "pool.ntp.org", "time.google.com");
#if defined(USE_HTTP_INGESTION) && (USE_HTTP_INGESTION == 1)
            drainOfflineQueue();
#endif
        }
        return;
    }

    wifiReportedConnected = false;
    unsigned long now = millis();
    if (now - lastWifiConnectAttempt > 15000) {
        lastWifiConnectAttempt = now;
        Serial.printf("[WIFI] Connecting to '%s' (backoff: 15000ms)...\n", WIFI_SSID);
        WiFi.disconnect();
        delay(100);
        WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    }
}

void maintainMQTT() {
#if defined(USE_HTTP_INGESTION) && (USE_HTTP_INGESTION == 1)
    return;
#endif
    if (WiFi.status() != WL_CONNECTED || mqttClient.connected()) return;
    unsigned long now = millis();
    if (now - lastMqttAttempt > mqttBackoffMs) {
        lastMqttAttempt = now;
        Serial.printf("[MQTT] Attempting broker connection %s:%d...\n", MQTT_BROKER_HOST, MQTT_BROKER_PORT);
        bool connected = (strlen(MQTT_USERNAME) > 0)
            ? mqttClient.connect(MQTT_CLIENT_ID, MQTT_USERNAME, MQTT_PASSWORD)
            : mqttClient.connect(MQTT_CLIENT_ID);

        if (connected) {
            Serial.println("[MQTT] Connected to broker successfully!");
            mqttBackoffMs = 2000;
            drainOfflineQueue();
        } else {
            Serial.printf("[MQTT] Connection failed, rc=%d\n", mqttClient.state());
            mqttBackoffMs = min(mqttBackoffMs * 2, maxMqttBackoffMs);
        }
    }
}

// =========================================================================================
// CRC16 COMPUTATION FOR MODBUS / PZEM-004T
// =========================================================================================
static uint16_t computeModbusCRC(const uint8_t *buf, uint16_t len) {
    uint16_t crc = 0xFFFF;
    for (uint16_t pos = 0; pos < len; pos++) {
        crc ^= (uint16_t)buf[pos];
        for (int i = 8; i != 0; i--) {
            if ((crc & 0x0001) != 0) {
                crc >>= 1;
                crc ^= 0xA001;
            } else {
                crc >>= 1;
            }
        }
    }
    return crc;
}

// =========================================================================================
// SENSOR 1: PEACEFAIR PZEM-004T AC ENERGY METER (UART2: GPIO16/17)
// =========================================================================================
bool readPZEM004TMeter(ElectricityReadings &out) {
#if defined(PZEM_ENABLED) && (PZEM_ENABLED == 1)
    // Clear residual UART RX buffer
    while (MeterSerial.available()) {
        MeterSerial.read();
    }

    // Standard PZEM-004T v3.0 Query Frame (Function 0x04 Read Input Registers, Address 0x0000, 10 Registers)
    uint8_t queryFrame[8] = { PZEM_SLAVE_ADDR, 0x04, 0x00, 0x00, 0x00, 0x0A, 0x70, 0x0D };
    MeterSerial.write(queryFrame, sizeof(queryFrame));
    MeterSerial.flush();

    // Read 25-byte response frame
    uint8_t resp[25];
    unsigned long startWait = millis();
    int bytesRead = 0;

    while (millis() - startWait < 500 && bytesRead < 25) {
        if (MeterSerial.available()) {
            resp[bytesRead++] = MeterSerial.read();
        }
    }

    if (bytesRead == 25 && resp[0] == PZEM_SLAVE_ADDR && resp[1] == 0x04 && resp[2] == 0x14) {
        // Validate CRC16
        uint16_t expectedCrc = (resp[24] << 8) | resp[23];
        uint16_t calcCrc = computeModbusCRC(resp, 23);

        if (calcCrc == expectedCrc) {
            // Voltage: 0.1V resolution (Reg 0x0000)
            out.voltage_v = (float)((resp[3] << 8) | resp[4]) * 0.1f;

            // Current: 0.001A resolution (Reg 0x0001 - 0x0002, Low word / High word)
            uint32_t rawCurrent = ((uint32_t)resp[7] << 24) | ((uint32_t)resp[8] << 16) | ((uint32_t)resp[5] << 8) | resp[6];
            out.current_a = (float)rawCurrent * 0.001f;

            // Power: 0.1W resolution (Reg 0x0003 - 0x0004) -> converted to kW
            uint32_t rawPower = ((uint32_t)resp[11] << 24) | ((uint32_t)resp[12] << 16) | ((uint32_t)resp[9] << 8) | resp[10];
            out.active_power_kw = ((float)rawPower * 0.1f) / 1000.0f;

            // Energy: 1Wh resolution (Reg 0x0005 - 0x0006) -> converted to kWh
            uint32_t rawEnergy = ((uint32_t)resp[15] << 24) | ((uint32_t)resp[16] << 16) | ((uint32_t)resp[13] << 8) | resp[14];
            out.cumulative_energy_kwh = (float)rawEnergy / 1000.0f;

            // Frequency: 0.1Hz resolution (Reg 0x0007)
            out.frequency_hz = (float)((resp[17] << 8) | resp[18]) * 0.1f;

            // Power Factor: 0.01 resolution (Reg 0x0008)
            out.power_factor = (float)((resp[19] << 8) | resp[20]) * 0.01f;

            out.valid = true;
            out.meter_type = "PZEM-004T v3.0";
            Serial.printf("[SENSOR-PZEM] Voltage: %.1fV | Current: %.3fA | Power: %.3fkW | Energy: %.2fkWh | PF: %.2f | Freq: %.1fHz\n",
                          out.voltage_v, out.current_a, out.active_power_kw, out.cumulative_energy_kwh, out.power_factor, out.frequency_hz);
            return true;
        } else {
            Serial.println("[SENSOR-PZEM] Modbus CRC16 checksum mismatch on packet response.");
        }
    }
#endif
    out.valid = false;
    return false;
}

// =========================================================================================
// SENSOR 2: ZJ-S201 / YF-S201 WATER FLOW PULSE SENSOR (Interrupt on GPIO4)
// =========================================================================================
bool readWaterFlowSensor(WaterReadings &out) {
#if defined(WATER_FLOW_ENABLED) && (WATER_FLOW_ENABLED == 1)
    if (WATER_PULSE_PIN < 0) {
        out.flow_valid = false;
        return false;
    }

    unsigned long now = millis();
    unsigned long elapsedMs = now - lastWaterCalcMillis;
    if (elapsedMs == 0) elapsedMs = 1;

    noInterrupts();
    unsigned long currentPulses = isrWaterPulseCount;
    interrupts();

    unsigned long deltaPulses = currentPulses - lastWaterPulseSnap;
    lastWaterPulseSnap = currentPulses;
    lastWaterCalcMillis = now;

    float deltaLiters = (float)deltaPulses * PULSE_FACTOR_L_PER_PULSE;
    float elapsedMinutes = (float)elapsedMs / 60000.0f;

    float flowRate = deltaLiters / elapsedMinutes;
    out.water_flow_lmin = (flowRate < 0.1f) ? 0.0f : flowRate;

    cumulativeWaterLiters += deltaLiters;
    cumulativeWaterVolumeM3 = cumulativeWaterLiters / 1000.0f;

    out.cumulative_water_m3 = cumulativeWaterVolumeM3;
    out.cumulative_liters = cumulativeWaterLiters;
    out.pulse_count_total = currentPulses;
    out.flow_valid = true;

    if (deltaPulses > 0) {
        Serial.printf("[SENSOR-FLOW] Flow: %.2f L/min | Cumulative: %.3f m3 (%lu pulses)\n",
                      out.water_flow_lmin, out.cumulative_water_m3, currentPulses);
    }
    return true;
#else
    out.flow_valid = false;
    return false;
#endif
}

// =========================================================================================
// SENSOR 3: ULTRASONIC TANK LEVEL SENSOR (JSN-SR04T / AJ-SR04M / HC-SR04)
// =========================================================================================
// Static tracking for smoothing and momentary echo bounce tolerance
static float s_lastKnownDistanceCm = 0.0f;
static float s_lastKnownFillPct = 0.0f;
static unsigned long s_lastValidDistanceMillis = 0;
static int s_consecutiveSonarMisses = 0;

bool readUltrasonicSensor(WaterReadings &out) {
#if defined(AJSR04M_ENABLED) && (AJSR04M_ENABLED == 1)
    if (AJSR04M_TRIG_PIN < 0 || AJSR04M_ECHO_PIN < 0) {
        out.tank_valid = false;
        return false;
    }

    pinMode(AJSR04M_TRIG_PIN, OUTPUT);
    pinMode(AJSR04M_ECHO_PIN, INPUT);

    // Perform up to 3 ultrasonic bursts with median filtering for robust tracking
    float validDists[3];
    int validCount = 0;
    unsigned long lastEchoUs = 0;

    for (int attempt = 0; attempt < 3; attempt++) {
        // 1. Ensure clean LOW state on Trig pin
        digitalWrite(AJSR04M_TRIG_PIN, LOW);
        delayMicroseconds(4);

        // 2. Transmit 15us trigger pulse (universally triggers HC-SR04 & AJ-SR04M / JSN-SR04T)
        digitalWrite(AJSR04M_TRIG_PIN, HIGH);
        delayMicroseconds(15);
        digitalWrite(AJSR04M_TRIG_PIN, LOW);

        // 3. Read echo return pulse (timeout: 35000us = ~6 meters max range)
        unsigned long echoDuration = pulseIn(AJSR04M_ECHO_PIN, HIGH, 35000UL);
        if (echoDuration > 0) {
            float distCm = (echoDuration * 0.0343f) / 2.0f;
            // Physical detection range: 2.0cm to 500.0cm (covers HC-SR04 near field and AJ-SR04M)
            if (distCm >= 2.0f && distCm <= 500.0f) {
                validDists[validCount++] = distCm;
                lastEchoUs = echoDuration;
            }
        }
        if (attempt < 2) delay(25); // Allow transducer acoustic ringing to settle
    }

    if (validCount > 0) {
        float distCm = validDists[0];
        if (validCount == 2) {
            distCm = (validDists[0] + validDists[1]) / 2.0f;
        } else if (validCount >= 3) {
            // Sort 3 samples for median
            if (validDists[0] > validDists[1]) { float tmp = validDists[0]; validDists[0] = validDists[1]; validDists[1] = tmp; }
            if (validDists[1] > validDists[2]) { float tmp = validDists[1]; validDists[1] = validDists[2]; validDists[2] = tmp; }
            if (validDists[0] > validDists[1]) { float tmp = validDists[0]; validDists[0] = validDists[1]; validDists[1] = tmp; }
            distCm = validDists[1];
        }

        // Geometric tank level calculation
        float depth = TANK_TOTAL_DEPTH_CM;
        float blind = TANK_MIN_BLIND_DISTANCE_CM;
        float fillPct = 0.0f;
        if (depth > blind) {
            fillPct = constrain(((depth - distCm) / (depth - blind)) * 100.0f, 0.0f, 100.0f);
        } else {
            fillPct = 50.0f;
        }

        // Small jitter smoothing (< 3cm change)
        if (s_lastKnownDistanceCm > 0.0f && fabs(distCm - s_lastKnownDistanceCm) < 3.0f) {
            distCm = 0.8f * distCm + 0.2f * s_lastKnownDistanceCm;
        }

        s_lastKnownDistanceCm = distCm;
        s_lastKnownFillPct = fillPct;
        s_lastValidDistanceMillis = millis();
        s_consecutiveSonarMisses = 0;

        out.tank_distance_cm = distCm;
        out.tank_level_pct = fillPct;
        out.tank_valid = true;

        Serial.printf("[ULTRASONIC-LIVE] >>> Real Distance Measured: %.1f cm | Tank Level: %.1f%% | Echo: %lu us (Samples: %d/3) <<<\n",
                      out.tank_distance_cm, out.tank_level_pct, lastEchoUs, validCount);
        return true;
    } else {
        // Bridge brief acoustic dropouts (up to 2 misses within 6 seconds)
        if (s_consecutiveSonarMisses < 2 && s_lastKnownDistanceCm > 0.0f && (millis() - s_lastValidDistanceMillis < 6000UL)) {
            s_consecutiveSonarMisses++;
            out.tank_distance_cm = s_lastKnownDistanceCm;
            out.tank_level_pct = s_lastKnownFillPct;
            out.tank_valid = true;
            Serial.printf("[ULTRASONIC-LIVE] Transient echo bounce miss (%d/2), holding last valid: %.1f cm\n",
                          s_consecutiveSonarMisses, s_lastKnownDistanceCm);
            return true;
        }

        s_consecutiveSonarMisses++;
        out.tank_valid = false;
        Serial.printf("[ULTRASONIC] Sensor awaiting echo on Trig: GPIO%d, Echo: GPIO%d (Check wiring, 5V power, or object orientation)\n",
                      AJSR04M_TRIG_PIN, AJSR04M_ECHO_PIN);
    }
#endif
    out.tank_valid = false;
    return false;
}

// =========================================================================================
// SENSOR 3B: HC-SR04 ULTRASONIC SENSOR (SMART WASTE MANAGEMENT BIN)
// Dedicated pins: Trig GPIO 14, Echo GPIO 27 (Divider protected)
// Auto-fallback: If GPIO 14/27 is unpopulated, sonar pulses on GPIO 5/18 auto-route to Waste Bin!
// =========================================================================================
static float s_lastKnownBinDistCm = -1.0f;
static float s_lastKnownBinFillPct = -1.0f;
static unsigned long s_lastValidBinDistanceMillis = 0;
static int s_consecutiveBinSonarMisses = 0;

bool readWasteUltrasonicSensor(WasteReadings &out, const WaterReadings &water) {
#if defined(HCSR04_WASTE_ENABLED) && (HCSR04_WASTE_ENABLED == 1)
    bool dedicatedPinsProbed = false;

    if (HCSR04_WASTE_TRIG_PIN >= 0 && HCSR04_WASTE_ECHO_PIN >= 0) {
        pinMode(HCSR04_WASTE_TRIG_PIN, OUTPUT);
        pinMode(HCSR04_WASTE_ECHO_PIN, INPUT);

        float validDists[3];
        int validCount = 0;
        unsigned long lastEchoUs = 0;

        for (int attempt = 0; attempt < 3; attempt++) {
            digitalWrite(HCSR04_WASTE_TRIG_PIN, LOW);
            delayMicroseconds(4);
            digitalWrite(HCSR04_WASTE_TRIG_PIN, HIGH);
            delayMicroseconds(12);
            digitalWrite(HCSR04_WASTE_TRIG_PIN, LOW);

            unsigned long echoDuration = pulseIn(HCSR04_WASTE_ECHO_PIN, HIGH, 30000UL); // ~5m max
            if (echoDuration > 0) {
                float distCm = (echoDuration * 0.0343f) / 2.0f;
                if (distCm >= 2.0f && distCm <= 450.0f) {
                    validDists[validCount++] = distCm;
                    lastEchoUs = echoDuration;
                }
            }
            if (attempt < 2) delay(20);
        }

        if (validCount > 0) {
            float distCm = validDists[0];
            if (validCount == 2) {
                distCm = (validDists[0] + validDists[1]) / 2.0f;
            } else if (validCount >= 3) {
                if (validDists[0] > validDists[1]) { float tmp = validDists[0]; validDists[0] = validDists[1]; validDists[1] = tmp; }
                if (validDists[1] > validDists[2]) { float tmp = validDists[1]; validDists[1] = validDists[2]; validDists[2] = tmp; }
                if (validDists[0] > validDists[1]) { float tmp = validDists[0]; validDists[0] = validDists[1]; validDists[1] = tmp; }
                distCm = validDists[1];
            }

            float depth = BIN_TOTAL_DEPTH_CM;
            float blind = BIN_MIN_BLIND_DISTANCE_CM;
            float fillPct = 0.0f;
            if (depth > blind) {
                fillPct = constrain(((depth - distCm) / (depth - blind)) * 100.0f, 0.0f, 100.0f);
            } else {
                fillPct = 50.0f;
            }

            if (s_lastKnownBinDistCm > 0.0f && fabs(distCm - s_lastKnownBinDistCm) < 3.0f) {
                distCm = 0.8f * distCm + 0.2f * s_lastKnownBinDistCm;
            }

            s_lastKnownBinDistCm = distCm;
            s_lastKnownBinFillPct = fillPct;
            s_lastValidBinDistanceMillis = millis();
            s_consecutiveBinSonarMisses = 0;

            out.bin_distance_cm = distCm;
            out.fill_level_percent = fillPct;
            out.bin_valid = true;
            out.echo_pin_used = HCSR04_WASTE_ECHO_PIN;

            Serial.printf("[HCSR04-WASTE-LIVE] >>> Real Bin Distance (GPIO %d/%d): %.1f cm | Fill: %.1f%% | Echo: %lu us <<<\n",
                          HCSR04_WASTE_TRIG_PIN, HCSR04_WASTE_ECHO_PIN, out.bin_distance_cm, out.fill_level_percent, lastEchoUs);
            return true;
        }
        dedicatedPinsProbed = true;
    }

    // Auto-detection fallback: If GPIO 14/27 did not return echo, check if user wired HC-SR04 to primary GPIO 5/18
    if (water.tank_valid && water.tank_distance_cm > 0.0f) {
        float distCm = water.tank_distance_cm;
        float depth = BIN_TOTAL_DEPTH_CM;
        float blind = BIN_MIN_BLIND_DISTANCE_CM;
        float fillPct = 0.0f;
        if (depth > blind) {
            fillPct = constrain(((depth - distCm) / (depth - blind)) * 100.0f, 0.0f, 100.0f);
        } else {
            fillPct = 50.0f;
        }

        s_lastKnownBinDistCm = distCm;
        s_lastKnownBinFillPct = fillPct;
        s_lastValidBinDistanceMillis = millis();

        out.bin_distance_cm = distCm;
        out.fill_level_percent = fillPct;
        out.bin_valid = true;
        out.echo_pin_used = AJSR04M_ECHO_PIN;

        Serial.printf("[HCSR04-WASTE-BENCH] >>> Bench Sonar Auto-Routed to Waste Bin (GPIO %d/%d): %.1f cm | Fill: %.1f%% <<<\n",
                      AJSR04M_TRIG_PIN, AJSR04M_ECHO_PIN, out.bin_distance_cm, out.fill_level_percent);
        return true;
    }

    // Bridge brief acoustic dropouts (up to 2 misses within 6 seconds)
    s_consecutiveBinSonarMisses++;
    if (s_lastKnownBinDistCm > 0.0f && (millis() - s_lastValidBinDistanceMillis < 6000UL) && s_consecutiveBinSonarMisses <= 2) {
        out.bin_distance_cm = s_lastKnownBinDistCm;
        out.fill_level_percent = s_lastKnownBinFillPct;
        out.bin_valid = true;
        out.echo_pin_used = dedicatedPinsProbed ? HCSR04_WASTE_ECHO_PIN : AJSR04M_ECHO_PIN;
        return true;
    }
#endif
    out.bin_valid = false;
    return false;
}

// =========================================================================================
// SENSOR 4: DHT11 DIGITAL TEMPERATURE & HUMIDITY SENSOR (1-Wire: GPIO23)
// =========================================================================================
bool readDHT11Sensor(EnvironmentalReadings &out) {
#if defined(DHT11_ENABLED) && (DHT11_ENABLED == 1)
    if (DHT11_PIN < 0) {
        out.dht_valid = false;
        return false;
    }

    uint8_t data[5] = {0, 0, 0, 0, 0};

    // 1. Host Start Signal: Pull LOW for 20ms, then pull HIGH for 30us
    pinMode(DHT11_PIN, OUTPUT);
    digitalWrite(DHT11_PIN, LOW);
    delay(20);
    digitalWrite(DHT11_PIN, HIGH);
    delayMicroseconds(30);

    // 2. Sensor Response: 80us LOW followed by 80us HIGH
    pinMode(DHT11_PIN, INPUT_PULLUP);
    unsigned long timeout = micros();
    while (digitalRead(DHT11_PIN) == HIGH) {
        if (micros() - timeout > 100) return false;
    }
    timeout = micros();
    while (digitalRead(DHT11_PIN) == LOW) {
        if (micros() - timeout > 100) return false;
    }
    timeout = micros();
    while (digitalRead(DHT11_PIN) == HIGH) {
        if (micros() - timeout > 100) return false;
    }

    // 3. Read 40 Data Bits (5 Bytes: Hum_Int, Hum_Dec, Temp_Int, Temp_Dec, Checksum)
    for (int i = 0; i < 40; i++) {
        timeout = micros();
        while (digitalRead(DHT11_PIN) == LOW) {
            if (micros() - timeout > 100) return false;
        }
        unsigned long tStart = micros();
        timeout = micros();
        while (digitalRead(DHT11_PIN) == HIGH) {
            if (micros() - timeout > 100) return false;
        }
        // Pulse > 40us indicates logic bit '1', else '0'
        if ((micros() - tStart) > 40) {
            data[i / 8] |= (1 << (7 - (i % 8)));
        }
    }

    // 4. Parity Checksum Validation
    if (data[4] == ((data[0] + data[1] + data[2] + data[3]) & 0xFF)) {
        out.humidity_pct = (float)data[0] + (float)data[1] * 0.1f;
        out.temperature_c = (float)data[2] + (float)data[3] * 0.1f;

        // NOAA Heat Index Calculation in Celsius
        float T = out.temperature_c;
        float R = out.humidity_pct;
        float c1 = -8.78469475556f;
        float c2 = 1.61139411f;
        float c3 = 2.33854883889f;
        float c4 = -0.14611605f;
        float c5 = -0.012308094f;
        float c6 = -0.0164248277778f;
        float c7 = 0.002211732f;
        float c8 = 0.00072546f;
        float c9 = -0.000003582f;
        out.heat_index_c = c1 + (c2 * T) + (c3 * R) + (c4 * T * R) + (c5 * T * T) +
                          (c6 * R * R) + (c7 * T * T * R) + (c8 * T * R * R) + (c9 * T * T * R * R);

        out.dht_valid = true;
        Serial.printf("[SENSOR-DHT11] Temp: %.1f C | Humidity: %.1f %% | Heat Index: %.1f C\n",
                      out.temperature_c, out.humidity_pct, out.heat_index_c);
        return true;
    } else {
        Serial.println("[SENSOR-DHT11] Checksum error on 40-bit packet stream.");
    }
#endif
    out.dht_valid = false;
    return false;
}

// =========================================================================================
// SENSOR 5: MQ-135 AIR QUALITY & GAS SENSOR (ADC1: GPIO34)
// =========================================================================================
bool readMQ135GasSensor(EnvironmentalReadings &out) {
#if defined(MQ135_ENABLED) && (MQ135_ENABLED == 1)
    if (MQ135_ANALOG_PIN < 0) {
        out.gas_valid = false;
        return false;
    }

    // 16-sample multi-read oversampling for stable ADC conversion
    long adcSum = 0;
    for (int i = 0; i < 16; i++) {
        adcSum += analogRead(MQ135_ANALOG_PIN);
        delayMicroseconds(250);
    }
    int avgAdc = adcSum / 16;
    out.raw_adc = avgAdc;

    // Scale with calibrated voltage divider ratio (10k series / 22k to ground)
    float adcVoltage = (avgAdc / 4095.0f) * 3.3f;
    out.sensor_voltage_v = adcVoltage * MQ135_VOLTAGE_DIVIDER_RATIO;

    // Physical connection check:
    // When no sensor is plugged into GPIO34, ADC reads 0 count (0.00V).
    // An actual powered MQ-135 has an active heater and internal resistance yielding > 0.35V.
    if (avgAdc < 80 || out.sensor_voltage_v < 0.08f) {
        out.gas_valid = false;
        Serial.printf("[SENSOR-MQ135] Floating/unconnected pin on GPIO %d (ADC: %d, %.2fV). Sensor not connected.\n",
                      MQ135_ANALOG_PIN, avgAdc, out.sensor_voltage_v);
        return false;
    }

    // Indicative CO2/gas ppm concentration estimate
    out.co2_estimate_ppm = 400.0f + ((avgAdc / 4095.0f) * 1600.0f);

    unsigned long uptimeSec = millis() / 1000;
    out.warming_up = (uptimeSec < MQ135_WARMUP_PERIOD_SEC);
    out.gas_valid = true;

    Serial.printf("[SENSOR-MQ135] Raw ADC: %d | Voltage: %.2fV | Warmup: %s | Est: %.0f ppm\n",
                  out.raw_adc, out.sensor_voltage_v,
                  out.warming_up ? "WARMING_UP" : "STABILIZED",
                  out.co2_estimate_ppm);
    return true;
#else
    out.gas_valid = false;
    return false;
#endif
}

// =========================================================================================
// ARDUINO SETUP ROUTINE
// =========================================================================================
void setup() {
    Serial.begin(115200);
    snprintf(bootId, sizeof(bootId), "%08lX", static_cast<unsigned long>(esp_random()));
    Serial.printf("[BOOT] Session ID: %s\n", bootId);
    delay(500);

    Serial.println();
    Serial.println("========================================================");
    Serial.println("EstateIQ ESP32 Edge Sensor Gateway Firmware v3.0-ProdIoT");
    Serial.println("========================================================");
    Serial.printf("[CONFIG] Gateway ID: %s | Facility: %s | Building: %s\n",
                  MQTT_CLIENT_ID, FACILITY_ID, BUILDING_ID);
    Serial.printf("[TRANSPORT] Ingestion: %s\n", USE_HTTP_INGESTION ? "Direct HTTP REST" : "MQTT Broker");
    Serial.printf("[ENDPOINT] %s\n", HTTP_API_ENDPOINT);

    // 1. Initialize PZEM-004T UART2
#if defined(PZEM_ENABLED) && (PZEM_ENABLED == 1)
    MeterSerial.begin(PZEM_BAUD_RATE, SERIAL_8N1, PZEM_RX_PIN, PZEM_TX_PIN);
    Serial.printf("[PZEM-004T] Initialized UART2 on RX:%d, TX:%d at %d baud\n",
                  PZEM_RX_PIN, PZEM_TX_PIN, PZEM_BAUD_RATE);
#endif

    // 2. Initialize Water Flow Sensor Interrupt on GPIO 4
#if defined(WATER_FLOW_ENABLED) && (WATER_FLOW_ENABLED == 1)
    if (WATER_PULSE_PIN >= 0) {
        pinMode(WATER_PULSE_PIN, INPUT_PULLUP);
        attachInterrupt(digitalPinToInterrupt(WATER_PULSE_PIN), onWaterPulseISR, RISING);
        Serial.printf("[WATER-FLOW] ZJ-S201 Hall pulse interrupt attached on GPIO %d\n", WATER_PULSE_PIN);
    }
#endif

    // 3. Initialize Ultrasonic Sonar Pins (Trig: GPIO5, Echo: GPIO18)
#if defined(AJSR04M_ENABLED) && (AJSR04M_ENABLED == 1)
    if (AJSR04M_TRIG_PIN >= 0 && AJSR04M_ECHO_PIN >= 0) {
        pinMode(AJSR04M_TRIG_PIN, OUTPUT);
        digitalWrite(AJSR04M_TRIG_PIN, LOW);
        pinMode(AJSR04M_ECHO_PIN, INPUT);
        Serial.printf("[ULTRASONIC] Sonar initialized: Trig=GPIO%d, Echo=GPIO%d\n",
                      AJSR04M_TRIG_PIN, AJSR04M_ECHO_PIN);
    }
#endif

    // 4. Initialize DHT11 Data Pin
#if defined(DHT11_ENABLED) && (DHT11_ENABLED == 1)
    if (DHT11_PIN >= 0) {
        pinMode(DHT11_PIN, INPUT_PULLUP);
        Serial.printf("[DHT11] Digital Temp/Humidity initialized on GPIO %d\n", DHT11_PIN);
    }
#endif

    // 5. Initialize MQ-135 Gas Sensor Analog Pin
#if defined(MQ135_ENABLED) && (MQ135_ENABLED == 1)
    if (MQ135_ANALOG_PIN >= 0) {
        pinMode(MQ135_ANALOG_PIN, INPUT);
        analogReadResolution(12);
        analogSetAttenuation(ADC_11db);
        Serial.printf("[MQ-135] Gas sensor initialized on ADC1 GPIO %d (Divider ratio: %.2fx)\n",
                      MQ135_ANALOG_PIN, MQ135_VOLTAGE_DIVIDER_RATIO);
    }
#endif

    // 6. Initialize 0.96 Inch OLED Display
#if defined(OLED_ENABLED) && (OLED_ENABLED == 1)
    oledInitDisplay();
#endif

    // 7. Initialize Wi-Fi
    WiFi.mode(WIFI_STA);
    WiFi.onEvent(onWiFiEvent);
    Serial.printf("[WIFI] Connecting to SSID: '%s'...\n", WIFI_SSID);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

#if !defined(USE_HTTP_INGESTION) || (USE_HTTP_INGESTION == 0)
    mqttClient.setServer(MQTT_BROKER_HOST, MQTT_BROKER_PORT);
#endif
}

// =========================================================================================
// MAIN EXECUTION LOOP
// =========================================================================================
void loop() {
    maintainWiFi();
    maintainMQTT();

#if !defined(USE_HTTP_INGESTION) || (USE_HTTP_INGESTION == 0)
    if (mqttClient.connected()) {
        mqttClient.loop();
    }
#endif

    unsigned long now = millis();

    // =================================================================================
    // 1. HIGH-FREQUENCY INTERNAL SENSOR ACQUISITION & EDGE ANOMALY DETECTION
    // =================================================================================
    if (now - lastAcquisitionMillis >= SENSOR_ACQUISITION_INTERVAL_MS) {
        lastAcquisitionMillis = now;

        // A. Sample physical hardware sensors at continuous high-frequency rate
        ElectricityReadings elec;
        readPZEM004TMeter(elec);
        g_lastElec = elec;

        WaterReadings water;
        readWaterFlowSensor(water);
        readUltrasonicSensor(water);
        g_lastWater = water;

        EnvironmentalReadings env;
        readDHT11Sensor(env);
        readMQ135GasSensor(env);
        g_lastEnv = env;

        WasteReadings waste;
        readWasteUltrasonicSensor(waste, water);
        g_lastWaste = waste;

        // PHYSICAL DISTANCE CHANGE TRIGGER:
        // When ultrasonic distance changes significantly (>= 3.0cm), immediately dispatch telemetry
        static float s_lastDispatchedDistCm = -999.0f;
        if (water.tank_valid) {
            if (s_lastDispatchedDistCm < 0.0f || fabs(water.tank_distance_cm - s_lastDispatchedDistCm) >= 3.0f) {
                Serial.printf("[ULTRASONIC-EVENT] Physical distance moved: %.1f cm -> %.1f cm (delta >= 3cm); triggering immediate telemetry dispatch!\n",
                              s_lastDispatchedDistCm, water.tank_distance_cm);
                s_lastDispatchedDistCm = water.tank_distance_cm;
                triggerImmediateAnomalyReport = true;
            }
        }

        static float s_lastDispatchedBinDistCm = -999.0f;
        if (waste.bin_valid) {
            if (s_lastDispatchedBinDistCm < 0.0f || fabs(waste.bin_distance_cm - s_lastDispatchedBinDistCm) >= 3.0f) {
                Serial.printf("[HCSR04-EVENT] Physical bin distance moved: %.1f cm -> %.1f cm (delta >= 3cm); triggering immediate telemetry dispatch!\n",
                              s_lastDispatchedBinDistCm, waste.bin_distance_cm);
                s_lastDispatchedBinDistCm = waste.bin_distance_cm;
                triggerImmediateAnomalyReport = true;
            }
        }

        // B. Evaluate Edge Anomaly Detection
        EdgeAnomalyState detectedAnomaly;
        bool hasAnomaly = evaluateEdgeAnomalies(elec, water, env, waste, detectedAnomaly);

        if (hasAnomaly) {
            g_edgeAnomaly.persistence_counter++;
            bool isExtreme = (detectedAnomaly.threshold_value > 0.0f && detectedAnomaly.observed_value > detectedAnomaly.threshold_value * 1.5f) ||
                             (detectedAnomaly.threshold_value > 0.0f && detectedAnomaly.observed_value < detectedAnomaly.threshold_value * 0.7f);

            if (isExtreme || g_edgeAnomaly.persistence_counter >= EDGE_ANOMALY_PERSISTENCE_COUNT) {
                if (currentReportingState != REPORT_STATE_ANOMALY_5M) {
                    currentReportingState = REPORT_STATE_ANOMALY_5M;
                    recoveryConfirmationCount = 0;
                    g_edgeAnomaly = detectedAnomaly;
                    g_edgeAnomaly.is_active = true;
                    g_edgeAnomaly.first_detected_ms = now;
                    triggerImmediateAnomalyReport = true; // IMMEDIATE EVENT BROADCAST!
                    Serial.printf("\n[ADAPTIVE-REPORTING] *** EDGE ANOMALY CONFIRMED: %s ***\n", g_edgeAnomaly.reason);
                    Serial.println("[ADAPTIVE-REPORTING] Cadence shifted: NORMAL_15M -> ANOMALY_5M (Immediate event transmitted)");
                } else {
                    g_edgeAnomaly = detectedAnomaly;
                    g_edgeAnomaly.is_active = true;
                }
            }
        } else {
            g_edgeAnomaly.persistence_counter = 0;

            if (currentReportingState == REPORT_STATE_ANOMALY_5M) {
                // Return to normal range -> begin recovery confirmation
                currentReportingState = REPORT_STATE_RECOVERY_5M;
                recoveryConfirmationCount = 0;
                Serial.println("\n[ADAPTIVE-REPORTING] Sensor readings returned to normal range. State -> RECOVERY_5M (Observing recovery confirmation...)");
            }
        }

        // C. Refresh Local OLED Screen with latest state
#if defined(OLED_ENABLED) && (OLED_ENABLED == 1)
        oledUpdateDashboard();
#endif
    }

    // =================================================================================
    // 2. ADAPTIVE TELEMETRY REPORTING CADENCE & NETWORK TRANSMISSION
    // =================================================================================
    unsigned long activeReportingInterval = (currentReportingState == REPORT_STATE_NORMAL_15M)
        ? REPORT_INTERVAL_NORMAL_ACTIVE_MS
        : REPORT_INTERVAL_ANOMALY_ACTIVE_MS;

    bool reportDue = (now - lastReportMillis >= activeReportingInterval) || triggerImmediateAnomalyReport;

    if (reportDue) {
        lastReportMillis = now;
        bool wasImmediate = triggerImmediateAnomalyReport;
        triggerImmediateAnomalyReport = false;
        sequenceCounter++;

        // If currently in recovery state, verify consecutive normal cycles
        if (currentReportingState == REPORT_STATE_RECOVERY_5M) {
            recoveryConfirmationCount++;
            Serial.printf("[ADAPTIVE-REPORTING] Recovery confirmation cycle %d/%d completed.\n", recoveryConfirmationCount, RECOVERY_CONFIRMATION_CYCLES);
            if (recoveryConfirmationCount >= RECOVERY_CONFIRMATION_CYCLES) {
                currentReportingState = REPORT_STATE_NORMAL_15M;
                g_edgeAnomaly.is_active = false;
                Serial.println("[ADAPTIVE-REPORTING] *** RECOVERY FULLY VERIFIED *** Returning to NORMAL_15M reporting cadence.");
            }
        }

        char timestampIso[32];
        if (!getISOTimestamp(timestampIso, sizeof(timestampIso))) {
            Serial.println("[TIME] Clock not yet synchronized; skipping telemetry to avoid fabricated timestamps.");
            return;
        }

        const char* stateStr = (currentReportingState == REPORT_STATE_NORMAL_15M) ? "NORMAL_15M" :
                               (currentReportingState == REPORT_STATE_ANOMALY_5M) ? "ANOMALY_5M" : "RECOVERY_5M";
        unsigned long intervalSec = activeReportingInterval / 1000UL;

        Serial.printf("[ADAPTIVE-REPORTING] Reporting Telemetry [State: %s | Cadence: %lus | Immediate: %s | Seq: %lu]\n",
                      stateStr, intervalSec, wasImmediate ? "YES" : "NO", sequenceCounter);

        ElectricityReadings elec = g_lastElec;
        WaterReadings water = g_lastWater;
        EnvironmentalReadings env = g_lastEnv;

        // =================================================================================
        // PACKET 1: AC ELECTRICAL METROLOGY (PZEM-004T / MODBUS)
        // ONLY transmitted when PZEM-004T hardware is physically connected & returning valid data!
        // =================================================================================
        if (elec.valid) {
            StaticJsonDocument<1536> docElec;
            docElec["schema_version"] = "1.0";
            char msgIdElec[48];
            snprintf(msgIdElec, sizeof(msgIdElec), "MSG_%s_%s_%lu", DEVICE_ID_ELEC, bootId, sequenceCounter);
            docElec["message_id"] = msgIdElec;
            docElec["gateway_id"] = MQTT_CLIENT_ID;
            docElec["boot_id"] = bootId;
            docElec["device_id"] = DEVICE_ID_ELEC;
            docElec["auth_token"] = GATEWAY_API_KEY;
            docElec["facility_id"] = FACILITY_ID;
            docElec["building_id"] = BUILDING_ID;
            docElec["source_type"] = "real_sensor";
            docElec["event_timestamp"] = timestampIso;
            docElec["sent_timestamp"] = timestampIso;
            docElec["sequence_number"] = sequenceCounter;

            docElec["reporting_state"] = stateStr;
            docElec["reporting_interval_sec"] = intervalSec;
            docElec["next_report_expected_sec"] = intervalSec;
            docElec["is_anomaly"] = (g_edgeAnomaly.is_active && strcmp(g_edgeAnomaly.device_id, DEVICE_ID_ELEC) == 0);

            if (g_edgeAnomaly.is_active && strcmp(g_edgeAnomaly.device_id, DEVICE_ID_ELEC) == 0) {
                docElec["anomaly_origin"] = "edge";
                docElec["anomaly_metric"] = g_edgeAnomaly.metric;
                docElec["anomaly_observed_value"] = g_edgeAnomaly.observed_value;
                docElec["anomaly_threshold"] = g_edgeAnomaly.threshold_value;
                docElec["anomaly_reason"] = g_edgeAnomaly.reason;
            }

            JsonArray metricsElec = docElec.createNestedArray("metrics");
            JsonObject m1 = metricsElec.createNestedObject();
            m1["metric"] = "voltage_v"; m1["value"] = elec.voltage_v; m1["unit"] = "V"; m1["quality"] = "good";

            JsonObject m2 = metricsElec.createNestedObject();
            m2["metric"] = "current_a"; m2["value"] = elec.current_a; m2["unit"] = "A"; m2["quality"] = "good";

            JsonObject m3 = metricsElec.createNestedObject();
            m3["metric"] = "active_power_kw"; m3["value"] = elec.active_power_kw; m3["unit"] = "kW"; m3["quality"] = "good";

            JsonObject m4 = metricsElec.createNestedObject();
            m4["metric"] = "cumulative_energy_kwh"; m4["value"] = elec.cumulative_energy_kwh; m4["unit"] = "kWh"; m4["quality"] = "good";

            JsonObject m5 = metricsElec.createNestedObject();
            m5["metric"] = "power_factor"; m5["value"] = elec.power_factor; m5["unit"] = "ratio"; m5["quality"] = "good";

            JsonObject m6 = metricsElec.createNestedObject();
            m6["metric"] = "frequency_hz"; m6["value"] = elec.frequency_hz; m6["unit"] = "Hz"; m6["quality"] = "good";

            char bufferElec[1536];
            serializeJson(docElec, bufferElec);
            Serial.printf("[PUB-ELEC] Transmitting live PZEM packet (%.2f kW, %.1f V) via HTTP\n", elec.active_power_kw, elec.voltage_v);
#if defined(USE_HTTP_INGESTION) && (USE_HTTP_INGESTION == 1)
            if (!sendHttpTelemetry(bufferElec)) enqueueTelemetry(MQTT_TOPIC_ELEC, bufferElec);
#else
            if (!mqttClient.publish(MQTT_TOPIC_ELEC, bufferElec, false)) enqueueTelemetry(MQTT_TOPIC_ELEC, bufferElec);
#endif
        } else {
            Serial.println("[ELEC-STANDBY] PZEM meter not connected/idle; skipping METER-BLOCK-B-001 packet.");
        }

        // =================================================================================
        // PACKET 2: WATER NODE (ZJ-S201 FLOW + ULTRASONIC TANK)
        // ONLY transmitted when ultrasonic sensor OR water flow sensor is physically valid!
        // =================================================================================
        if (water.tank_valid || water.flow_valid) {
            StaticJsonDocument<1536> docWater;
            docWater["schema_version"] = "1.0";
            char msgIdWater[48];
            snprintf(msgIdWater, sizeof(msgIdWater), "MSG_%s_%s_%lu", DEVICE_ID_WATER, bootId, sequenceCounter);
            docWater["message_id"] = msgIdWater;
            docWater["gateway_id"] = MQTT_CLIENT_ID;
            docWater["boot_id"] = bootId;
            docWater["device_id"] = DEVICE_ID_WATER;
            docWater["auth_token"] = GATEWAY_API_KEY;
            docWater["facility_id"] = FACILITY_ID;
            docWater["building_id"] = BUILDING_ID;
            docWater["source_type"] = "real_sensor";
            docWater["event_timestamp"] = timestampIso;
            docWater["sent_timestamp"] = timestampIso;
            docWater["sequence_number"] = sequenceCounter;

            docWater["reporting_state"] = stateStr;
            docWater["reporting_interval_sec"] = intervalSec;
            docWater["next_report_expected_sec"] = intervalSec;
            docWater["is_anomaly"] = (g_edgeAnomaly.is_active && strcmp(g_edgeAnomaly.device_id, DEVICE_ID_WATER) == 0);

            if (g_edgeAnomaly.is_active && strcmp(g_edgeAnomaly.device_id, DEVICE_ID_WATER) == 0) {
                docWater["anomaly_origin"] = "edge";
                docWater["anomaly_metric"] = g_edgeAnomaly.metric;
                docWater["anomaly_observed_value"] = g_edgeAnomaly.observed_value;
                docWater["anomaly_threshold"] = g_edgeAnomaly.threshold_value;
                docWater["anomaly_reason"] = g_edgeAnomaly.reason;
            }

            JsonArray metricsWater = docWater.createNestedArray("metrics");

            // 1. Ultrasonic Distance & Tank Metrics
            if (water.tank_valid) {
                float distVal = round(water.tank_distance_cm * 10.0f) / 10.0f;
                float fillVal = round(water.tank_level_pct * 10.0f) / 10.0f;

                JsonObject w4 = metricsWater.createNestedObject();
                w4["metric"] = "tank_distance_cm"; w4["value"] = distVal; w4["unit"] = "cm"; w4["quality"] = "good";

                JsonObject w5 = metricsWater.createNestedObject();
                w5["metric"] = "tank_level_pct"; w5["value"] = fillVal; w5["unit"] = "%"; w5["quality"] = "good";

                JsonObject w_alias = metricsWater.createNestedObject();
                w_alias["metric"] = "distance_cm"; w_alias["value"] = distVal; w_alias["unit"] = "cm"; w_alias["quality"] = "good";

                // Flat top-level fields for maximum compatibility
                docWater["tank_distance_cm"] = distVal;
                docWater["tank_level_pct"] = fillVal;
                docWater["distance_cm"] = distVal;
            }

            // 2. Water Flow Sensor Metrics
            if (water.flow_valid) {
                JsonObject w1 = metricsWater.createNestedObject();
                w1["metric"] = "water_flow_lmin"; w1["value"] = water.water_flow_lmin; w1["unit"] = "L/min"; w1["quality"] = "good";

                JsonObject w2 = metricsWater.createNestedObject();
                w2["metric"] = "cumulative_water_m3"; w2["value"] = water.cumulative_water_m3; w2["unit"] = "m3"; w2["quality"] = "good";

                JsonObject w3 = metricsWater.createNestedObject();
                w3["metric"] = "water_cumulative_liters"; w3["value"] = water.cumulative_liters; w3["unit"] = "L"; w3["quality"] = "good";
            }

            char bufferWater[1536];
            serializeJson(docWater, bufferWater);
            Serial.printf("[PUB-WATER] Transmitting real water packet seq=%lu (tank_valid=%d, dist=%.1f cm) via HTTP\n",
                          sequenceCounter, water.tank_valid ? 1 : 0, water.tank_distance_cm);
#if defined(USE_HTTP_INGESTION) && (USE_HTTP_INGESTION == 1)
            if (!sendHttpTelemetry(bufferWater)) enqueueTelemetry(MQTT_TOPIC_WATER, bufferWater);
#else
            if (!mqttClient.publish(MQTT_TOPIC_WATER, bufferWater, false)) enqueueTelemetry(MQTT_TOPIC_WATER, bufferWater);
#endif
        } else {
            Serial.println("[WATER-STANDBY] Sonar / Flow sensor not connected; skipping WATER-BLOCK-B-001 packet.");
        }

        // =================================================================================
        // PACKET 4: SMART WASTE BIN NODE (HC-SR04 ULTRASONIC SONAR)
        // ONLY transmitted when HC-SR04 sensor is physically valid!
        // =================================================================================
        WasteReadings waste = g_lastWaste;
        if (waste.bin_valid) {
            StaticJsonDocument<1536> docWaste;
            docWaste["schema_version"] = "1.0";
            char msgIdWaste[48];
            snprintf(msgIdWaste, sizeof(msgIdWaste), "MSG_%s_%s_%lu", DEVICE_ID_WASTE, bootId, sequenceCounter);
            docWaste["message_id"] = msgIdWaste;
            docWaste["gateway_id"] = MQTT_CLIENT_ID;
            docWaste["boot_id"] = bootId;
            docWaste["device_id"] = DEVICE_ID_WASTE;
            docWaste["auth_token"] = GATEWAY_API_KEY;
            docWaste["facility_id"] = FACILITY_ID;
            docWaste["building_id"] = BUILDING_ID;
            docWaste["source_type"] = "real_sensor";
            docWaste["event_timestamp"] = timestampIso;
            docWaste["sent_timestamp"] = timestampIso;
            docWaste["sequence_number"] = sequenceCounter;

            docWaste["reporting_state"] = stateStr;
            docWaste["reporting_interval_sec"] = intervalSec;
            docWaste["next_report_expected_sec"] = intervalSec;
            docWaste["is_anomaly"] = (g_edgeAnomaly.is_active && strcmp(g_edgeAnomaly.device_id, DEVICE_ID_WASTE) == 0);

            if (g_edgeAnomaly.is_active && strcmp(g_edgeAnomaly.device_id, DEVICE_ID_WASTE) == 0) {
                docWaste["anomaly_origin"] = "edge";
                docWaste["anomaly_metric"] = g_edgeAnomaly.metric;
                docWaste["anomaly_observed_value"] = g_edgeAnomaly.observed_value;
                docWaste["anomaly_threshold"] = g_edgeAnomaly.threshold_value;
                docWaste["anomaly_reason"] = g_edgeAnomaly.reason;
            }

            float binDistVal = round(waste.bin_distance_cm * 10.0f) / 10.0f;
            float binFillVal = round(waste.fill_level_percent * 10.0f) / 10.0f;

            // Flat top-level compatibility fields
            docWaste["bin_distance_cm"] = binDistVal;
            docWaste["fill_level_percent"] = binFillVal;
            docWaste["fill_level_pct"] = binFillVal;

            JsonArray metricsWaste = docWaste.createNestedArray("metrics");
            JsonObject m1 = metricsWaste.createNestedObject();
            m1["metric"] = "bin_distance_cm"; m1["value"] = binDistVal; m1["unit"] = "cm"; m1["quality"] = "good";

            JsonObject m2 = metricsWaste.createNestedObject();
            m2["metric"] = "fill_level_percent"; m2["value"] = binFillVal; m2["unit"] = "%"; m2["quality"] = "good";

            JsonObject m3 = metricsWaste.createNestedObject();
            m3["metric"] = "fill_level_pct"; m3["value"] = binFillVal; m3["unit"] = "%"; m3["quality"] = "good";

            char bufferWaste[1536];
            serializeJson(docWaste, bufferWaste);
            Serial.printf("[PUB-WASTE] Transmitting live HC-SR04 waste packet (dist=%.1f cm, fill=%.1f%%) via HTTP\n",
                          binDistVal, binFillVal);
#if defined(USE_HTTP_INGESTION) && (USE_HTTP_INGESTION == 1)
            if (!sendHttpTelemetry(bufferWaste)) enqueueTelemetry(MQTT_TOPIC_WASTE, bufferWaste);
#else
            if (!mqttClient.publish(MQTT_TOPIC_WASTE, bufferWaste, false)) enqueueTelemetry(MQTT_TOPIC_WASTE, bufferWaste);
#endif
        } else {
            Serial.println("[WASTE-STANDBY] HC-SR04 Sonar not connected; skipping WASTE-BLOCK-B-001 packet.");
        }

        // =================================================================================
        // PACKET 3: ENVIRONMENTAL NODE (MQ-135 GAS + DHT11 CLIMATE)
        // ONLY transmitted when MQ-135 or DHT11 is physically connected!
        // =================================================================================
        if ((env.gas_valid && env.raw_adc >= 80) || env.dht_valid) {
            StaticJsonDocument<1536> docEnv;
            docEnv["schema_version"] = "1.0";
            char msgIdEnv[48];
            snprintf(msgIdEnv, sizeof(msgIdEnv), "MSG_%s_%s_%lu", DEVICE_ID_ENV, bootId, sequenceCounter);
            docEnv["message_id"] = msgIdEnv;
            docEnv["gateway_id"] = MQTT_CLIENT_ID;
            docEnv["boot_id"] = bootId;
            docEnv["device_id"] = DEVICE_ID_ENV;
            docEnv["auth_token"] = GATEWAY_API_KEY;
            docEnv["facility_id"] = FACILITY_ID;
            docEnv["building_id"] = BUILDING_ID;
            docEnv["source_type"] = "real_sensor";
            docEnv["event_timestamp"] = timestampIso;
            docEnv["sent_timestamp"] = timestampIso;
            docEnv["sequence_number"] = sequenceCounter;

            docEnv["reporting_state"] = stateStr;
            docEnv["reporting_interval_sec"] = intervalSec;
            docEnv["next_report_expected_sec"] = intervalSec;
            docEnv["is_anomaly"] = (g_edgeAnomaly.is_active && strcmp(g_edgeAnomaly.device_id, DEVICE_ID_ENV) == 0);

            if (g_edgeAnomaly.is_active && strcmp(g_edgeAnomaly.device_id, DEVICE_ID_ENV) == 0) {
                docEnv["anomaly_origin"] = "edge";
                docEnv["anomaly_metric"] = g_edgeAnomaly.metric;
                docEnv["anomaly_observed_value"] = g_edgeAnomaly.observed_value;
                docEnv["anomaly_threshold"] = g_edgeAnomaly.threshold_value;
                docEnv["anomaly_reason"] = g_edgeAnomaly.reason;
            }

            JsonArray metricsEnv = docEnv.createNestedArray("metrics");
            if (env.gas_valid && env.raw_adc >= 80) {
                JsonObject e1 = metricsEnv.createNestedObject();
                e1["metric"] = "mq135_raw_adc"; e1["value"] = env.raw_adc; e1["unit"] = "count"; e1["quality"] = "good";

                JsonObject e2 = metricsEnv.createNestedObject();
                e2["metric"] = "mq135_voltage_v"; e2["value"] = env.sensor_voltage_v; e2["unit"] = "V"; e2["quality"] = "good";

                JsonObject e3 = metricsEnv.createNestedObject();
                e3["metric"] = "mq135_co2_estimate_ppm"; e3["value"] = env.co2_estimate_ppm; e3["unit"] = "ppm (sensor estimate)"; e3["quality"] = "good";

                JsonObject e4 = metricsEnv.createNestedObject();
                e4["metric"] = "mq135_warmup_status"; e4["value"] = env.warming_up ? 0 : 1; e4["unit"] = "status"; e4["quality"] = "good";
            }

            if (env.dht_valid) {
                JsonObject d1 = metricsEnv.createNestedObject();
                d1["metric"] = "temperature_c"; d1["value"] = env.temperature_c; d1["unit"] = "°C"; d1["quality"] = "good";

                JsonObject d2 = metricsEnv.createNestedObject();
                d2["metric"] = "humidity_pct"; d2["value"] = env.humidity_pct; d2["unit"] = "%"; d2["quality"] = "good";

                JsonObject d3 = metricsEnv.createNestedObject();
                d3["metric"] = "heat_index_c"; d3["value"] = env.heat_index_c; d3["unit"] = "°C"; d3["quality"] = "good";
            }

            char bufferEnv[1536];
            serializeJson(docEnv, bufferEnv);
            Serial.printf("[PUB-ENV] Transmitting live environmental packet (gas_valid=%d, dht_valid=%d) via HTTP\n",
                          env.gas_valid ? 1 : 0, env.dht_valid ? 1 : 0);
#if defined(USE_HTTP_INGESTION) && (USE_HTTP_INGESTION == 1)
            if (!sendHttpTelemetry(bufferEnv)) enqueueTelemetry(MQTT_TOPIC_ENV, bufferEnv);
#else
            if (!mqttClient.publish(MQTT_TOPIC_ENV, bufferEnv, false)) enqueueTelemetry(MQTT_TOPIC_ENV, bufferEnv);
#endif
        } else {
            Serial.println("[ENV-STANDBY] MQ-135 / DHT11 not connected; skipping ENV-BLOCK-B-001 packet.");
        }

        // Final OLED dashboard refresh with latest cloud ingestion status
#if defined(OLED_ENABLED) && (OLED_ENABLED == 1)
        oledUpdateDashboard();
#endif
    }
}
