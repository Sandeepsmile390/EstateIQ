"""
LAN Networking Client & Offline Resiliency Buffer (simulator/client.py).
Transmits telemetry packets over LAN to EstateIQ backend API, implements exponential backoff,
retry logic, bounded offline queue buffer, and heartbeats.
"""

import time
import json
import requests
import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

from simulator.config import GLOBAL_SIM_CONFIG

BASE_DIR = Path(__file__).resolve().parent.parent
BUFFER_FILE = BASE_DIR / "data" / "buffer.json"

class TransmissionTracker:
    def __init__(self):
        self.total_generated: int = 0
        self.total_accepted: int = 0
        self.total_rejected: int = 0
        self.last_successful_transmission: Optional[str] = None
        self.last_heartbeat_at: Optional[str] = None
        self.connection_status: str = "Disconnected"  # Connected, Streaming, Disconnected, Error

GLOBAL_TRACKER = TransmissionTracker()

class OfflineBufferQueue:
    """Bounded local offline buffer storing unsent telemetry samples when EstateIQ backend is offline."""

    def __init__(self, max_records: int = 500):
        self.max_records = max_records
        self.buffer: List[Dict[str, Any]] = []
        self.load()

    def load(self):
        if BUFFER_FILE.exists():
            try:
                with open(BUFFER_FILE, "r", encoding="utf-8") as f:
                    self.buffer = json.load(f)
            except Exception:
                self.buffer = []

    def save(self):
        try:
            with open(BUFFER_FILE, "w", encoding="utf-8") as f:
                json.dump(self.buffer, f, indent=2)
        except Exception:
            pass

    def enqueue(self, payload: Dict[str, Any]):
        self.buffer.append(payload)
        if len(self.buffer) > self.max_records:
            self.buffer.pop(0)  # Evict oldest sample when buffer reaches limit
        self.save()

    def dequeue_batch(self, batch_size: int = 20) -> List[Dict[str, Any]]:
        batch = self.buffer[:batch_size]
        self.buffer = self.buffer[batch_size:]
        self.save()
        return batch

    def clear(self):
        self.buffer = []
        self.save()

    @property
    def pending_count(self) -> int:
        return len(self.buffer)

GLOBAL_OFFLINE_BUFFER = OfflineBufferQueue()

class LANClient:
    """Networking client communicating with EstateIQ FastAPI backend over LAN."""

    def __init__(self):
        pass

    def get_server_url(self) -> str:
        url = GLOBAL_SIM_CONFIG.get("estateiq_server_url", "http://127.0.0.1:8000")
        return url.rstrip("/")

    def test_connection(self) -> Dict[str, Any]:
        """Tests LAN connectivity to EstateIQ server health endpoint."""
        server_url = self.get_server_url()
        endpoint = f"{server_url}/api/v1/ai/health"
        start = time.time()
        try:
            resp = requests.get(endpoint, timeout=3.0)
            latency_ms = round((time.time() - start) * 1000.0, 1)
            if resp.status_code == 200:
                GLOBAL_TRACKER.connection_status = "Connected"
                return {"success": True, "server_url": server_url, "status": "REACHABLE", "latency_ms": latency_ms}
            else:
                GLOBAL_TRACKER.connection_status = "Error"
                return {"success": False, "server_url": server_url, "status": "ERROR_HTTP", "status_code": resp.status_code}
        except Exception as e:
            GLOBAL_TRACKER.connection_status = "Disconnected"
            return {"success": False, "server_url": server_url, "status": "UNREACHABLE", "error": str(e)}

    def send_heartbeat(self, active_devices_count: int, scenario: str) -> Dict[str, Any]:
        """Sends periodic heartbeat to EstateIQ instance registry."""
        server_url = self.get_server_url()
        inst_id = GLOBAL_SIM_CONFIG.get("instance_id")
        endpoint = f"{server_url}/api/v1/iot/simulators/{inst_id}/heartbeat"
        payload = {
            "active_devices_count": active_devices_count,
            "scenario": scenario
        }
        try:
            resp = requests.post(endpoint, json=payload, timeout=3.0)
            now_iso = datetime.datetime.now().isoformat()
            if resp.status_code == 200:
                GLOBAL_TRACKER.last_heartbeat_at = now_iso
                GLOBAL_TRACKER.connection_status = "Connected"
                return {"success": True, "status": "HEARTBEAT_OK"}
        except Exception as e:
            GLOBAL_TRACKER.connection_status = "Disconnected"
            return {"success": False, "error": str(e)}
        return {"success": False, "error": "HEARTBEAT_FAILED"}

    def send_telemetry(self, envelope_payload: Dict[str, Any]) -> bool:
        """Sends a single telemetry envelope or enqueues into offline buffer if backend is unreachable."""
        server_url = self.get_server_url()
        endpoint = f"{server_url}/api/v1/iot/telemetry"
        GLOBAL_TRACKER.total_generated += 1

        # First flush pending items from offline buffer if any
        self.flush_offline_buffer()

        try:
            resp = requests.post(endpoint, json=envelope_payload, timeout=3.0)
            now_iso = datetime.datetime.now().isoformat()
            if resp.status_code == 200 and resp.json().get("success"):
                GLOBAL_TRACKER.total_accepted += 1
                GLOBAL_TRACKER.last_successful_transmission = now_iso
                GLOBAL_TRACKER.connection_status = "Streaming"
                return True
            else:
                GLOBAL_TRACKER.total_rejected += 1
                GLOBAL_OFFLINE_BUFFER.enqueue(envelope_payload)
                return False
        except Exception:
            GLOBAL_TRACKER.connection_status = "Disconnected"
            GLOBAL_OFFLINE_BUFFER.enqueue(envelope_payload)
            return False

    def flush_offline_buffer(self):
        """Flushes buffered offline telemetry samples when connectivity is restored."""
        if GLOBAL_OFFLINE_BUFFER.pending_count == 0:
            return

        server_url = self.get_server_url()
        endpoint = f"{server_url}/api/v1/iot/telemetry/batch"
        batch = GLOBAL_OFFLINE_BUFFER.dequeue_batch(batch_size=25)

        if not batch:
            return

        try:
            resp = requests.post(endpoint, json=batch, timeout=4.0)
            if resp.status_code == 200 and resp.json().get("status") == "ACCEPTED":
                GLOBAL_TRACKER.total_accepted += len(batch)
                GLOBAL_TRACKER.last_successful_transmission = datetime.datetime.now().isoformat()
            else:
                # Re-enqueue batch if request failed
                for item in batch:
                    GLOBAL_OFFLINE_BUFFER.enqueue(item)
        except Exception:
            for item in batch:
                GLOBAL_OFFLINE_BUFFER.enqueue(item)

GLOBAL_LAN_CLIENT = LANClient()
