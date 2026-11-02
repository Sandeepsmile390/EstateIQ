/*
 * =========================================================================================
 * EstateIQ ESP32 Edge Gateway & Real-Time Sensor Firmware (hardware/esp32/firmware/main.ino)
 * =========================================================================================
 *
 * SAFETY NOTICE & ELECTRICAL COMPLIANCE:
 * - This firmware is strictly an edge DATA ACQUISITION & MONITORING node for low-voltage signals.
 * - NEVER connect 230V / 415V AC mains voltage or raw current transformers directly to ESP32 pins.
 * - All high-voltage metrology must be performed by a certified DIN-rail energy meter.
 * - Communication with the energy meter is via an optically isolated RS-485 Modbus RTU transceiver.
 * - Water pulse and pressure inputs must be routed through appropriate level-shifting or opto-isolation.
 * - This gateway performs OBSERVATION ONLY; it NEVER implements, triggers, or implies automatic
 *   mains switching, circuit breaker tripping, or physical load control.
 * =========================================================================================
 */

#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <time.h>
#include <math.h>

// Include site configuration. If config.h is not found, fall back to safe local definitions.
#if __has_include("config.h")
  #include "config.h"
#else
  #define WIFI_SSID           "CHANGE_ME_WIFI_SSID"
  #define WIFI_PASSWORD       "CHANGE_ME_WIFI_PASSWORD"
  #define MQTT_BROKER_HOST    "192.168.1.100"
  #define MQTT_BROKER_PORT    1883
  #define MQTT_CLIENT_ID      "ESP32_EDGE_GATEWAY_01"
  #define MQTT_USERNAME       ""
  #define MQTT_PASSWORD       ""
  #define GATEWAY_API_KEY     "UNCONFIGURED_SET_IN_ENV"

  #define FACILITY_ID         "FAC_GEC_CAMPUS"
  #define BUILDING_ID         "Block B Hostel"
  #define DEVICE_ID_ELEC      "METER-BLOCK-B-001"
  #define DEVICE_ID_WATER     "WATER-BLOCK-B-001"

  #define MQTT_TOPIC_ELEC     "estateiq/FAC_GEC_CAMPUS/Block_B_Hostel/meter/METER-BLOCK-B-001/telemetry"
  #define MQTT_TOPIC_WATER    "estateiq/FAC_GEC_CAMPUS/Block_B_Hostel/meter/WATER-BLOCK-B-001/telemetry"

  #define RS485_RX_PIN        16
  #define RS485_TX_PIN        17
  #define RS485_DE_RE_PIN     4
  #define MODBUS_BAUD_RATE    9600
  #define MODBUS_SLAVE_ID     1

  // Eastron SDM630 Modbus Register Map
  #define REG_VOLTAGE_L1           0x0000
  #define REG_CURRENT_L1           0x0006
  #define REG_ACTIVE_POWER_TOTAL   0x0034 // Total Active Power in Watts (W)
  #define REG_POWER_FACTOR         0x001E
  #define REG_FREQUENCY            0x0046
  #define REG_ACTIVE_ENERGY_IMPORT 0x0156 // Total Active Energy in kWh
  #define MODBUS_FLOAT_WORD_ORDER_ABCD 1

  // Water Flow Sensor (YF-S201 Hall-Effect Turbine Meter)
  // Confirmed physical operating range: 1.0 to 30.0 L/min (±3% tolerance).
  // Characteristic: F (Hz) = 7.5 * Q (L/min) -> 450 pulses/liter. Max 225 Hz at 30 L/min.
  // Readings > 30.0 L/min exceed sensor rating and indicate pulse bounce or sensor fault.
  // ELECTRICAL SAFETY: When powering sensor at 5V VCC, use 10k/20k divider to limit output to 3.3V at GPIO5!
  #define WATER_PULSE_PIN     5
  #define FLOW_CALIBRATION_PULSES_PER_LITER 450.0f
  #define PULSE_FACTOR_L_PER_PULSE (1.0f / FLOW_CALIBRATION_PULSES_PER_LITER)
  #define YF_S201_MAX_RATED_FLOW_LMIN 30.0f

  #define WATER_PRESSURE_ANALOG_PIN  -1
  #define TANK_LEVEL_ANALOG_PIN     -1

  #define SAMPLING_INTERVAL_MS 15000
  #define OFFLINE_QUEUE_SIZE   30
