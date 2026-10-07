"""
Closed-Loop Work Order Management Engine (src/decisions/work_orders.py).
Handles creation of work orders from AI recommendations, staff assignment,
status lifecycle (NEW -> ASSIGNED -> ACKNOWLEDGED -> IN_PROGRESS -> COMPLETED -> VERIFIED),
and manager verification.
"""

import uuid
import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class WorkOrder(BaseModel):
    work_order_id: str
    title: str
    description: str
    facility_id: str = "FAC_GEC_CAMPUS"
    building_id: str = "Block B Hostel"
    location: str = "Block B - HVAC Compressor Deck"
    priority: str = "P1_CRITICAL"
    source: str = "AI_RECOMMENDATION"
    recommendation_id: Optional[str] = None
    assigned_to: str = "operations@estateiq.in" # Staff user
    assigned_by: str = "manager@estateiq.in"   # Manager user
    created_at: str = Field(default_factory=lambda: datetime.datetime.now().isoformat())
    due_date: str = Field(default_factory=lambda: (datetime.datetime.now() + datetime.timedelta(hours=24)).isoformat())
    status: str = "NEW" # NEW, ASSIGNED, ACKNOWLEDGED, IN_PROGRESS, COMPLETED, VERIFIED, CANCELLED
    completion_notes: Optional[str] = None
    verification_evidence: Optional[Dict[str, Any]] = None
    verification_status: str = "PENDING"

class WorkOrderEngine:
    """Manages full closed-loop lifecycle of operational work orders."""
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(WorkOrderEngine, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self._orders: Dict[str, WorkOrder] = {}
        self._seed_default_orders()

    def _seed_default_orders(self):
        """Seeds initial work orders for testing and demonstration."""
        wo1 = WorkOrder(
            work_order_id="WO_20261008_001",
            title="HVAC Thermostat Setback Schedule Adjustment",
            description="Reset Block B Hostel thermostat setback schedule to 24.5°C during 13:00-16:00 window to clear 50% energy surge.",
            facility_id="FAC_GEC_CAMPUS",
            building_id="Block B Hostel",
            location="Block B - 3rd Floor HVAC Control Panel",
            priority="P1_CRITICAL",
            source="AI_RECOMMENDATION",
            recommendation_id="REC_HVAC_RESET_01",
            assigned_to="alex@estateiq.in",
            assigned_by="lead@estateiq.in",
            status="ASSIGNED",
            due_date=(datetime.datetime.now() + datetime.timedelta(hours=4)).isoformat()
        )
        wo2 = WorkOrder(
            work_order_id="WO_20261008_002",
            title="Acoustic Water Leak Inspection Riser B-2",
            description="Inspect acoustic leak profile on main distribution riser B-2 in Block A Hostel to resolve 18 L/min overnight baseline flow.",
            facility_id="FAC_GEC_CAMPUS",
            building_id="Block A Academic",
            location="Block A - Basement Plumbing Manifold",
            priority="P2_HIGH",
            source="AI_RECOMMENDATION",
            recommendation_id="REC_WATER_LEAK_01",
            assigned_to="staff@estateiq.in",
            assigned_by="lead@estateiq.in",
            status="NEW",
            due_date=(datetime.datetime.now() + datetime.timedelta(hours=12)).isoformat()
        )
        self._orders[wo1.work_order_id] = wo1
        self._orders[wo2.work_order_id] = wo2

    def create_work_order(
        self,
        title: str,
        description: str,
        facility_id: str = "FAC_GEC_CAMPUS",
        building_id: str = "Block B Hostel",
        location: str = "Block B HVAC Room",
        priority: str = "P1_CRITICAL",
        source: str = "AI_RECOMMENDATION",
        recommendation_id: Optional[str] = None,
        assigned_to: str = "staff@estateiq.in",
        assigned_by: str = "lead@estateiq.in",
        due_hours: int = 24
    ) -> WorkOrder:
        wo_id = f"WO_{datetime.datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:6].upper()}"
        now = datetime.datetime.now()
        due = (now + datetime.timedelta(hours=due_hours)).isoformat()
        
        order = WorkOrder(
            work_order_id=wo_id,
            title=title,
            description=description,
            facility_id=facility_id,
            building_id=building_id,
            location=location,
            priority=priority,
            source=source,
            recommendation_id=recommendation_id,
            assigned_to=assigned_to,
            assigned_by=assigned_by,
            created_at=now.isoformat(),
            due_date=due,
            status="ASSIGNED"
        )
        self._orders[wo_id] = order
        return order

    def update_status(
        self,
        work_order_id: str,
        target_status: str,
        actor: str = "User",
        notes: Optional[str] = None,
        evidence: Optional[Dict[str, Any]] = None
    ) -> WorkOrder:
        if work_order_id not in self._orders:
            raise KeyError(f"Work Order ID '{work_order_id}' not found.")
            
        order = self._orders[work_order_id]
        order.status = target_status.upper()
        if notes:
            order.completion_notes = notes
        if evidence:
            order.verification_evidence = evidence
            
        if order.status == "VERIFIED":
            order.verification_status = "VERIFIED_SAVINGS_ACHIEVED"
            
        return order

    def get_work_order(self, work_order_id: str) -> Optional[WorkOrder]:
        return self._orders.get(work_order_id)

    def list_work_orders(
        self,
        assigned_to: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[WorkOrder]:
        res = list(self._orders.values())
        if assigned_to:
            res = [o for o in res if assigned_to.lower() in o.assigned_to.lower()]
        if status:
            res = [o for o in res if o.status.upper() == status.upper()]
        return res

GLOBAL_WORK_ORDER_ENGINE = WorkOrderEngine()
