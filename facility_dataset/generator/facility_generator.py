"""
Facility Metadata Generator.
Produces facilities.csv, buildings.csv, locations.csv, and assets.csv.
"""

import pandas as pd
from generator.config import RAW_DATA_DIR, load_json_config, logger

def generate_facility_metadata():
    logger.info("Generating Facility Metadata (facilities, buildings, locations, assets)...")
    
    cfg = load_json_config("facility_config.json")
    
    # 1. facilities.csv
    fac_info = cfg["facility"]
    df_fac = pd.DataFrame([fac_info])
    df_fac.to_csv(RAW_DATA_DIR / "facilities.csv", index=False)
    
    # 2. buildings.csv
    df_bld = pd.DataFrame(cfg["buildings"])
    df_bld.to_csv(RAW_DATA_DIR / "buildings.csv", index=False)
    
    # 3. locations.csv
    df_loc = pd.DataFrame(cfg["locations"])
    df_loc.to_csv(RAW_DATA_DIR / "locations.csv", index=False)
    
    # 4. assets.csv (35 campus assets)
    asset_types = [
        ("HVAC_Chiller", "Chiller", "BLD003", 5),
        ("HVAC_VRF", "VRF_Unit", "BLD001", 4),
        ("Transformer_Main", "Transformer", "BLD010", 2),
        ("Water_Pump_Submersible", "Water_Pump", "BLD010", 4),
        ("DG_Set_Backup", "Generator", "BLD010", 3),
        ("Elevator_Passenger", "Elevator", "BLD003", 4),
        ("Air_Handling_Unit", "AHU", "BLD005", 3),
        ("Air_Compressor", "Compressor", "BLD010", 2),
        ("Solar_Inverter", "Solar_Inverter", "BLD001", 4),
        ("Waste_Compactor", "Waste_Compactor", "BLD008", 4)
    ]
    
    assets = []
    idx = 1
    for name_prefix, category, bld_id, count in asset_types:
        for i in range(1, count + 1):
            asset_id = f"AST_{category.upper()}_{idx:02d}"
            assets.append({
                "asset_id": asset_id,
                "facility_id": fac_info["facility_id"],
                "building_id": bld_id,
                "asset_name": f"{name_prefix} {i}",
                "category": category,
                "rated_power_kw": 45.0 if "Chiller" in category else (15.0 if "Pump" in category else 30.0),
                "installation_year": 2015 + (idx % 8),
                "status": "OPERATIONAL"
            })
            idx += 1
            
    df_ast = pd.DataFrame(assets)
    df_ast.to_csv(RAW_DATA_DIR / "assets.csv", index=False)
    
    logger.info("Facility Metadata generated successfully.")
    return df_fac, df_bld, df_loc, df_ast

if __name__ == "__main__":
    generate_facility_metadata()