#endif

// --- Telemetry Data Structures ---
struct ElectricityReadings {
    bool has_voltage = false;
    float voltage_v = 0.0f;
    bool has_current = false;
    float current_a = 0.0f;
    bool has_power = false;
    float active_power_kw = 0.0f;
    bool has_energy = false;
    float cumulative_energy_kwh = 0.0f;
    bool has_pf = false;
    float power_factor = 0.0f;
    bool has_freq = false;
    float frequency_hz = 0.0f;
    bool valid = false;
    unsigned long last_read_millis = 0;
    const char* error_msg = nullptr;
};

struct WaterReadings {
    bool valid = false;
    float water_flow_lmin = 0.0f;
    float cumulative_water_m3 = 0.0f;
    unsigned long pulse_count_total = 0;
    unsigned long last_read_millis = 0;
};

struct WaterAuxReadings {
    bool pressure_valid = false;
    float water_pressure_bar = 0.0f;
    bool tank_valid = false;
    float tank_level_pct = 0.0f;
    float tank_distance_cm = 0.0f;
};

// --- Offline Queue for Network Dropouts ---
struct QueuedEnvelope {
    char topic[96];
    char payload[768];
    bool in_use = false;
};

QueuedEnvelope offlineQueue[OFFLINE_QUEUE_SIZE];
int queueHead = 0;
int queueTail = 0;
int queueCount = 0;

// --- Networking and State Variables ---
WiFiClient espClient;
PubSubClient mqttClient(espClient);

unsigned long lastSampleTime = 0;
unsigned long sequenceCounter = 1;

// Non-blocking reconnection timers & backoff
unsigned long lastWifiAttempt = 0;
unsigned long wifiBackoffMs = 2000;
const unsigned long maxWifiBackoffMs = 60000;

unsigned long lastMqttAttempt = 0;
unsigned long mqttBackoffMs = 2000;
const unsigned long maxMqttBackoffMs = 60000;

// Water pulse counter state (interrupt-driven)
volatile unsigned long isrWaterPulseCount = 0;
unsigned long lastWaterCalcMillis = 0;
unsigned long lastWaterPulseSnap = 0;
float cumulativeWaterVolumeM3 = 0.0f;

// Hardware Serial for Modbus RS-485
HardwareSerial ModbusSerial(2);

// --- ISR: Interrupt Service Routine for Water Pulse Sensor ---
void IRAM_ATTR onWaterPulseISR() {
    isrWaterPulseCount++;
}

// --- ISO8601 UTC Timestamp Helper ---
bool getISOTimestamp(char* outBuf, size_t bufSize) {
    time_t nowSec = time(nullptr);
    if (nowSec > 1600000000) { // Valid NTP time acquired
        struct tm timeinfo;
        gmtime_r(&nowSec, &timeinfo);
        strftime(outBuf, bufSize, "%Y-%m-%dT%H:%M:%SZ", &timeinfo);
        return true;
    }
    outBuf[0] = '\0';
    return false;
}

uint16_t modbusCrc16(const uint8_t* data, size_t length) {
    uint16_t crc = 0xFFFF;
    for (size_t i = 0; i < length; ++i) {
        crc ^= data[i];
        for (uint8_t bit = 0; bit < 8; ++bit)
            crc = (crc & 1) ? (crc >> 1) ^ 0xA001 : crc >> 1;
    }
    return crc;
}

