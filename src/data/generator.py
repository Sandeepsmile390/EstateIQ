"""
Synthetic Data Generator for Sustainable Facility and Estate Intelligence Dashboard.
Generates realistic multi-module hourly datasets with proper physics-based patterns,
diurnal seasonality, noise, anomalies, and target relations.
All datasets produced by this module are explicitly marked as SYNTHETIC.
"""

import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

SYNTHETIC_MARKER = True

def generate_energy_data(num_days: int = 60, facility_id: str = "FAC_COLLEGE_01") -> pd.DataFrame:
    """
    Generates Energy Consumption Dataset.
    Columns: timestamp, facility_id, building_id, temperature, humidity, occupancy,
             hvac_load, lighting_load, equipment_load, previous_energy_kwh, energy_kwh
    """
    np.random.seed(42)
    start_time = datetime(2026, 1, 1, 0, 0)
    hours = num_days * 24
    timestamps = [start_time + timedelta(hours=i) for i in range(hours)]
    
    buildings = ["Block_A_Academic", "Block_B_Hostel", "Block_C_Admin", "Block_D_Labs"]
    records = []
    
    for b_idx, building in enumerate(buildings):
        # Base demand variations per building type
        base_load = 50 + b_idx * 25
        
        for i, ts in enumerate(timestamps):
            hr = ts.hour
            dow = ts.weekday()
            is_weekend = 1 if dow >= 5 else 0
            
            # Weather factors
            temp = 22.0 + 8.0 * np.sin((hr - 8) * np.pi / 12) + np.random.normal(0, 1.5)
            humidity = 55.0 + 15.0 * np.cos((hr - 4) * np.pi / 12) + np.random.normal(0, 2.0)
            
            # Occupancy pattern
            if is_weekend:
                occupancy = np.random.randint(5, 30) if "Hostel" in building else np.random.randint(0, 10)
            else:
                if 8 <= hr <= 18:
                    occupancy = np.random.randint(70, 250) if "Academic" in building else np.random.randint(40, 150)
                else:
                    occupancy = np.random.randint(10, 50) if "Hostel" in building else np.random.randint(0, 15)
            
            # Sub-meter loads
            hvac_load = max(5.0, (temp - 20.0) * 4.5 + occupancy * 0.3 + np.random.normal(0, 3.0))
            lighting_load = max(2.0, (18.0 - abs(hr - 14)) * 1.5 + occupancy * 0.1 + np.random.normal(0, 1.0))
            equipment_load = base_load * 0.4 + occupancy * 0.25 + np.random.normal(0, 2.0)
            
            # Energy consumption formula with physical dependencies + small noise
            energy_kwh = hvac_load + lighting_load + equipment_load + np.random.normal(0, 3.0)
            energy_kwh = max(10.0, energy_kwh)
            
            records.append({
                "timestamp": ts,
                "facility_id": facility_id,
                "building_id": building,
                "temperature": round(temp, 2),
                "humidity": round(humidity, 2),
                "occupancy": occupancy,
                "hvac_load": round(hvac_load, 2),
                "lighting_load": round(lighting_load, 2),
                "equipment_load": round(equipment_load, 2),
                "energy_kwh": round(energy_kwh, 2)
            })
            
    df = pd.DataFrame(records)
    df.sort_values(by=["building_id", "timestamp"], inplace=True)
    # Compute previous_energy_kwh for lag feature without leakage
    df["previous_energy_kwh"] = df.groupby("building_id")["energy_kwh"].shift(1).fillna(df["energy_kwh"].mean())
    df["is_synthetic"] = SYNTHETIC_MARKER
    return df


