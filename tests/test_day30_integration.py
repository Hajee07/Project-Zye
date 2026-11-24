"""
Day 30 Test Suite: Full Personal Assistant & Phase 2 Integration
Verifies that all 10 Personal Assistant tools in personal_assistant_mcp are registered,
executable via FastMCP tool calls, cross-module integrated, and return valid JSON.
"""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

import personal_assistant_mcp as pamcp


class TestDay30Integration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp_dir = Path(tempfile.mkdtemp(prefix="zye_test_d30_integ_"))
        cls.sample_csv = cls.tmp_dir / "sales.csv"
        cls.sample_csv.write_text("date,revenue,cost\n2026-03-01,1000.0,400.0\n2026-03-02,2000.0,800.0\n", encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(str(cls.tmp_dir), ignore_errors=True)

    def test_01_all_ten_tools_registered(self):
        """Verify that all 10 core personal assistant capabilities are present on the MCP server."""
        tools = dir(pamcp)
        expected_tools = [
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
        ]
        for t in expected_tools:
            self.assertIn(t, tools, f"Tool '{t}' missing from personal_assistant_mcp")

    def test_02_plan_travel_itinerary_mcp_wrapper(self):
        """Test plan_travel_itinerary FastMCP tool execution."""
        raw = pamcp.plan_travel_itinerary(
            destination="Goa",
            days=3,
            purpose="Relaxation & Exploration",
            budget_tier="Moderate",
        )
        res = json.loads(raw)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["destination"], "Goa")
        self.assertEqual(len(res["itinerary"]), 3)

    def test_03_conduct_information_research_mcp_wrapper(self):
        """Test conduct_information_research FastMCP tool execution."""
        raw = pamcp.conduct_information_research(
            topic="SQLite WAL mode concurrency benefits",
            depth="EXECUTIVE_BRIEF",
        )
        res = json.loads(raw)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertGreaterEqual(len(res["key_findings"]), 2)
        self.assertGreaterEqual(len(res["supporting_sources"]), 1)

    def test_04_generate_daily_report_mcp_wrapper(self):
        """Test generate_daily_report FastMCP tool execution."""
        raw = pamcp.generate_daily_report(report_type="morning_brief")
        res = json.loads(raw)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["report_type"], "morning_brief")
        self.assertIn("markdown", res)
        self.assertIn("voice_tanglish", res)

    def test_05_analyze_business_data_mcp_wrapper(self):
        """Test analyze_business_data FastMCP tool execution."""
        raw = pamcp.analyze_business_data(
            file_path=str(self.sample_csv),
            business_question="What is total revenue?",
        )
        res = json.loads(raw)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["business_kpis"]["total_revenue"], 3000.0)

    def test_06_cross_module_tasks_and_morning_brief(self):
        """Verify that tasks created via schedule_and_timeblock_tasks appear in generate_daily_report."""
        # Add high priority task
        add_raw = pamcp.schedule_and_timeblock_tasks(
            action="add",
            title="Day 30 Integration Task",
            priority="CRITICAL",
        )
        add_res = json.loads(add_raw)
        self.assertEqual(add_res["status"], "SUCCESS")

        # Generate report
        report_raw = pamcp.generate_daily_report(report_type="morning_brief")
        report_res = json.loads(report_raw)
        self.assertEqual(report_res["status"], "SUCCESS")
        self.assertGreaterEqual(report_res["critical_task_count"], 1)
        self.assertIn("Day 30 Integration Task", report_res["markdown"])

    def test_07_fastmcp_tool_callability(self):
        """Ensure all 10 tools are directly callable or have valid .fn attributes."""
        tools = [
            "manage_calendar", "check_meeting_reminders", "manage_emails", "manage_documents",
            "schedule_and_timeblock_tasks", "plan_travel_itinerary", "conduct_information_research",
            "generate_daily_report", "analyze_business_data", "manage_project_support"
        ]
        for t in tools:
            tool_obj = getattr(pamcp, t)
            is_callable = callable(tool_obj) or (hasattr(tool_obj, "fn") and callable(tool_obj.fn))
            self.assertTrue(is_callable, f"Tool '{t}' is not callable")


if __name__ == "__main__":
    unittest.main()
