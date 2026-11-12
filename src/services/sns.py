"""Persistent EstateIQ Smart Notification System primitives.

SNS shares EstateIQ's SQLite database and alert/event model. Notifications and
delivery attempts are durable; external delivery is handled by the optional
worker so sensor ingestion never blocks on a third-party network.
"""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from src.data.canonical_db import get_db_connection, init_canonical_schema


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _json(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True, default=str)


def init_sns_schema() -> None:
    init_canonical_schema()
    conn = get_db_connection()
    try:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS sns_rules (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
            event_type TEXT NOT NULL, enabled INTEGER NOT NULL DEFAULT 1,
            conditions_json TEXT NOT NULL DEFAULT '[]', logical_operator TEXT NOT NULL DEFAULT 'AND',
            severity TEXT NOT NULL DEFAULT 'MEDIUM', recipient_roles_json TEXT NOT NULL DEFAULT '["OPERATIONS_ENGINEER"]',
            recipient_emails_json TEXT NOT NULL DEFAULT '[]', channels_json TEXT NOT NULL DEFAULT '["in_app"]',
            cooldown_seconds INTEGER NOT NULL DEFAULT 300, created_by TEXT NOT NULL DEFAULT 'system',
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_sns_rules_event_enabled ON sns_rules(event_type, enabled);
        CREATE TABLE IF NOT EXISTS sns_notifications (
            id TEXT PRIMARY KEY, recipient_email TEXT NOT NULL, recipient_role TEXT NOT NULL DEFAULT 'STAFF',
            facility_id TEXT, source TEXT NOT NULL, event_type TEXT NOT NULL, severity TEXT NOT NULL,
            title TEXT NOT NULL, message TEXT NOT NULL, payload_json TEXT NOT NULL DEFAULT '{}',
            related_id TEXT, event_key TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'UNREAD',
            created_at TEXT NOT NULL, read_at TEXT, acknowledged_at TEXT, resolved_at TEXT,
            UNIQUE(recipient_email, event_key)
        );
        CREATE INDEX IF NOT EXISTS idx_sns_notifications_recipient_created ON sns_notifications(recipient_email, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_sns_notifications_status ON sns_notifications(status, severity);
        CREATE TABLE IF NOT EXISTS sns_outbox (
            id TEXT PRIMARY KEY, notification_id TEXT NOT NULL, channel TEXT NOT NULL,
            recipient TEXT NOT NULL, payload_json TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'PENDING',
            attempts INTEGER NOT NULL DEFAULT 0, next_attempt_at TEXT, last_error TEXT,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
            UNIQUE(notification_id, channel, recipient)
        );
        CREATE INDEX IF NOT EXISTS idx_sns_outbox_claim ON sns_outbox(status, next_attempt_at, created_at);
        CREATE TABLE IF NOT EXISTS sns_deliveries (
            id TEXT PRIMARY KEY, notification_id TEXT NOT NULL, outbox_id TEXT NOT NULL,
            channel TEXT NOT NULL, recipient TEXT NOT NULL, status TEXT NOT NULL,
            attempt INTEGER NOT NULL DEFAULT 1, error TEXT, attempted_at TEXT NOT NULL,
            UNIQUE(outbox_id, attempt)
        );
        CREATE TABLE IF NOT EXISTS sns_rule_events (
            rule_id TEXT NOT NULL, dedupe_key TEXT NOT NULL, last_fired_at TEXT NOT NULL,
            PRIMARY KEY(rule_id, dedupe_key)
        );
        CREATE TABLE IF NOT EXISTS sns_link_tokens (
            token_hash TEXT PRIMARY KEY, user_email TEXT NOT NULL, expires_at REAL NOT NULL,
            used_at TEXT, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS sns_telegram_poll_state (
            id INTEGER PRIMARY KEY CHECK (id=1), next_update_id INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS sns_telegram_global_events (
            event_key TEXT PRIMARY KEY, notification_id TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS sns_recipient_channels (
            user_email TEXT NOT NULL, channel TEXT NOT NULL, channel_user_id TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1, linked_at TEXT NOT NULL,
            PRIMARY KEY(user_email, channel)
        );
        """)
        now = _now()
        conn.execute("""INSERT OR IGNORE INTO sns_rules
            (id,name,description,event_type,enabled,conditions_json,logical_operator,severity,
             recipient_roles_json,recipient_emails_json,channels_json,cooldown_seconds,created_by,created_at,updated_at)
            VALUES(?,?,?,?,1,'[]','AND','HIGH','[\"OPERATIONS_ENGINEER\",\"FACILITY_ADMIN\",\"SUPER_ADMIN\"]','[]','[\"in_app\",\"telegram\"]',300,'system',?,?)""",
            ("sns-default-alert-created", "Notify on new facility alert", "Routes new EstateIQ alerts to operations and facility administrators.", "alert.created", now, now))
        # Upgrade the shipped default for existing databases while preserving an admin's custom rule settings.
        conn.execute("UPDATE sns_rules SET channels_json='[\"in_app\",\"telegram\"]' WHERE id='sns-default-alert-created' AND channels_json='[\"in_app\"]'")
        conn.commit()
    finally:
        conn.close()


def _all_users() -> List[Dict[str, Any]]:
    from src.auth.security import USERS_DB
    unique: Dict[str, Dict[str, Any]] = {}
    for user in USERS_DB.values():
        email = (user.get("email") or "").strip().lower()
        if email:
            unique[email] = user
    return list(unique.values())


def list_notifications(email: str, unread_only: bool = False, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
    init_sns_schema()
    conn = get_db_connection()
    try:
        where = "recipient_email = ?" + (" AND status = 'UNREAD'" if unread_only else "")
        total = conn.execute(f"SELECT COUNT(*) FROM sns_notifications WHERE {where}", (email.lower(),)).fetchone()[0]
        rows = conn.execute(f"SELECT * FROM sns_notifications WHERE {where} ORDER BY created_at DESC LIMIT ? OFFSET ?", (email.lower(), limit, offset)).fetchall()
        items = []
        for row in rows:
            item = dict(row)
            item["payload"] = json.loads(item.pop("payload_json") or "{}")
            item["read"] = item["read_at"] is not None
            items.append(item)
        unread = conn.execute("SELECT COUNT(*) FROM sns_notifications WHERE recipient_email=? AND status='UNREAD'", (email.lower(),)).fetchone()[0]
        return {"count": total, "unread_count": unread, "notifications": items}
    finally:
        conn.close()


def get_notification(notification_id: str, email: str) -> Optional[Dict[str, Any]]:
    init_sns_schema()
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT * FROM sns_notifications WHERE id=? AND recipient_email=?", (notification_id,email.lower())).fetchone()
        if not row:
            return None
        item = dict(row)
        item["payload"] = json.loads(item.pop("payload_json") or "{}")
        item["read"] = item["read_at"] is not None
        return item
    finally:
        conn.close()


def update_notification(notification_id: str, email: str, action: str) -> Optional[Dict[str, Any]]:
    init_sns_schema()
    now = _now()
    fields = {"read": ("read_at", "READ"), "acknowledge": ("acknowledged_at", "ACKNOWLEDGED"), "resolve": ("resolved_at", "RESOLVED")}
    if action not in fields:
        raise ValueError("Unsupported notification action")
    column, status = fields[action]
    conn = get_db_connection()
    try:
        read_update = ", read_at=COALESCE(read_at, ?)" if action in ("acknowledge", "resolve") else ""
        params = (now, status, now, notification_id, email.lower()) if read_update else (now, status, notification_id, email.lower())
        cur = conn.execute(f"UPDATE sns_notifications SET {column}=COALESCE({column}, ?), status=?{read_update} WHERE id=? AND recipient_email=?", params)
        if not cur.rowcount:
            conn.rollback()
            return None
        row = conn.execute("SELECT * FROM sns_notifications WHERE id=?", (notification_id,)).fetchone()
        conn.execute("INSERT INTO audit_events(id,user_id,entity_type,entity_id,action,after_json,timestamp) VALUES(?,?,?,?,?,?,?)",
                     ("AUD_"+uuid.uuid4().hex[:10],email.lower(),"sns_notification",notification_id,action.upper(),_json({"status":status}),now))
        conn.commit()
        result = dict(row)
        result["payload"] = json.loads(result.pop("payload_json") or "{}")
        result["read"] = result["read_at"] is not None
        return result
    finally:
        conn.close()


def create_notification(*, recipient_email: str, title: str, message: str, recipient_role: str = "STAFF",
                        priority: str = "MEDIUM", related_object_id: Optional[str] = None,
                        action_link: Optional[str] = None, source: str = "estateiq",
                        event_type: str = "notification.created", facility_id: Optional[str] = None,
                        payload: Optional[Dict[str, Any]] = None, event_key: Optional[str] = None,
                        channels: Optional[Iterable[str]] = None) -> Dict[str, Any]:
    init_sns_schema()
    email = recipient_email.strip().lower()
    key = event_key or uuid.uuid4().hex
    notification_id = "SNS_" + uuid.uuid4().hex[:16].upper()
    now = _now()
    body = dict(payload or {})
    if action_link:
        body["action_link"] = action_link
    channel_list = list(channels or ["in_app"])
    global_chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    # A configured shared chat receives every newly-created SNS notification.
    # Per-user Telegram links remain available when no shared chat is configured.
    if global_chat_id:
        channel_list = [channel for channel in channel_list if channel != "telegram"]
    conn = get_db_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        inserted = conn.execute("""INSERT OR IGNORE INTO sns_notifications
            (id,recipient_email,recipient_role,facility_id,source,event_type,severity,title,message,payload_json,related_id,event_key,status,created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,'UNREAD',?)""",
            (notification_id,email,recipient_role.upper(),facility_id,source,event_type,priority.upper(),title,message,_json(body),related_object_id,key,now))
        row = conn.execute("SELECT * FROM sns_notifications WHERE recipient_email=? AND event_key=?", (email,key)).fetchone()
        if row is None:
            raise RuntimeError("Notification persistence failed")
        persisted_id = row["id"]
        if inserted.rowcount:
            conn.execute("INSERT INTO audit_events(id,user_id,entity_type,entity_id,action,after_json,timestamp) VALUES(?,?,?,?,?,?,?)",
                         ("AUD_"+uuid.uuid4().hex[:10],"system","sns_notification",persisted_id,"CREATED",_json({"recipient":email,"event_type":event_type,"severity":priority.upper()}),now))
        for channel in channel_list:
            if channel not in ("in_app", "telegram"):
                continue
            outbox_id = "OUT_" + uuid.uuid4().hex[:16].upper()
            recipient = email
            payload_json = _json({"title": title, "message": message, "severity": priority.upper(), "notification_id": persisted_id})
            out_status = "SENT" if channel == "in_app" else "PENDING"
            conn.execute("INSERT OR IGNORE INTO sns_outbox (id,notification_id,channel,recipient,payload_json,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
                         (outbox_id,persisted_id,channel,recipient,payload_json,out_status,now,now))
            outbox = conn.execute("SELECT id,status FROM sns_outbox WHERE notification_id=? AND channel=? AND recipient=?", (persisted_id,channel,recipient)).fetchone()
            if channel == "in_app" and outbox:
                conn.execute("INSERT OR IGNORE INTO sns_deliveries (id,notification_id,outbox_id,channel,recipient,status,attempt,attempted_at) VALUES(?,?,?,?,?,'DELIVERED',1,?)",
                             ("DLV_" + uuid.uuid4().hex[:16].upper(),persisted_id,outbox["id"],channel,recipient,now))
        if inserted.rowcount and global_chat_id:
            global_event = conn.execute("INSERT OR IGNORE INTO sns_telegram_global_events(event_key,notification_id,created_at) VALUES(?,?,?)",
                (key, persisted_id, now))
            if global_event.rowcount:
                telegram_outbox_id = "OUT_" + uuid.uuid4().hex[:16].upper()
                telegram_payload = _json({"title": title, "message": message, "severity": priority.upper(), "notification_id": persisted_id})
                conn.execute("INSERT OR IGNORE INTO sns_outbox (id,notification_id,channel,recipient,payload_json,status,created_at,updated_at) VALUES(?,?, 'telegram', ?, ?, 'PENDING', ?, ?)",
                    (telegram_outbox_id, persisted_id, global_chat_id, telegram_payload, now, now))
        conn.commit()
        if inserted.rowcount and (global_chat_id or any(c == "telegram" for c in channel_list)):
            try:
                import threading
                threading.Thread(target=deliver_telegram_outbox, kwargs={"batch_size": 10}, daemon=True).start()
            except Exception:
                pass
        result = dict(row)
        result["payload"] = body
        result["read"] = False
        return result
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _condition_matches(event: Dict[str, Any], condition: Dict[str, Any]) -> bool:
    field = str(condition.get("field", ""))
    actual: Any = event
    for part in field.split("."):
        if not isinstance(actual, dict) or part not in actual:
            return False
        actual = actual[part]
    op, expected = condition.get("operator", "eq"), condition.get("value")
    try:
        if op in ("gt", "gte", "lt", "lte"):
            a, b = float(actual), float(expected)
            return {"gt": a > b, "gte": a >= b, "lt": a < b, "lte": a <= b}[op]
        if op == "ne": return actual != expected
        if op == "in": return actual in expected
        if op == "contains": return expected in actual
        return actual == expected
    except (TypeError, ValueError):
        return False


def emit_event(event: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Evaluate enabled rules and persist recipient notifications idempotently."""
    init_sns_schema()
    event_type = str(event.get("event_type", ""))
    conn = get_db_connection()
    try:
        rows = conn.execute("SELECT * FROM sns_rules WHERE enabled=1 AND event_type IN (?, '*') ORDER BY id", (event_type,)).fetchall()
    finally:
        conn.close()
    created: List[Dict[str, Any]] = []
    users = _all_users()
    for row in rows:
        rule = dict(row)
        conditions = json.loads(rule["conditions_json"] or "[]")
        matches = [_condition_matches(event, condition) for condition in conditions]
        if conditions and not (all(matches) if rule["logical_operator"] == "AND" else any(matches)):
            continue
        rule_id = rule["id"]
        dedupe_key = str(event.get("dedupe_key") or event.get("related_id") or event.get("device_id") or event_type)
        now = _now()
        conn = get_db_connection()
        try:
            conn.execute("BEGIN IMMEDIATE")
            previous = conn.execute("SELECT last_fired_at FROM sns_rule_events WHERE rule_id=? AND dedupe_key=?", (rule_id,dedupe_key)).fetchone()
            if previous:
                try:
                    elapsed = datetime.fromisoformat(now.replace("Z", "+00:00")).timestamp() - datetime.fromisoformat(previous[0].replace("Z", "+00:00")).timestamp()
                except Exception:
                    elapsed = 0
                if elapsed < int(rule["cooldown_seconds"]):
                    conn.rollback()
                    continue
            conn.execute("INSERT INTO sns_rule_events(rule_id,dedupe_key,last_fired_at) VALUES(?,?,?) ON CONFLICT(rule_id,dedupe_key) DO UPDATE SET last_fired_at=excluded.last_fired_at", (rule_id,dedupe_key,now))
            conn.commit()
        finally:
            conn.close()
        roles = set(json.loads(rule["recipient_roles_json"] or "[]"))
        explicit = {value.lower() for value in json.loads(rule["recipient_emails_json"] or "[]")}
        recipients = [user for user in users if user.get("role") in roles or user.get("email", "").lower() in explicit]
        channels = json.loads(rule["channels_json"] or '["in_app"]')
        for user in recipients:
            email = user["email"].lower()
            event_key = f"{rule_id}:{dedupe_key}"
            result = create_notification(recipient_email=email,recipient_role=user.get("role","STAFF"),title=str(event.get("title") or rule["name"]),
                message=str(event.get("message") or event.get("summary") or rule["description"] or rule["name"]),priority=str(event.get("severity") or rule["severity"]),
                related_object_id=event.get("related_id"),source=str(event.get("source", "estateiq")),event_type=event_type,
                facility_id=event.get("facility_id"),payload=event,event_key=event_key,channels=channels)
            created.append(result)
    return created


def list_rules() -> List[Dict[str, Any]]:
    init_sns_schema()
    conn = get_db_connection()
    try:
        results = []
        for row in conn.execute("SELECT * FROM sns_rules ORDER BY created_at DESC"):
            item = dict(row)
            for col, key in (("conditions_json","conditions"),("recipient_roles_json","recipient_roles"),("recipient_emails_json","recipient_emails"),("channels_json","channels")):
                item[key] = json.loads(item.pop(col))
            item["enabled"] = bool(item["enabled"])
            results.append(item)
        return results
    finally:
        conn.close()


def save_rule(data: Dict[str, Any], rule_id: Optional[str] = None, actor: str = "system") -> Dict[str, Any]:
    init_sns_schema()
    rule_id = rule_id or "RULE_" + uuid.uuid4().hex[:12].upper()
    now = _now()
    conn = get_db_connection()
    try:
        exists = conn.execute("SELECT id FROM sns_rules WHERE id=?", (rule_id,)).fetchone()
        if exists and rule_id == "sns-default-alert-created":
            raise ValueError("The built-in alert routing rule cannot be edited or deleted")
        if exists:
            conn.execute("""UPDATE sns_rules SET name=?,description=?,event_type=?,enabled=?,conditions_json=?,logical_operator=?,severity=?,recipient_roles_json=?,recipient_emails_json=?,channels_json=?,cooldown_seconds=?,updated_at=? WHERE id=?""",
                (data["name"],data.get("description",""),data["event_type"],int(data.get("enabled",True)),_json(data.get("conditions",[])),data.get("logical_operator","AND"),data.get("severity","MEDIUM"),_json(data.get("recipient_roles",[])),_json(data.get("recipient_emails",[])),_json(data.get("channels",["in_app"])),int(data.get("cooldown_seconds",300)),now,rule_id))
            action = "UPDATED"
        else:
            conn.execute("""INSERT INTO sns_rules (id,name,description,event_type,enabled,conditions_json,logical_operator,severity,recipient_roles_json,recipient_emails_json,channels_json,cooldown_seconds,created_by,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",(rule_id,data["name"],data.get("description",""),data["event_type"],int(data.get("enabled",True)),_json(data.get("conditions",[])),data.get("logical_operator","AND"),data.get("severity","MEDIUM"),_json(data.get("recipient_roles",[])),_json(data.get("recipient_emails",[])),_json(data.get("channels",["in_app"])),int(data.get("cooldown_seconds",300)),actor,now,now))
            action = "CREATED"
        conn.execute("INSERT INTO audit_events(id,user_id,entity_type,entity_id,action,after_json,timestamp) VALUES(?,?,?,?,?,?,?)",
                     ("AUD_"+uuid.uuid4().hex[:10],actor,"sns_rule",rule_id,action,_json({"event_type":data["event_type"],"enabled":bool(data.get("enabled",True))}),now))
        conn.commit()
    finally:
        conn.close()
    return next(item for item in list_rules() if item["id"] == rule_id)


def delete_rule(rule_id: str) -> bool:
    if rule_id == "sns-default-alert-created":
        raise ValueError("The built-in alert routing rule cannot be deleted")
    init_sns_schema()
    conn = get_db_connection()
    try:
        cur = conn.execute("DELETE FROM sns_rules WHERE id=?", (rule_id,))
        if cur.rowcount:
            conn.execute("INSERT INTO audit_events(id,user_id,entity_type,entity_id,action,timestamp) VALUES(?,?,?,?,?,?)",
                         ("AUD_"+uuid.uuid4().hex[:10],"system","sns_rule",rule_id,"DELETED",_now()))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def list_deliveries(limit: int = 100, offset: int = 0, recipient_email: Optional[str] = None) -> List[Dict[str, Any]]:
    init_sns_schema()
    conn = get_db_connection()
    try:
        if recipient_email:
            return [dict(row) for row in conn.execute("SELECT * FROM sns_deliveries WHERE recipient=? ORDER BY attempted_at DESC LIMIT ? OFFSET ?", (recipient_email.lower(),limit,offset))]
        return [dict(row) for row in conn.execute("SELECT * FROM sns_deliveries ORDER BY attempted_at DESC LIMIT ? OFFSET ?", (limit,offset))]
    finally:
        conn.close()


def retry_delivery(delivery_id: str) -> bool:
    init_sns_schema()
    conn = get_db_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT outbox_id,status FROM sns_deliveries WHERE id=?", (delivery_id,)).fetchone()
        if not row or row["status"] not in ("FAILED", "RETRYING"):
            conn.rollback()
            return False
        cur = conn.execute("UPDATE sns_outbox SET status='PENDING',attempts=0,next_attempt_at=NULL,last_error=NULL,updated_at=? WHERE id=? AND channel='telegram'", (_now(),row["outbox_id"]))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def overview() -> Dict[str, int]:
    init_sns_schema()
    conn = get_db_connection()
    try:
        return {
            "notifications": conn.execute("SELECT COUNT(*) FROM sns_notifications").fetchone()[0],
            "unread": conn.execute("SELECT COUNT(*) FROM sns_notifications WHERE status='UNREAD'").fetchone()[0],
            "critical": conn.execute("SELECT COUNT(*) FROM sns_notifications WHERE severity='CRITICAL' AND status NOT IN ('RESOLVED','READ')").fetchone()[0],
            "failed_deliveries": conn.execute("SELECT COUNT(*) FROM sns_outbox WHERE status='FAILED'").fetchone()[0],
            "active_rules": conn.execute("SELECT COUNT(*) FROM sns_rules WHERE enabled=1").fetchone()[0],
            "pending_external_deliveries": conn.execute("SELECT COUNT(*) FROM sns_outbox WHERE channel='telegram' AND status IN ('PENDING','RETRYING')").fetchone()[0]
        }
    finally:
        conn.close()


def create_telegram_link_token(email: str) -> str:
    init_sns_schema()
    token = secrets.token_urlsafe(24)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    conn = get_db_connection()
    try:
        conn.execute("INSERT INTO sns_link_tokens(token_hash,user_email,expires_at,created_at) VALUES(?,?,?,?)", (token_hash,email.lower(),time.time()+600,_now()))
        conn.commit()
    finally:
        conn.close()
    return token


def complete_telegram_link(token: str, telegram_chat_id: str) -> bool:
    init_sns_schema()
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    conn = get_db_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT * FROM sns_link_tokens WHERE token_hash=? AND used_at IS NULL", (token_hash,)).fetchone()
        if not row or float(row["expires_at"]) < time.time():
            conn.rollback()
            return False
        now = _now()
        conn.execute("UPDATE sns_link_tokens SET used_at=? WHERE token_hash=?", (now,token_hash))
        conn.execute("INSERT INTO sns_recipient_channels(user_email,channel,channel_user_id,active,linked_at) VALUES(?,'telegram',?,1,?) ON CONFLICT(user_email,channel) DO UPDATE SET channel_user_id=excluded.channel_user_id,active=1,linked_at=excluded.linked_at", (row["user_email"],str(telegram_chat_id),now))
        conn.commit()
        return True
    finally:
        conn.close()


def telegram_status(email: str) -> Dict[str, Any]:
    configured = bool(os.getenv("TELEGRAM_BOT_TOKEN"))
    shared_chat_configured = bool(os.getenv("TELEGRAM_CHAT_ID", "").strip())
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT active,linked_at FROM sns_recipient_channels WHERE user_email=? AND channel='telegram'", (email.lower(),)).fetchone()
        linked = shared_chat_configured or bool(row and row["active"])
        return {"configured": configured, "linked": linked,
                "mode": "shared_chat" if shared_chat_configured else "per_user",
                "linked_at": row["linked_at"] if row else None}
    finally:
        conn.close()


def unlink_telegram(email: str) -> bool:
    conn = get_db_connection()
    try:
        cur = conn.execute("UPDATE sns_recipient_channels SET active=0 WHERE user_email=? AND channel='telegram' AND active=1", (email.lower(),))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def deliver_telegram_outbox(batch_size: int = 20) -> Dict[str, int]:
    """Deliver queued Telegram messages; safe to run from a separate worker process or asynchronously."""
    import urllib.request
    from dotenv import load_dotenv
    load_dotenv()
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        return {"sent": 0, "failed": 0, "skipped": 0}
    configured_chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    init_sns_schema()
    conn = get_db_connection()
    try:
        rows = conn.execute("""SELECT o.*, COALESCE(c.channel_user_id, o.recipient) AS channel_user_id FROM sns_outbox o
            LEFT JOIN sns_recipient_channels c ON c.user_email=o.recipient AND c.channel='telegram' AND c.active=1
            WHERE o.channel='telegram' AND o.status IN ('PENDING','RETRYING')
              AND (c.channel_user_id IS NOT NULL OR o.recipient=?)
              AND (o.next_attempt_at IS NULL OR o.next_attempt_at<=?) ORDER BY o.created_at LIMIT ?""", (configured_chat_id,_now(),batch_size)).fetchall()
    finally:
        conn.close()
    counts = {"sent": 0, "failed": 0, "skipped": 0}
    for row in rows:
        outbox_id = row["id"]
        conn = get_db_connection()
        try:
            conn.execute("BEGIN IMMEDIATE")
            claimed = conn.execute("UPDATE sns_outbox SET status='PROCESSING',updated_at=? WHERE id=? AND status IN ('PENDING','RETRYING')", (_now(),outbox_id)).rowcount
            conn.commit()
        finally:
            conn.close()
        if not claimed:
            counts["skipped"] += 1
            continue
        payload = json.loads(row["payload_json"])
        severity = str(payload.get('severity', 'INFO')).upper()
        title = payload.get('title', 'EstateIQ Alert')
        message = payload.get('message', '').strip()
        icon = "🚨" if severity in ("CRITICAL", "HIGH") else "⚠️" if severity == "MEDIUM" else "🔔"
        text = f"{icon} [{severity}] {title}\n{message}"
        target_chat = str(row["channel_user_id"] or configured_chat_id).strip()
        status, error = "DELIVERED", None
        try:
            req = urllib.request.Request(
                f"https://api.telegram.org/bot{token}/sendMessage",
                data=_json({"chat_id": target_chat, "text": text}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode())
                if not result.get("ok"):
                    raise RuntimeError("Telegram API rejected delivery")
        except Exception as exc:
            status = "FAILED" if row["attempts"] >= 4 else "RETRYING"
            # urllib exceptions may include the request URL, which contains the bot token.
            error = f"Telegram request failed ({type(exc).__name__})"
        conn = get_db_connection()
        try:
            conn.execute("BEGIN IMMEDIATE")
            attempt = int(row["attempts"])+1
            retry_at = None if status == "DELIVERED" or status == "FAILED" else datetime.fromtimestamp(time.time()+min(3600,30*(2**(attempt-1))),timezone.utc).isoformat().replace("+00:00","Z")
            conn.execute("UPDATE sns_outbox SET status=?,attempts=?,last_error=?,next_attempt_at=?,updated_at=? WHERE id=?", (status,attempt,error,retry_at,_now(),outbox_id))
            conn.execute("INSERT OR IGNORE INTO sns_deliveries(id,notification_id,outbox_id,channel,recipient,status,attempt,error,attempted_at) VALUES(?,?,?,?,?,?,?,?,?)", ("DLV_"+uuid.uuid4().hex[:16].upper(),row["notification_id"],outbox_id,"telegram",row["recipient"],status,attempt,error,_now()))
            conn.commit()
        finally:
            conn.close()
        counts["sent" if status == "DELIVERED" else "failed"] += 1
    return counts


def poll_telegram_link_commands() -> Dict[str, int]:
    """Poll Telegram updates and process /link commands for local demos.

    Do not configure a webhook for the same bot while polling is active.
    """
    import urllib.parse
    import urllib.request

    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not token:
        return {"processed": 0, "linked": 0, "failed": 0}
    init_sns_schema()
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT next_update_id FROM sns_telegram_poll_state WHERE id=1").fetchone()
        offset = int(row["next_update_id"]) if row else 0
    finally:
        conn.close()

    query = urllib.parse.urlencode({"offset": offset, "timeout": 0, "allowed_updates": '["message"]'})
    request = urllib.request.Request(f"https://api.telegram.org/bot{token}/getUpdates?{query}", method="GET")
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            result = json.loads(response.read().decode())
        if not result.get("ok"):
            return {"processed": 0, "linked": 0, "failed": 1}
    except Exception:
        # Exception messages can contain the tokenized request URL; never persist/log them.
        return {"processed": 0, "linked": 0, "failed": 1}

    counts = {"processed": 0, "linked": 0, "failed": 0}
    for update in result.get("result", []):
        update_id = int(update.get("update_id", -1))
        message = update.get("message") or {}
        chat = message.get("chat") or {}
        parts = str(message.get("text", "")).strip().split()
        if len(parts) == 2 and parts[0].split("@", 1)[0].lower() == "/link" and chat.get("id") is not None:
            linked = complete_telegram_link(parts[1], str(chat["id"]))
            reply = ("EstateIQ Telegram notifications are now linked." if linked else
                     "That link code is invalid or expired. Generate a new one in EstateIQ Notifications.")
            try:
                body = _json({"chat_id": chat["id"], "text": reply}).encode()
                send = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=body,
                    headers={"Content-Type": "application/json"}, method="POST")
                with urllib.request.urlopen(send, timeout=8) as response:
                    if not json.loads(response.read().decode()).get("ok"):
                        counts["failed"] += 1
            except Exception:
                counts["failed"] += 1
            if linked:
                counts["linked"] += 1
        counts["processed"] += 1
        if update_id >= 0:
            conn = get_db_connection()
            try:
                conn.execute("INSERT INTO sns_telegram_poll_state(id,next_update_id,updated_at) VALUES(1,?,?) ON CONFLICT(id) DO UPDATE SET next_update_id=excluded.next_update_id,updated_at=excluded.updated_at",
                    (update_id + 1, _now()))
                conn.commit()
            finally:
                conn.close()
    return counts