def generate_water_data(num_days: int = 60, facility_id: str = "FAC_COLLEGE_01") -> pd.DataFrame:
    """
    Generates Water Consumption Dataset.
    Columns: timestamp, facility_id, building_id, flow_rate, water_usage_liters, occupancy, temperature, humidity, hour, day_of_week
    """
    np.random.seed(43)
    start_time = datetime(2026, 1, 1, 0, 0)
    hours = num_days * 24
    timestamps = [start_time + timedelta(hours=i) for i in range(hours)]
    
    buildings = ["Block_A_Academic", "Block_B_Hostel", "Block_C_Admin", "Block_D_Labs"]
    records = []
    
    for building in buildings:
        for ts in timestamps:
            hr = ts.hour
            dow = ts.weekday()
            
            temp = 24.0 + 6.0 * np.sin((hr - 9) * np.pi / 12) + np.random.normal(0, 1.0)
            humidity = 50.0 + 10.0 * np.cos(hr * np.pi / 12)
            
            occupancy = np.random.randint(10, 200) if 7 <= hr <= 20 else np.random.randint(2, 30)
            
            # Flow rate and total liters calculation
            base_flow = 15.0 if "Hostel" in building else 8.0
            flow_rate = base_flow + occupancy * 0.12 + np.random.normal(0, 2.0)
            flow_rate = max(1.0, flow_rate)
            
            # Inject synthetic abnormal usage spikes (potential leak / waste)
            if np.random.rand() < 0.02:
                flow_rate *= np.random.uniform(2.5, 4.0)
                
            water_usage_liters = flow_rate * 60.0 + np.random.normal(0, 10.0)
            water_usage_liters = max(10.0, water_usage_liters)
            
            records.append({
                "timestamp": ts,
                "facility_id": facility_id,
                "building_id": building,
                "flow_rate": round(flow_rate, 2),
                "water_usage_liters": round(water_usage_liters, 2),
                "occupancy": occupancy,
                "temperature": round(temp, 2),
                "humidity": round(humidity, 2),
                "hour": hr,
                "day_of_week": dow,
                "is_synthetic": SYNTHETIC_MARKER
            })
            
    return pd.DataFrame(records)


def generate_waste_data(num_days: int = 60, facility_id: str = "FAC_COLLEGE_01") -> pd.DataFrame:
    """
    Generates Waste Management Dataset.
    Columns: timestamp, facility_id, bin_id, location, fill_level, fill_rate, temperature, occupancy, day_of_week, hour, collection_time, overflow
    Target: overflow (1 if overflowed in next 2 hours, else 0)
    """
    np.random.seed(44)
    start_time = datetime(2026, 1, 1, 0, 0)
    hours = num_days * 24
    timestamps = [start_time + timedelta(hours=i) for i in range(hours)]
    
    bins = [("BIN_01", "Cafeteria"), ("BIN_02", "Hostel_Courtyard"), ("BIN_03", "Main_Gate"), ("BIN_04", "Library_Plaza")]
    records = []
    
    for bin_id, location in bins:
        current_fill = np.random.uniform(10.0, 40.0)
        
        for ts in timestamps:
            hr = ts.hour
            dow = ts.weekday()
            occupancy = np.random.randint(5, 300) if 8 <= hr <= 20 else np.random.randint(0, 20)
            temp = 25.0 + 5.0 * np.sin(hr * np.pi / 12)
            
            # Fill rate depends on occupancy and location
            fill_rate = max(0.0, occupancy * 0.08 + np.random.normal(0.5, 0.5))
            
            # Reset bin when emptied
            is_collection = 1 if (hr in [6, 18] and np.random.rand() < 0.8) else 0
            if is_collection:
                current_fill = np.random.uniform(0.0, 10.0)
            else:
                current_fill = min(100.0, current_fill + fill_rate)
                
            # Overflow indicator for next 2 hours
            projected_2hr_fill = current_fill + 2.0 * fill_rate
            overflow = 1 if projected_2hr_fill >= 90.0 else 0
            
            records.append({
                "timestamp": ts,
                "facility_id": facility_id,
                "bin_id": bin_id,
                "location": location,
                "fill_level": round(current_fill, 2),
                "fill_rate": round(fill_rate, 2),
                "temperature": round(temp, 2),
                "occupancy": occupancy,
                "day_of_week": dow,
                "hour": hr,
                "collection_time": is_collection,
                "overflow": overflow,
                "is_synthetic": SYNTHETIC_MARKER
            })
            
    return pd.DataFrame(records)


