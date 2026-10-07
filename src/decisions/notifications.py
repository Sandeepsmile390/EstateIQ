"""
Dynamic Real-Time Notification System (src/decisions/notifications.py).
Generates recipient-tailored alerts for work order assignments, high-priority anomalies,
verification requests, and status changes.
"""

import uuid
import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class Notification(BaseModel):
    notification_id: str
    recipient_email: str
    recipient_role: str = "STAFF"
    title: str
    message: str
    priority: str = "MEDIUM" # HIGH, MEDIUM, INFO
    timestamp: str = Field(default_factory=lambda: datetime.datetime.now().isoformat())
    read: bool = False
    action_link: Optional[str] = None
    related_object_id: Optional[str] = None

class NotificationEngine:
    """Manages creation, filtering, and read-state tracking of user notifications."""

    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(NotificationEngine, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self._notifications: Dict[str, Notification] = {}
        self._seed_default_notifications()

    def _seed_default_notifications(self):
        """Seeds sample operational notifications."""
        n1 = Notification(
            notification_id="NOTIF_001",
            recipient_email="staff@estateiq.in",
            recipient_role="STAFF",
            title="⚡ New Work Order Assigned: HVAC Reset",
            message="You have been assigned to inspect and reset Block B Hostel HVAC thermostat setpoint to 24.5°C.",
            priority="HIGH",
            related_object_id="WO_20261008_001"
        )
        n2 = Notification(
            notification_id="NOTIF_002",
            recipient_email="alex@estateiq.in",
            recipient_role="OPERATIONS",
            title="💧 Water Leak Inspection Assigned",
            message="Inspect acoustic leak profile on riser B-2 in Block A Academic building.",
            priority="MEDIUM",
            related_object_id="WO_20261008_002"
        )
        n3 = Notification(
            notification_id="NOTIF_003",
            recipient_email="lead@estateiq.in",
            recipient_role="FACILITY_MANAGER",
            title="✅ Work Order Verified: Chiller 01 Serviced",
            message="Chiller 01 bearing lubrication completed by Alex Chen. Verified 18.5% energy reduction achieved.",
            priority="INFO",
            related_object_id="WO_20261008_000"
        )
        self._notifications[n1.notification_id] = n1
        self._notifications[n2.notification_id] = n2
        self._notifications[n3.notification_id] = n3

    def create_notification(
        self,
        recipient_email: str,
        title: str,
        message: str,
        recipient_role: str = "STAFF",
        priority: str = "MEDIUM",
        related_object_id: Optional[str] = None,
        action_link: Optional[str] = None
    ) -> Notification:
        notif_id = f"NOTIF_{uuid.uuid4().hex[:8].upper()}"
        notif = Notification(
            notification_id=notif_id,
            recipient_email=recipient_email,
            recipient_role=recipient_role,
            title=title,
            message=message,
            priority=priority,
            related_object_id=related_object_id,
            action_link=action_link
        )
        self._notifications[notif_id] = notif
        return notif

    def get_user_notifications(
        self,
        recipient_email: Optional[str] = None,
        recipient_role: Optional[str] = None,
        unread_only: bool = False
    ) -> List[Notification]:
        res = list(self._notifications.values())
        if recipient_email:
            res = [n for n in res if n.recipient_email.lower() == recipient_email.lower()]
        elif recipient_role:
            res = [n for n in res if n.recipient_role.upper() == recipient_role.upper()]
        if unread_only:
            res = [n for n in res if not n.read]
        return sorted(res, key=lambda x: x.timestamp, reverse=True)

    def mark_read(self, notification_id: str) -> bool:
        if notification_id in self._notifications:
            self._notifications[notification_id].read = True
            return True
        return False

GLOBAL_NOTIFICATION_ENGINE = NotificationEngine()
