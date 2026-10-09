"""
Standalone FastAPI Web Application for IoT Simulator (simulator/app.py).
Serves local web UI interface at http://localhost:8502 and REST API for device control,
scenario injection, network diagnostics, and telemetry monitoring.
"""

import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from simulator.config import GLOBAL_SIM_CONFIG
from simulator.client import GLOBAL_LAN_CLIENT, GLOBAL_TRACKER, GLOBAL_OFFLINE_BUFFER
from simulator.device_manager import GLOBAL_DEVICE_MANAGER, VirtualDevice
from simulator.scenario_engine import GLOBAL_SCENARIO_ENGINE
from simulator.registration import GLOBAL_REGISTRATION_MANAGER, get_local_ip
from simulator.simulation_engine import GLOBAL_SIMULATION_ENGINE

BASE_DIR = Path(__file__).resolve().parent.parent
UI_DIR = BASE_DIR / "ui"
TEMPLATES_DIR = UI_DIR / "templates"
STATIC_DIR = UI_DIR / "static"

TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="EstateIQ Standalone IoT Simulator",
    description="Multi-Device Physics Telemetry Simulator & LAN Integration Engine",
    version="1.0.0"
)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Auto-initialize default virtual devices if inventory is empty
if len(GLOBAL_DEVICE_MANAGER.list_devices()) == 0:
    GLOBAL_DEVICE_MANAGER.initialize_default_devices()

# Auto-start simulation engine
GLOBAL_SIMULATION_ENGINE.start()

class ConfigUpdateRequest(BaseModel):
    instance_name: Optional[str] = None
    estateiq_server_url: Optional[str] = None
    facility_id: Optional[str] = None
    building_id: Optional[str] = None
    sample_interval_sec: Optional[float] = None
    simulation_speed: Optional[float] = None
    active_scenario: Optional[str] = None

class PairRequest(BaseModel):
    server_url: str
    pairing_code: str

class DeviceCreateRequest(BaseModel):
    device_id: str
    name: str
    profile: str
    facility_id: Optional[str] = "FAC_GEC_CAMPUS"
    building_id: Optional[str] = "Block B Hostel"
    sample_interval_sec: Optional[float] = 5.0
    initial_readings: Optional[Dict[str, float]] = None

