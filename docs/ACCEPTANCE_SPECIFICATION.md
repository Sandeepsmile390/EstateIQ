# EstateIQ — Master Implementation & Acceptance Specification

**Aligned with `EstateIQ_Final_Round_Implementation_Report.pdf` (Version 1.0, 29 October 2026, Problem Statement PS-04)**

---

## 1. Executive Summary & Verification Result

| Metric / Dimension | Outcome / Status | Implementation & Evidence Reference |
|---|---|---|
| **Overall Acceptance Status** | **PASS** | Core local demo journey verified end-to-end |
| **Acceptance Suite (T-01 to T-15)** | **16 / 16 Tests Passing (100%)** | `tests/test_final_round_acceptance.py` |
| **Total Test Suite Pass Rate** | **143 / 143 Tests Passing (100%)** | `pytest tests/` |
| **Local Demo Reliability** | **PASS** | Deterministic seed/reset, offline mode, zero cloud dependency |
| **Canonical Storage Schema** | **PASS** | SQLite (`facility_dataset/facility.db`) with 9 canonical tables |
| **Data Ingestion & Quality** | **PASS** | 20-row preview, column mapping, row validation, batch rollback |
| **Forecasting & Anomaly Detection** | **PASS** | Seasonal-naive fallback, chronological holdout, MAD anomaly detection |
| **Persistent Action Tracking** | **PASS** | Alert state machine, assignments, due dates, SQLite audit events |
| **Scoped Reporting & Exports** | **PASS** | Filtered CSV export and printable HTML summary |
| **Security & RBAC Enforcement** | **PASS** | Server-side role checks (`403 Forbidden` on unauthorized writes) |

---

## 2. Functional Requirements Checklist (Report Table 2.1)

| ID | Requirement | Status | Acceptance Evidence & Verifiable Implementation |
|---|---|---|---|
| **FR-01** | **Facility and zone selector** | **PASS** | Sidebar filters update KPIs, charts, alerts, and export scopes (`app.py`, `Home.py`). API endpoints (`/readings`, `/alerts`, `/reports/summary`) enforce `facility_id` and `zone_id` parameters. Verified in `TestFinalRoundAcceptance.test_t13_scoped_report_export`. |
| **FR-02** | **Data ingestion** | **PASS** | `/readings/import/csv` validates timestamps, units, and ranges. Returns exact row number and cause for rejected rows. Preview endpoint `/readings/preview` shows first 20 rows and inferred mapping. Verified in `test_t03_import_valid_csv` and `test_t04_import_malformed_csv_validation`. |
| **FR-03** | **Synthetic feed** | **PASS** | `scripts/seed_demo_data.py` and `scripts/reset_demo.py` generate deterministic 14-day campus dataset across 14 zones with 4 injected anomalies (`BLOCK_B` energy spike, overnight water leak, waste overflow, PM2.5 surge). Verified in `test_t01_clean_init_and_seed` and `test_t06_injected_anomalies_detected`. |
| **FR-04** | **Data quality** | **PASS** | `src/ingestion/validation.py` detects missing, out-of-range, and stale readings. Duplicate prevention rejects identical timestamps in batch or DB. Quality banners show status. Verified in `test_t05_duplicate_upload_prevention` and `test_t14_stale_sensor_data_quality_warning`. |
| **FR-05** | **Analytics refresh** | **PASS** | `/analysis/run` executes anomaly pipeline and persists run record to `analysis_runs` with timestamps, model name, and execution metrics. Verified in `test_t06_injected_anomalies_detected`. |
| **FR-06** | **Anomaly alerts** | **PASS** | `src/analytics/anomaly.py` detects deviations via rolling median + MAD. Alerts include `severity`, `observed_value`, `baseline_value`, `timestamp`, `zone_id`, `explanation`, and `evidence`. Verified in `test_t06_injected_anomalies_detected`. |
| **FR-07** | **Forecast** | **PASS** | `src/analytics/forecast.py` generates 24h horizon with chronological train/test holdout validation (MAE/RMSE). Automatically falls back to deterministic seasonal-naive when ML is absent or history is short. Verified in `test_t07_forecast_chronological_holdout_and_baseline` and `test_t08_forecast_fallback_on_limited_history`. |
| **FR-08** | **Scenario** | **PASS** | `src/analytics/scenarios.py` calculates proportional energy what-if: baseline, scenario, delta, and cost at configurable tariff (₹9.50/kWh). Displays `"Estimate, not verified savings"`. Verified in `test_t09_whatif_scenario_arithmetic`. |
| **FR-09** | **Action tracking** | **PASS** | Alerts transition through `OPEN` ➔ `ACKNOWLEDGED` ➔ `ASSIGNED` ➔ `IN_PROGRESS` ➔ `COMPLETED` ➔ `DISMISSED`. All changes persist to SQLite `actions` and log to `audit_events`. Verified in `test_t10_alert_action_lifecycle_and_audit_persistence`. |
| **FR-10** | **Report export** | **PASS** | `/reports/export/csv` and `/reports/printable` generate scoped summaries matching selected facility, zone, and time range without leaking other data. Verified in `test_t13_scoped_report_export`. |
| **FR-11** | **Role-based access** | **PASS** | `src/auth/security.py` enforces server-side role validation via `require_role(...)`. Unauthorized operations users receive `403 Forbidden` on admin-only endpoints. Verified in `test_t11_rbac_server_side_enforcement`. |
| **FR-12** | **Resilience** | **PASS** | Empty database, malformed CSV, and offline mode return structured responses without crashing. Fallback rule templates operate when external LLM key is absent. Verified in `test_t02_empty_database_resilience` and `test_t12_offline_recommendations_resilience`. |