def generate_air_quality_data(num_days: int = 60, facility_id: str = "FAC_COLLEGE_01") -> pd.DataFrame:
    """
    Generates Air Quality Dataset.
    Columns: timestamp, facility_id, location, PM2_5, PM10, CO2, temperature, humidity, wind_speed, traffic_level, AQI
    """
    np.random.seed(45)
    start_time = datetime(2026, 1, 1, 0, 0)
    hours = num_days * 24
    timestamps = [start_time + timedelta(hours=i) for i in range(hours)]
    
    locations = ["North_Gate", "Central_Quad", "South_Parking", "Lab_Complex"]
    records = []
    
    for loc in locations:
        for ts in timestamps:
            hr = ts.hour
            traffic_level = np.random.randint(20, 95) if (7 <= hr <= 10 or 17 <= hr <= 20) else np.random.randint(5, 40)
            wind_speed = max(0.5, 3.5 + np.random.normal(0, 1.0))
            temp = 23.0 + 7.0 * np.sin((hr - 10) * np.pi / 12)
            humidity = 50.0 + 15.0 * np.cos(hr * np.pi / 12)
            
            pm25 = max(5.0, 35.0 + traffic_level * 0.6 - wind_speed * 3.0 + np.random.normal(0, 5.0))
            pm10 = pm25 * 1.6 + np.random.normal(0, 4.0)
            co2 = 400.0 + traffic_level * 2.5 + np.random.normal(0, 15.0)
            
            # Simple AQI calculation proxy based on Indian CPCB scale for PM2.5
            aqi = pm25 * 2.1 + np.random.normal(0, 2.0)
            aqi = max(10.0, min(500.0, aqi))
            
            records.append({
                "timestamp": ts,
                "facility_id": facility_id,
                "location": loc,
                "PM2_5": round(pm25, 2),
                "PM10": round(pm10, 2),
                "CO2": round(co2, 2),
                "temperature": round(temp, 2),
                "humidity": round(humidity, 2),
                "wind_speed": round(wind_speed, 2),
                "traffic_level": traffic_level,
                "AQI": round(aqi, 2),
                "is_synthetic": SYNTHETIC_MARKER
            })
            
    return pd.DataFrame(records)


def generate_traffic_data(num_days: int = 60, facility_id: str = "FAC_COLLEGE_01") -> pd.DataFrame:
    """
    Generates Traffic Dataset.
    Columns: timestamp, facility_id, location, vehicle_count, average_speed, pedestrian_count, parking_occupancy, weather, day_of_week, hour, congestion_level
    """
    np.random.seed(46)
    start_time = datetime(2026, 1, 1, 0, 0)
    hours = num_days * 24
    timestamps = [start_time + timedelta(hours=i) for i in range(hours)]
    
    locations = ["Main_Gate_Entry", "East_Gate_Exit", "Internal_Ring_Road"]
    weathers = ["Clear", "Rainy", "Foggy", "Overcast"]
    records = []
    
    for loc in locations:
        for ts in timestamps:
            hr = ts.hour
            dow = ts.weekday()
            weather = np.random.choice(weathers, p=[0.7, 0.1, 0.1, 0.1])
            
            if 8 <= hr <= 10 or 16 <= hr <= 19:
                v_count = np.random.randint(120, 350)
                p_count = np.random.randint(80, 250)
            else:
                v_count = np.random.randint(10, 80)
                p_count = np.random.randint(5, 50)
                
            avg_speed = max(5.0, 40.0 - v_count * 0.08 + np.random.normal(0, 3.0))
            p_occ = min(1.0, max(0.0, v_count / 350.0 + np.random.normal(0, 0.05)))
            
            # Categorical Congestion Level: 0 = LOW, 1 = MEDIUM, 2 = HIGH
            if v_count < 100:
                c_level = "LOW"
            elif v_count < 220:
                c_level = "MEDIUM"
            else:
                c_level = "HIGH"
                
            records.append({
                "timestamp": ts,
                "facility_id": facility_id,
                "location": loc,
                "vehicle_count": v_count,
                "average_speed": round(avg_speed, 2),
                "pedestrian_count": p_count,
                "parking_occupancy": round(p_occ, 2),
                "weather": weather,
                "day_of_week": dow,
                "hour": hr,
                "congestion_level": c_level,
                "is_synthetic": SYNTHETIC_MARKER
            })
            
    return pd.DataFrame(records)


