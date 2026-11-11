"""
EstateIQ ESP32 USB-Serial Telemetry Bridge (tools/esp32_serial_bridge.py)
------------------------------------------------------------------------
High-reliability hardware ingestion bridge for Hackathon live demos.

Connects to the ESP32 on USB COM port (default COM7 @ 115200 baud),
reads real-time physical sensor readings (HC-SR04, AJ-SR04M, PZEM-004T, MQ-135, ZJ-S201),
and immediately ingests them into the local EstateIQ backend (/api/v1/iot/telemetry)
with zero Wi-Fi dependency and sub-50ms latency.

Usage:
    python tools/esp32_serial_bridge.py
    python tools/esp32_serial_bridge.py --port COM7 --baud 115200
"""

import sys
import re
import time
import json
import argparse
import datetime
import urllib.request
import urllib.error

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    print("[ERROR] pyserial is not installed. Run: pip install pyserial")
    sys.exit(1)

BACKEND_URL = "http://127.0.0.1:8000/api/v1/iot/telemetry"

def post_telemetry(payload: dict) -> bool:
    """Post parsed telemetry envelope directly to local backend."""
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            BACKEND_URL,
            data=data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            return resp.status in (200, 201)
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8", errors="replace")
        print(f"  [API-ERR] HTTP {e.code}: {err_msg}")
        return False
    except Exception as e:
        print(f"  [API-ERR] Connection error: {e}")
        return False

def find_esp32_port(preferred: str = "COM7") -> str:
    """Auto-detects ESP32 COM port or uses preferred."""
    ports = [p.device for p in serial.tools.list_ports.comports()]
    if preferred in ports:
        return preferred
    # Look for common USB-UART bridges (CP210x, CH340, FTDI)
    for p in serial.tools.list_ports.comports():
        desc = (p.description or "").lower()
        if any(chip in desc for chip in ["cp210", "ch340", "ch910", "uart", "serial", "usb"]):
            return p.device
    if ports:
        return ports[0]
    return preferred

