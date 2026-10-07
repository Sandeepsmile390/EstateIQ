"""
Closed-Loop Work Orders & Notifications Lifecycle Test Suite.
Validates work order creation from AI recommendation, staff assignment, real-time notification delivery,
status transitions (NEW -> ASSIGNED -> ACKNOWLEDGED -> IN_PROGRESS -> COMPLETED -> VERIFIED), and manager verification.
"""

import unittest
from src.decisions.work_orders import GLOBAL_WORK_ORDER_ENGINE, WorkOrder
from src.decisions.notifications import GLOBAL_NOTIFICATION_ENGINE

class TestWorkOrdersAndNotifications(unittest.TestCase):
    """Closed-Loop Work Order and Notification Lifecycle Test."""

    def test_01_work_order_creation_and_assignment(self):
        """1. Test creating a work order and assigning it to staff."""
        order = GLOBAL_WORK_ORDER_ENGINE.create_work_order(
            title="Reset Block B Thermostat Setback",
            description="Adjust setback to 24.5°C between 13:00-16:00.",
            facility_id="FAC_GEC_CAMPUS",
            building_id="Block B Hostel",
            location="Block B Control Room",
            priority="P1_CRITICAL",
            recommendation_id="REC_HVAC_01",
            assigned_to="staff@estateiq.in",
            assigned_by="lead@estateiq.in"
        )
        self.assertIsNotNone(order.work_order_id)
        self.assertEqual(order.status, "ASSIGNED")
        self.assertEqual(order.assigned_to, "staff@estateiq.in")

    def test_02_notification_creation_and_delivery(self):
        """2. Test creating notification and filtering by recipient."""
        notif = GLOBAL_NOTIFICATION_ENGINE.create_notification(
            recipient_email="staff@estateiq.in",
            recipient_role="STAFF",
            title="⚡ High Priority Work Order Assigned",
            message="Inspect main HVAC chiller drive bearing.",
            priority="HIGH",
            related_object_id="WO_TEST_001"
        )
        self.assertIsNotNone(notif.notification_id)

        user_notifs = GLOBAL_NOTIFICATION_ENGINE.get_user_notifications(recipient_email="staff@estateiq.in")
        self.assertGreater(len(user_notifs), 0)
        self.assertTrue(any(n.notification_id == notif.notification_id for n in user_notifs))

    def test_03_work_order_lifecycle_transitions(self):
        """3. Test full lifecycle status transitions."""
        order = GLOBAL_WORK_ORDER_ENGINE.create_work_order(
            title="Acoustic Water Leak Test",
            description="Perform acoustic leak detection on riser B-2.",
            assigned_to="staff@estateiq.in"
        )

        # 1. Staff acknowledges
        order = GLOBAL_WORK_ORDER_ENGINE.update_status(order.work_order_id, "ACKNOWLEDGED", actor="Staff")
        self.assertEqual(order.status, "ACKNOWLEDGED")

        # 2. Staff starts work
        order = GLOBAL_WORK_ORDER_ENGINE.update_status(order.work_order_id, "IN_PROGRESS", actor="Staff")
        self.assertEqual(order.status, "IN_PROGRESS")

        # 3. Staff completes work
        order = GLOBAL_WORK_ORDER_ENGINE.update_status(
            order.work_order_id,
            "COMPLETED",
            actor="Staff",
            notes="Repaired loose flange valve; baseline flow recovered.",
            evidence={"flow_recovered_lpm": 0.0}
        )
        self.assertEqual(order.status, "COMPLETED")
        self.assertIsNotNone(order.completion_notes)

        # 4. Manager verifies work order
        order = GLOBAL_WORK_ORDER_ENGINE.update_status(order.work_order_id, "VERIFIED", actor="Manager")
        self.assertEqual(order.status, "VERIFIED")
        self.assertEqual(order.verification_status, "VERIFIED_SAVINGS_ACHIEVED")

    def test_04_notification_read_tracking(self):
        """4. Test notification read state tracking."""
        notif = GLOBAL_NOTIFICATION_ENGINE.create_notification(
            recipient_email="staff@estateiq.in",
            title="Test Alert",
            message="Test Message"
        )
        self.assertFalse(notif.read)

        success = GLOBAL_NOTIFICATION_ENGINE.mark_read(notif.notification_id)
        self.assertTrue(success)
        self.assertTrue(GLOBAL_NOTIFICATION_ENGINE._notifications[notif.notification_id].read)


if __name__ == "__main__":
    unittest.main()
