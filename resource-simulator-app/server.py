"""
EstateIQ Standalone Resource Simulator Server (resource-simulator-app/server.py).
FastAPI application serving the standalone simulator UI and REST control endpoints on port 8503.
"""

import os
import time
import threading
import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from engine.models import (
    ElectricityState,
    WaterState,
    AirQualityState,
    WasteState,
    GlobalSimulatorConfig,
    SimulatorStatusResponse
)
from engine.physics import (
    update_electricity_physics,
    update_water_physics,
    update_air_quality_physics,
    update_waste_physics
)
from engine.client import build_telemetry_packets, dispatch_telemetry

app = FastAPI(
    title="EstateIQ Multi-Utility Resource Simulator",
    description="Standalone demo telemetry generator for Electricity, Water, Air Quality, and Waste.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Master Simulator Manager Class ---
class StandaloneSimulatorManager:
    def __init__(self):
        self.lock = threading.RLock()
        self.config = GlobalSimulatorConfig()
        self.electricity = ElectricityState()
        self.water = WaterState()
        self.air = AirQualityState()
        self.waste = WasteState()

        self.samples_generated = 0
        self.last_sample_at: Optional[str] = None
        self.backend_connected = False
        self.history_buffer_max = 30
        self.history: Dict[str, Dict[str, List[Any]]] = {
            "electricity": {"time": [], "power": [], "kwh": [], "voltage": []},
            "water": {"time": [], "flow": [], "m3": [], "pressure": []},
            "air": {"time": [], "co2": [], "pm25": [], "aqi": []},
            "waste": {"time": [], "fill": [], "mass": []}
        }

        self._thread: Optional[threading.Thread] = None
        self._running = False

    def start_loop(self):
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()

    def _loop(self):
        while self._running:
            time.sleep(max(0.5, self.config.sample_interval_sec))
            if self.config.global_running:
                try:
                    self.step()
                except Exception:
                    pass

    def stop_loop(self):
        self._running = False

    def step(self):
        with self.lock:
            dt = self.config.sample_interval_sec
            update_electricity_physics(self.electricity, dt)
            update_water_physics(self.water, dt)
            update_air_quality_physics(self.air, dt)
            update_waste_physics(self.waste, dt)

            self.samples_generated += 1
            now_dt = datetime.datetime.now()
            now_str = now_dt.strftime("%H:%M:%S")
            self.last_sample_at = now_dt.isoformat()

            # Record history buffers
            eh = self.history["electricity"]
            eh["time"].append(now_str)
            eh["power"].append(self.electricity.active_power_kw)
            eh["kwh"].append(self.electricity.cumulative_energy_kwh)
            eh["voltage"].append(self.electricity.voltage_v)

            wh = self.history["water"]
            wh["time"].append(now_str)
            wh["flow"].append(self.water.flow_rate_lmin)
            wh["m3"].append(self.water.cumulative_water_m3)
            wh["pressure"].append(self.water.water_pressure_bar)

            ah = self.history["air"]
            ah["time"].append(now_str)
            ah["co2"].append(self.air.co2_ppm)
            ah["pm25"].append(self.air.pm25)
            ah["aqi"].append(self.air.air_quality_aqi)

            wsth = self.history["waste"]
            wsth["time"].append(now_str)
            wsth["fill"].append(self.waste.fill_level_percent)
            wsth["mass"].append(self.waste.estimated_waste_kg)

            # Trim history to max size
            for category in self.history.values():
                for lst in category.values():
                    if len(lst) > self.history_buffer_max:
                        lst.pop(0)

            # Ingest to EstateIQ backend if auto_ingest enabled
            if self.config.auto_ingest:
                packets = build_telemetry_packets(
                    self.electricity, self.water, self.air, self.waste
                )
                ok, count, _ = dispatch_telemetry(packets, self.config.backend_url)
                self.backend_connected = ok

    def reset_defaults(self):
        with self.lock:
            self.electricity.baseline_kw = 55.0
            self.electricity.scenario = "NORMAL"
            self.electricity.cumulative_energy_kwh = 3420.5
            self.electricity.running = True

            self.water.baseline_lmin = 35.0
            self.water.scenario = "NORMAL"
            self.water.cumulative_water_m3 = 842.15
            self.water.running = True

            self.air.baseline_occupancy = 120
            self.air.scenario = "NORMAL"
            self.air.running = True

            self.waste.accumulation_rate_pct = 2.5
            self.waste.scenario = "NORMAL"
            self.waste.fill_level_percent = 38.0
            self.waste.running = True

    def get_status(self) -> Dict[str, Any]:
        with self.lock:
            status_str = "RUNNING" if self.config.global_running else "PAUSED"
            return {
                "status": status_str,
                "global_running": self.config.global_running,
                "sample_interval_sec": self.config.sample_interval_sec,
                "samples_generated": self.samples_generated,
                "last_sample_at": self.last_sample_at,
                "backend_url": self.config.backend_url,
                "backend_connected": self.backend_connected,
                "auto_ingest": self.config.auto_ingest,
                "electricity": self.electricity.dict(),
                "water": self.water.dict(),
                "air": self.air.dict(),
                "waste": self.waste.dict(),
                "provenance_badge": "[SIMULATED DATA]",
                "is_verified_hardware": False
            }

SIMULATOR = StandaloneSimulatorManager()

# --- Request Schemas ---
class ScenarioRequest(BaseModel):
    utility: str  # electricity, water, air, waste
    scenario: str

class BaselineConfigRequest(BaseModel):
    utility: str
    value: float

class IntervalConfigRequest(BaseModel):
    interval_sec: float

# --- REST Endpoints ---
@app.on_event("startup")
def startup_event():
    if os.environ.get("TESTING") != "1":
        SIMULATOR.start_loop()

@app.get("/health")
def health():
    return {"status": "ok", "app": "EstateIQ-Standalone-Resource-Simulator", "port": 8503}

@app.get("/api/status")
def get_status():
    return SIMULATOR.get_status()

@app.post("/api/start")
def start_simulation(utility: Optional[str] = None):
    with SIMULATOR.lock:
        if not utility or utility == "all":
            SIMULATOR.config.global_running = True
            SIMULATOR.electricity.running = True
            SIMULATOR.water.running = True
            SIMULATOR.air.running = True
            SIMULATOR.waste.running = True
        elif utility == "electricity": SIMULATOR.electricity.running = True
        elif utility == "water": SIMULATOR.water.running = True
        elif utility == "air": SIMULATOR.air.running = True
        elif utility == "waste": SIMULATOR.waste.running = True
    return {"success": True, "message": f"Started {utility or 'all'}"}

@app.post("/api/pause")
def pause_simulation(utility: Optional[str] = None):
    with SIMULATOR.lock:
        if not utility or utility == "all":
            SIMULATOR.config.global_running = not SIMULATOR.config.global_running
        elif utility == "electricity": SIMULATOR.electricity.running = not SIMULATOR.electricity.running
        elif utility == "water": SIMULATOR.water.running = not SIMULATOR.water.running
        elif utility == "air": SIMULATOR.air.running = not SIMULATOR.air.running
        elif utility == "waste": SIMULATOR.waste.running = not SIMULATOR.waste.running
    return {"success": True, "status": SIMULATOR.config.global_running}

@app.post("/api/stop")
def stop_simulation():
    with SIMULATOR.lock:
        SIMULATOR.config.global_running = False
        SIMULATOR.electricity.running = False
        SIMULATOR.water.running = False
        SIMULATOR.air.running = False
        SIMULATOR.waste.running = False
    return {"success": True, "message": "All simulators stopped"}

@app.post("/api/step")
def step_simulation():
    SIMULATOR.step()
    return {"success": True, "samples_generated": SIMULATOR.samples_generated}

@app.post("/api/reset")
def reset_simulation(utility: Optional[str] = None):
    with SIMULATOR.lock:
        if not utility or utility == "all":
            SIMULATOR.reset_defaults()
        elif utility == "electricity":
            SIMULATOR.electricity.cumulative_energy_kwh = 3420.5
        elif utility == "water":
            SIMULATOR.water.cumulative_water_m3 = 842.15
        elif utility == "waste":
            SIMULATOR.waste.scenario = "RESET_EMPTIED"
            update_waste_physics(SIMULATOR.waste, 5.0)
    return {"success": True, "message": f"Reset {utility or 'defaults'}"}

@app.post("/api/scenario")
def set_scenario(req: ScenarioRequest):
    with SIMULATOR.lock:
        u = req.utility.lower()
        if u == "electricity": SIMULATOR.electricity.scenario = req.scenario
        elif u == "water": SIMULATOR.water.scenario = req.scenario
        elif u == "air": SIMULATOR.air.scenario = req.scenario
        elif u == "waste": SIMULATOR.waste.scenario = req.scenario
        else:
            raise HTTPException(status_code=400, detail=f"Unknown utility: {req.utility}")
    return {"success": True, "utility": req.utility, "scenario": req.scenario}

@app.post("/api/config/baseline")
def set_baseline(req: BaselineConfigRequest):
    with SIMULATOR.lock:
        u = req.utility.lower()
        if u == "electricity": SIMULATOR.electricity.baseline_kw = max(5.0, req.value)
        elif u == "water": SIMULATOR.water.baseline_lmin = max(1.0, req.value)
        elif u == "air": SIMULATOR.air.baseline_occupancy = int(max(0, req.value))
        elif u == "waste": SIMULATOR.waste.accumulation_rate_pct = max(0.1, req.value)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown utility: {req.utility}")
    return {"success": True, "utility": req.utility, "value": req.value}

@app.post("/api/config/interval")
def set_interval(req: IntervalConfigRequest):
    with SIMULATOR.lock:
        val = max(0.5, min(60.0, req.interval_sec))
        SIMULATOR.config.sample_interval_sec = val
    return {"success": True, "interval_sec": val}

@app.get("/api/stream")
def get_stream():
    with SIMULATOR.lock:
        return {
            "timestamp": datetime.datetime.now().isoformat(),
            "history": SIMULATOR.history
        }

# Mount static files
static_dir = Path(__file__).resolve().parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

@app.get("/")
def serve_index():
    index_file = static_dir / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "EstateIQ Standalone Resource Simulator API Running. Visit /docs for API schema."}
