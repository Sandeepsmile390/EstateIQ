"""
Master Pipeline Runner for Sustainable Facility Platform.
Trains models across all 9 facility domain tasks, executes ModelSelectionEngine,
saves artifacts, and populates model metadata registry.
"""

from src.models.energy.pipeline import train_energy_module
from src.models.water.pipeline import train_water_module
from src.models.waste.pipeline import train_waste_module
from src.models.air.pipeline import train_air_module
from src.models.traffic.pipeline import train_traffic_module
from src.models.parking.pipeline import train_parking_module
from src.models.equipment.pipeline import train_equipment_module
from src.models.emissions.pipeline import train_emissions_module
from src.models.safety.pipeline import analyze_safety_incidents
from src.registry.manager import ModelRegistryManager

def train_entire_facility_system():
    print("==================================================")
    print("   STARTING SUSTAINABLE FACILITY AI SYSTEM TRAINING")
    print("==================================================")
    
    reg_mgr = ModelRegistryManager()
    
    # 1. Energy
    print("\n--- [1/9] Training Energy Consumption Module ---")
    _, e_meta, _ = train_energy_module()
    reg_mgr.register_model(
        model_id="energy_kwh_prediction_v1",
        task=e_meta["task"],
        algorithm=e_meta["selected_model"],
        model_version="v1.0",
        facility_type="configurable_estate",
        features=e_meta["feature_names"],
        hyperparameters=e_meta["hyperparameters"],
        metrics=e_meta["val_metrics"]
    )
    
    # 2. Water
    print("\n--- [2/9] Training Water Consumption Module ---")
    _, w_meta, _ = train_water_module()
    reg_mgr.register_model(
        model_id="water_usage_forecasting_v1",
        task=w_meta["task"],
        algorithm=w_meta["selected_model"],
        model_version="v1.0",
        facility_type="configurable_estate",
        features=w_meta["feature_names"],
        hyperparameters=w_meta["hyperparameters"],
        metrics=w_meta["val_metrics"]
    )
    
    # 3. Waste
    print("\n--- [3/9] Training Waste Management Module ---")
    _, wst_meta, _ = train_waste_module()
    reg_mgr.register_model(
        model_id="waste_overflow_2hr_v1",
        task=wst_meta["task"],
        algorithm=wst_meta["selected_model"],
        model_version="v1.0",
        facility_type="configurable_estate",
        features=wst_meta["feature_names"],
        hyperparameters=wst_meta["hyperparameters"],
        metrics=wst_meta["val_metrics"]
    )
    
    # 4. Air Quality
    print("\n--- [4/9] Training Air Quality Module ---")
    _, air_meta, _ = train_air_module()
    reg_mgr.register_model(
        model_id="air_pm25_prediction_v1",
        task=air_meta["task"],
        algorithm=air_meta["selected_model"],
        model_version="v1.0",
        facility_type="configurable_estate",
        features=air_meta["feature_names"],
        hyperparameters=air_meta["hyperparameters"],
        metrics=air_meta["val_metrics"]
    )
    
    # 5. Traffic
    print("\n--- [5/9] Training Traffic Congestion Module ---")
    _, tr_meta, _ = train_traffic_module()
    reg_mgr.register_model(
        model_id="traffic_congestion_class_v1",
        task=tr_meta["task"],
        algorithm=tr_meta["selected_model"],
        model_version="v1.0",
        facility_type="configurable_estate",
        features=tr_meta["feature_names"],
        hyperparameters=tr_meta["hyperparameters"],
        metrics=tr_meta["val_metrics"]
    )
    
    # 6. Parking
    print("\n--- [6/9] Training Parking Occupancy Module ---")
    _, prk_meta, _ = train_parking_module()
    reg_mgr.register_model(
        model_id="parking_occupancy_forecasting_v1",
        task=prk_meta["task"],
        algorithm=prk_meta["selected_model"],
        model_version="v1.0",
        facility_type="configurable_estate",
        features=prk_meta["feature_names"],
        hyperparameters=prk_meta["hyperparameters"],
        metrics=prk_meta["val_metrics"]
    )
    
    # 7. Equipment
    print("\n--- [7/9] Training Equipment Utilization Module ---")
    _, eq_meta, _ = train_equipment_module()
    reg_mgr.register_model(
        model_id="equipment_maintenance_risk_v1",
        task=eq_meta["task"],
        algorithm=eq_meta["selected_model"],
        model_version="v1.0",
        facility_type="configurable_estate",
        features=eq_meta["feature_names"],
        hyperparameters=eq_meta["hyperparameters"],
        metrics=eq_meta["val_metrics"]
    )
    
    # 8. Safety
    print("\n--- [8/9] Analyzing Safety Incidents Module ---")
    safety_res = analyze_safety_incidents()
    print("[Safety Analysis] Complete:", safety_res["total_incidents_recorded"], "incidents analyzed.")
    
    # 9. Emissions
    print("\n--- [9/9] Training Emissions Forecasting Module ---")
    _, em_meta, _ = train_emissions_module()
    reg_mgr.register_model(
        model_id="emissions_forecasting_v1",
        task=em_meta["task"],
        algorithm=em_meta["selected_model"],
        model_version="v1.0",
        facility_type="configurable_estate",
        features=em_meta["feature_names"],
        hyperparameters=em_meta["hyperparameters"],
        metrics=em_meta["val_metrics"]
    )
    
    print("\n==================================================")
    print("   ALL MODULES TRAINED & REGISTERED SUCCESSFULLY!")
    print("==================================================")

if __name__ == "__main__":
    train_entire_facility_system()
