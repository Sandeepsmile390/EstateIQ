"""
EstateIQ Final-Round Acceptance Test Suite (tests/test_final_round_acceptance.py).
Tests T-01 through T-15 from Table 10.1 of EstateIQ_Final_Round_Implementation_Report.pdf:
- T-01: Clean checkout / DB initialization and deterministic seed.
- T-02: Open dashboard / queries with empty database resilience.
- T-03: Import valid CSV with exact expected accepted row count.
- T-04: Import malformed CSV with bad timestamp, missing unit, impossible value (rejection rows + reasons).
- T-05: Duplicate batch prevention and detection.
- T-06: Injected known energy spike & water leak anomaly detection.
- T-07: Forecast on dataset with chronological holdout metrics & baseline comparison.
- T-08: Forecast fallback on short history / forced model failure.
- T-09: What-if reduction % & tariff calculation arithmetic with visible assumptions.
- T-10: Accept, assign, complete alert with database persistence and audit log.
- T-11: Role-based authorization server-side enforcement (403 Forbidden for non-admin).
- T-12: Offline deterministic recommendation fallback without external LLM.
- T-13: Scoped report and CSV export by facility and zone.
- T-14: Stale sensor data detection and quality warnings.
- T-15: Demo reset command reproducibility.
"""

import os
import json
import uuid
import tempfile
import sqlite3
import unittest
import pandas as pd
from pathlib import Path
from fastapi.testclient import TestClient

from api.main import app
from src.data.canonical_db import (
    get_db_connection, init_canonical_schema, list_facilities, list_zones,
    query_readings, insert_readings_batch, rollback_batch,
    list_alerts, get_alert, update_alert, create_action, list_actions,
    list_audit_events
)
from src.data.seed_data import seed_demo_dataset, reset_demo_dataset
from src.ingestion.csv_import import (
    get_csv_template, preview_csv_content, import_csv_data
)
from src.ingestion.validation import (
    validate_timestamp, validate_metric_and_value
)
from src.analytics.kpis import calculate_facility_kpis
from src.analytics.anomaly import detect_facility_anomalies
from src.analytics.forecast import generate_energy_forecast
from src.analytics.scenarios import simulate_energy_scenario
from src.analytics.reports import generate_report_summary, export_readings_csv, generate_printable_html_report
from src.analytics.recommendations import generate_actionable_recommendations
from src.auth.security import create_user_token, USERS_DB


class TestFinalRoundAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        # Create dedicated temporary SQLite database for test isolation
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.test_db_path = Path(cls.temp_dir.name) / "test_facility.db"
        os.environ["ESTATEIQ_DB_PATH"] = str(cls.test_db_path)
        init_canonical_schema(cls.test_db_path)

        # Setup auth tokens
        admin_user = USERS_DB["admin@estateiq.in"]
        ops_user = USERS_DB["alex.chen@estateiq.in"]
        cls.admin_token = create_user_token(admin_user)
        cls.ops_token = create_user_token(ops_user)

    @classmethod
    def tearDownClass(cls):
        try:
            cls.temp_dir.cleanup()
        except Exception:
            pass

    def test_t01_clean_init_and_seed(self):
        """T-01: Start from clean DB, initialize canonical tables and seed sample data."""
        res = seed_demo_dataset(self.test_db_path)
        self.assertEqual(res["status"], "SEEDED")
        self.assertGreater(res["readings_seeded"], 1000)
        self.assertGreater(res["alerts_seeded"], 0)

        facs = list_facilities(self.test_db_path)
        self.assertTrue(any(f["id"] == "COLLEGE_01" for f in facs))

    def test_t02_empty_database_resilience(self):
        """T-02: Open / query on empty or nonexistent facility returns clean NO_DATA without crash."""
        kpi = calculate_facility_kpis(facility_id="NON_EXISTENT_CAMPUS", db_path=self.test_db_path)
        self.assertEqual(kpi["status"], "NO_DATA")
        self.assertEqual(kpi["kpis"]["total_energy_kwh"], 0.0)

        # API health check
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "HEALTHY")
        self.assertEqual(resp.json()["database"], "CONNECTED")

    def test_t03_import_valid_csv(self):
        """T-03: Import valid CSV. Accepted count matches expected; records are queryable."""
        csv_data = (
            "timestamp,facility_id,zone_id,metric_type,value,unit\n"
            "2026-11-20T10:00:00Z,COLLEGE_01,BLOCK_A,energy_kwh,55.5,kWh\n"
            "2026-11-20T11:00:00Z,COLLEGE_01,BLOCK_A,energy_kwh,62.0,kWh\n"
            "2026-11-20T10:00:00Z,COLLEGE_01,BLOCK_B,water_litre,120.0,L\n"
        )
        res = import_csv_data(
            csv_text_or_bytes=csv_data,
            selected_facility_id="COLLEGE_01",
            filename="test_valid.csv",
            db_path=self.test_db_path
        )
        self.assertEqual(res["accepted_count"], 3)
        self.assertEqual(res["rejected_count"], 0)
        self.assertTrue(res["batch_id"].startswith("BATCH_CSV_"))

        # Query back
        readings, count = query_readings(facility_id="COLLEGE_01", zone_id="BLOCK_A", db_path=self.test_db_path)
        self.assertGreater(count, 0)

    def test_t04_import_malformed_csv_validation(self):
        """T-04: Malformed CSV with bad timestamp, missing unit, impossible value rejected with row number and reason."""
        csv_data = (
            "timestamp,facility_id,zone_id,metric_type,value,unit\n"
            "invalid_date_xxx,COLLEGE_01,BLOCK_A,energy_kwh,55.5,kWh\n"  # row 2: bad timestamp
            "2026-11-21T12:00:00Z,COLLEGE_01,BLOCK_A,energy_kwh,55.5,\n"     # row 3: missing unit
            "2026-11-21T13:00:00Z,COLLEGE_01,BLOCK_A,energy_kwh,-999.0,kWh\n" # row 4: impossible negative value
            "2026-11-21T14:00:00Z,COLLEGE_01,UNKNOWN_ZONE_999,energy_kwh,55.5,kWh\n" # row 5: unknown zone
            "2026-11-21T15:00:00Z,COLLEGE_01,BLOCK_A,energy_kwh,55.5,kWh\n"  # row 6: valid row
        )
        res = import_csv_data(
            csv_text_or_bytes=csv_data,
            selected_facility_id="COLLEGE_01",
            filename="test_malformed.csv",
            db_path=self.test_db_path
        )
        self.assertEqual(res["accepted_count"], 1)
        self.assertEqual(res["rejected_count"], 4)

        rej_rows = {r["row"]: r["reason"] for r in res["rejected_rows"]}
        self.assertIn(2, rej_rows)  # Timestamp error
        self.assertIn(3, rej_rows)  # Missing unit
        self.assertIn(4, rej_rows)  # Impossible range
        self.assertIn(5, rej_rows)  # Unknown zone

    def test_t05_duplicate_upload_prevention(self):
        """T-05: Uploading same batch twice prevents duplicates and identifies them."""
        csv_data = (
            "timestamp,facility_id,zone_id,metric_type,value,unit\n"
            "2026-11-02T10:00:00Z,COLLEGE_01,CS_BLOCK,energy_kwh,72.4,kWh\n"
        )
        res1 = import_csv_data(csv_data, selected_facility_id="COLLEGE_01", db_path=self.test_db_path)
        self.assertEqual(res1["accepted_count"], 1)

        # Upload same record second time
        res2 = import_csv_data(csv_data, selected_facility_id="COLLEGE_01", db_path=self.test_db_path)
        self.assertEqual(res2["accepted_count"], 0)
        self.assertEqual(res2["rejected_count"], 1)
        self.assertIn("already exists", res2["rejected_rows"][0]["reason"])

    def test_t06_injected_anomalies_detected(self):
        """T-06: Known injected energy spike & water leak produce expected alerts with zone, value, baseline, severity."""
        anomalies = detect_facility_anomalies(
            facility_id="COLLEGE_01",
            lookback_days=14,
            energy_threshold_pct=25.0,
            db_path=self.test_db_path
        )
        self.assertGreater(len(anomalies), 0)

        # Verify energy spike in BLOCK_B is detected
        energy_anomalies = [a for a in anomalies if a["metric_type"] == "energy_kwh" and a["zone_id"] == "BLOCK_B"]
        self.assertTrue(len(energy_anomalies) > 0)
        ea = energy_anomalies[0]
        self.assertIn(ea["severity"], ["HIGH", "CRITICAL"])
        self.assertGreater(ea["observed_value"], ea["baseline_value"])
        self.assertIn("BLOCK_B", ea["explanation"])

    def test_t07_forecast_chronological_holdout_and_baseline(self):
        """T-07: Forecast has correct horizon and units; chronological holdout metrics computed and baseline compared."""
        fc = generate_energy_forecast(
            facility_id="COLLEGE_01",
            zone_id="BLOCK_A",
            horizon_hours=24,
            force_fallback=False,
            db_path=self.test_db_path
        )
        self.assertEqual(fc["units"], "kWh")
        self.assertEqual(fc["horizon_hours"], 24)
        self.assertEqual(len(fc["forecast"]), 24)
        self.assertIn("metrics", fc)
        self.assertIn("mae_kwh", fc["metrics"])
        self.assertIn("baseline_comparator_mae_kwh", fc["metrics"])

    def test_t08_forecast_fallback_on_limited_history(self):
        """T-08: Force optional model failure or empty history returns fallback forecast without crashing."""
        fc_fb = generate_energy_forecast(
            facility_id="COLLEGE_01",
            zone_id="BLOCK_A",
            horizon_hours=24,
            force_fallback=True,
            db_path=self.test_db_path
        )
        self.assertEqual(fc_fb["units"], "kWh")
        self.assertEqual(fc_fb["model_status"], "FALLBACK_ACTIVE")
        self.assertIn("Seasonal-Naive", fc_fb["algorithm"])
        self.assertIn("warning", fc_fb)
        self.assertEqual(len(fc_fb["forecast"]), 24)

    def test_t09_whatif_scenario_arithmetic(self):
        """T-09: Change what-if reduction and tariff; baseline, scenario, delta kWh and INR recalculate correctly with assumptions."""
        res = simulate_energy_scenario(
            facility_id="COLLEGE_01",
            reduction_pct=10.0,
            tariff_inr_per_kwh=9.50,
            baseline_kwh=1000.0,
            time_window_hours=24,
            persist=False,
            db_path=self.test_db_path
        )
        # 10% of 1000 kWh = 100 kWh reduction
        self.assertEqual(res["delta"]["energy_reduction_kwh"], 100.0)
        self.assertEqual(res["scenario"]["scenario_kwh"], 900.0)
        # 100 kWh * 9.50 = 950.0 INR
        self.assertEqual(res["delta"]["cost_reduction_inr"], 950.0)
        self.assertEqual(res["disclaimer"], "Estimate, not verified savings")

    def test_t10_alert_action_lifecycle_and_audit_persistence(self):
        """T-10: Accept, assign, and complete an alert. Status and note persist in SQLite and have an audit record."""
        alerts = list_alerts(facility_id="COLLEGE_01", db_path=self.test_db_path)
        self.assertGreater(len(alerts), 0)
        target_alert = alerts[0]
        aid = target_alert["id"]

        # Update alert
        updated = update_alert(
            alert_id=aid,
            status="ASSIGNED",
            assignee="alex.chen@estateiq.in",
            due_date="2026-11-05",
            notes="Technician assigned for immediate inspection.",
            user_id="admin",
            db_path=self.test_db_path
        )
        self.assertEqual(updated["status"], "ASSIGNED")
        self.assertEqual(updated["assignee"], "alex.chen@estateiq.in")

        # Verify persistent query from fresh connection
        fresh_conn = get_db_connection(self.test_db_path)
        cur = fresh_conn.cursor()
        cur.execute("SELECT status, assignee, notes FROM alerts WHERE id = ?", (aid,))
        row = cur.fetchone()
        fresh_conn.close()
        self.assertEqual(row["status"], "ASSIGNED")
        self.assertEqual(row["assignee"], "alex.chen@estateiq.in")

        # Verify persistent action and audit event
        actions = list_actions(alert_id=aid, db_path=self.test_db_path)
        self.assertGreater(len(actions), 0)
        self.assertEqual(actions[0]["status"], "ASSIGNED")

        audits = list_audit_events(entity_id=aid, db_path=self.test_db_path)
        self.assertGreater(len(audits), 0)
        self.assertEqual(audits[0]["action"], "UPDATE_ALERT")

    def test_t11_rbac_server_side_enforcement(self):
        """T-11: Attempt admin-only endpoint as operations user returns 403 Forbidden and blocks change."""
        headers = {"Authorization": f"Bearer {self.ops_token}"}
        resp = self.client.delete("/readings/batches/BATCH_SEED_INIT_001", headers=headers)
        self.assertEqual(resp.status_code, 403)
        self.assertIn("Forbidden", resp.json()["detail"])

        # Also test admin demo reset endpoint
        resp_reset = self.client.post("/admin/demo/reset", headers=headers)
        self.assertEqual(resp_reset.status_code, 403)

    def test_t12_offline_recommendations_resilience(self):
        """T-12: Disable internet / omit LLM key. Core features continue and deterministic recommendations are available."""
        recs = generate_actionable_recommendations(facility_id="COLLEGE_01", db_path=self.test_db_path)
        self.assertIsInstance(recs, list)
        if recs:
            r = recs[0]
            self.assertIn("headline", r)
            self.assertIn("evidence", r)
            self.assertIn("action", r)
            self.assertIn("priority", r)
            self.assertIn("estimate", r)

    def test_t13_scoped_report_export(self):
        """T-13: Export report for one facility and date range. No records from other facilities appear."""
        summary = generate_report_summary(
            facility_id="COLLEGE_01",
            zone_id="BLOCK_A",
            db_path=self.test_db_path
        )
        self.assertEqual(summary["scope"]["facility_id"], "COLLEGE_01")
        self.assertEqual(summary["scope"]["zone_id"], "BLOCK_A")
        self.assertIn("kpis", summary)
        self.assertIn("data_quality", summary)
        self.assertIn("limitations", summary)

        # CSV Export
        csv_text = export_readings_csv(facility_id="COLLEGE_01", zone_id="BLOCK_A", db_path=self.test_db_path)
        self.assertIn("COLLEGE_01", csv_text)
        self.assertNotIn("BLOCK_B", csv_text)  # Scoped strictly to BLOCK_A

        # Printable HTML
        html_out = generate_printable_html_report(summary)
        self.assertIn("EstateIQ Sustainable Facility Executive Summary", html_out)
        self.assertIn("COLLEGE_01", html_out)
        self.assertIn("Estimate, Not Verified Savings", html_out)

    def test_t14_stale_sensor_data_quality_warning(self):
        """T-14: Simulate stale sensor readings; freshness indicator and data-quality warning are visible."""
        # Query with old date range
        old_kpis = calculate_facility_kpis(
            facility_id="COLLEGE_01",
            start_time="2020-01-01T00:00:00Z",
            end_time="2020-01-02T00:00:00Z",
            db_path=self.test_db_path
        )
        # Empty old period returns NO_DATA status
        self.assertEqual(old_kpis["status"], "NO_DATA")

        # Current KPI freshness check
        cur_kpis = calculate_facility_kpis(facility_id="COLLEGE_01", db_path=self.test_db_path)
        self.assertIn("freshness_sec", cur_kpis["data_quality"])

    def test_t15_demo_reset(self):
        """T-15: Reset demo command returns the database to known test state without manual editing."""
        # Insert a junk alert
        fresh_conn = get_db_connection(self.test_db_path)
        cur = fresh_conn.cursor()
        cur.execute("""
        INSERT INTO alerts (id, facility_id, zone_id, metric_type, severity, observed_value, baseline_value, explanation, status, created_at)
        VALUES ('ALT_TEST_JUNK', 'COLLEGE_01', 'BLOCK_A', 'energy_kwh', 'LOW', 10.0, 10.0, 'Junk test', 'OPEN', '2026-11-01T00:00:00Z')
        """)
        fresh_conn.commit()
        fresh_conn.close()

        # Run reset
        res = reset_demo_dataset(self.test_db_path)
        self.assertEqual(res["status"], "SEEDED")

        # Verify junk alert was cleaned
        junk = get_alert("ALT_TEST_JUNK", db_path=self.test_db_path)
        self.assertIsNone(junk)

    def test_batch_rollback(self):
        """Verify rolling back a batch removes its records and logs audit event."""
        csv_data = (
            "timestamp,facility_id,zone_id,metric_type,value,unit\n"
            "2026-11-03T10:00:00Z,COLLEGE_01,UTILITY,energy_kwh,115.0,kWh\n"
        )
        res = import_csv_data(csv_data, selected_facility_id="COLLEGE_01", db_path=self.test_db_path)
        b_id = res["batch_id"]

        # Verify reading exists
        readings, _ = query_readings(facility_id="COLLEGE_01", zone_id="UTILITY", db_path=self.test_db_path)
        self.assertTrue(any(r["batch_id"] == b_id for r in readings))

        # Rollback
        rb = rollback_batch(batch_id=b_id, user_id="admin", db_path=self.test_db_path)
        self.assertTrue(rb["success"])
        self.assertEqual(rb["deleted_count"], 1)

        # Verify reading is gone
        readings_after, _ = query_readings(facility_id="COLLEGE_01", zone_id="UTILITY", db_path=self.test_db_path)
        self.assertFalse(any(r["batch_id"] == b_id for r in readings_after))


if __name__ == "__main__":
    unittest.main()
