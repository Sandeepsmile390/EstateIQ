"""
Structured Enterprise Audit Logging Engine (src/monitoring/audit_log.py).
Records immutable security and operational audit events across authentication, action execution,
simulation runs, role changes, and permission validations with automatic secret redaction.
"""

import time
import uuid
import pandas as pd
from typing import Dict, Any, List, Optional
from src.security.secrets import redact_secrets

# Global in-memory audit trail store
AUDIT_LOGS_STORE: List[Dict[str, Any]] = [
    {
        "audit_id": "AUD_LOG_001",
        "request_id": "REQ_INIT_01",
        "timestamp": "2026-10-04T08:00:00",
        "event_type": "LOGIN_SUCCESS",
        "user_id": "USR_SUPER_00",
        "email": "admin@estateiq.in",
        "role": "SUPER_ADMIN",
        "facility_id": "FAC_GEC_01",
        "resource": "auth",
        "action": "LOGIN",
        "result": "SUCCESS",
        "metadata": {"ip": "127.0.0.1", "auth_mode": "JWT"}
    }
]

def record_audit_event(
    event_type: str,
    user: Dict[str, Any],
    action: str,
    resource: str,
    resource_id: Optional[str] = None,
    result: str = "SUCCESS",
    metadata: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    # Automatically redact any secrets in metadata payload
    sanitized_metadata = redact_secrets(metadata or {})
    
    audit_entry = {
        "audit_id": f"AUD_{uuid.uuid4().hex[:8]}",
        "request_id": request_id or f"REQ_{uuid.uuid4().hex[:6]}",
        "timestamp": pd.Timestamp.now().isoformat(),
        "event_type": event_type,
        "user_id": user.get("user_id", "ANONYMOUS"),
        "email": user.get("email", "anonymous@estateiq.in"),
        "role": user.get("role", "UNKNOWN"),
        "facility_id": user.get("facility_id", "FAC_GEC_01"),
        "resource": resource,
        "resource_id": resource_id,
        "action": action,
        "result": result,
        "metadata": sanitized_metadata
    }
    AUDIT_LOGS_STORE.append(audit_entry)
    return audit_entry

def get_audit_logs(
    facility_id: Optional[str] = None,
    event_type: Optional[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    logs = list(AUDIT_LOGS_STORE)
    if facility_id:
        logs = [l for l in logs if l.get("facility_id") == facility_id]
    if event_type:
        logs = [l for l in logs if l.get("event_type") == event_type]
    return logs[-limit:]
