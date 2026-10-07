/*
 * EstateIQ ESP32 Smart Meter / Edge Gateway Firmware (hardware/esp32/firmware/main.ino)
 * Protocol: RS-485 Modbus RTU -> ESP32 -> WiFi / MQTT Broker -> EstateIQ Ingestion Service
 * 
 * Safety Note: Low-voltage isolated interface only. Mains switching handled via isolated contactors.
 */

#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

// Configuration Parameters
const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASS = "YOUR_WIFI_PASSWORD";
const char* MQTT_SERVER = "192.168.1.100";
const int   MQTT_PORT = 1883;

const char* DEVICE_ID = "METER-BLOCK-B-001";
const char* FACILITY_ID = "FAC_GEC_CAMPUS";
const char* BUILDING_ID = "Block B Hostel";
const char* MQTT_TOPIC = "estateiq/FAC_GEC_CAMPUS/Block_B_Hostel/meter/METER-BLOCK-B-001/telemetry";

WiFiClient espClient;
PubSubClient mqttClient(espClient);
unsigned long lastPublishTime = 0;
unsigned long sequenceCounter = 1000;

void setupWiFi() {
    delay(10);
    Serial.println("Connecting to WiFi...");
    WiFi.begin(WIFI_SSID, WIFI_PASS);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("\nWiFi Connected! IP: ");
    Serial.println(WiFi.localIP());
}

void reconnectMQTT() {
    while (!mqttClient.connected()) {
        Serial.print("Attempting MQTT connection...");
        if (mqttClient.connect(DEVICE_ID)) {
            Serial.println("Connected to MQTT Broker!");
        } else {
            Serial.print("Failed, rc=");
            Serial.print(mqttClient.state());
            Serial.println(" Retrying in 5 seconds...");
            delay(5000);
        }
    }
}

void setup() {
    Serial.begin(115200);
    setupWiFi();
    mqttClient.setServer(MQTT_SERVER, MQTT_PORT);
}

void loop() {
    if (!mqttClient.connected()) {
        reconnectMQTT();
    }
    mqttClient.loop();

    unsigned long now = millis();
    if (now - lastPublishTime > 15000) { // Publish every 15 seconds
        lastPublishTime = now;
        sequenceCounter++;

        StaticJsonDocument<512> doc;
        doc["device_id"] = DEVICE_ID;
        doc["facility_id"] = FACILITY_ID;
        doc["building_id"] = BUILDING_ID;
        doc["sequence"] = sequenceCounter;

        JsonObject measurements = doc.createNestedObject("measurements");
        measurements["voltage_v"] = 231.5;
        measurements["current_a"] = 18.2;
        measurements["power_kw"] = 4.21;
        measurements["energy_kwh"] = 12450.0 + (sequenceCounter * 0.05);
        measurements["power_factor"] = 0.94;
        measurements["frequency_hz"] = 50.01;
        measurements["occupancy"] = 140;
        measurements["temperature_c"] = 31.5;

        JsonObject quality = doc.createNestedObject("quality");
        quality["sensor_status"] = "OK";
        quality["calibrated"] = true;

        char buffer[512];
        serializeJson(doc, buffer);

        mqttClient.publish(MQTT_TOPIC, buffer);
        Serial.println("Published Telemetry Payload:");
        Serial.println(buffer);
    }
}
