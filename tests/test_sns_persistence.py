import hashlib

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from src.data import canonical_db
from src.services import sns


@pytest.fixture
def sns_db(tmp_path, monkeypatch):
    db_file = tmp_path / "estateiq-sns-test.db"
    monkeypatch.setattr(canonical_db, "get_db_path", lambda: db_file)
    sns.init_sns_schema()
    return db_file


def test_alert_event_persists_and_deduplicates_per_recipient(sns_db):
    event = {
        "event_type": "alert.created", "source": "simulated_iot", "severity": "HIGH",
        "title": "Energy spike", "message": "Energy is above baseline", "facility_id": "FAC_GEC_01",
        "related_id": "ALT_TEST_1", "device_id": "DEV_1", "metric": "active_power_kw",
        "dedupe_key": "ALT_TEST_1"
    }
    created = sns.emit_event(event)
    assert {item["recipient_email"] for item in created} == {"admin@estateiq.in", "operations@estateiq.in"}
    assert sns.emit_event(event) == []
    for email in ("admin@estateiq.in", "operations@estateiq.in"):
        result = sns.list_notifications(email)
        assert result["count"] == 1
        assert result["notifications"][0]["title"] == "Energy spike"


def test_notification_state_is_durable_and_recipient_scoped(sns_db):
    item = sns.create_notification(recipient_email="operations@estateiq.in", title="Water alert", message="Leak", event_key="water-1")
    assert sns.get_notification(item["id"], "admin@estateiq.in") is None
    assert sns.update_notification(item["id"], "admin@estateiq.in", "read") is None
    updated = sns.update_notification(item["id"], "operations@estateiq.in", "acknowledge")
    assert updated["status"] == "ACKNOWLEDGED"
    assert updated["read"] is True
    assert sns.list_notifications("operations@estateiq.in", unread_only=True)["count"] == 0


def test_configurable_rule_checks_conditions(sns_db):
    sns.save_rule({
        "name": "Large reading", "event_type": "meter.reading", "enabled": True,
        "conditions": [{"field": "value", "operator": "gt", "value": 10}],
        "logical_operator": "AND", "severity": "HIGH", "recipient_roles": [],
        "recipient_emails": ["admin@estateiq.in"], "channels": ["in_app"], "cooldown_seconds": 0
    }, actor="admin@estateiq.in")
    assert sns.emit_event({"event_type": "meter.reading", "value": 11, "dedupe_key": "reading-1", "title": "High meter"})
    assert not sns.emit_event({"event_type": "meter.reading", "value": 9, "dedupe_key": "reading-2", "title": "Normal meter"})


def test_telegram_link_tokens_are_single_use(sns_db):
    token = sns.create_telegram_link_token("operations@estateiq.in")
    assert sns.complete_telegram_link(token, "telegram-chat-42") is True
    assert sns.complete_telegram_link(token, "telegram-chat-43") is False
    conn = canonical_db.get_db_connection()
    try:
        saved_hash = conn.execute("SELECT token_hash FROM sns_link_tokens").fetchone()[0]
        assert saved_hash == hashlib.sha256(token.encode()).hexdigest()
        assert saved_hash != token
    finally:
        conn.close()


def test_sns_endpoints_reject_missing_bearer_credentials():
    from api.sns_routes import _current_user
    from src.auth.security import DEFAULT_USER, create_user_token
    with pytest.raises(HTTPException) as error:
        _current_user(None)
    assert error.value.status_code == 401
    demo_token = create_user_token(DEFAULT_USER, auth_method="demo_role_switch")
    with pytest.raises(HTTPException) as demo_error:
        _current_user(HTTPAuthorizationCredentials(scheme="Bearer", credentials=demo_token))
    assert demo_error.value.status_code == 401
    real_token = create_user_token(DEFAULT_USER, auth_method="password")
    assert _current_user(HTTPAuthorizationCredentials(scheme="Bearer", credentials=real_token))["role"] == "SUPER_ADMIN"


