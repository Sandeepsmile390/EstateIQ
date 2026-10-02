"""
Centralized Data Access Layer (DataRepository).
Provides high-performance, unified access methods querying SQLite database facility.db and CSV feeds.
All dashboard pages and API endpoints retrieve data through this layer.
"""

import os
import sqlite3
import pandas as pd
from typing import Dict, Any, List, Optional
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "facility_dataset" / "facility.db"
RAW_DIR = BASE_DIR / "facility_dataset" / "data" / "raw"

class DataRepository:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path

    def _get_connection(self):
        if self.db_path.exists():
            return sqlite3.connect(self.db_path)
        return None

    def query_table(self, table_name: str, limit: Optional[int] = None) -> pd.DataFrame:
        """Queries table from SQLite DB if available, else falls back to CSV."""
        conn = self._get_connection()
        if conn is not None:
            try:
                query = f"SELECT * FROM {table_name}"
                if limit:
                    query += f" LIMIT {limit}"
                df = pd.read_sql_query(query, conn)
                conn.close()
                if "timestamp" in df.columns:
                    df["timestamp"] = pd.to_datetime(df["timestamp"])
                return df
            except Exception:
                if conn:
                    conn.close()

        # CSV Fallback
        csv_path = RAW_DIR / f"{table_name}.csv"
        if csv_path.exists():
            df = pd.read_csv(csv_path)
            if limit:
                df = df.head(limit)
            if "timestamp" in df.columns:
                df["timestamp"] = pd.to_datetime(df["timestamp"])
            return df

        return pd.DataFrame()

    def get_facility_info(self) -> Dict[str, Any]:
        df = self.query_table("facilities")
        if not df.empty:
            return df.iloc[0].to_dict()
        return {
            "facility_id": "FAC_GEC_01",
            "facility_name": "GEC Smart Campus",
            "facility_type": "engineering_college",
            "city": "Pune",
            "state": "Maharashtra",
            "country": "India"
        }

    def get_buildings(self) -> pd.DataFrame:
        return self.query_table("buildings")

    def get_locations(self) -> pd.DataFrame:
        return self.query_table("locations")

    def get_assets(self) -> pd.DataFrame:
        return self.query_table("assets")

    def get_weather_data(self, limit: Optional[int] = None) -> pd.DataFrame:
        return self.query_table("weather_readings", limit=limit)

    def get_occupancy_data(self, limit: Optional[int] = None) -> pd.DataFrame:
        return self.query_table("occupancy_readings", limit=limit)

    def get_energy_data(self, limit: Optional[int] = None) -> pd.DataFrame:
        return self.query_table("energy_readings", limit=limit)

    def get_water_data(self, limit: Optional[int] = None) -> pd.DataFrame:
        return self.query_table("water_readings", limit=limit)

    def get_waste_data(self, limit: Optional[int] = None) -> pd.DataFrame:
        return self.query_table("waste_readings", limit=limit)

    def get_air_quality_data(self, limit: Optional[int] = None) -> pd.DataFrame:
        return self.query_table("air_quality_readings", limit=limit)

    def get_traffic_data(self, limit: Optional[int] = None) -> pd.DataFrame:
        return self.query_table("traffic_readings", limit=limit)

    def get_parking_data(self, limit: Optional[int] = None) -> pd.DataFrame:
        return self.query_table("parking_readings", limit=limit)

    def get_equipment_data(self, limit: Optional[int] = None) -> pd.DataFrame:
        return self.query_table("equipment_sensor_readings", limit=limit)

    def get_safety_data(self, limit: Optional[int] = None) -> pd.DataFrame:
        return self.query_table("safety_incidents", limit=limit)

    def get_emissions_data(self, limit: Optional[int] = None) -> pd.DataFrame:
        return self.query_table("emissions", limit=limit)