def generate_parking_data(num_days: int = 60) -> pd.DataFrame:
    """
    Generates Parking Dataset.
    Columns: timestamp, parking_zone, capacity, occupied_spaces, occupancy_rate, vehicle_arrivals, vehicle_departures, hour, day_of_week, event_flag
    """
    np.random.seed(47)
    start_time = datetime(2026, 1, 1, 0, 0)
    hours = num_days * 24
    timestamps = [start_time + timedelta(hours=i) for i in range(hours)]
    
    zones = [("Zone_A_Visitor", 150), ("Zone_B_Faculty", 200), ("Zone_C_Student", 300)]
    records = []
    
    for zone_name, cap in zones:
        curr_occ = int(cap * 0.15)
        for ts in timestamps:
            hr = ts.hour
            dow = ts.weekday()
            event_flag = 1 if (dow == 4 and 14 <= hr <= 18 and np.random.rand() < 0.3) else 0
            
            if 7 <= hr <= 11:
                arrivals = np.random.randint(15, 45) + (30 if event_flag else 0)
                departures = np.random.randint(2, 10)
            elif 16 <= hr <= 19:
                arrivals = np.random.randint(2, 10)
                departures = np.random.randint(20, 50)
            else:
                arrivals = np.random.randint(0, 5)
                departures = np.random.randint(0, 5)
                
            curr_occ = max(0, min(cap, curr_occ + arrivals - departures))
            occ_rate = round(curr_occ / cap, 4)
            
            records.append({
                "timestamp": ts,
                "parking_zone": zone_name,
                "capacity": cap,
                "occupied_spaces": curr_occ,
                "occupancy_rate": occ_rate,
                "vehicle_arrivals": arrivals,
                "vehicle_departures": departures,
                "hour": hr,
                "day_of_week": dow,
                "event_flag": event_flag,
                "is_synthetic": SYNTHETIC_MARKER
            })
            
    return pd.DataFrame(records)


def generate_equipment_data(num_days: int = 60, facility_id: str = "FAC_COLLEGE_01") -> pd.DataFrame:
    """
    Generates Equipment / Asset Utilization Dataset.
    Columns: timestamp, facility_id, equipment_id, equipment_type, runtime_hours, load, temperature, vibration, power_consumption, maintenance_history, utilization_rate
    """
    np.random.seed(48)
    start_time = datetime(2026, 1, 1, 0, 0)
    hours = num_days * 24
    timestamps = [start_time + timedelta(hours=i) for i in range(hours)]
    
    equipments = [
        ("EQ_CHILLER_01", "Chiller"),
        ("EQ_TRANSFORMER_01", "Transformer"),
        ("EQ_PUMP_01", "Water_Pump"),
        ("EQ_GENSET_01", "DG_Set")
    ]
    records = []
    
    for eq_id, eq_type in equipments:
        runtime_accum = 100.0
        maint_hist = 0
        for ts in timestamps:
            hr = ts.hour
            runtime_accum += 1.0 if (7 <= hr <= 22) else 0.2
            
            load = np.random.uniform(0.4, 0.95) if (7 <= hr <= 22) else np.random.uniform(0.1, 0.3)
            temp = 45.0 + load * 35.0 + np.random.normal(0, 2.0)
            vibration = 1.2 + load * 2.5 + (runtime_accum / 2000.0) + np.random.normal(0, 0.3)
            power = load * 75.0 + np.random.normal(0, 2.0)
            util_rate = round(load, 2)
            
            # Anomaly injection for maintenance risk indicator
            if np.random.rand() < 0.015:
                vibration *= np.random.uniform(2.0, 3.5)
                temp += np.random.uniform(15.0, 30.0)
                maint_hist += 1
                
            records.append({
                "timestamp": ts,
                "facility_id": facility_id,
                "equipment_id": eq_id,
                "equipment_type": eq_type,
                "runtime_hours": round(runtime_accum, 1),
                "load": round(load, 2),
                "temperature": round(temp, 2),
                "vibration": round(vibration, 2),
                "power_consumption": round(power, 2),
                "maintenance_history": maint_hist,
                "utilization_rate": util_rate,
                "is_synthetic": SYNTHETIC_MARKER
            })
            
    return pd.DataFrame(records)


