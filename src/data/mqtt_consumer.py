"""
MQTT IoT Sensor Telemetry Ingestion Consumer (src/data/mqtt_consumer.py).
Provides hardware readiness for ESP32 / Arduino / Modbus edge gateways.
Subscribes to documented topic hierarchy: estateiq/{facility}/{building}/meter/{device}/telemetry
Validates, normalizes, and ingests telemetry directly through the canonical DeviceRegistryEngine.
"""

import json
import logging
from typing import Dict, Any, Optional, Callable, List

try:
    import paho.mqtt.client as mqtt
    PAHO_AVAILABLE = True
except ImportError:
    PAHO_AVAILABLE = False

from src.data.telemetry_schema import SourceType, resolve_provenance_badge
from src.registry.device_registry import GLOBAL_DEVICE_REGISTRY

logger = logging.getLogger("EstateIQ.MQTT")


def parse_topic_metadata(topic: str) -> Dict[str, str]:
    """
    Extracts facility_id, building_id, and device_id from structured topic:
    estateiq/{facility_id}/{building_id}/meter/{device_id}/telemetry
    or estateiq/telemetry/{device_id}
    """
    parts = topic.strip("/").split("/")
    meta = {}
    if len(parts) >= 6 and parts[0] == "estateiq" and parts[-1] == "telemetry":
        meta["facility_id"] = parts[1]
        meta["building_id"] = parts[2].replace("_", " ")
        meta["device_id"] = parts[4]
    elif len(parts) >= 3 and parts[0] == "estateiq" and parts[1] == "telemetry":
        meta["device_id"] = parts[2]
    return meta


class MQTTTelemetryConsumer:
    """MQTT Client for estateiq/# edge telemetry topics."""

    def __init__(
        self,
        broker_host: str = "localhost",
        broker_port: int = 1883,
        topic_patterns: Optional[List[str]] = None,
        on_message_callback: Optional[Callable[[Dict[str, Any], Dict[str, Any]], None]] = None
    ):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.topic_patterns = topic_patterns or [
            "estateiq/+/+/meter/+/telemetry",
            "estateiq/+/+/sensor/+/telemetry",
            "estateiq/telemetry/+"
        ]
        self.on_message_callback = on_message_callback
        self.client = None
        self.is_connected = False

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.is_connected = True
            logger.info(f"[MQTT] Connected to Broker {self.broker_host}:{self.broker_port}")
            for topic in self.topic_patterns:
                client.subscribe(topic, qos=1)
                logger.info(f"[MQTT] Subscribed to topic: {topic} (QoS 1)")
        else:
            logger.warning(f"[MQTT] Connection failed with code {rc}")

    def process_message_payload(self, topic: str, payload_bytes: bytes) -> Dict[str, Any]:
        """
        Parses, enriches, and ingests MQTT payload through the unified canonical registry.
        Can be invoked directly for unit testing without a live network broker.
        """
        try:
            payload = json.loads(payload_bytes.decode("utf-8"))
        except Exception as e:
            logger.error(f"[MQTT] JSON decode error on topic {topic}: {e}")
            return {"success": False, "error": f"JSON_DECODE_ERROR: {str(e)}"}

        # Extract metadata from topic if missing in JSON body
        topic_meta = parse_topic_metadata(topic)
        for k, v in topic_meta.items():
            if k not in payload or not payload[k]:
                payload[k] = v

        payload["mqtt_topic"] = topic

        # Physical MQTT hardware messages default to REAL_SENSOR provenance unless explicitly tagged
        default_source = SourceType.REAL_SENSOR
        if "source_type" in payload:
            src_str = str(payload["source_type"]).lower()
            if "sim" in src_str:
                default_source = SourceType.SIMULATED_IOT

        ingest_res = GLOBAL_DEVICE_REGISTRY.ingest_telemetry(payload, default_source=default_source)
        logger.info(f"[MQTT] Ingested telemetry from {topic}: status={ingest_res.get('status')}")

        if self.on_message_callback:
            try:
                self.on_message_callback(payload, ingest_res)
            except Exception as cb_err:
                logger.error(f"[MQTT] Error in on_message_callback: {cb_err}")

        return ingest_res

    def on_message(self, client, userdata, msg):
        self.process_message_payload(msg.topic, msg.payload)

    def start(self):
        """Starts MQTT loop asynchronously."""
        if not PAHO_AVAILABLE:
            logger.warning("[MQTT] paho-mqtt is not installed. Running in offline simulated mode.")
            return False
        try:
            self.client = mqtt.Client()
            self.client.on_connect = self.on_connect
            self.client.on_message = self.on_message
            self.client.connect_async(self.broker_host, self.broker_port, 60)
            self.client.loop_start()
            return True
        except Exception as e:
            logger.error(f"[MQTT] Connection error: {e}")
            return False

    def stop(self):
        """Stops MQTT client loop."""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            self.is_connected = False
