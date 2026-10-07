"""
MQTT IoT Sensor Telemetry Ingestion Consumer.
Provides hardware readiness for ESP32 / Arduino IoT sensor gateways.
Parses inbound MQTT payload topics (estateiq/telemetry/+) and ingests into EstateIQ DataRepository.
"""

import json
import logging
from typing import Dict, Any, Optional, Callable

try:
    import paho.mqtt.client as mqtt
    PAHO_AVAILABLE = True
except ImportError:
    PAHO_AVAILABLE = False

logger = logging.getLogger("EstateIQ.MQTT")

class MQTTTelemetryConsumer:
    """MQTT Client Wrapper for estateiq/telemetry/# topics."""
    
    def __init__(
        self,
        broker_host: str = "localhost",
        broker_port: int = 1883,
        topic_prefix: str = "estateiq/telemetry/#",
        on_message_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.topic_prefix = topic_prefix
        self.on_message_callback = on_message_callback
        self.client = None
        self.is_connected = False

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.is_connected = True
            logger.info(f"[MQTT] Connected to Broker {self.broker_host}:{self.broker_port}")
            client.subscribe(self.topic_prefix)
        else:
            logger.warning(f"[MQTT] Connection failed with code {rc}")

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            payload["mqtt_topic"] = msg.topic
            payload["provenance"] = "LIVE_HARDWARE_MQTT"
            logger.info(f"[MQTT] Received telemetry on {msg.topic}: {payload}")
            
            if self.on_message_callback:
                self.on_message_callback(payload)
        except Exception as e:
            logger.error(f"[MQTT] Error parsing payload on {msg.topic}: {e}")

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