class DeviceUpdateRequest(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    sensor_overrides: Optional[Dict[str, float]] = None
    active_scenario: Optional[str] = None

class ScenarioApplyRequest(BaseModel):
    scenario_id: str
    target: Optional[str] = "all"  # all, device, building
    target_id: Optional[str] = None

@app.get("/", response_class=HTMLResponse)
def index_page(request: Request):
    """Renders standalone simulator dashboard HTML page."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/status")
def get_status():
    """Returns complete real-time status of simulator instance, network, tracker, and buffer."""
    active_devs = len(GLOBAL_DEVICE_MANAGER.get_active_devices())
    total_devs = len(GLOBAL_DEVICE_MANAGER.list_devices())
    offline_devs = total_devs - active_devs

    return {
        "instance_id": GLOBAL_SIM_CONFIG.get("instance_id"),
        "instance_name": GLOBAL_SIM_CONFIG.get("instance_name"),
        "local_ip": get_local_ip(),
        "estateiq_server_url": GLOBAL_SIM_CONFIG.get("estateiq_server_url"),
        "pairing_code": GLOBAL_SIM_CONFIG.get("pairing_code"),
        "registered": GLOBAL_SIM_CONFIG.get("registered", False),
        "connection_status": GLOBAL_TRACKER.connection_status,
        "last_successful_transmission": GLOBAL_TRACKER.last_successful_transmission,
        "last_heartbeat_at": GLOBAL_TRACKER.last_heartbeat_at,
        "total_configured_devices": total_devs,
        "total_running_devices": active_devs,
        "total_offline_devices": offline_devs,
        "total_telemetry_generated": GLOBAL_TRACKER.total_generated,
        "total_telemetry_accepted": GLOBAL_TRACKER.total_accepted,
        "total_telemetry_rejected": GLOBAL_TRACKER.total_rejected,
        "pending_offline_buffer_count": GLOBAL_OFFLINE_BUFFER.pending_count,
        "active_scenario": GLOBAL_SIM_CONFIG.get("active_scenario", "Normal Campus Operation"),
        "simulation_speed": GLOBAL_SIM_CONFIG.get("simulation_speed", 1),
        "sample_interval_sec": GLOBAL_SIM_CONFIG.get("sample_interval_sec", 5.0),
        "is_engine_running": GLOBAL_SIMULATION_ENGINE.is_running,
        "is_engine_paused": GLOBAL_SIMULATION_ENGINE.is_paused
    }

@app.post("/api/config")
def update_config(req: ConfigUpdateRequest):
    """Updates simulator configuration parameters."""
    if req.instance_name:
        GLOBAL_SIM_CONFIG.set("instance_name", req.instance_name)
    if req.estateiq_server_url:
        GLOBAL_SIM_CONFIG.set("estateiq_server_url", req.estateiq_server_url)
    if req.facility_id:
        GLOBAL_SIM_CONFIG.set("facility_id", req.facility_id)
    if req.building_id:
        GLOBAL_SIM_CONFIG.set("building_id", req.building_id)
    if req.sample_interval_sec is not None:
        GLOBAL_SIM_CONFIG.set("sample_interval_sec", max(0.5, req.sample_interval_sec))
    if req.simulation_speed is not None:
        GLOBAL_SIM_CONFIG.set("simulation_speed", max(0.1, req.simulation_speed))
    if req.active_scenario:
        GLOBAL_SIM_CONFIG.set("active_scenario", req.active_scenario)

    return {"success": True, "config": GLOBAL_SIM_CONFIG.to_dict()}

@app.post("/api/pair")
def pair_simulator(req: PairRequest):
    """Pairs simulator with EstateIQ backend and registers virtual devices."""
    res = GLOBAL_REGISTRATION_MANAGER.pair_and_register(req.server_url, req.pairing_code)
    return res

@app.post("/api/test-connection")
def test_connection():
    """Tests LAN connectivity to EstateIQ server."""
    return GLOBAL_LAN_CLIENT.test_connection()

@app.post("/api/simulation/start")
def start_simulation():
    GLOBAL_SIMULATION_ENGINE.start()
    return {"success": True, "status": "Started"}

@app.post("/api/simulation/pause")
def pause_simulation():
    GLOBAL_SIMULATION_ENGINE.pause()
    return {"success": True, "status": "Paused"}

@app.post("/api/simulation/resume")
def resume_simulation():
    GLOBAL_SIMULATION_ENGINE.resume()
    return {"success": True, "status": "Resumed"}

@app.post("/api/simulation/stop")
def stop_simulation():
    GLOBAL_SIMULATION_ENGINE.stop()
    return {"success": True, "status": "Stopped"}

@app.get("/api/devices")
def list_devices():
    """Lists all virtual devices with recent sensor readings."""
    devs = GLOBAL_DEVICE_MANAGER.list_devices()
    return [dev.to_dict() for dev in devs]

@app.post("/api/devices")
def create_device(req: DeviceCreateRequest):
    """Creates a new virtual device."""
    dev = VirtualDevice(
        device_id=req.device_id,
        name=req.name,
        profile=req.profile,
        facility_id=req.facility_id or GLOBAL_SIM_CONFIG.get("facility_id"),
        building_id=req.building_id or GLOBAL_SIM_CONFIG.get("building_id"),
        sample_interval_sec=req.sample_interval_sec or 5.0,
        initial_readings=req.initial_readings or {}
    )
    GLOBAL_DEVICE_MANAGER.add_device(dev)
    
    # Try registering with backend if already paired
    if GLOBAL_SIM_CONFIG.get("registered"):
        GLOBAL_REGISTRATION_MANAGER.register_virtual_devices()

    return {"success": True, "device": dev.to_dict()}

@app.put("/api/devices/{device_id}")
def update_device(device_id: str, req: DeviceUpdateRequest):
    """Updates device properties or sensor reading overrides from sliders."""
    dev = GLOBAL_DEVICE_MANAGER.get_device(device_id)
    if not dev:
        raise HTTPException(status_code=404, detail="Device not found")

    if req.name:
        dev.name = req.name
    if req.status:
        dev.status = req.status
    if req.active_scenario is not None:
        dev.active_scenario = req.active_scenario
    if req.sensor_overrides:
        for k, v in req.sensor_overrides.items():
            dev.set_sensor_override(k, v)

    # Immediately tick and transmit updated reading to EstateIQ
    if req.sensor_overrides:
        sample = dev.generate_sample()
        scenario_name = dev.active_scenario or GLOBAL_SIM_CONFIG.get("active_scenario", "Normal Campus Operation")
        mod_sample = GLOBAL_SCENARIO_ENGINE.apply_scenario(scenario_name, dev.to_dict(), sample)
        
        now_iso = dev.last_generated_sample.get("timestamp") if dev.last_generated_sample else ""
        metrics_list = [{"metric": k, "value": float(v), "unit": mod_sample.get("units", {}).get(k, ""), "quality": "good"} 
                        for k, v in mod_sample.get("readings", {}).items()]

        envelope = {
            "schema_version": "1.0",
            "message_id": f"MSG_{dev.device_id}_{int(dev.sample_count)}",
            "simulator_id": GLOBAL_SIM_CONFIG.get("instance_id"),
            "device_id": dev.device_id,
            "facility_id": dev.facility_id,
            "building_id": dev.building_id,
            "source_type": "simulated_iot",
            "event_timestamp": now_iso,
            "sent_timestamp": now_iso,
            "sequence_number": dev.sample_count,
            "metrics": metrics_list
        }
        GLOBAL_LAN_CLIENT.send_telemetry(envelope)

    return {"success": True, "device": dev.to_dict()}

@app.delete("/api/devices/{device_id}")
def delete_device(device_id: str):
    """Deletes a virtual device."""
    ok = GLOBAL_DEVICE_MANAGER.remove_device(device_id)
    return {"success": ok}

@app.post("/api/devices/reset-defaults")
def reset_default_devices():
    """Resets virtual device list to standard 9 campus default profiles."""
    GLOBAL_DEVICE_MANAGER.initialize_default_devices()
    if GLOBAL_SIM_CONFIG.get("registered"):
        GLOBAL_REGISTRATION_MANAGER.register_virtual_devices()
    return {"success": True, "devices": [d.to_dict() for d in GLOBAL_DEVICE_MANAGER.list_devices()]}

@app.get("/api/scenarios")
def list_scenarios():
    """Lists available physics & anomaly scenario presets."""
    return GLOBAL_SCENARIO_ENGINE.list_scenarios()

@app.post("/api/scenarios/apply")
def apply_scenario(req: ScenarioApplyRequest):
    """Applies a scenario preset to the simulator or target devices."""
    GLOBAL_SIM_CONFIG.set("active_scenario", req.scenario_id)
    if req.target == "device" and req.target_id:
        dev = GLOBAL_DEVICE_MANAGER.get_device(req.target_id)
        if dev:
            dev.active_scenario = req.scenario_id
    elif req.target == "all":
        for dev in GLOBAL_DEVICE_MANAGER.list_devices():
            dev.active_scenario = req.scenario_id
    return {"success": True, "active_scenario": req.scenario_id}