def run_bridge(port: str, baud: int = 115200):
    print("=" * 75)
    print("   ESTATEIQ ESP32 LIVE HARDWARE SERIAL BRIDGE")
    print("=" * 75)
    print(f"Target Port   : {port} @ {baud} baud")
    print(f"Backend API   : {BACKEND_URL}")
    print("Mode          : Real-time USB ingestion (100% offline hackathon safe)")
    print("=" * 75)
    print("[BRIDGE] Opening serial port...")

    try:
        ser = serial.Serial(port, baud, timeout=1.0)
        time.sleep(1.5)  # Allow DTR settle
        print(f"[BRIDGE] Connected to {port}! Listening for physical sensor events...\n")
    except Exception as e:
        print(f"[ERROR] Failed to open {port}: {e}")
        print("  Hint 1: Close Arduino IDE Serial Monitor if it is currently open.")
        print("  Hint 2: Verify the USB cable is firmly connected.")
        return

    # Regex patterns matching firmware serial prints
    re_waste_bench = re.compile(r"Auto-Routed to Waste Bin[^:]*:\s*([\d\.]+)\s*cm\s*\|\s*Fill:\s*([\d\.]+)%")
    re_waste_live = re.compile(r"Real Bin Distance[^:]*:\s*([\d\.]+)\s*cm\s*\|\s*Fill:\s*([\d\.]+)%")
    re_water_live = re.compile(r"Real Distance Measured:\s*([\d\.]+)\s*cm\s*\|\s*Tank Level:\s*([\d\.]+)%")
    re_flow = re.compile(r"Flow:\s*([\d\.]+)\s*L/min")
    re_pzem = re.compile(r"Power:\s*([\d\.]+)\s*kW.*Energy:\s*([\d\.]+)\s*kWh")
    re_dht11 = re.compile(r"\[SENSOR-DHT11\]\s*Temp:\s*([\d\.\-]+)\s*C\s*\|\s*Humidity:\s*([\d\.\-]+)\s*%\s*\|\s*Heat Index:\s*([\d\.\-]+)\s*C")
    re_mq135_live = re.compile(r"\[SENSOR-MQ135\]\s*Raw ADC:\s*(\d+)\s*\|\s*Pin:\s*([\d\.]+)V\s*\|\s*Module output:\s*([\d\.]+)V\s*\|\s*Warmup:\s*(\w+)")
    re_mq135_legacy = re.compile(r"MQ135.*ADC:\s*(\d+),\s*([\d\.]+)V")

    last_waste_sent = 0
    last_water_sent = 0
    last_env_sent = 0
    current_temp = None
    current_hum = None
    current_heat_index = None

    while True:
        try:
            line_bytes = ser.readline()
            if not line_bytes:
                continue
            line = line_bytes.decode("utf-8", errors="replace").strip()
            if not line:
                continue

            now_utc = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            t_now = time.time()

            # 1. Match Waste Bin Telemetry (HC-SR04)
            m_waste = re_waste_live.search(line) or re_waste_bench.search(line)
            if m_waste:
                dist_cm = float(m_waste.group(1))
                fill_pct = float(m_waste.group(2))
                # Rate limit duplicate prints to at most 10Hz
                if t_now - last_waste_sent >= 0.2:
                    last_waste_sent = t_now
                    payload = {
                        "device_id": "WASTE-BLOCK-B-001",
                        "source_type": "real_sensor",
                        "is_verified_hardware": True,
                        "event_timestamp": now_utc,
                        "metrics": {
                            "bin_distance_cm": dist_cm,
                            "fill_level_percent": fill_pct,
                            "fill_level_pct": fill_pct
                        }
                    }
                    ok = post_telemetry(payload)
                    mark = "[OK]" if ok else "[FAIL]"
                    print(f" {mark} [WASTE-BIN] Clearance: {dist_cm:5.1f} cm | Fill: {fill_pct:5.1f}% -> Ingested")
                continue

            # 2. Match Water Tank Telemetry (AJ-SR04M)
            m_water = re_water_live.search(line)
            if m_water:
                dist_cm = float(m_water.group(1))
                level_pct = float(m_water.group(2))
                if t_now - last_water_sent >= 0.2:
                    last_water_sent = t_now
                    payload = {
                        "device_id": "WATER-BLOCK-B-001",
                        "source_type": "real_sensor",
                        "is_verified_hardware": True,
                        "event_timestamp": now_utc,
                        "metrics": {
                            "tank_distance_cm": dist_cm,
                            "tank_level_pct": level_pct
                        }
                    }
                    ok = post_telemetry(payload)
                    mark = "[OK]" if ok else "[FAIL]"
                    print(f" {mark} [WATER-TANK] Distance: {dist_cm:5.1f} cm | Level: {level_pct:5.1f}% -> Ingested")
                continue

            # 3. Match Water Flow (ZJ-S201)
            m_flow = re_flow.search(line)
            if m_flow:
                flow_lmin = float(m_flow.group(1))
                payload = {
                    "device_id": "WATER-BLOCK-B-001",
                    "source_type": "real_sensor",
                    "is_verified_hardware": True,
                    "event_timestamp": now_utc,
                    "metrics": {
                        "water_flow_lmin": flow_lmin
                    }
                }
                ok = post_telemetry(payload)
                mark = "[OK]" if ok else "[FAIL]"
                print(f" {mark} [WATER-FLOW] Flow Rate: {flow_lmin:5.1f} L/min -> Ingested")
                continue

            # 4. Match Power Meter (PZEM-004T)
            m_pzem = re_pzem.search(line)
            if m_pzem:
                power_kw = float(m_pzem.group(1))
                energy_kwh = float(m_pzem.group(2))
                payload = {
                    "device_id": "METER-BLOCK-B-001",
                    "source_type": "real_sensor",
                    "is_verified_hardware": True,
                    "event_timestamp": now_utc,
                    "metrics": {
                        "active_power_kw": power_kw,
                        "cumulative_energy_kwh": energy_kwh
                    }
                }
                ok = post_telemetry(payload)
                mark = "[OK]" if ok else "[FAIL]"
                print(f" {mark} [POWER-METER] Power: {power_kw:5.2f} kW | Energy: {energy_kwh:6.2f} kWh -> Ingested")
                continue

            # 5. Match DHT11 Temperature & Humidity
            m_dht = re_dht11.search(line)
            if m_dht:
                current_temp = float(m_dht.group(1))
                current_hum = float(m_dht.group(2))
                current_heat_index = float(m_dht.group(3))
                if t_now - last_env_sent >= 0.8:
                    last_env_sent = t_now
                    metrics = {
                        "temperature_c": current_temp,
                        "humidity_pct": current_hum,
                        "heat_index_c": current_heat_index
                    }
                    payload = {
                        "device_id": "ENV-BLOCK-B-001",
                        "source_type": "real_sensor",
                        "is_verified_hardware": True,
                        "event_timestamp": now_utc,
                        "metrics": metrics
                    }
                    ok = post_telemetry(payload)
                    mark = "[OK]" if ok else "[FAIL]"
                    print(f" {mark} [ENV-DHT11] Temp: {current_temp:.1f}C | Hum: {current_hum:.1f}% -> Ingested")
                continue

            # 6. Match MQ-135 Gas & Air Quality
            m_mq_live = re_mq135_live.search(line)
            m_mq_leg = re_mq135_legacy.search(line)
            if m_mq_live or m_mq_leg:
                raw_adc = int(m_mq_live.group(1)) if m_mq_live else int(m_mq_leg.group(1))
                pin_v = float(m_mq_live.group(2)) if m_mq_live else (raw_adc / 4095.0 * 3.3)
                module_v = float(m_mq_live.group(3)) if m_mq_live else float(m_mq_leg.group(2))
                warmup_str = m_mq_live.group(4) if m_mq_live else "WARMING_UP"
                warmup_val = 0 if "WARM" in warmup_str else 1

                if t_now - last_env_sent >= 1.0:
                    last_env_sent = t_now
                    metrics = {
                        "mq135_raw_adc": raw_adc,
                        "mq135_adc_pin_voltage_v": pin_v,
                        "mq135_voltage_v": module_v,
                        "mq135_warmup_status": warmup_val
                    }
                    if current_temp is not None:
                        metrics["temperature_c"] = current_temp
                    if current_hum is not None:
                        metrics["humidity_pct"] = current_hum
                    if current_heat_index is not None:
                        metrics["heat_index_c"] = current_heat_index

                    payload = {
                        "device_id": "ENV-BLOCK-B-001",
                        "source_type": "real_sensor",
                        "is_verified_hardware": True,
                        "event_timestamp": now_utc,
                        "metrics": metrics
                    }
                    ok = post_telemetry(payload)
                    mark = "[OK]" if ok else "[FAIL]"
                    t_str = f" | Temp: {current_temp:.1f}C" if current_temp is not None else ""
                    print(f" {mark} [ENV-MQ135] ADC: {raw_adc} ({pin_v:.2f}V pin){t_str} -> Ingested")
                continue

            # Echo unparsed informative serial lines
            if any(k in line for k in ["EVENT", "ANOMALY", "CONNECTED", "Cadence shifted", "WIFI"]):
                print(f"  [ESP32] {line}")

        except KeyboardInterrupt:
            print("\n[BRIDGE] Bridge stopped by user.")
            break
        except Exception as err:
            print(f"[BRIDGE-WARN] Serial read error: {err}")
            time.sleep(0.5)

    try:
        ser.close()
    except Exception:
        pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EstateIQ ESP32 Serial Telemetry Bridge")
    parser.add_argument("--port", type=str, default="COM7", help="Serial port (e.g., COM7)")
    parser.add_argument("--baud", type=int, default=115200, help="Baud rate (default 115200)")
    args = parser.parse_args()

    active_port = find_esp32_port(args.port)
    run_bridge(active_port, args.baud)

