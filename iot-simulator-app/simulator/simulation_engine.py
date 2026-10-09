"""
Simulation Engine Loop Manager (simulator/simulation_engine.py).
Runs background telemetry generation loop, advances virtual device sensor models,
applies scenario anomaly modifications, and transmits telemetry packets to EstateIQ LAN API.
"""

import time
import threading
import datetime
from typing import Dict, Any, List, Optional

from simulator.config import GLOBAL_SIM_CONFIG
from simulator.client import GLOBAL_LAN_CLIENT, GLOBAL_TRACKER
from simulator.device_manager import GLOBAL_DEVICE_MANAGER
from simulator.scenario_engine import GLOBAL_SCENARIO_ENGINE

class SimulationEngine:
    """Controls background telemetry loop, device sampling, and heartbeat dispatch."""

    def __init__(self):
        self._running: bool = False
        self._paused: bool = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._last_heartbeat_time: float = 0.0

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def is_paused(self) -> bool:
        return self._paused

    def start(self):
        with self._lock:
            if self._running:
                self._paused = False
                return
            self._running = True
            self._paused = False
            self._thread = threading.Thread(target=self._run_loop, daemon=True, name="SimulationEngineThread")
            self._thread.start()

    def pause(self):
        with self._lock:
            self._paused = True

    def resume(self):
        with self._lock:
            self._paused = False

    def stop(self):
        with self._lock:
            self._running = False
            self._paused = False

    def _run_loop(self):
        """Main loop executed in dedicated background thread."""
        while self._running:
            try:
                sample_interval = float(GLOBAL_SIM_CONFIG.get("sample_interval_sec", 5.0))
                speed = float(GLOBAL_SIM_CONFIG.get("simulation_speed", 1))
                if speed <= 0:
                    speed = 1.0
                effective_interval = max(0.5, sample_interval / speed)

                if not self._paused:
                    self._tick_simulation()

                # Send periodic heartbeat every 10 seconds
                now = time.time()
                if now - self._last_heartbeat_time >= 10.0:
                    self._last_heartbeat_time = now
                    active_count = len(GLOBAL_DEVICE_MANAGER.get_active_devices())
                    curr_scenario = GLOBAL_SIM_CONFIG.get("active_scenario", "Normal Campus Operation")
                    GLOBAL_LAN_CLIENT.send_heartbeat(active_count, curr_scenario)

                time.sleep(effective_interval)
            except Exception as e:
                print(f"Error in simulation loop: {e}")
                time.sleep(2.0)

    def _tick_simulation(self):
        """Generates telemetry samples for all enabled devices and transmits via LAN client."""
        active_devices = GLOBAL_DEVICE_MANAGER.get_active_devices()
        if not active_devices:
            return

        scenario_name = GLOBAL_SIM_CONFIG.get("active_scenario", "Normal Campus Operation")
        instance_id = GLOBAL_SIM_CONFIG.get("instance_id")
        facility_id = GLOBAL_SIM_CONFIG.get("facility_id")

        for dev in active_devices:
            # Generate next physics telemetry sample
            raw_sample = dev.generate_sample()

            # Apply active scenario anomaly modifications
            modified_sample = GLOBAL_SCENARIO_ENGINE.apply_scenario(scenario_name, dev.to_dict(), raw_sample)

            # Build standardized EstateIQ Telemetry Envelope
            metrics_list = []
            for metric_key, val in modified_sample.get("readings", {}).items():
                unit = modified_sample.get("units", {}).get(metric_key, "")
                quality = modified_sample.get("quality", "good")
                metrics_list.append({
                    "metric": metric_key,
                    "value": float(val),
                    "unit": unit,
                    "quality": quality
                })

            now_iso = datetime.datetime.now().isoformat()
            envelope = {
                "schema_version": "1.0",
                "message_id": f"MSG_{dev.device_id}_{int(time.time()*1000)}",
                "simulator_id": instance_id,
                "device_id": dev.device_id,
                "facility_id": dev.facility_id or facility_id,
                "building_id": dev.building_id or "Main Building",
                "source_type": "simulated_iot",
                "event_timestamp": now_iso,
                "sent_timestamp": now_iso,
                "sequence_number": dev.last_generated_sample.get("sequence_number", 0) if dev.last_generated_sample else 1,
                "metrics": metrics_list
            }

            # Transmit to EstateIQ server
            GLOBAL_LAN_CLIENT.send_telemetry(envelope)

GLOBAL_SIMULATION_ENGINE = SimulationEngine()
