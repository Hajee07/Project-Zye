"""
Unit and integration tests for Day 28 FastMCP Tools and Voice Bridge.
Tests personal_assistant_mcp tool invocations and multi-lingual voice announcements
(English, Tanglish, Tamil) for calendar reminders.
"""

import json
import os
import tempfile
import unittest
from pathlib import Path

from zye_personal_assistant.calendar.calendar_database import initialize_calendar_database
from zye_personal_assistant.reminders.reminder_voice_bridge import build_calendar_reminder_message


class TestDay28MCPAndVoice(unittest.TestCase):
    def setUp(self):
        self._tmp_fd, self._tmp_path = tempfile.mkstemp(suffix=".sqlite", prefix="zye_d28_mcp_")
        os.close(self._tmp_fd)
        initialize_calendar_database(self._tmp_path)
        import personal_assistant_mcp
        from zye_personal_assistant.calendar_engine import CalendarEngine
        self._orig_calendar = personal_assistant_mcp._calendar
        personal_assistant_mcp._calendar = CalendarEngine(db_path=self._tmp_path, safety_gateway=personal_assistant_mcp._safety)

    def tearDown(self):
        import personal_assistant_mcp
        personal_assistant_mcp._calendar = self._orig_calendar
        try:
            Path(self._tmp_path).unlink(missing_ok=True)
        except Exception:
            pass

    def test_01_manage_calendar_mcp_crud_flow(self):
        import personal_assistant_mcp

        # 1. Add event
        res_raw = personal_assistant_mcp.manage_calendar(
            action="add",
            title="Team All-Hands",
            start_iso="2026-11-25T10:00:00",
            duration_minutes=60,
        )
        res = json.loads(res_raw)
        self.assertEqual(res["status"], "SUCCESS")
        event_id = res["event_id"]

        # 2. List upcoming
        up_raw = personal_assistant_mcp.manage_calendar(action="list_upcoming")
        up = json.loads(up_raw)
        self.assertGreaterEqual(len(up), 1)

        # 3. Reschedule event
        resch_raw = personal_assistant_mcp.manage_calendar(
            action="reschedule",
            event_id=event_id,
            start_iso="2026-11-25T14:00:00",
            duration_minutes=60,
        )
        resch = json.loads(resch_raw)
        self.assertEqual(resch["status"], "SUCCESS")

        # 4. Check conflicts
        conf_raw = personal_assistant_mcp.manage_calendar(
            action="check_conflicts",
            start_iso="2026-11-25T14:30:00",
            duration_minutes=30,
        )
        conf = json.loads(conf_raw)
        self.assertTrue(conf["has_conflict"])

        # 5. Cancel event
        canc_raw = personal_assistant_mcp.manage_calendar(
            action="cancel",
            event_id=event_id,
        )
        canc = json.loads(canc_raw)
        self.assertEqual(canc["status"], "CANCELLED")

    def test_02_fastmcp_convenience_tools(self):
        import personal_assistant_mcp

        # Test find_available_calendar_slots
        slots_raw = personal_assistant_mcp.find_available_calendar_slots(
            target_date_iso="2026-11-25",
            min_duration_minutes=30,
        )
        slots = json.loads(slots_raw)
        self.assertGreater(len(slots), 0)

        # Test get_calendar_health
        health_raw = personal_assistant_mcp.get_calendar_health()
        health = json.loads(health_raw)
        self.assertIn(health["status"], ["SUCCESS", "HEALTHY"])
        self.assertEqual(health["schema_version"], 28)

    def test_03_voice_reminder_message_english(self):
        msg_15 = build_calendar_reminder_message(
            title="Executive Review",
            reminder_type="15_MIN",
            language="en",
            location="Boardroom A",
        )
        self.assertIn("starts in 15 minutes", msg_15)
        self.assertIn("Executive Review", msg_15)
        self.assertIn("Boardroom A", msg_15)

        msg_2 = build_calendar_reminder_message(
            title="Executive Review",
            reminder_type="2_MIN",
            language="en",
        )
        self.assertIn("starts in 2 minutes", msg_2)

    def test_04_voice_reminder_message_tanglish(self):
        msg_15 = build_calendar_reminder_message(
            title="Project Demo",
            reminder_type="15_MIN",
            language="tanglish",
        )
        self.assertIn("Project Demo", msg_15)
        self.assertIn("15 minutes-la start aaguthu", msg_15)

        msg_2 = build_calendar_reminder_message(
            title="Project Demo",
            reminder_type="2_MIN",
            language="tanglish",
        )
        self.assertIn("2 minutes-la start aaguthu", msg_2)

    def test_05_voice_reminder_message_tamil(self):
        msg_15 = build_calendar_reminder_message(
            title="ஆலோசனை கூட்டம்",
            reminder_type="15_MIN",
            language="ta",
        )
        self.assertIn("ஆலோசனை கூட்டம்", msg_15)
        self.assertIn("15 நிமிடங்களில் தொடங்கும்", msg_15)

        msg_2 = build_calendar_reminder_message(
            title="ஆலோசனை கூட்டம்",
            reminder_type="2_MIN",
            language="ta",
        )
        self.assertIn("இரண்டு நிமிடங்களில் தொடங்கும்", msg_2)


if __name__ == "__main__":
    unittest.main()
