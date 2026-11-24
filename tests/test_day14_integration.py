"""
Unit tests for Day 14 Personal Assistant Master Integration.
Verifies FastMCP tool registration (10 tools), main.py allowlist, reminder loop, and voice interceptors.
"""

import inspect
import unittest

import personal_assistant_mcp as pam
from main import MCP_SERVERS, ZyeVoiceOrchestrator


class TestDay14Integration(unittest.TestCase):
    def test_01_all_ten_mcp_tools_registered(self):
        tools = [t.name for t in pam.mcp._tool_manager._tools.values()]
        expected_tools = {
            "manage_calendar",
            "check_meeting_reminders",
            "manage_emails",
            "manage_documents",
            "schedule_and_timeblock_tasks",
            "plan_travel_itinerary",
            "conduct_information_research",
            "generate_daily_report",
            "analyze_business_data",
            "manage_project_support",
        }
        self.assertTrue(
            expected_tools.issubset(set(tools)),
            f"Missing MCP tools: {expected_tools - set(tools)}"
        )

    def test_02_personal_assistant_in_main_mcp_servers_allowlist(self):
        self.assertIn("personal_assistant", MCP_SERVERS)
        cfg = MCP_SERVERS["personal_assistant"]
        self.assertIn("personal_assistant_mcp.py", cfg["args"][0])

    def test_03_main_meeting_reminder_loop_coroutine_exists(self):
        self.assertTrue(
            hasattr(ZyeVoiceOrchestrator, "meeting_reminder_loop"),
            "ZyeVoiceOrchestrator must define meeting_reminder_loop"
        )
        self.assertTrue(
            inspect.iscoroutinefunction(ZyeVoiceOrchestrator.meeting_reminder_loop),
            "meeting_reminder_loop must be an async coroutine"
        )

    def test_04_personal_assistant_offline_mode_operational(self):
        from zye_personal_assistant import (
            CalendarEngine, TaskScheduler, ProjectManager, DailyReportEngine
        )
        ce = CalendarEngine(db_path=":memory:")
        ts = TaskScheduler(db_path=":memory:")
        pm = ProjectManager(db_path=":memory:")
        dre = DailyReportEngine(db_path=":memory:")

        # All four engines should execute completely offline without internet
        ce.add_event(title="Offline Sync", start_iso="2026-11-20T10:00:00")
        ts.add_task(title="Offline Task")
        pm.create_or_update_project(name="Offline Project")
        rep = dre.generate_report("morning_brief")

        self.assertEqual(rep["status"], "SUCCESS")


if __name__ == "__main__":
    unittest.main()