bool readModbusFloat(uint16_t address, float &value) {
    uint8_t request[8] = {MODBUS_SLAVE_ID, 0x04, (uint8_t)(address >> 8), (uint8_t)address, 0, 2, 0, 0};
    uint16_t crc = modbusCrc16(request, 6);
    request[6] = (uint8_t)crc;
    request[7] = (uint8_t)(crc >> 8);
    while (ModbusSerial.available()) ModbusSerial.read();
    if (RS485_DE_RE_PIN >= 0) digitalWrite(RS485_DE_RE_PIN, HIGH);
    ModbusSerial.write(request, sizeof(request));
    ModbusSerial.flush();
    if (RS485_DE_RE_PIN >= 0) digitalWrite(RS485_DE_RE_PIN, LOW);

    uint8_t response[9];
    size_t count = 0;
    unsigned long started = millis();
    while (millis() - started < 150 && count < sizeof(response)) {
        if (ModbusSerial.available()) response[count++] = (uint8_t)ModbusSerial.read();
    }
    if (count != sizeof(response) || response[0] != MODBUS_SLAVE_ID || response[1] != 0x04 || response[2] != 4)
        return false;
    uint16_t receivedCrc = response[7] | ((uint16_t)response[8] << 8);
    if (modbusCrc16(response, 7) != receivedCrc) return false;
    uint32_t raw;
    #if defined(MODBUS_FLOAT_WORD_ORDER_ABCD) && (MODBUS_FLOAT_WORD_ORDER_ABCD == 1)
    // Standard Big-Endian word order (Eastron SDM630 default)
    raw = ((uint32_t)response[3] << 24) | ((uint32_t)response[4] << 16) |
          ((uint32_t)response[5] << 8)  | (uint32_t)response[6];
    #else
    // Word-swapped Mid-Little order (CDAB - for meters like Selec / Schneider)
    raw = ((uint32_t)response[5] << 24) | ((uint32_t)response[6] << 16) |
          ((uint32_t)response[3] << 8)  | (uint32_t)response[4];
    #endif
    union { uint32_t raw; float f; } decoded;
    decoded.raw = raw;
    value = decoded.f;
    return isfinite(value);
}

// --- Offline Queue Helper Functions ---
void enqueueTelemetry(const char* topic, const char* payload) {
    if (queueCount < OFFLINE_QUEUE_SIZE) {
        strncpy(offlineQueue[queueHead].topic, topic, sizeof(offlineQueue[queueHead].topic) - 1);
        strncpy(offlineQueue[queueHead].payload, payload, sizeof(offlineQueue[queueHead].payload) - 1);
        offlineQueue[queueHead].in_use = true;
        queueHead = (queueHead + 1) % OFFLINE_QUEUE_SIZE;
        queueCount++;
        Serial.printf("[QUEUE] Stored packet offline (queue depth: %d/%d)\n", queueCount, OFFLINE_QUEUE_SIZE);
    } else {
        Serial.println("[QUEUE] Offline queue full! Dropping oldest sample.");
        queueTail = (queueTail + 1) % OFFLINE_QUEUE_SIZE;
        strncpy(offlineQueue[queueHead].topic, topic, sizeof(offlineQueue[queueHead].topic) - 1);
        strncpy(offlineQueue[queueHead].payload, payload, sizeof(offlineQueue[queueHead].payload) - 1);
        queueHead = (queueHead + 1) % OFFLINE_QUEUE_SIZE;
    }
}

void drainOfflineQueue() {
    while (queueCount > 0 && mqttClient.connected()) {
        QueuedEnvelope &item = offlineQueue[queueTail];
        if (item.in_use) {
            // PubSubClient outbound publishes are QoS 0; retained is intentionally false.
            bool ok = mqttClient.publish(item.topic, item.payload, false);
            if (ok) {
                item.in_use = false;
                queueTail = (queueTail + 1) % OFFLINE_QUEUE_SIZE;
                queueCount--;
                Serial.printf("[QUEUE] Replayed buffered packet (remaining: %d)\n", queueCount);
            } else {
                break; // Network stalled, retry next cycle
            }
        }
    }
}

