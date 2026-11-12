/*
 * EstateIQ ESP32 Edge Sensor Gateway Firmware v3.0-ProductionIoT
 * =========================================================================================
 * Full Hardware Support for Multi-Modal Facility Intelligence:
 * 1. Peacefair PZEM-004T 10A / 100A AC Metrology Monitor (UART2: GPIO16/17)
 * 2. ZJ-S201 / YF-S201 Water Flow Sensor (Interrupt Pulse Counter: GPIO26 in supplied wiring)
 * 3. JSN-SR04T / AJ-SR04M / HC-SR04 Waterproof Ultrasonic Sonar (Trig: GPIO5, Echo: GPIO18)
 * 4. DHT11 Digital Temperature & Humidity Module (1-Wire: GPIO4 in supplied wiring)
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
#include <stdlib.h>
#include <esp_wifi.h>
#include "DHT.h"

#include "config.h"

DHT dhtSensor(DHT11_PIN, DHT11);
#if defined(DHT11_PIN_ALT) && (DHT11_PIN_ALT >= 0)
DHT dhtSensorAlt(DHT11_PIN_ALT, DHT11);
#endif

#ifndef WATER_PULSE_PIN_ALT
#define WATER_PULSE_PIN_ALT -1
#endif

#ifndef DHT11_PIN_ALT
#define DHT11_PIN_ALT -1
#endif

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
    unsigned long last_update_ms = 0;
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
    float adc_pin_voltage_v = 0.0f;
    float sensor_voltage_v = 0.0f;
    float rs_kohm = 0.0f;
    float rs_ro_ratio = 1.0f;
    float estimated_ppm = 0.0f;
    int air_quality_level = 0; // 0=Clean, 1=Moderate, 2=Harmful Gases/Pollutants, 3=Smoke Alert
    char air_quality_label[24] = "Clean Air";
    bool gas_alert = false;
    bool smoke_detected = false;
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
    // Electrical anomaly checks handled by dedicated Node #2 (PZEM-004T)

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
    if (env.gas_valid && (env.raw_adc >= MQ135_POLLUTED_ADC_MAX || env.gas_alert || env.smoke_detected)) {
        outAnomaly.is_active = true;
        if (env.smoke_detected || env.raw_adc >= MQ135_SMOKE_ADC_THRESHOLD) {
            strncpy(outAnomaly.metric, "smoke_alert", sizeof(outAnomaly.metric));
            outAnomaly.observed_value = (float)env.raw_adc;
            outAnomaly.threshold_value = (float)MQ135_SMOKE_ADC_THRESHOLD;
            snprintf(outAnomaly.reason, sizeof(outAnomaly.reason), "CRITICAL: Smoke / hazardous combustion fumes detected! (ADC %d, ~%.0f PPM)", env.raw_adc, env.estimated_ppm);
        } else {
            strncpy(outAnomaly.metric, "harmful_gas", sizeof(outAnomaly.metric));
            outAnomaly.observed_value = (float)env.raw_adc;
            outAnomaly.threshold_value = (float)MQ135_POLLUTED_ADC_MAX;
            snprintf(outAnomaly.reason, sizeof(outAnomaly.reason), "Harmful gases & pollutants detected: %s (ADC %d, ~%.0f PPM)", env.air_quality_label, env.raw_adc, env.estimated_ppm);
        }
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
static uint8_t s_oledAddress = OLED_I2C_ADDRESS;
static uint8_t s_oledColOffset = 0;
static uint8_t oledConsecutiveErrors = 0;
static uint8_t oledCurrentPage = 0;
static unsigned long oledLastPageFlip = 0;

static void oledCommand(uint8_t cmd) {
    Wire.beginTransmission(s_oledAddress);
    Wire.write(0x00); // Command stream
    Wire.write(cmd);
    Wire.endTransmission();
}

static void oledCommand2(uint8_t c1, uint8_t c2) {
    Wire.beginTransmission(s_oledAddress);
    Wire.write(0x00);
    Wire.write(c1);
    Wire.write(c2);
    Wire.endTransmission();
}

static void oledInitDisplay() {
    // 1. Hardware Power-On Stabilization Delay
    delay(150);

    // 2. Release Wire before touching the pins, then recover a stuck I2C bus.
    // I2C is open-drain: drive LOW to pulse a line and switch to INPUT_PULLUP
    // to release it HIGH. Never drive an I2C line HIGH push-pull.
    Wire.end();
    delay(5);
    pinMode(OLED_SCL_PIN, INPUT_PULLUP);
    pinMode(OLED_SDA_PIN, INPUT_PULLUP);
    for (int i = 0; i < 9; i++) {
        pinMode(OLED_SCL_PIN, OUTPUT_OPEN_DRAIN);
        digitalWrite(OLED_SCL_PIN, LOW);
        delayMicroseconds(5);
        pinMode(OLED_SCL_PIN, INPUT_PULLUP);
        delayMicroseconds(5);
    }
    // Generate STOP condition
    pinMode(OLED_SDA_PIN, OUTPUT_OPEN_DRAIN);
    digitalWrite(OLED_SDA_PIN, LOW);
    delayMicroseconds(5);
    pinMode(OLED_SCL_PIN, INPUT_PULLUP);
    delayMicroseconds(5);
    pinMode(OLED_SDA_PIN, INPUT_PULLUP);
    delayMicroseconds(5);

    // 3. Initialize I2C Bus at 100 kHz with a finite timeout so a stuck
    // display/bus cannot wedge the entire sensor and Wi-Fi loop indefinitely.
    Wire.begin(OLED_SDA_PIN, OLED_SCL_PIN);
    Wire.setClock(100000);
    Wire.setTimeOut(50);

    // 4. Auto-detect OLED I2C Address (0x3C vs 0x3D)
    uint8_t detected = 0;
    const uint8_t candidateAddresses[] = { OLED_I2C_ADDRESS, OLED_I2C_ADDRESS_ALT, 0x3C, 0x3D };
    for (size_t i = 0; i < sizeof(candidateAddresses); i++) {
        Wire.beginTransmission(candidateAddresses[i]);
        if (Wire.endTransmission() == 0) {
            detected = candidateAddresses[i];
            break;
        }
    }

    // Fallback: If not found, probe swapped I2C pin configuration (SDA=22, SCL=21)
    if (detected == 0) {
        Wire.end();
        Wire.begin(OLED_SCL_PIN, OLED_SDA_PIN);
        Wire.setClock(100000);
        Wire.setTimeOut(50);
        for (size_t i = 0; i < sizeof(candidateAddresses); i++) {
            Wire.beginTransmission(candidateAddresses[i]);
            if (Wire.endTransmission() == 0) {
                detected = candidateAddresses[i];
                Serial.println("[OLED] Notice: Display detected on swapped pins (SDA=22, SCL=21)");
                break;
            }
        }
    }

    if (detected == 0) {
        Serial.printf("[OLED] Display not detected on I2C bus (checked 0x3C, 0x3D); will auto-retry in background.\n");
        oledInitialized = false;
        return;
    }

    s_oledAddress = detected;
    Serial.printf("[OLED] Connected to display at I2C address 0x%02X\n", s_oledAddress);

    // 5. Universal Hardware Initialization Sequence (Dual SSD1306 & SH1106 charge-pump activation)
    oledCommand(0xAE); // Display OFF (sleep mode)
    oledCommand2(0xD5, 0x80); // Display clock divide ratio/oscillator
    oledCommand2(0xA8, 0x3F); // Multiplex ratio (64 lines)
    oledCommand2(0xD3, 0x00); // Display offset = 0
    oledCommand(0x40);        // Start line = 0

    // DUAL CHARGE PUMP ENABLE:
    // - SSD1306 requires 0x8D 0x14 (Charge pump 7.5V)
    // - SH1106 requires 0xAD 0x8B (DC-DC Converter 9.0V) & 0x32 (Pump mode)
    oledCommand2(0x8D, 0x14); // SSD1306 DC-DC Charge Pump ON
    oledCommand2(0xAD, 0x8B); // SH1106 DC-DC Converter ON (9.0V)
    oledCommand(0x32);        // SH1106 DC-DC pump mode

    oledCommand2(0x20, 0x02); // Page addressing mode (compatible with SSD1306 & SH1106)
    oledCommand(0xA1);        // Segment re-map: col 127 mapped to SEG0
    oledCommand(0xC8);        // COM Output scan direction: remapped mode
    oledCommand2(0xDA, 0x12); // COM pins hardware config
    oledCommand2(0x81, 0xFF); // Contrast control: Maximum brightness (0xFF / 255)
    oledCommand2(0xD9, 0xF1); // Pre-charge period (fast discharge / charge)
    oledCommand2(0xDB, 0x40); // VCOMH deselect level (~0.77xVcc)
    oledCommand(0x2E);        // Deactivate horizontal scroll
    oledCommand(0xA4);        // Entire display ON follows RAM content (not forced all ON)
    oledCommand(0xA6);        // Normal display (non-inverted)

    // 6. Clear physical GDDRAM with zero bytes across all 8 pages
    for (uint8_t p = 0; p < 8; p++) {
        Wire.beginTransmission(s_oledAddress);
        Wire.write(0x00);
        Wire.write(0xB0 + p); // Set page
        Wire.write(0x00);     // Low col = 0
        Wire.write(0x10);     // High col = 0
        Wire.endTransmission();
        for (uint8_t c = 0; c < 128; c += 16) {
            Wire.beginTransmission(s_oledAddress);
            Wire.write(0x40);
            for (uint8_t k = 0; k < 16; k++) {
                Wire.write(0x00);
            }
            Wire.endTransmission();
        }
    }

    // 7. Turn Display ON
    oledCommand(0xAF); // Display ON (clean bright pixels)
    memset(oledBuffer, 0x00, sizeof(oledBuffer));
    oledInitialized = true;
    oledConsecutiveErrors = 0;
    Serial.printf("[OLED] Display turned ON successfully (I2C 0x%02X, Max Contrast 0xFF)!\n", s_oledAddress);
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
    if (!oledInitialized || page < 0 || page >= 8 || !str) return;
    int curX = x;
    while (*str && curX <= 122) {
        oledDrawChar(curX, page, *str);
        curX += 6;
        str++;
    }
}

// Guaranteed line fitter: bounds any string to maximum 21 characters so it NEVER exceeds the 128px screen width
static void oledDrawLineClamped(int page, const char* str) {
    if (!oledInitialized || page < 0 || page >= 8 || !str) return;
    char clean[22];
    strncpy(clean, str, 21);
    clean[21] = '\0';
    oledDrawString(0, page, clean);
}

// Draw a compact, legible Wi-Fi status icon in the header's top-right corner.
// The custom font contains ASCII only, so draw the tick/X directly in the buffer.
static void oledDrawPixel(int x, int y) {
    if (x < 0 || x >= 128 || y < 0 || y >= 64) return;
    oledBuffer[(y / 8) * 128 + x] |= (uint8_t)(1U << (y % 8));
}

static void oledDrawWifiIcon(bool connected) {
    if (!oledInitialized) return;
    if (connected) {
        oledDrawPixel(114, 3);
        oledDrawPixel(115, 4);
        oledDrawPixel(116, 5);
        oledDrawPixel(117, 4);
        oledDrawPixel(118, 3);
        oledDrawPixel(119, 2);
        oledDrawPixel(120, 1);
        oledDrawPixel(121, 0);
    } else {
        for (int i = 0; i < 8; i++) {
            oledDrawPixel(114 + i, i);
            oledDrawPixel(121 - i, i);
        }
    }
}

static void oledDrawHeader() {
    oledDrawLineClamped(0, "ESTATEIQ");
    oledDrawString(78, 0, "WiFi:");
    oledDrawWifiIcon(WiFi.status() == WL_CONNECTED);
}

// Ultra-reliable page-by-page OLED renderer with auto-recovery
static void oledRender() {
    if (!oledInitialized) return;

    bool hasError = false;
    for (uint8_t page = 0; page < 8; page++) {
        // Set page and column origin on each slice
        Wire.beginTransmission(s_oledAddress);
        Wire.write(0x00);
        Wire.write(0xB0 + page);
        Wire.write(0x00 | (s_oledColOffset & 0x0F));
        Wire.write(0x10 | ((s_oledColOffset >> 4) & 0x0F));
        if (Wire.endTransmission() != 0) {
            hasError = true;
            break;
        }

        const uint8_t* pPage = &oledBuffer[page * 128];
        for (uint8_t col = 0; col < 128; col += 16) {
            Wire.beginTransmission(s_oledAddress);
            Wire.write(0x40);
            for (uint8_t k = 0; k < 16; k++) {
                Wire.write(pPage[col + k]);
            }
            if (Wire.endTransmission() != 0) {
                hasError = true;
                break;
            }
        }
        if (hasError) break;
    }

    if (hasError) {
        oledConsecutiveErrors++;
        if (oledConsecutiveErrors >= 3) {
            Serial.println("[OLED-WARN] I2C transmission glitch detected; auto-recovering display bus...");
            oledInitialized = false;
            delay(50);
            oledInitDisplay();
        }
    } else {
        oledConsecutiveErrors = 0;
        // Reassert display-on during normal refresh. This recovers a controller
        // that accepted I2C data but entered display-off/sleep state.
        oledCommand(0xAF);
    }
}

static void oledUpdateDashboard() {
    if (!oledInitialized) {
        static unsigned long s_lastOledInitRetry = 0;
        if (millis() - s_lastOledInitRetry >= 2000UL) {
            s_lastOledInitRetry = millis();
            oledInitDisplay();
        }
        if (!oledInitialized) return;
    }

    // Redraw the complete buffer every second. Rotate three focused pages so
    // all sensor values, including the full PZEM sample, remain readable.
    const unsigned long now = millis();
    if (oledLastPageFlip == 0) oledLastPageFlip = now;
    if (now - oledLastPageFlip >= 3000UL) {
        oledCurrentPage = (oledCurrentPage + 1) % 3;
        oledLastPageFlip = now;
        Serial.printf("[OLED] Switched to display page %u/3\n", (unsigned int)oledCurrentPage + 1U);
    }

    oledClear();
    oledDrawHeader();
    char lineBuf[32];

    if (oledCurrentPage == 0) {
        if (g_lastWaste.bin_valid) {
            snprintf(lineBuf, sizeof(lineBuf), "Bin: %.1f cm", g_lastWaste.bin_distance_cm);
        } else {
            snprintf(lineBuf, sizeof(lineBuf), "Bin: Standby");
        }
        oledDrawLineClamped(2, lineBuf);

        if (g_lastWater.tank_valid) snprintf(lineBuf, sizeof(lineBuf), "Tank: %.1f cm", g_lastWater.tank_distance_cm);
        else snprintf(lineBuf, sizeof(lineBuf), "Tank: Standby");
        oledDrawLineClamped(4, lineBuf);

        if (g_lastWater.flow_valid) snprintf(lineBuf, sizeof(lineBuf), "Flow: %.1f L/min", g_lastWater.water_flow_lmin);
        else snprintf(lineBuf, sizeof(lineBuf), "Flow: Standby");
        oledDrawLineClamped(6, lineBuf);
        oledDrawString(108, 7, "1/3");
    } else if (oledCurrentPage == 1) {
        if (g_lastEnv.dht_valid) snprintf(lineBuf, sizeof(lineBuf), "Temp: %.1f C", g_lastEnv.temperature_c);
        else snprintf(lineBuf, sizeof(lineBuf), "Temp: Standby");
        oledDrawLineClamped(2, lineBuf);

        if (g_lastEnv.dht_valid) snprintf(lineBuf, sizeof(lineBuf), "Humidity: %.1f%%", g_lastEnv.humidity_pct);
        else snprintf(lineBuf, sizeof(lineBuf), "Humidity: Standby");
        oledDrawLineClamped(4, lineBuf);

        if (!g_lastEnv.gas_valid) {
            snprintf(lineBuf, sizeof(lineBuf), "MQ135: Standby");
        } else if (g_lastEnv.smoke_detected) {
            snprintf(lineBuf, sizeof(lineBuf), "MQ135: SMOKE ALERT");
        } else if (g_lastEnv.gas_alert) {
            snprintf(lineBuf, sizeof(lineBuf), "MQ135: GAS ALERT");
        } else if (g_lastEnv.warming_up) {
            snprintf(lineBuf, sizeof(lineBuf), "MQ135: Warming up");
        } else {
            snprintf(lineBuf, sizeof(lineBuf), "Air: %s", g_lastEnv.air_quality_label);
        }
        oledDrawLineClamped(6, lineBuf);
        oledDrawString(108, 7, "2/3");
    } else {
        const bool pzemFresh = g_lastElec.valid && g_lastElec.last_update_ms != 0 &&
                               (now - g_lastElec.last_update_ms) <= 12000UL;
        if (pzemFresh) snprintf(lineBuf, sizeof(lineBuf), "PZEM: %.1fV %.3fA", g_lastElec.voltage_v, g_lastElec.current_a);
        else snprintf(lineBuf, sizeof(lineBuf), "PZEM: waiting for data");
        oledDrawLineClamped(2, lineBuf);

        if (pzemFresh) snprintf(lineBuf, sizeof(lineBuf), "Power: %.0fW PF:%.2f", g_lastElec.active_power_kw * 1000.0f, g_lastElec.power_factor);
        else snprintf(lineBuf, sizeof(lineBuf), "Power: --  PF: --");
        oledDrawLineClamped(4, lineBuf);

        if (pzemFresh) snprintf(lineBuf, sizeof(lineBuf), "E:%.3fkWh F:%.1fHz", g_lastElec.cumulative_energy_kwh, g_lastElec.frequency_hz);
        else snprintf(lineBuf, sizeof(lineBuf), "Energy: waiting");
        oledDrawLineClamped(6, lineBuf);
        oledDrawString(108, 7, "3/3");
    }

    oledRender();
}

#endif // OLED_ENABLED

// =========================================================================================
// WATER FLOW INTERRUPT SERVICE ROUTINE (ZJ-S201 / YF-S201)
// =========================================================================================
static volatile unsigned long s_lastWaterPulseUs = 0;
void IRAM_ATTR onWaterPulseISR() {
    unsigned long nowUs = micros();
    // 1500us debounce (filters switch bounce / contact noise while supporting up to 600 Hz / ~80 L/min)
    if (nowUs - s_lastWaterPulseUs >= 1500UL) {
        isrWaterPulseCount++;
        s_lastWaterPulseUs = nowUs;
    }
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
    // Fallback: Use deterministic current date (2026-11-10T00:00:00Z) + millis uptime
    // so edge anomalies and offline queues are never dropped when time sync is pending.
    time_t baseEpoch = 1794268800; // ~2026-11-10T00:00:00Z
    time_t fallbackUtc = baseEpoch + (millis() / 1000);
    struct tm* timeinfo = gmtime(&fallbackUtc);
    strftime(outBuf, bufSize, "%Y-%m-%dT%H:%M:%SZ", timeinfo);
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

// ---------------- Peer PZEM-004T Synchronization (Node #2) ----------------
static unsigned long g_lastPeerPzemSyncMillis = 0;
static char g_lastPeerPzemSampleAt[40] = "";

static float peerJsonFloat(JsonVariantConst value) {
    // The dedicated PZEM node's /api/data currently serializes values as
    // display strings (for example "241.2" or "--"). Accept both strings
    // and numeric JSON values so the optional direct-LAN path works too.
    if (!value.is<const char*>()) return value.as<float>();
    const char* text = value.as<const char*>();
    if (!text || !text[0] || strcmp(text, "--") == 0) return NAN;
    char* end = nullptr;
    float parsed = strtof(text, &end);
    return (end != text && *end == '\0') ? parsed : NAN;
}

static bool isNewPeerPzemSample(const char* sampleAt) {
    // The backend's latest-reading endpoint provides this timestamp. Keeping
    // it lets us distinguish a fresh meter packet from a cached old response.
    if (!sampleAt || sampleAt[0] == '\0') return false;
    if (strncmp(g_lastPeerPzemSampleAt, sampleAt, sizeof(g_lastPeerPzemSampleAt)) == 0) return false;
    strncpy(g_lastPeerPzemSampleAt, sampleAt, sizeof(g_lastPeerPzemSampleAt) - 1);
    g_lastPeerPzemSampleAt[sizeof(g_lastPeerPzemSampleAt) - 1] = '\0';
    return true;
}

static void syncPeerPzemFromNetwork() {
    unsigned long now = millis();
    if (g_lastElec.last_update_ms != 0 && (now - g_lastElec.last_update_ms) > 12000UL) {
        g_lastElec.valid = false;
    }
    if (WiFi.status() != WL_CONNECTED) return;
    if (now - g_lastPeerPzemSyncMillis < PEER_PZEM_SYNC_INTERVAL_MS) return;
    g_lastPeerPzemSyncMillis = now;

    HTTPClient http;
    bool syncSuccess = false;

    // Option A: Direct LAN Peer Query if Node #2 IP is configured
    if (strlen(PEER_PZEM_ESP32_IP) > 0) {
        char peerUrl[96];
        snprintf(peerUrl, sizeof(peerUrl), "http://%s/api/data", PEER_PZEM_ESP32_IP);
        http.begin(peerUrl);
        http.setTimeout(1200);
        int code = http.GET();
        if (code == 200) {
            String payload = http.getString();
            StaticJsonDocument<512> pDoc;
            DeserializationError err = deserializeJson(pDoc, payload);
            if (!err) {
                float newVoltage = peerJsonFloat(pDoc["voltage"]);
                float newCurrent = peerJsonFloat(pDoc["current"]);
                float newPower = peerJsonFloat(pDoc["power"]);
                float newEnergy = peerJsonFloat(pDoc["energy"]);
                float newFrequency = peerJsonFloat(pDoc["frequency"]);
                float newPf = peerJsonFloat(pDoc["pf"]);
                const bool validDirectSample = pDoc["connected"].as<bool>() &&
                    isfinite(newVoltage) && newVoltage >= 80.0f && newVoltage <= 280.0f &&
                    isfinite(newCurrent) && newCurrent >= 0.0f && newCurrent <= 100.0f &&
                    isfinite(newPower) && newPower >= 0.0f && newPower <= 28000.0f &&
                    isfinite(newEnergy) && newEnergy >= 0.0f &&
                    isfinite(newFrequency) && newFrequency >= 45.0f && newFrequency <= 65.0f &&
                    isfinite(newPf) && newPf >= 0.0f && newPf <= 1.0f;
                if (validDirectSample) {
                    g_lastElec.valid = true;
                    g_lastElec.voltage_v = newVoltage;
                    g_lastElec.current_a = newCurrent;
                    g_lastElec.active_power_kw = newPower / 1000.0f;
                    g_lastElec.cumulative_energy_kwh = newEnergy;
                    g_lastElec.frequency_hz = newFrequency;
                    g_lastElec.power_factor = newPf;
                    g_lastElec.last_update_ms = now;
                    syncSuccess = true;
                } else {
                    g_lastElec.valid = false;
                }
            }
        }
        http.end();
    }

    // Option B: Shared EstateIQ Backend Relay (automatic zero-config sync)
    if (!syncSuccess) {
        http.begin(PEER_METER_ENDPOINT);
        http.setTimeout(1500);
        int code = http.GET();
        if (code == 200) {
            String payload = http.getString();
            StaticJsonDocument<768> bDoc;
            DeserializationError err = deserializeJson(bDoc, payload);
            if (!err && bDoc.containsKey("telemetry")) {
                JsonObject tel = bDoc["telemetry"].as<JsonObject>();
                if (tel.containsKey("active_power_kw") || tel.containsKey("voltage_v")) {
                    float newVoltage = tel["voltage_v"] | (tel["voltage"] | 0.0f);
                    float newCurrent = tel["current_a"] | (tel["current"] | 0.0f);
                    float newPowerKw = tel["active_power_kw"] | (tel["power_kw"] | 0.0f);
                    float newEnergy = tel["cumulative_energy_kwh"] | (tel["energy_kwh"] | 0.0f);
                    if (isfinite(newVoltage) && newVoltage >= 80.0f && newVoltage <= 280.0f &&
                        isfinite(newCurrent) && newCurrent >= 0.0f && newCurrent <= 100.0f &&
                        isfinite(newPowerKw) && newPowerKw >= 0.0f && newPowerKw <= 28.0f &&
                        isfinite(newEnergy) && newEnergy >= 0.0f) {
                        const char* sampleAt = bDoc["last_sample_at"] | "";
                        const bool newSample = isNewPeerPzemSample(sampleAt);
                        if (newSample) g_lastElec.last_update_ms = now;
                        g_lastElec.voltage_v = newVoltage;
                        g_lastElec.current_a = newCurrent;
                        g_lastElec.active_power_kw = newPowerKw;
                        g_lastElec.cumulative_energy_kwh = newEnergy;
                        g_lastElec.power_factor = tel["power_factor"] | 0.0f;
                        g_lastElec.frequency_hz = tel["frequency_hz"] | 0.0f;
                        g_lastElec.valid = newSample ||
                            (g_lastElec.last_update_ms != 0 && (now - g_lastElec.last_update_ms) <= 12000UL);
                        syncSuccess = g_lastElec.valid;
                    }
                }
            }
        }
        http.end();
    }

    if (syncSuccess) {
        Serial.printf("[PZEM-PEER] Live sample: %.1fV %.3fA %.1fW %.3fkWh PF %.2f %.1fHz\n",
                      g_lastElec.voltage_v, g_lastElec.current_a,
                      g_lastElec.active_power_kw * 1000.0f,
                      g_lastElec.cumulative_energy_kwh,
                      g_lastElec.power_factor, g_lastElec.frequency_hz);
    }
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

        // Auto-extract peer PZEM-004T metrology readings piggybacked in backend response
        String resp = http.getString();
        if (resp.length() > 0) {
            StaticJsonDocument<512> doc;
            DeserializationError err = deserializeJson(doc, resp);
            if (!err && doc.containsKey("peer_meter")) {
                JsonObject pm = doc["peer_meter"];
                if (pm["valid"].as<bool>()) {
                    float newPowerKw = pm["power_kw"].as<float>();
                    float newVoltage = pm["voltage_v"].as<float>();
                    float newCurrent = pm["current_a"].as<float>();
                    float newEnergy = pm["energy_kwh"].as<float>();
                    if (isfinite(newVoltage) && newVoltage >= 80.0f && newVoltage <= 280.0f &&
                        isfinite(newCurrent) && newCurrent >= 0.0f && newCurrent <= 100.0f &&
                        isfinite(newPowerKw) && newPowerKw >= 0.0f && newPowerKw <= 28.0f &&
                        isfinite(newEnergy) && newEnergy >= 0.0f) {
                        const char* sampleAt = pm["last_sample_at"] | "";
                        const bool newSample = isNewPeerPzemSample(sampleAt);
                        if (newSample) {
                            g_lastElec.voltage_v = newVoltage;
                            g_lastElec.current_a = newCurrent;
                            g_lastElec.active_power_kw = newPowerKw;
                            g_lastElec.cumulative_energy_kwh = newEnergy;
                            g_lastElec.last_update_ms = millis();
                        }
                        g_lastElec.valid = newSample ||
                            (g_lastElec.last_update_ms != 0 && (millis() - g_lastElec.last_update_ms) <= 12000UL);
                    }
                }
            }
        }
    } else {
        Serial.printf("[HTTP] Telemetry POST failed (HTTP %d: %s)\n",
                      httpResponseCode, http.errorToString(httpResponseCode).c_str());
        g_lastIngestionStatus = "POST ERR";
    }
    http.end();
    return success;
}

void drainOfflineQueue() {
    static unsigned long lastQueueDrainMillis = 0;
    if (queueCount == 0 || WiFi.status() != WL_CONNECTED) return;

    // Flush one item per interval. A long backlog must not monopolize loop()
    // and leave the OLED frozen while Wi-Fi/backend connectivity recovers.
    const unsigned long now = millis();
    if (now - lastQueueDrainMillis < 5000UL) return;
    lastQueueDrainMillis = now;

    OfflinePacket &item = offlineQueue[queueTail];
    if (item.in_use) {
#if defined(USE_HTTP_INGESTION) && (USE_HTTP_INGESTION == 1)
        bool ok = sendHttpTelemetry(item.payload);
#else
        bool ok = mqttClient.publish(item.topic, item.payload, false);
#endif
        if (!ok) {
            Serial.printf("[QUEUE] Retry pending; packet retained (queue depth: %d/%d).\n",
                          queueCount, OFFLINE_QUEUE_SIZE);
            return;
        }
    }

    item.in_use = false;
    queueTail = (queueTail + 1) % OFFLINE_QUEUE_SIZE;
    queueCount--;
    Serial.printf("[QUEUE] One buffered packet sent; remaining: %d/%d.\n",
                  queueCount, OFFLINE_QUEUE_SIZE);
}

// =========================================================================================
// ROBUST WI-FI & NETWORK STATE MACHINE
// =========================================================================================
void onWiFiEvent(WiFiEvent_t event, WiFiEventInfo_t info) {
    if (event == ARDUINO_EVENT_WIFI_STA_DISCONNECTED) {
        wifiReportedConnected = false;
        const uint8_t reason = info.wifi_sta_disconnected.reason;
        const char* reasonDesc = "Unknown";
        if (reason == 201) reasonDesc = "NO_AP_FOUND (Hotspot must be set to 2.4 GHz band, not 5 GHz)";
        else if (reason == 36) reasonDesc = "AUTH_EXPIRED / BEACON_TIMEOUT (Weak signal or phone sleep)";
        else if (reason == 202) reasonDesc = "AUTH_FAIL (Incorrect Wi-Fi password)";
        else if (reason == 15) reasonDesc = "4WAY_HANDSHAKE_TIMEOUT (Signal drop during auth)";
        else if (reason == 2) reasonDesc = "AUTH_EXPIRE";
        Serial.printf("[WIFI] Disconnected (Reason %u: %s).\n", reason, reasonDesc);
    }
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
        }
        return;
    }

    wifiReportedConnected = false;
    unsigned long now = millis();
    if (now - lastWifiConnectAttempt > 20000) {
        lastWifiConnectAttempt = now;
        Serial.printf("[WIFI] Re-attempting connection to '%s' (status: %d)...\n", WIFI_SSID, (int)WiFi.status());
        WiFi.disconnect();
        delay(150);
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
        } else {
            Serial.printf("[MQTT] Connection failed, rc=%d\n", mqttClient.state());
            mqttBackoffMs = min(mqttBackoffMs * 2, maxMqttBackoffMs);
        }
    }
}

// =========================================================================================
// NOTE: PZEM-004T AC Electricity Meter is hosted on dedicated ESP32 Node #2
// (See: hardware/esp32/firmware_pzem/main/main.ino)
// =========================================================================================

// =========================================================================================
// SENSOR 2: ZJ-S201 / YF-S201 WATER FLOW PULSE SENSOR (pin selected in config.h)
// =========================================================================================
bool readWaterFlowSensor(WaterReadings &out) {
#if defined(WATER_FLOW_ENABLED) && (WATER_FLOW_ENABLED == 1)
    if (WATER_PULSE_PIN < 0 && WATER_PULSE_PIN_ALT < 0) {
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

    float flowRate = (elapsedMinutes > 0.0f) ? (deltaLiters / elapsedMinutes) : 0.0f;
    out.water_flow_lmin = (flowRate < 0.05f) ? 0.0f : flowRate;

    cumulativeWaterLiters += deltaLiters;
    cumulativeWaterVolumeM3 = cumulativeWaterLiters / 1000.0f;

    out.cumulative_water_m3 = cumulativeWaterVolumeM3;
    out.cumulative_liters = cumulativeWaterLiters;
    out.pulse_count_total = currentPulses;
    out.flow_valid = true;

    if (deltaPulses > 0) {
        Serial.printf("[WATER-FLOW] Active Flow: %.2f L/min | +%lu pulses | Total: %.3f L (%lu total pulses)\n",
                      out.water_flow_lmin, deltaPulses, cumulativeWaterLiters, currentPulses);
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

// Helper: 3-burst ultrasonic distance measurement with sound speed compensation
static float sampleSonicDistanceCm(int trigPin, int echoPin, float speedCmPerUs) {
    if (trigPin < 0 || echoPin < 0) return -1.0f;
    pinMode(trigPin, OUTPUT);
    pinMode(echoPin, INPUT);

    float validDists[3];
    int validCount = 0;

    for (int attempt = 0; attempt < 3; attempt++) {
        digitalWrite(trigPin, LOW);
        delayMicroseconds(4);
        digitalWrite(trigPin, HIGH);
        delayMicroseconds(12);
        digitalWrite(trigPin, LOW);

        unsigned long echoUs = pulseIn(echoPin, HIGH, 30000UL); // ~5m max range
        if (echoUs > 0) {
            float dist = (echoUs * speedCmPerUs) / 2.0f;
            if (dist >= 2.0f && dist <= 450.0f) {
                validDists[validCount++] = dist;
            }
        }
        if (attempt < 2) delay(18); // Transducer acoustic settle
    }

    if (validCount == 0) return -1.0f;
    if (validCount == 1) return validDists[0];
    if (validCount == 2) return (validDists[0] + validDists[1]) / 2.0f;

    // Median of 3
    if (validDists[0] > validDists[1]) { float tmp = validDists[0]; validDists[0] = validDists[1]; validDists[1] = tmp; }
    if (validDists[1] > validDists[2]) { float tmp = validDists[1]; validDists[1] = validDists[2]; validDists[2] = tmp; }
    if (validDists[0] > validDists[1]) { float tmp = validDists[0]; validDists[0] = validDists[1]; validDists[1] = tmp; }
    return validDists[1];
}

bool readUltrasonicSensor(WaterReadings &out) {
#if defined(AJSR04M_ENABLED) && (AJSR04M_ENABLED == 1)
    if (AJSR04M_TRIG_PIN < 0 || AJSR04M_ECHO_PIN < 0) {
        out.tank_valid = false;
        return false;
    }

    float ambientT = 20.0f;
    if (g_lastEnv.dht_valid && g_lastEnv.temperature_c >= 0.0f && g_lastEnv.temperature_c <= 55.0f) {
        ambientT = g_lastEnv.temperature_c;
    }
    float speedSound = (331.3f + 0.606f * ambientT) / 10000.0f;

    float distCm = sampleSonicDistanceCm(AJSR04M_TRIG_PIN, AJSR04M_ECHO_PIN, speedSound);

    if (distCm >= 2.0f && distCm <= 450.0f) {
        float depth = TANK_TOTAL_DEPTH_CM;
        float blind = TANK_MIN_BLIND_DISTANCE_CM;
        float fillPct = 0.0f;
        if (depth > blind) {
            fillPct = constrain(((depth - distCm) / (depth - blind)) * 100.0f, 0.0f, 100.0f);
        } else {
            fillPct = 50.0f;
        }

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

        Serial.printf("[ULTRASONIC-LIVE] >>> Tank Sonar: %.1f cm | Level: %.1f%% (Compensated @ %.1fC) <<<\n",
                      out.tank_distance_cm, out.tank_level_pct, ambientT);
        return true;
    } else {
        if (s_consecutiveSonarMisses < 2 && s_lastKnownDistanceCm > 0.0f && (millis() - s_lastValidDistanceMillis < 6000UL)) {
            s_consecutiveSonarMisses++;
            out.tank_distance_cm = s_lastKnownDistanceCm;
            out.tank_level_pct = s_lastKnownFillPct;
            out.tank_valid = true;
            return true;
        }

        s_consecutiveSonarMisses++;
        out.tank_valid = false;
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
    // 1. Calculate temperature-compensated acoustic sound speed
    float ambientT = 20.0f;
    if (g_lastEnv.dht_valid && g_lastEnv.temperature_c >= 0.0f && g_lastEnv.temperature_c <= 55.0f) {
        ambientT = g_lastEnv.temperature_c;
    }
    float speedSound = (331.3f + 0.606f * ambientT) / 10000.0f;

    // 2. Probe primary waste header (Trig GPIO 14, Echo GPIO 27)
    int echoPinUsed = HCSR04_WASTE_ECHO_PIN;
    float distCm = sampleSonicDistanceCm(HCSR04_WASTE_TRIG_PIN, HCSR04_WASTE_ECHO_PIN, speedSound);

    // 3. Fallback: If no echo on GPIO 14/27, automatically probe secondary header (Trig GPIO 5, Echo GPIO 18)
    if (distCm < 0.0f && AJSR04M_TRIG_PIN >= 0 && AJSR04M_ECHO_PIN >= 0) {
        distCm = sampleSonicDistanceCm(AJSR04M_TRIG_PIN, AJSR04M_ECHO_PIN, speedSound);
        if (distCm > 0.0f) {
            echoPinUsed = AJSR04M_ECHO_PIN;
        }
    }

    if (distCm >= 2.0f && distCm <= 450.0f) {
        float depth = BIN_TOTAL_DEPTH_CM;
        float blind = BIN_MIN_BLIND_DISTANCE_CM;
        float fillPct = 0.0f;
        if (depth > blind) {
            fillPct = constrain(((depth - distCm) / (depth - blind)) * 100.0f, 0.0f, 100.0f);
        } else {
            fillPct = 50.0f;
        }

        // Slight jitter smoothing (< 3cm change)
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
        out.echo_pin_used = echoPinUsed;

        Serial.printf("[HCSR04-WASTE-LIVE] >>> Real Bin Distance (Echo GPIO %d): %.1f cm | Fill: %.1f%% (Compensated @ %.1fC) <<<\n",
                      echoPinUsed, out.bin_distance_cm, out.fill_level_percent, ambientT);
        return true;
    }

    // Also route water tank sonar if available
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
        return true;
    }

    // Bridge brief acoustic dropouts (up to 2 misses within 6 seconds)
    s_consecutiveBinSonarMisses++;
    if (s_lastKnownBinDistCm > 0.0f && (millis() - s_lastValidBinDistanceMillis < 6000UL) && s_consecutiveBinSonarMisses <= 2) {
        out.bin_distance_cm = s_lastKnownBinDistCm;
        out.fill_level_percent = s_lastKnownBinFillPct;
        out.bin_valid = true;
        out.echo_pin_used = echoPinUsed;
        return true;
    }
#endif
    out.bin_valid = false;
    return false;
}

// =========================================================================================
// SENSOR 4: DHT11 DIGITAL TEMPERATURE & HUMIDITY SENSOR (pin selected in config.h)
// =========================================================================================
bool readDHT11Sensor(EnvironmentalReadings &out) {
#if defined(DHT11_ENABLED) && (DHT11_ENABLED == 1)
    if (DHT11_PIN < 0) {
        out.dht_valid = false;
        return false;
    }

    static float lastValidTemp = 0.0f;
    static float lastValidHum = 0.0f;
    static unsigned long lastValidDhtMs = 0;

    float newHumidity = dhtSensor.readHumidity();
    float newTemperature = dhtSensor.readTemperature();

#if defined(DHT11_PIN_ALT) && (DHT11_PIN_ALT >= 0)
    if ((isnan(newHumidity) || isnan(newTemperature)) && DHT11_PIN_ALT != WATER_PULSE_PIN) {
        newHumidity = dhtSensorAlt.readHumidity();
        newTemperature = dhtSensorAlt.readTemperature();
    }
#endif

    if (isnan(newHumidity) || isnan(newTemperature) || newTemperature < -10.0f || newTemperature > 60.0f || newHumidity < 5.0f || newHumidity > 100.0f) {
        // Bridge single transient read miss for up to 8 seconds to prevent screen flickering
        if (lastValidTemp > 0.0f && (millis() - lastValidDhtMs < 8000UL)) {
            out.temperature_c = lastValidTemp;
            out.humidity_pct = lastValidHum;
            out.heat_index_c = dhtSensor.computeHeatIndex(lastValidTemp, lastValidHum, false);
            out.dht_valid = true;
            return true;
        }
        out.dht_valid = false;
        Serial.println("[SENSOR-DHT11] Read failed; awaiting next sample cycle.");
        return false;
    }

    out.humidity_pct = newHumidity;
    out.temperature_c = newTemperature;
    out.heat_index_c = dhtSensor.computeHeatIndex(newTemperature, newHumidity, false);
    out.dht_valid = true;

    lastValidTemp = newTemperature;
    lastValidHum = newHumidity;
    lastValidDhtMs = millis();

    Serial.printf("[SENSOR-DHT11] Temp: %.1f C | Humidity: %.1f %% | Heat Index: %.1f C\n",
                  out.temperature_c, out.humidity_pct, out.heat_index_c);
    return true;
#endif
    out.dht_valid = false;
    return false;
}

// =========================================================================================
// SENSOR 5: MQ-135 AIR QUALITY, HARMFUL GAS & SMOKE SENSOR (ADC1: GPIO34)
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

    out.adc_pin_voltage_v = (avgAdc / 4095.0f) * 3.3f;
    out.sensor_voltage_v = out.adc_pin_voltage_v * MQ135_VOLTAGE_DIVIDER_RATIO;

    // Physical connection check:
    // When no sensor is plugged into GPIO34, ADC reads 0 count (< 80 count, < 0.08V).
    if (avgAdc < 80 || out.sensor_voltage_v < 0.08f) {
        out.gas_valid = false;
        Serial.printf("[SENSOR-MQ135] Floating/unconnected pin on GPIO %d (ADC: %d, %.2fV). Sensor not connected.\n",
                      MQ135_ANALOG_PIN, avgAdc, out.sensor_voltage_v);
        return false;
    }

    // Calculate sensor resistance Rs (kOhms) with RL = 10.0 kOhm
    float vOut = constrain(out.sensor_voltage_v, 0.15f, 4.85f);
    out.rs_kohm = ((5.0f - vOut) / vOut) * MQ135_RL_KOHM;
    out.rs_ro_ratio = out.rs_kohm / MQ135_RO_CLEAN_AIR_KOHM;

    // Calculate estimated PPM using logarithmic gas curve
    // PPM = 400 * (ADC / 350)^1.85, calibrated for indoor ambient
    float estimatedPpm = 400.0f * pow(((float)avgAdc / 350.0f), 1.85f);
    out.estimated_ppm = constrain(estimatedPpm, 100.0f, 9999.0f);

    // Multi-level Harmful Gas, Smoke & Pollutants Classification:
    if (avgAdc < MQ135_CLEAN_AIR_ADC_MAX) {
        out.air_quality_level = 0;
        strncpy(out.air_quality_label, "Clean Air", sizeof(out.air_quality_label));
        out.gas_alert = false;
        out.smoke_detected = false;
    } else if (avgAdc < MQ135_MODERATE_ADC_MAX) {
        out.air_quality_level = 1;
        strncpy(out.air_quality_label, "Moderate Air", sizeof(out.air_quality_label));
        out.gas_alert = false;
        out.smoke_detected = false;
    } else if (avgAdc < MQ135_SMOKE_ADC_THRESHOLD) {
        out.air_quality_level = 2;
        strncpy(out.air_quality_label, "Harmful Gas!", sizeof(out.air_quality_label));
        out.gas_alert = true;
        out.smoke_detected = false;
    } else {
        out.air_quality_level = 3;
        strncpy(out.air_quality_label, "Smoke Detected!", sizeof(out.air_quality_label));
        out.gas_alert = true;
        out.smoke_detected = true;
    }

    unsigned long uptimeSec = millis() / 1000;
    out.warming_up = (uptimeSec < MQ135_WARMUP_PERIOD_SEC);
    out.gas_valid = true;

    Serial.printf("[SENSOR-MQ135] ADC: %d | %.2fV | Rs: %.1fk | Ratio: %.2f | ~%.0f PPM | State: %s | Smoke: %s | Warmup: %s\n",
                  out.raw_adc, out.sensor_voltage_v, out.rs_kohm, out.rs_ro_ratio, out.estimated_ppm,
                  out.air_quality_label, out.smoke_detected ? "YES" : "NO",
                  out.warming_up ? "WARMING_UP" : "READY");
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


    // 2. Initialize Water Flow Sensor Interrupt on Primary (GPIO 26) and Secondary (GPIO 4) Pins
#if defined(WATER_FLOW_ENABLED) && (WATER_FLOW_ENABLED == 1)
    if (WATER_PULSE_PIN >= 0) {
        pinMode(WATER_PULSE_PIN, INPUT_PULLUP);
        attachInterrupt(digitalPinToInterrupt(WATER_PULSE_PIN), onWaterPulseISR, FALLING);
        Serial.printf("[WATER-FLOW] Primary Hall pulse interrupt attached on GPIO %d\n", WATER_PULSE_PIN);
    }
#if defined(WATER_PULSE_PIN_ALT) && (WATER_PULSE_PIN_ALT >= 0)
    if (WATER_PULSE_PIN_ALT != DHT11_PIN) {
        pinMode(WATER_PULSE_PIN_ALT, INPUT_PULLUP);
        attachInterrupt(digitalPinToInterrupt(WATER_PULSE_PIN_ALT), onWaterPulseISR, FALLING);
        Serial.printf("[WATER-FLOW] Secondary Hall pulse interrupt attached on GPIO %d\n", WATER_PULSE_PIN_ALT);
    }
#endif
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
        dhtSensor.begin();
        Serial.printf("[DHT11] Primary Temp/Humidity initialized on GPIO %d\n", DHT11_PIN);
    }
#if defined(DHT11_PIN_ALT) && (DHT11_PIN_ALT >= 0)
    if (DHT11_PIN_ALT != WATER_PULSE_PIN) {
        dhtSensorAlt.begin();
        Serial.printf("[DHT11] Secondary Temp/Humidity initialized on GPIO %d\n", DHT11_PIN_ALT);
    }
#endif
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
    oledClear();
    oledDrawHeader();
    oledDrawLineClamped(2, "Firmware v3.0");
    oledDrawLineClamped(4, "Sensors starting");
    oledDrawLineClamped(6, "WiFi connecting...");
    oledRender();
#endif

    // 7. Initialize Wi-Fi
    WiFi.disconnect(true);
    delay(100);
    WiFi.mode(WIFI_STA);
    WiFi.setAutoReconnect(true);
    WiFi.setSleep(false); // CRITICAL: Disable modem sleep power saving to avoid dropping beacon frames
#if defined(WIFI_POWER_19_5dBm)
    WiFi.setTxPower(WIFI_POWER_19_5dBm);
#endif
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
    // 0. Active Edge-Detection Polling for Water Flow Turbine (Zero Missed Pulses)
#if defined(WATER_FLOW_ENABLED) && (WATER_FLOW_ENABLED == 1)
    if (WATER_PULSE_PIN >= 0) {
        static int s_lastWaterPinState1 = HIGH;
        int s_curWaterPinState1 = digitalRead(WATER_PULSE_PIN);
        if (s_lastWaterPinState1 == HIGH && s_curWaterPinState1 == LOW) {
            onWaterPulseISR();
        }
        s_lastWaterPinState1 = s_curWaterPinState1;
    }

#if defined(WATER_PULSE_PIN_ALT) && (WATER_PULSE_PIN_ALT >= 0)
    if (WATER_PULSE_PIN_ALT != DHT11_PIN) {
        static int s_lastWaterPinState2 = HIGH;
        int s_curWaterPinState2 = digitalRead(WATER_PULSE_PIN_ALT);
        if (s_lastWaterPinState2 == HIGH && s_curWaterPinState2 == LOW) {
            onWaterPulseISR();
        }
        s_lastWaterPinState2 = s_curWaterPinState2;
    }
#endif
#endif

    maintainWiFi();
    maintainMQTT();

#if !defined(USE_HTTP_INGESTION) || (USE_HTTP_INGESTION == 0)
    if (mqttClient.connected()) {
        mqttClient.loop();
    }
#endif

    unsigned long now = millis();

    // Refresh the OLED before network requests so a slow HTTP call cannot
    // postpone the visible page update. Keep one renderer call per interval.
    static unsigned long lastOledRefreshMillis = 0;
    if (now - lastOledRefreshMillis >= 1000UL) {
        lastOledRefreshMillis = now;
#if defined(OLED_ENABLED) && (OLED_ENABLED == 1)
        oledUpdateDashboard();
#endif
    }

    // Pull the latest PZEM-004T readings from Node #2/backend after rendering.
    syncPeerPzemFromNetwork();

    // Resume at most one queued send at a time so reconnect backlogs cannot
    // freeze the display or starve live sensor acquisition.
#if defined(USE_HTTP_INGESTION) && (USE_HTTP_INGESTION == 1)
    if (WiFi.status() == WL_CONNECTED) drainOfflineQueue();
#else
    if (mqttClient.connected()) drainOfflineQueue();
#endif

    // =================================================================================
    // 1. HIGH-FREQUENCY INTERNAL SENSOR ACQUISITION & EDGE ANOMALY DETECTION
    // =================================================================================
    if (now - lastAcquisitionMillis >= SENSOR_ACQUISITION_INTERVAL_MS) {
        lastAcquisitionMillis = now;

        // A. Sample physical hardware sensors at continuous high-frequency rate
        ElectricityReadings elec = g_lastElec; // Dedicated to Node #2 (PZEM-004T)

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
            Serial.printf("[TIME] Clock sync pending; using relative uptime timestamp (%s) to guarantee zero packet loss.\n", timestampIso);
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

                JsonObject w4 = metricsWater.createNestedObject();
                w4["metric"] = "water_pulse_count_total"; w4["value"] = water.pulse_count_total; w4["unit"] = "count"; w4["quality"] = "good";
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
                // Top-level convenience fields for environmental monitoring
                docEnv["mq135_raw_adc"] = env.raw_adc;
                docEnv["mq135_voltage_v"] = env.sensor_voltage_v;
                docEnv["mq135_estimated_ppm"] = env.estimated_ppm;
                docEnv["air_quality"] = env.air_quality_label;
                docEnv["gas_alert"] = env.gas_alert ? 1 : 0;
                docEnv["smoke_detected"] = env.smoke_detected ? 1 : 0;

                JsonObject e1 = metricsEnv.createNestedObject();
                e1["metric"] = "mq135_raw_adc"; e1["value"] = env.raw_adc; e1["unit"] = "count"; e1["quality"] = "good";

                JsonObject e2 = metricsEnv.createNestedObject();
                e2["metric"] = "mq135_voltage_v"; e2["value"] = env.sensor_voltage_v; e2["unit"] = "V"; e2["quality"] = "good";

                JsonObject e3 = metricsEnv.createNestedObject();
                e3["metric"] = "mq135_adc_pin_voltage_v"; e3["value"] = env.adc_pin_voltage_v; e3["unit"] = "V"; e3["quality"] = "good";

                JsonObject e4 = metricsEnv.createNestedObject();
                e4["metric"] = "mq135_warmup_status"; e4["value"] = env.warming_up ? 0 : 1; e4["unit"] = "status"; e4["quality"] = "good";

                JsonObject e5 = metricsEnv.createNestedObject();
                e5["metric"] = "mq135_estimated_ppm"; e5["value"] = env.estimated_ppm; e5["unit"] = "ppm"; e5["quality"] = "good";

                JsonObject e6 = metricsEnv.createNestedObject();
                e6["metric"] = "gas_alert"; e6["value"] = env.gas_alert ? 1 : 0; e6["unit"] = "flag"; e6["quality"] = "good";

                JsonObject e7 = metricsEnv.createNestedObject();
                e7["metric"] = "smoke_detected"; e7["value"] = env.smoke_detected ? 1 : 0; e7["unit"] = "flag"; e7["quality"] = "good";
            }

            if (env.dht_valid) {
                docEnv["temperature_c"] = env.temperature_c;
                docEnv["humidity_pct"] = env.humidity_pct;
                docEnv["heat_index_c"] = env.heat_index_c;

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

    }
}