def generate_safety_data(num_days: int = 60, facility_id: str = "FAC_COLLEGE_01") -> pd.DataFrame:
    """
    Generates Safety Incidents Dataset.
    Columns: timestamp, facility_id, location, incident_type, severity, weather, occupancy, traffic_level, previous_incidents, time_of_day
    """
    np.random.seed(49)
    start_time = datetime(2026, 1, 1, 0, 0)
    hours = num_days * 24
    timestamps = [start_time + timedelta(hours=i) for i in range(hours)]
    
    locations = ["Chemistry_Lab", "Main_Gate_Intersection", "Sports_Complex", "Substation_Yard"]
    incident_types = ["Slip/Trip", "Electrical_Flicker", "Traffic_NearMiss", "Chemical_Spill_Minor"]
    weathers = ["Clear", "Rainy", "Foggy"]
    
    records = []
    prev_incidents = 0
    for ts in timestamps:
        hr = ts.hour
        # Incidents are rare events (~1.5% chance per hour across zones)
        if np.random.rand() < 0.015:
            loc = np.random.choice(locations)
            inc_type = np.random.choice(incident_types)
            severity = np.random.choice(["LOW", "MEDIUM", "HIGH"], p=[0.7, 0.2, 0.1])
            weather = np.random.choice(weathers, p=[0.7, 0.2, 0.1])
            occupancy = np.random.randint(20, 200)
            traffic_level = np.random.randint(10, 90)
            prev_incidents += 1
            
            records.append({
                "timestamp": ts,
                "facility_id": facility_id,
                "location": loc,
                "incident_type": inc_type,
                "severity": severity,
                "weather": weather,
                "occupancy": occupancy,
                "traffic_level": traffic_level,
                "previous_incidents": prev_incidents,
                "time_of_day": "Day" if 6 <= hr <= 18 else "Night",
                "is_synthetic": SYNTHETIC_MARKER
            })
            
    return pd.DataFrame(records)


def generate_emissions_data(num_days: int = 60, facility_id: str = "FAC_COLLEGE_01") -> pd.DataFrame:
    """
    Generates Emissions Dataset.
    Columns: timestamp, facility_id, energy_consumption, fuel_consumption, vehicle_count, production_level, emission_estimate
    Doc: Conversion factors used:
         - Grid Energy: 0.82 kg CO2e per kWh (Indian Grid Emission Factor Baseline)
         - Diesel Fuel: 2.68 kg CO2e per Liter
         - Vehicle Travel Proxy: 0.14 kg CO2e per vehicle-km (average fleet mix)
    """
    np.random.seed(50)
    start_time = datetime(2026, 1, 1, 0, 0)
    hours = num_days * 24
    timestamps = [start_time + timedelta(hours=i) for i in range(hours)]
    
    records = []
    for ts in timestamps:
        hr = ts.hour
        energy = 150.0 + 80.0 * np.sin(hr * np.pi / 12) + np.random.normal(0, 10.0)
        energy = max(20.0, energy)
        
        # Diesel Generator runtime during grid outage / peak load
        fuel = np.random.uniform(5.0, 25.0) if (np.random.rand() < 0.1) else 0.0
        v_count = np.random.randint(10, 150) if (7 <= hr <= 19) else np.random.randint(0, 20)
        prod_level = np.random.uniform(50.0, 100.0)
        
        # Calculate emission estimate (kg CO2e) based on standard emission factors
        emission_est = (energy * 0.82) + (fuel * 2.68) + (v_count * 0.14 * 2.5) + np.random.normal(0, 5.0)
        emission_est = max(5.0, emission_est)
        
        records.append({
            "timestamp": ts,
            "facility_id": facility_id,
            "energy_consumption": round(energy, 2),
            "fuel_consumption": round(fuel, 2),
            "vehicle_count": v_count,
            "production_level": round(prod_level, 2),
            "emission_estimate": round(emission_est, 2),
            "is_synthetic": SYNTHETIC_MARKER
        })
        
    return pd.DataFrame(records)


def generate_all_datasets(output_dir: str = "data/synthetic"):
    """Generates and saves all 9 synthetic datasets to CSV format."""
    os.makedirs(output_dir, exist_ok=True)
    
    datasets = {
        "energy.csv": generate_energy_data(),
        "water.csv": generate_water_data(),
        "waste.csv": generate_waste_data(),
        "air_quality.csv": generate_air_quality_data(),
        "traffic.csv": generate_traffic_data(),
        "parking.csv": generate_parking_data(),
        "equipment.csv": generate_equipment_data(),
        "safety.csv": generate_safety_data(),
        "emissions.csv": generate_emissions_data()
    }
    
    for name, df in datasets.items():
        path = os.path.join(output_dir, name)
        df.to_csv(path, index=False)
        print(f"[Synthetic Data Generator] Generated {name} ({len(df)} rows) saved to {path}")

if __name__ == "__main__":
    generate_all_datasets()