// --- Non-Blocking Network Handlers ---
void maintainWiFi() {
    if (WiFi.status() == WL_CONNECTED) {
        wifiBackoffMs = 2000; // Reset backoff on success
        return;
    }

    unsigned long now = millis();
    if (now - lastWifiAttempt > wifiBackoffMs) {
        lastWifiAttempt = now;
        Serial.printf("[WIFI] Non-blocking connect to %s (backoff: %lums)...\n", WIFI_SSID, wifiBackoffMs);
        WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
        wifiBackoffMs = min(wifiBackoffMs * 2, maxWifiBackoffMs);
    }
}

void maintainMQTT() {
    if (WiFi.status() != WL_CONNECTED || mqttClient.connected()) {
        if (mqttClient.connected()) {
            mqttBackoffMs = 2000;
        }
        return;
    }

    unsigned long now = millis();
    if (now - lastMqttAttempt > mqttBackoffMs) {
        lastMqttAttempt = now;
        Serial.printf("[MQTT] Attempting broker connection %s:%d...\n", MQTT_BROKER_HOST, MQTT_BROKER_PORT);

        bool connected = false;
        if (strlen(MQTT_USERNAME) > 0) {
            connected = mqttClient.connect(MQTT_CLIENT_ID, MQTT_USERNAME, MQTT_PASSWORD);
        } else {
            connected = mqttClient.connect(MQTT_CLIENT_ID);
        }

        if (connected) {
            Serial.println("[MQTT] Connected to Broker successfully! Draining offline queue...");
            mqttBackoffMs = 2000;
            drainOfflineQueue();
        } else {
            Serial.printf("[MQTT] Connect failed, rc=%d. Backing off %lums...\n", mqttClient.state(), mqttBackoffMs);
            mqttBackoffMs = min(mqttBackoffMs * 2, maxMqttBackoffMs);
        }
    }
}

// =========================================================================================
// SENSOR ADAPTER 1: Modbus RTU Energy Meter
// =========================================================================================
/*
 * NOTE ON REGISTER MAP COMPLIANCE:
 * The register addresses below reflect the Eastron SDM630 Modbus RTU specification:
 * - 0x0000: Line 1 Voltage (V) [Float32, Input Register, Read 0x04]
 * - 0x0006: Line 1 Current (A) [Float32]
 * - 0x000C: Active Power (W) [Float32] -> converted to kW
 * - 0x001E: Power Factor [Float32]
 * - 0x0046: Frequency (Hz) [Float32]
 * - 0x0156: Total Active Energy (kWh) [Float32]
 *
 * IF CONNECTING A DIFFERENT METER (Schneider, Selec, etc.), YOU MUST UPDATE THIS
 * REGISTER MAP ACCORDING TO YOUR COMMISSIONED METER'S DATASHEET.
 */
bool readModbusElectricityMeter(ElectricityReadings &out) {
    // Eastron SDM630 register map (Function 0x04 Input Registers)
    out.has_voltage = readModbusFloat(REG_VOLTAGE_L1, out.voltage_v);
    out.has_current = readModbusFloat(REG_CURRENT_L1, out.current_a);
    float rawPowerW = 0.0f;
    out.has_power = readModbusFloat(REG_ACTIVE_POWER_TOTAL, rawPowerW);
    if (out.has_power) {
        // SDM630 register 0x0034 reports Watts (W). Convert to kW exactly once.
        out.active_power_kw = rawPowerW / 1000.0f;
    }
    out.has_pf = readModbusFloat(REG_POWER_FACTOR, out.power_factor);
    out.has_freq = readModbusFloat(REG_FREQUENCY, out.frequency_hz);
    out.has_energy = readModbusFloat(REG_ACTIVE_ENERGY_IMPORT, out.cumulative_energy_kwh);

    out.valid = out.has_voltage || out.has_current || out.has_power || out.has_energy;
    out.last_read_millis = millis();
    out.error_msg = out.valid ? nullptr : "MODBUS_READ_OR_CRC_ERROR";
    return out.valid;
}

