"""
Unit Tests for MongoDB Integration & Connection Manager
Validates connection status, in-memory fallback, log persistence, and API status endpoint.
"""

import unittest
from fastapi.testclient import TestClient
from api.main import app
from src.data.mongo_db import get_db_status, save_prediction_log, query_prediction_logs, connect_mongo_db

class TestMongoDBIntegration(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)

    def test_mongo_connection_attempt(self):
        # connect_mongo_db should return boolean without throwing exceptions
        status_bool = connect_mongo_db()
        self.assertIsInstance(status_bool, bool)

    def test_db_status_structure(self):
        status = get_db_status()
        self.assertIn("status", status)
        self.assertIn("engine", status)
        self.assertIn("collections", status)
        self.assertIsInstance(status["collections"], dict)

    def test_save_and_query_prediction_log(self):
        payload = {
            "task": "unit_test_task",
            "val": 42.0,
            "unit": "kWh"
        }
        doc_id = save_prediction_log("predictions", payload)
        self.assertTrue(len(str(doc_id)) > 0)

        logs = query_prediction_logs("predictions", limit=10)
        self.assertGreaterEqual(len(logs), 1)

    def test_fastapi_db_status_endpoint(self):
        response = self.client.get("/api/v1/db/status")
        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertIn("status", json_data)
        self.assertIn("collections", json_data)

    def test_fastapi_db_logs_endpoint(self):
        response = self.client.get("/api/v1/db/logs/predictions")
        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertEqual(json_data["collection"], "predictions")
        self.assertIn("data", json_data)

if __name__ == "__main__":
    unittest.main()
