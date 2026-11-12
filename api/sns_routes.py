"""Authenticated API routes for EstateIQ's persistent notification center."""
from __future__ import annotations

import hmac
import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Security, status
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, field_validator

from src.auth.security import ROLE_PERMISSIONS, security_scheme, verify_current_user
from src.services import sns

router = APIRouter(prefix="/api/v1/sns", tags=["Smart Notifications"])


def _current_user(credentials: Optional[HTTPAuthorizationCredentials] = Security(security_scheme)) -> Dict[str, Any]:
    # The legacy EstateIQ dependency has a demo-user fallback. SNS deliberately
    # requires a real bearer token so sensitive notification data is never anonymous.
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    user = verify_current_user(credentials)
    if user.get("auth_method") != "password":
        raise HTTPException(status_code=401, detail="Sign in with your account credentials to access SNS")
    return user


def _permission(permission: str):
    def dependency(user: Dict[str, Any] = Depends(_current_user)) -> Dict[str, Any]:
        granted = set(user.get("permissions", ROLE_PERMISSIONS.get(user.get("role", ""), [])))
        if permission not in granted:
            raise HTTPException(status_code=403, detail="Insufficient permission")
        return user
    return dependency


class RuleCondition(BaseModel):
    field: str = Field(min_length=1, max_length=120)
    operator: str = Field(default="eq", pattern="^(eq|ne|gt|gte|lt|lte|in|contains)$")
    value: Any


class RuleRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: str = Field(default="", max_length=500)
    event_type: str = Field(min_length=2, max_length=100)
    enabled: bool = True
    conditions: List[RuleCondition] = Field(default_factory=list, max_length=20)
    logical_operator: str = Field(default="AND", pattern="^(AND|OR)$")
    severity: str = Field(default="MEDIUM", pattern="^(CRITICAL|HIGH|MEDIUM|LOW|INFO)$")
    recipient_roles: List[str] = Field(default_factory=lambda: ["OPERATIONS_ENGINEER"], max_length=10)
    recipient_emails: List[str] = Field(default_factory=list, max_length=30)
    channels: List[str] = Field(default_factory=lambda: ["in_app"], max_length=2)
    cooldown_seconds: int = Field(default=300, ge=0, le=604800)

    @field_validator("channels")
    @classmethod
    def valid_channels(cls, values: List[str]) -> List[str]:
        if not values or any(v not in {"in_app", "telegram"} for v in values):
            raise ValueError("channels must contain in_app and/or telegram")
        return list(dict.fromkeys(values))

    @field_validator("recipient_emails")
    @classmethod
    def normalize_emails(cls, values: List[str]) -> List[str]:
        return list(dict.fromkeys(v.strip().lower() for v in values if "@" in v and len(v) <= 254))


class TestRuleRequest(BaseModel):
    event: Dict[str, Any]


@router.get("/overview")
def get_overview(user: Dict[str, Any] = Depends(_permission("sns.read"))):
    summary = sns.overview()
    summary["telegram"] = sns.telegram_status(user["email"])
    return summary


@router.get("/notifications")
def get_notifications(unread_only: bool = False, limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0), user: Dict[str, Any] = Depends(_permission("sns.read"))):
    return sns.list_notifications(user["email"], unread_only=unread_only, limit=limit, offset=offset)


@router.get("/notifications/{notification_id}")
def get_notification(notification_id: str, user: Dict[str, Any] = Depends(_permission("sns.read"))):
    item = sns.get_notification(notification_id, user["email"])
    if not item:
        raise HTTPException(status_code=404, detail="Notification not found")
    return item


def _notification_action(notification_id: str, action: str, user: Dict[str, Any]):
    result = sns.update_notification(notification_id, user["email"], action)
    if not result:
        raise HTTPException(status_code=404, detail="Notification not found")
    return result


@router.post("/notifications/{notification_id}/read")
def mark_read(notification_id: str, user: Dict[str, Any] = Depends(_permission("sns.read"))):
    return _notification_action(notification_id, "read", user)


@router.post("/notifications/{notification_id}/acknowledge")
def acknowledge(notification_id: str, user: Dict[str, Any] = Depends(_permission("sns.notifications.acknowledge"))):
    return _notification_action(notification_id, "acknowledge", user)


@router.post("/notifications/{notification_id}/resolve")
def resolve(notification_id: str, user: Dict[str, Any] = Depends(_permission("sns.notifications.acknowledge"))):
    return _notification_action(notification_id, "resolve", user)


@router.get("/rules")
def get_rules(user: Dict[str, Any] = Depends(_permission("sns.read"))):
    rules = sns.list_rules()
    if "sns.rules.manage" not in set(user.get("permissions", [])):
        for rule in rules:
            rule["recipient_emails"] = []
    return {"rules": rules}