// =========================================================================================
// SENSOR ADAPTER 2: Interrupt-Driven Water Flow Pulse Counter
// =========================================================================================
bool readWaterFlowMeter(WaterReadings &out) {
    if (WATER_PULSE_PIN < 0) {
        out.valid = false;
        return false;
    }

    unsigned long now = millis();
    unsigned long elapsedMs = now - lastWaterCalcMillis;
    if (elapsedMs == 0) elapsedMs = 1;

    // Safely snapshot atomic ISR counter
    noInterrupts();
    unsigned long currentPulses = isrWaterPulseCount;
    interrupts();

    unsigned long deltaPulses = currentPulses - lastWaterPulseSnap;
    lastWaterPulseSnap = currentPulses;
    lastWaterCalcMillis = now;

    // Convert pulses to liters using calibrated factor
    float deltaLiters = (float)deltaPulses * PULSE_FACTOR_L_PER_PULSE;
    float elapsedMinutes = (float)elapsedMs / 60000.0f;

    // Instantaneous flow rate in Liters / minute (clamped to 0 if static noise < 0.1 L/min)
    float calculatedFlow = deltaLiters / elapsedMinutes;
    out.water_flow_lmin = (calculatedFlow < 0.1f) ? 0.0f : calculatedFlow;

    // Accumulate total cubic meters (1 m³ = 1000 L)
    cumulativeWaterVolumeM3 += (deltaLiters / 1000.0f);
    out.cumulative_water_m3 = cumulativeWaterVolumeM3;
    out.pulse_count_total = currentPulses;
    out.valid = true;
    out.last_read_millis = now;
    return true;
}

// =========================================================================================
// SENSOR ADAPTER 3: Water Pressure & Tank Level (Optional Inputs)
// =========================================================================================
bool readWaterAuxSensors(WaterAuxReadings &out) {
    // 4-20mA inputs require a properly rated 150-ohm shunt (0.6-3.0V) and calibrated range.
    if (WATER_PRESSURE_ANALOG_PIN >= 0) {
        int rawAdc = analogRead(WATER_PRESSURE_ANALOG_PIN);
        // Placeholder calibration for a 0-10 bar, 4-20mA transmitter and 150-ohm shunt.
        float voltage = (rawAdc / 4095.0f) * 3.3f;
        float bar = (voltage - 0.6f) * (10.0f / 2.4f);
        if (voltage < 0.45f || voltage > 3.15f) { out.pressure_valid = false; }
        else {
        out.water_pressure_bar = max(0.0f, bar);
        out.pressure_valid = true;
        }
    } else {
        out.pressure_valid = false;
    }

    // Tank level is intentionally unsupported here: an ADC percentage is not a calibrated level.
    out.tank_valid = false;

    return out.pressure_valid || out.tank_valid;
}

// =========================================================================================
// SETUP & INITIALIZATION
// =========================================================================================
void setup() {
    Serial.begin(115200);
    delay(500);

    Serial.println("\n========================================================");
    Serial.println("EstateIQ ESP32 Edge Sensor Gateway Firmware v2.0-RealIoT");
    Serial.println("========================================================");

    // RS-485 Modbus Serial Setup
    if (RS485_DE_RE_PIN >= 0) {
        pinMode(RS485_DE_RE_PIN, OUTPUT);
        digitalWrite(RS485_DE_RE_PIN, LOW); // Start in Receive mode
    }
    ModbusSerial.begin(MODBUS_BAUD_RATE, SERIAL_8N1, RS485_RX_PIN, RS485_TX_PIN);
    Serial.printf("[MODBUS] RS-485 initialized on RX:%d, TX:%d, Baud:%d\n", RS485_RX_PIN, RS485_TX_PIN, MODBUS_BAUD_RATE);

    // Water Pulse Sensor Hardware Interrupt Setup
    if (WATER_PULSE_PIN >= 0) {
        pinMode(WATER_PULSE_PIN, INPUT_PULLUP);
        attachInterrupt(digitalPinToInterrupt(WATER_PULSE_PIN), onWaterPulseISR, RISING);
        Serial.printf("[WATER] Pulse interrupt attached on GPIO %d\n", WATER_PULSE_PIN);
    }

    // Configure SNTP for accurate UTC timestamps
    configTime(0, 0, "pool.ntp.org", "time.nist.gov");

    // Initialize Network Client
    mqttClient.setServer(MQTT_BROKER_HOST, MQTT_BROKER_PORT);
    mqttClient.setBufferSize(768);

    lastWaterCalcMillis = millis();
    lastSampleTime = millis();
}

