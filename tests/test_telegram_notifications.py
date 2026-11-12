import json
import os
import unittest
from unittest.mock import patch, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.sns_routes import router as sns_router
from src.services import sns

test_app = FastAPI()
test_app.include_router(sns_router)

class TestTelegramNotifications(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(test_app)
        os.environ["TELEGRAM_BOT_TOKEN"] = "9238667783:AAEVWNcV6XoYIs9VOWnHuN-zgl2PyFP2tQI"
        os.environ["TELEGRAM_CHAT_ID"] = "5291396960"

    def test_telegram_config_endpoint(self):
        """Verify GET /api/v1/sns/telegram/config returns current configuration."""
        res = self.client.get("/api/v1/sns/telegram/config")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["configured"])
        self.assertEqual(data["chat_id"], "5291396960")
        self.assertEqual(data["bot_token"], "9238667783:AAEVWNcV6XoYIs9VOWnHuN-zgl2PyFP2tQI")
        self.assertTrue(data["endpoint"].startswith("https://api.telegram.org/bot"))

    @patch("urllib.request.urlopen")
    def test_telegram_send_endpoint(self, mock_urlopen):
        """Verify POST /api/v1/sns/telegram/send issues HTTP POST to Telegram Bot API."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"ok": True, "result": {"message_id": 123}}).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        payload = {
            "text": "🚨 [HIGH] EstateIQ Alert Popup\nDevice: ESP32_PZEM_01\nIssue: Surge detected",
            "chat_id": "5291396960"
        }
        res = self.client.post("/api/v1/sns/telegram/send", json=payload)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["ok"])

        # Check call arguments
        mock_urlopen.assert_called_once()
        req_arg = mock_urlopen.call_args[0][0]
        self.assertEqual(req_arg.get_method(), "POST")
        self.assertIn("9238667783:AAEVWNcV6XoYIs9VOWnHuN-zgl2PyFP2tQI/sendMessage", req_arg.get_full_url())
        req_data = json.loads(req_arg.data.decode("utf-8"))
        self.assertEqual(req_data["chat_id"], "5291396960")
        self.assertEqual(req_data["text"], payload["text"])

    @patch("urllib.request.urlopen")
    def test_popup_alert_endpoint_allows_dashboard(self, mock_urlopen):
        """Verify POST /api/v1/sns/popup-alert accepts popup notification from dashboard session."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"ok": True}).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        popup_body = {
            "anomaly_key": "test_anomaly_esp32_1",
            "title": "Voltage Spike Detected",
            "message": "Observed 265V exceeds 240V threshold",
            "severity": "CRITICAL",
            "source": "dashboard_popup",
            "device_id": "ESP32_PZEM_01",
            "building_id": "BLOCK_B",
            "metric": "voltage_v",
            "observed_value": 265.0,
            "expected_value": 230.0,
            "recommended_action": "Check main transformer tap and isolate sensitive loads."
        }
        res = self.client.post("/api/v1/sns/popup-alert", json=popup_body)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["accepted"])
        self.assertIn("event_key", data)

    @patch("urllib.request.urlopen")
    def test_deliver_telegram_outbox_formatting(self, mock_urlopen):
        """Verify deliver_telegram_outbox formats messages with severity icons and delivers via POST."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"ok": True}).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # Create a notification in SNS
        sns.init_sns_schema()
        notif = sns.create_notification(
            recipient_email="admin@estateiq.in",
            title="High Water Consumption",
            message="Tank fill dropped unexpectedly",
            priority="HIGH",
            source="hardware_sensor"
        )
        self.assertIsNotNone(notif)

        counts = sns.deliver_telegram_outbox(batch_size=5)
        self.assertIn("sent", counts)

if __name__ == "__main__":
    unittest.main()
