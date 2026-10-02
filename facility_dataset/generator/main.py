"""
Master Facility Dataset Orchestrator.
Executes end-to-end dataset generation for 180 days (Jan-June 2026) at 15-minute resolution.
Creates facility.db (SQLite), data_dictionary.csv, and outputs comprehensive summary statistics.

Usage:
    python generator/main.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import sqlite3
import pandas as pd
from pathlib import Path

from generator.config import (
    RAW_DATA_DIR, ML_DATA_DIR, REPORTS_DIR, DB_PATH, BASE_DIR, logger
)
from generator.facility_generator import generate_facility_metadata
from generator.event_generator import generate_events
from generator.weather_generator import generate_weather
from generator.occupancy_generator import generate_occupancy
from generator.energy_generator import generate_energy
from generator.water_generator import generate_water
from generator.waste_generator import generate_waste
from generator.air_quality_generator import generate_air_quality
from generator.traffic_generator import generate_traffic
from generator.parking_generator import generate_parking
from generator.equipment_generator import generate_equipment
from generator.safety_generator import generate_safety
from generator.emissions_generator import generate_emissions
from generator.anomaly_generator import inject_anomalies
from generator.ml_dataset_generator import generate_ml_datasets
from generator.validator import validate_and_report

def create_data_dictionary():
    logger.info("Generating Data Dictionary (data_dictionary.csv)...")
    
    dictionary = [
        # Energy
        {"dataset": "energy_readings", "column": "electricity_kwh", "datatype": "float", "unit": "kWh", "description": "Total 15-min building electricity consumption", "source_type": "synthetic", "generated_or_derived": "generated", "allowed_range": ">=0"},
        {"dataset": "energy_readings", "column": "hvac_kwh", "datatype": "float", "unit": "kWh", "description": "HVAC sub-meter electricity consumption", "source_type": "synthetic", "generated_or_derived": "generated", "allowed_range": ">=0"},
        {"dataset": "energy_readings", "column": "power_factor", "datatype": "float", "unit": "ratio", "description": "Electrical power factor", "source_type": "synthetic", "generated_or_derived": "generated", "allowed_range": "0.70-1.00"},
        # Water
        {"dataset": "water_readings", "column": "water_consumption_liters", "datatype": "float", "unit": "Liters", "description": "15-min building water usage", "source_type": "synthetic", "generated_or_derived": "generated", "allowed_range": ">=0"},
        {"dataset": "water_readings", "column": "water_flow_rate_lpm", "datatype": "float", "unit": "LPM", "description": "Water flow rate in Liters Per Minute", "source_type": "synthetic", "generated_or_derived": "generated", "allowed_range": ">=0"},
        # Waste
        {"dataset": "waste_readings", "column": "fill_level_percent", "datatype": "float", "unit": "%", "description": "Waste bin fill percentage", "source_type": "synthetic", "generated_or_derived": "generated", "allowed_range": "0-100"},
        {"dataset": "waste_readings", "column": "overflow_within_2h", "datatype": "int", "unit": "binary", "description": "Target: Bin overflow in next 2 hours", "source_type": "synthetic", "generated_or_derived": "derived", "allowed_range": "0 or 1"},
        # Air Quality
        {"dataset": "air_quality_readings", "column": "pm25", "datatype": "float", "unit": "µg/m³", "description": "Particulate matter PM2.5 concentration", "source_type": "synthetic", "generated_or_derived": "generated", "allowed_range": ">=0"},
        {"dataset": "air_quality_readings", "column": "aqi", "datatype": "float", "unit": "index", "description": "CPCB Indian Air Quality Index proxy", "source_type": "synthetic", "generated_or_derived": "derived", "allowed_range": "0-500"},
        # Traffic & Parking
        {"dataset": "traffic_readings", "column": "vehicle_count", "datatype": "int", "unit": "vehicles", "description": "Count of vehicles passed in 15-min interval", "source_type": "synthetic", "generated_or_derived": "generated", "allowed_range": ">=0"},
        {"dataset": "parking_readings", "column": "occupancy_percent", "datatype": "float", "unit": "%", "description": "Parking zone occupied space ratio", "source_type": "synthetic", "generated_or_derived": "derived", "allowed_range": "0-100"},
        # Equipment
        {"dataset": "equipment_sensor_readings", "column": "vibration_mm_s", "datatype": "float", "unit": "mm/s", "description": "Equipment vibration amplitude", "source_type": "synthetic", "generated_or_derived": "generated", "allowed_range": ">=0"},
        {"dataset": "equipment_sensor_readings", "column": "maintenance_risk_score", "datatype": "float", "unit": "score", "description": "Predictive maintenance risk indicator", "source_type": "synthetic", "generated_or_derived": "derived", "allowed_range": "0.0-1.0"}
    ]
    
    df_dict = pd.DataFrame(dictionary)
    df_dict.to_csv(BASE_DIR / "data_dictionary.csv", index=False)
    logger.info("Data dictionary saved to data_dictionary.csv.")

def build_sqlite_database():
    logger.info("Building SQLite database (facility.db)...")
    
    conn = sqlite3.connect(DB_PATH)
    
    raw_files = [
        "facilities.csv", "buildings.csv", "locations.csv", "assets.csv",
        "events.csv", "weather_readings.csv", "occupancy_readings.csv",
        "energy_readings.csv", "water_readings.csv", "waste_readings.csv",
        "air_quality_readings.csv", "traffic_readings.csv", "parking_readings.csv",
        "equipment_sensor_readings.csv", "safety_incidents.csv", "emissions.csv"
    ]
    
    for f in raw_files:
        p = RAW_DATA_DIR / f
        if p.exists():
            tbl_name = f.replace(".csv", "")
            df = pd.read_csv(p)
            df.to_sql(tbl_name, conn, if_exists="replace", index=False)
            logger.info("Imported table '%s' (%d rows) into facility.db", tbl_name, len(df))
            
    conn.close()
    logger.info("SQLite database built successfully at facility.db.")

def run_master_generation():
    start_time_sec = time.time()
    
    print("\n==================================================")
    print("  GEC SMART CAMPUS IOT SYNTHETIC DATASET GENERATOR")
    print("==================================================\n")
    
    # 1. Metadata & Events
    generate_facility_metadata()
    generate_events()
    
    # 2. Base Physics Feeds
    df_w = generate_weather()
    df_o = generate_occupancy()
    
    # 3. Connected Module Feeds
    df_e = generate_energy(df_w, df_o)
    df_wat = generate_water(df_o)
    df_wst = generate_waste(df_o)
    df_air = generate_air_quality(df_w)
    df_tr = generate_traffic(df_w, df_o)
    df_prk = generate_parking(df_tr)
    df_eq = generate_equipment()
    df_sf = generate_safety()
    df_em = generate_emissions(df_e, df_tr)
    
    # 4. Inject Anomaly Ground-Truth Scenarios
    inject_anomalies()
    
    # 5. Build ML-Ready Datasets (Lags & Targets)
    generate_ml_datasets()
    
    # 6. Data Validation & Quality Checks
    validate_and_report()
    
    # 7. Metadata Deliverables
    create_data_dictionary()
    build_sqlite_database()
    
    elapsed_sec = round(time.time() - start_time_sec, 2)
    
    # Print Summary Statistics
    print("\n==============================")
    print("FACILITY DATASET GENERATED")
    print("==============================")
    print(f"Date range: 2026-01-01 00:00:00 to 2026-06-29 23:45:00 (180 Days @ 15-min)")
    print(f"Buildings: 10")
    print(f"Assets: 35")
    print(f"Waste bins: 32")
    print(f"Parking zones: 4")
    print(f"Traffic locations: 6")
    print("")
    print(f"Energy records: {len(df_e):,}")
    print(f"Water records: {len(df_wat):,}")
    print(f"Waste records: {len(df_wst):,}")
    print(f"Air records: {len(df_air):,}")
    print(f"Traffic records: {len(df_tr):,}")
    print(f"Parking records: {len(df_prk):,}")
    print(f"Equipment records: {len(df_eq):,}")
    print("")
    print(f"Anomalies Injected:")
    print(f"  Energy: HVAC fault & After-hours usage")
    print(f"  Water: Abnormal consumption leak proxy")
    print(f"  Waste: Rapid fill overflow")
    print(f"  Air: Gate pollution spike")
    print(f"  Equipment: Bearing wear overheating")
    print("")
    print(f"Missing data: ~1.2% - 1.5% (Realistic IoT network loss)")
    print(f"Average energy: {round(df_e['electricity_kwh'].mean(), 2)} kWh / 15-min")
    print(f"Average water consumption: {round(df_wat['water_consumption_liters'].mean(), 2)} L / 15-min")
    print("")
    print(f"Generation time: {elapsed_sec} seconds")
    print("==============================\n")

if __name__ == "__main__":
    run_master_generation()
