"""
Data Integrity and Repository Tests
"""

import unittest
import pandas as pd
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from src.data.repository import DataRepository

class TestDataRepository(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo = DataRepository()

    def test_facility_info(self):
        info = self.repo.get_facility_info()
        self.assertIsInstance(info, dict)
        self.assertIn("facility_name", info)

    def test_buildings_and_assets(self):
        buildings = self.repo.get_buildings()
        self.assertFalse(buildings.empty, "Buildings table should not be empty")
        assets = self.repo.get_assets()
        self.assertFalse(assets.empty, "Assets table should not be empty")

    def test_energy_data_bounds(self):
        df = self.repo.get_energy_data(limit=100)
        self.assertFalse(df.empty, "Energy data should not be empty")
        self.assertIn("electricity_kwh", df.columns)
        self.assertTrue((df["electricity_kwh"].dropna() >= 0).all(), "Electricity kWh must be >= 0")

    def test_waste_data_bounds(self):
        df = self.repo.get_waste_data(limit=100)
        self.assertFalse(df.empty, "Waste data should not be empty")
        self.assertIn("fill_level_percent", df.columns)
        self.assertTrue((df["fill_level_percent"] >= 0).all() and (df["fill_level_percent"] <= 100).all(), "Fill level must be between 0 and 100")

    def test_weather_data_bounds(self):
        df = self.repo.get_weather_data(limit=100)
        self.assertFalse(df.empty, "Weather data should not be empty")
        self.assertIn("humidity_percent", df.columns)
        self.assertTrue((df["humidity_percent"] >= 0).all() and (df["humidity_percent"] <= 100).all(), "Humidity must be between 0 and 100")

    def test_occupancy_data_bounds(self):
        df = self.repo.get_occupancy_data(limit=100)
        self.assertFalse(df.empty, "Occupancy data should not be empty")
        self.assertIn("occupancy_count", df.columns)
        self.assertTrue((df["occupancy_count"] >= 0).all(), "Occupancy count must be >= 0")

if __name__ == "__main__":
    unittest.main()