---

## 3. Required Test Cases (Report Table 10.1)

| Test ID | Test Action | Expected Result | Result | Evidence File / Function |
|---|---|---|---|---|
| **T-01** | Start from clean checkout with no existing DB | DB initializes, sample data seeds, apps start | **PASS** | `TestFinalRoundAcceptance.test_t01_clean_init_and_seed` |
| **T-02** | Open dashboard with empty database | No crash; clear onboarding/no-data state | **PASS** | `TestFinalRoundAcceptance.test_t02_empty_database_resilience` |
| **T-03** | Import valid CSV | Accepted row count matches; queryable records | **PASS** | `TestFinalRoundAcceptance.test_t03_import_valid_csv` |
| **T-04** | Import malformed CSV (bad TS, missing unit, impossible value) | Bad rows rejected with row # and cause; valid rows ingested | **PASS** | `TestFinalRoundAcceptance.test_t04_import_malformed_csv_validation` |
| **T-05** | Upload same batch twice | Duplicates prevented; duplicate count reported | **PASS** | `TestFinalRoundAcceptance.test_t05_duplicate_upload_prevention` |
| **T-06** | Inject known energy spike and water leak | Expected alerts appear with correct zone, timestamp, value, baseline | **PASS** | `TestFinalRoundAcceptance.test_t06_injected_anomalies_detected` |
| **T-07** | Run forecast on dataset with enough history | Correct horizon, chronological holdout MAE/RMSE compared to baseline | **PASS** | `TestFinalRoundAcceptance.test_t07_forecast_chronological_holdout_and_baseline` |
| **T-08** | Run forecast on limited history / forced model failure | Fallback forecast returns; low-confidence warning displayed; no crash | **PASS** | `TestFinalRoundAcceptance.test_t08_forecast_fallback_on_limited_history` |
| **T-09** | Change what-if reduction and tariff | Baseline, scenario, estimated kWh and ₹ delta recalculate correctly | **PASS** | `TestFinalRoundAcceptance.test_t09_whatif_scenario_arithmetic` |
| **T-10** | Accept, assign, and complete an alert | Status/owner/note persists across restart; audit event exists | **PASS** | `TestFinalRoundAcceptance.test_t10_alert_action_lifecycle_and_audit_persistence` |
| **T-11** | Attempt admin-only endpoint as operations user | Server returns 403 Forbidden; no data changed | **PASS** | `TestFinalRoundAcceptance.test_t11_rbac_server_side_enforcement` |
| **T-12** | Disable internet / omit LLM key | Deterministic recommendations available offline | **PASS** | `TestFinalRoundAcceptance.test_t12_offline_recommendations_resilience` |
| **T-13** | Export report for one facility and date range | No records from other facilities appear; provenance labels included | **PASS** | `TestFinalRoundAcceptance.test_t13_scoped_report_export` |
| **T-14** | Simulate stale sensor data | Freshness indicator and data-quality warning visible | **PASS** | `TestFinalRoundAcceptance.test_t14_stale_sensor_data_quality_warning` |
| **T-15** | Reset demo | Documented command returns app to clean state | **PASS** | `TestFinalRoundAcceptance.test_t15_demo_reset` |

---

## 4. Acceptance Thresholds & Verification Summary (Report Section 10.2)

- **Application Reliability**: 100% of demo steps operate locally without crashing.
- **Data Processing**: 100% of invalid rows in test fixtures rejected with explicit reasons.
- **Anomaly Detection**: 100% of predefined injected critical anomalies detected.
- **Forecasting**: Deterministic seasonal-naive fallback operational under all failure modes.
- **Traceability**: 100% of generated recommendations reference underlying evidence and thresholds.
- **Persistence**: All actions, alerts, and audit logs persist in SQLite across restarts.
- **Authorization**: Server-side role checks reject unauthorized mutations (`403 Forbidden`).
