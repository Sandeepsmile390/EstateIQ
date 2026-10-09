"""
Registration & Pairing Manager (simulator/registration.py).
Handles simulator instance pairing with EstateIQ server using one-time pairing codes,
scoped credentials, and virtual device discovery registration.
"""

import socket
import requests
from typing import Dict, Any, List

from simulator.config import GLOBAL_SIM_CONFIG
from simulator.client import GLOBAL_LAN_CLIENT, GLOBAL_TRACKER
from simulator.device_manager import GLOBAL_DEVICE_MANAGER

def get_local_ip() -> str:
    """Detects current machine local network IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

class RegistrationManager:
    """Manages pairing and device registration with EstateIQ backend server."""

    def __init__(self):
        pass

    def pair_and_register(self, server_url: str, pairing_code: str) -> Dict[str, Any]:
        """
        Pairs simulator instance with EstateIQ server using a pairing code,
        obtains auth token, registers simulator metadata, and registers all devices.
        """
        clean_url = server_url.rstrip("/")
        GLOBAL_SIM_CONFIG.set("estateiq_server_url", clean_url)
        GLOBAL_SIM_CONFIG.set("pairing_code", pairing_code)

        # 1. Pair to get auth token
        pair_endpoint = f"{clean_url}/api/v1/iot/pair"
        try:
            resp = requests.post(pair_endpoint, json={"pairing_code": pairing_code}, timeout=5.0)
            if resp.status_code != 200:
                return {"success": False, "error": f"Pairing failed with status {resp.status_code}: {resp.text}"}
            pair_data = resp.json()
            if not pair_data.get("success"):
                return {"success": False, "error": pair_data.get("error", "Pairing rejected")}
            
            auth_token = pair_data.get("auth_token", "")
            GLOBAL_SIM_CONFIG.set("auth_token", auth_token)
        except Exception as e:
            return {"success": False, "error": f"Could not connect to EstateIQ server at {clean_url}: {str(e)}"}

        # 2. Register simulator instance
        reg_endpoint = f"{clean_url}/api/v1/iot/simulators/register"
        instance_id = GLOBAL_SIM_CONFIG.get("instance_id")
        instance_name = GLOBAL_SIM_CONFIG.get("instance_name")
        facility_id = GLOBAL_SIM_CONFIG.get("facility_id")
        building_id = GLOBAL_SIM_CONFIG.get("building_id")
        local_ip = get_local_ip()

        sim_payload = {
            "instance_id": instance_id,
            "name": instance_name,
            "facility_id": facility_id,
            "building_id": building_id,
            "ip_address": local_ip,
            "software_version": "1.0.0-standalone"
        }

        try:
            reg_resp = requests.post(reg_endpoint, json=sim_payload, timeout=5.0)
            if reg_resp.status_code != 200 or not reg_resp.json().get("success"):
                return {"success": False, "error": "Instance registration rejected by backend"}
            
            GLOBAL_SIM_CONFIG.set("registered", True)
            GLOBAL_TRACKER.connection_status = "Registered"
        except Exception as e:
            return {"success": False, "error": f"Simulator instance registration failed: {str(e)}"}

        # 3. Register all virtual devices
        dev_result = self.register_virtual_devices()

        return {
            "success": True,
            "instance_id": instance_id,
            "name": instance_name,
            "auth_token": auth_token,
            "devices_registered": dev_result.get("registered_count", 0),
            "local_ip": local_ip
        }

    def register_virtual_devices(self) -> Dict[str, Any]:
        """Registers all configured virtual devices with EstateIQ server."""
        clean_url = GLOBAL_SIM_CONFIG.get("estateiq_server_url", "http://127.0.0.1:8000").rstrip("/")
        instance_id = GLOBAL_SIM_CONFIG.get("instance_id")
        endpoint = f"{clean_url}/api/v1/iot/simulators/{instance_id}/devices/register"

        devices = GLOBAL_DEVICE_MANAGER.list_devices()
        dev_payloads = [dev.to_dict() for dev in devices]

        try:
            resp = requests.post(endpoint, json=dev_payloads, timeout=5.0)
            if resp.status_code == 200 and resp.json().get("success"):
                return {"success": True, "registered_count": len(dev_payloads)}
            return {"success": False, "error": f"Device registration failed: {resp.text}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def unregister(self) -> Dict[str, Any]:
        """Unregisters simulator instance locally and clears registration flag."""
        GLOBAL_SIM_CONFIG.set("registered", False)
        GLOBAL_SIM_CONFIG.set("auth_token", "")
        GLOBAL_TRACKER.connection_status = "Disconnected"
        return {"success": True, "message": "Simulator instance unregistered locally"}

GLOBAL_REGISTRATION_MANAGER = RegistrationManager()