@router.post("/rules")
def create_rule(req: RuleRequest, user: Dict[str, Any] = Depends(_permission("sns.rules.manage"))):
    try:
        return sns.save_rule(req.model_dump(), actor=user["email"])
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.put("/rules/{rule_id}")
def update_rule(rule_id: str, req: RuleRequest, user: Dict[str, Any] = Depends(_permission("sns.rules.manage"))):
    try:
        return sns.save_rule(req.model_dump(), rule_id=rule_id, actor=user["email"])
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.delete("/rules/{rule_id}")
def remove_rule(rule_id: str, user: Dict[str, Any] = Depends(_permission("sns.rules.manage"))):
    try:
        if not sns.delete_rule(rule_id):
            raise HTTPException(status_code=404, detail="Rule not found")
        return {"deleted": True, "rule_id": rule_id}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/rules/{rule_id}/test")
def test_rule(rule_id: str, req: TestRuleRequest, user: Dict[str, Any] = Depends(_permission("sns.rules.manage"))):
    rule = next((item for item in sns.list_rules() if item["id"] == rule_id), None)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    checks = [sns._condition_matches(req.event, condition.model_dump()) for condition in rule["conditions"]]
    matched = not checks or (all(checks) if rule["logical_operator"] == "AND" else any(checks))
    return {"matched": matched, "conditions": checks, "would_notify": matched and rule["enabled"]}


@router.post("/rules/{rule_id}/enable")
def enable_rule(rule_id: str, user: Dict[str, Any] = Depends(_permission("sns.rules.manage"))):
    rule = next((r for r in sns.list_rules() if r["id"] == rule_id), None)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    rule["enabled"] = True
    return sns.save_rule(rule, rule_id=rule_id, actor=user["email"])


@router.post("/rules/{rule_id}/disable")
def disable_rule(rule_id: str, user: Dict[str, Any] = Depends(_permission("sns.rules.manage"))):
    rule = next((r for r in sns.list_rules() if r["id"] == rule_id), None)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    rule["enabled"] = False
    return sns.save_rule(rule, rule_id=rule_id, actor=user["email"])


@router.get("/deliveries")
def get_deliveries(limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0), user: Dict[str, Any] = Depends(_permission("sns.deliveries.read"))):
    global_roles = {"SUPER_ADMIN", "FACILITY_ADMIN", "ESG_AUDITOR"}
    recipient = None if user.get("role") in global_roles else user.get("email")
    return {"deliveries": sns.list_deliveries(limit, offset, recipient_email=recipient)}


@router.post("/deliveries/{delivery_id}/retry")
def retry_delivery(delivery_id: str, user: Dict[str, Any] = Depends(_permission("sns.channels.manage"))):
    if not sns.retry_delivery(delivery_id):
        raise HTTPException(status_code=409, detail="Delivery is not retryable or no longer exists")
    return {"queued": True, "delivery_id": delivery_id}


@router.get("/integrations/telegram")
def get_telegram_status(user: Dict[str, Any] = Depends(_permission("sns.read"))):
    return sns.telegram_status(user["email"])


@router.post("/integrations/telegram/link")
def link_telegram(user: Dict[str, Any] = Depends(_permission("sns.read"))):
    if not os.getenv("TELEGRAM_BOT_TOKEN"):
        return {"configured": False, "linked": False, "message": "Configure TELEGRAM_BOT_TOKEN and start the SNS worker to enable Telegram."}
    token = sns.create_telegram_link_token(user["email"])
    return {"configured": True, "linked": False, "link_token": token, "expires_in_seconds": 600, "instruction": "Open the configured EstateIQ Telegram bot and send /link followed by this token. It is single-use."}


@router.post("/integrations/telegram/unlink")
def unlink_telegram(user: Dict[str, Any] = Depends(_permission("sns.read"))):
    return {"unlinked": sns.unlink_telegram(user["email"])}


@router.post("/integrations/telegram/webhook")
async def telegram_webhook(payload: Dict[str, Any], x_telegram_bot_api_secret_token: Optional[str] = Header(default=None)):
    configured = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
    if not configured or not x_telegram_bot_api_secret_token or not hmac.compare_digest(configured, x_telegram_bot_api_secret_token):
        raise HTTPException(status_code=403, detail="Invalid webhook secret")
    message = payload.get("message") or payload.get("edited_message") or {}
    text = str(message.get("text", "")).strip().split()
    chat = message.get("chat") or {}
    if len(text) == 2 and text[0].lower() == "/link" and chat.get("id") is not None:
        linked = sns.complete_telegram_link(text[1], str(chat["id"]))
        return {"ok": True, "linked": linked}
    return {"ok": True, "linked": False}