// =========================================================================================
// MAIN NON-BLOCKING EXECUTION LOOP
// =========================================================================================
void loop() {
    // 1. Maintain background connectivity without blocking sensor operations
    maintainWiFi();
    maintainMQTT();
    mqttClient.loop();

    unsigned long now = millis();

    // 2. Periodic Sampling and Publishing Window
    if (now - lastSampleTime >= SAMPLING_INTERVAL_MS) {
        lastSampleTime = now;
        sequenceCounter++;

        char timestampIso[32];
        if (!getISOTimestamp(timestampIso, sizeof(timestampIso))) {
            Serial.println("[TIME] NTP not synchronized; skipping telemetry to avoid fabricated timestamps.");
            return;
        }

        // ---------------------------------------------------------------------------------
        // A. Read Electricity Modbus Meter
        // ---------------------------------------------------------------------------------
        ElectricityReadings elec;
        bool elecReadOk = readModbusElectricityMeter(elec);

        StaticJsonDocument<768> docElec;
        docElec["schema_version"] = "1.0";
        char msgIdElec[48];
        snprintf(msgIdElec, sizeof(msgIdElec), "MSG_%s_%lu", DEVICE_ID_ELEC, sequenceCounter);
        docElec["message_id"] = msgIdElec;
        docElec["gateway_id"] = MQTT_CLIENT_ID;
        docElec["device_id"] = DEVICE_ID_ELEC;
        docElec["auth_token"] = GATEWAY_API_KEY;
        docElec["facility_id"] = FACILITY_ID;
        docElec["building_id"] = BUILDING_ID;
        docElec["source_type"] = "real_sensor";
        docElec["event_timestamp"] = timestampIso;
        docElec["sent_timestamp"] = timestampIso;
        docElec["sequence_number"] = sequenceCounter;

        JsonArray metricsElec = docElec.createNestedArray("metrics");
        if (elecReadOk && elec.valid) {
            if (elec.has_voltage) {
                JsonObject m1 = metricsElec.createNestedObject();
                m1["metric"] = "voltage_v";
                m1["value"] = elec.voltage_v;
                m1["unit"] = "V";
                m1["quality"] = "good";
            }

            if (elec.has_power) {
                JsonObject m2 = metricsElec.createNestedObject();
                m2["metric"] = "active_power_kw";
                m2["value"] = elec.active_power_kw;
                m2["unit"] = "kW";
                m2["quality"] = "good";
            }

            if (elec.has_energy) {
                JsonObject m3 = metricsElec.createNestedObject();
                m3["metric"] = "cumulative_energy_kwh";
                m3["value"] = elec.cumulative_energy_kwh;
                m3["unit"] = "kWh";
                m3["quality"] = "good";
            }

            if (elec.has_current) {
                JsonObject m4 = metricsElec.createNestedObject();
                m4["metric"] = "current_a";
                m4["value"] = elec.current_a;
                m4["unit"] = "A";
                m4["quality"] = "good";
            }

            if (elec.has_pf) {
                JsonObject m5 = metricsElec.createNestedObject();
                m5["metric"] = "power_factor";
                m5["value"] = elec.power_factor;
                m5["unit"] = "ratio";
                m5["quality"] = "good";
            }

            if (elec.has_freq) {
                JsonObject m6 = metricsElec.createNestedObject();
                m6["metric"] = "frequency_hz";
                m6["value"] = elec.frequency_hz;
                m6["unit"] = "Hz";
                m6["quality"] = "good";
            }
        } else {
            // Document sensor fault honestly without fake values
            JsonObject mFault = metricsElec.createNestedObject();
            mFault["metric"] = "meter_status";
            mFault["value"] = 0.0;
            mFault["unit"] = "status";
            mFault["quality"] = "bad";
            docElec["error"] = elec.error_msg ? elec.error_msg : "METER_DISCONNECTED_OR_UNCOMMISSIONED";
        }

        char bufferElec[768];
        serializeJson(docElec, bufferElec);

        if (mqttClient.connected()) {
            mqttClient.publish(MQTT_TOPIC_ELEC, bufferElec, false); // PubSubClient publishes QoS 0 only.
            Serial.printf("[PUB-ELEC] Transmitted real meter packet seq=%lu\n", sequenceCounter);
        } else {
            enqueueTelemetry(MQTT_TOPIC_ELEC, bufferElec);
        }

        // ---------------------------------------------------------------------------------
        // B. Read Water Flow & Aux Sensors
        // ---------------------------------------------------------------------------------
        WaterReadings water;
        bool waterReadOk = readWaterFlowMeter(water);

        WaterAuxReadings aux;
        readWaterAuxSensors(aux);

        StaticJsonDocument<768> docWater;
        docWater["schema_version"] = "1.0";
        char msgIdWater[48];
        snprintf(msgIdWater, sizeof(msgIdWater), "MSG_%s_%lu", DEVICE_ID_WATER, sequenceCounter);
        docWater["message_id"] = msgIdWater;
        docWater["gateway_id"] = MQTT_CLIENT_ID;
        docWater["device_id"] = DEVICE_ID_WATER;
        docWater["auth_token"] = GATEWAY_API_KEY;
        docWater["facility_id"] = FACILITY_ID;
        docWater["building_id"] = BUILDING_ID;
        docWater["source_type"] = "real_sensor";
        docWater["event_timestamp"] = timestampIso;
        docWater["sent_timestamp"] = timestampIso;
        docWater["sequence_number"] = sequenceCounter;

        JsonArray metricsWater = docWater.createNestedArray("metrics");
        if (waterReadOk && water.valid) {
            JsonObject w1 = metricsWater.createNestedObject();
            w1["metric"] = "water_flow_lmin";
            w1["value"] = water.water_flow_lmin;
            w1["unit"] = "L/min";
            w1["quality"] = "good";

            JsonObject w2 = metricsWater.createNestedObject();
            w2["metric"] = "cumulative_water_m3";
            w2["value"] = water.cumulative_water_m3;
            w2["unit"] = "m3";
            w2["quality"] = "good";
        }

        if (aux.pressure_valid) {
            JsonObject w3 = metricsWater.createNestedObject();
            w3["metric"] = "water_pressure_bar";
            w3["value"] = aux.water_pressure_bar;
            w3["unit"] = "bar";
            w3["quality"] = "good";
        }

        if (aux.tank_valid) {
            JsonObject w4 = metricsWater.createNestedObject();
            w4["metric"] = "tank_level_pct";
            w4["value"] = aux.tank_level_pct;
            w4["unit"] = "%";
            w4["quality"] = "good";
        }

        char bufferWater[768];
        serializeJson(docWater, bufferWater);

        if (mqttClient.connected()) {
            mqttClient.publish(MQTT_TOPIC_WATER, bufferWater, false);
            Serial.printf("[PUB-WATER] Transmitted real water packet seq=%lu\n", sequenceCounter);
        } else {
            enqueueTelemetry(MQTT_TOPIC_WATER, bufferWater);
        }
    }
}
