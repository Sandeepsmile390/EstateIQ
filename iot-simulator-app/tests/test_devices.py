import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from simulator.device_manager import VirtualDevice, DeviceManager
from simulator.sensor_models import SensorProfile

class TestVirtualDevices(unittest.TestCase):

    def setUp(self):
        self.mgr = DeviceManager()

    def test_device_creation_and_physics_sample(self):
        dev = VirtualDevice({
            "device_id": "TEST-METER-001",
            "device_name": "Test Electricity Meter",
            "device_type": "electricity_meter",
            "facility_id": "FAC_GEC_CAMPUS",
            "building_id": "Block B Hostel"
        })
        self.assertEqual(dev.device_id, "TEST-METER-001")
        self.assertEqual(dev.device_type, "electricity_meter")

        sample = dev.generate_next_sample()
        self.assertIn("metrics", sample)
        metric_names = [m["metric"] for m in sample["metrics"]]
        self.assertIn("active_power_kw", metric_names)

    def test_hvac_physics_sample(self):
        metrics = SensorProfile.generate_metrics("hvac_monitor", {})
        self.assertIn("hvac_power_kw", metrics)
        self.assertIn("chiller_temp_c", metrics)

    def test_water_tank_physics_sample(self):
        metrics = SensorProfile.generate_metrics("water_tank", {})
        self.assertIn("water_level_pct", metrics)
        self.assertGreaterEqual(metrics["water_level_pct"], 0)
        self.assertLessEqual(metrics["water_level_pct"], 100)

    def test_device_manager_inventory(self):
        self.mgr.initialize_default_devices()
        devs = self.mgr.list_devices()
        self.assertGreaterEqual(len(devs), 9)

if __name__ == "__main__":
    unittest.main()
