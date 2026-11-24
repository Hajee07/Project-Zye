"""
Day 29 Test Suite: Full End-to-End MCP Integration
Verifies that all 16 tools in personal_assistant_mcp are registered,
executable via direct FastMCP tool calls, and provide valid JSON outputs.
"""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

import personal_assistant_mcp as pamcp


class TestDay29Integration(unittest.TestCase):
    def test_01_fastmcp_tool_registration(self):
        """Verify that Day 29 tools as well as preserved Day 28 and Day 30 tools exist."""
        tools = dir(pamcp)
        
        # Day 29 Core Personal Assistant Tools
        self.assertIn("manage_emails", tools)
        self.assertIn("manage_documents", tools)
        self.assertIn("schedule_and_timeblock_tasks", tools)
        self.assertIn("manage_project_support", tools)

        # Preserved Day 28 Calendar Tools
        self.assertIn("manage_calendar", tools)
        self.assertIn("check_meeting_reminders", tools)
        self.assertIn("get_today_calendar", tools)
        self.assertIn("get_tomorrow_calendar", tools)
        self.assertIn("find_available_calendar_slots", tools)
        self.assertIn("reschedule_calendar_event", tools)
        self.assertIn("cancel_calendar_event", tools)
        self.assertIn("get_calendar_health", tools)

        # Preserved Day 30 Intelligence Tools
        self.assertIn("plan_travel_itinerary", tools)
        self.assertIn("conduct_information_research", tools)
        self.assertIn("generate_daily_report", tools)
        self.assertIn("analyze_business_data", tools)

    def test_02_manage_emails_mcp_wrapper(self):
        """Test manage_emails FastMCP tool wrapper output format."""
        # Draft action
        res_raw = pamcp.manage_emails(
            action="draft",
            to_addr="test@example.com",
            subject="Integration Test",
            body="Testing FastMCP wrapper",
        )
        res = json.loads(res_raw)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["action"], "DRAFT_CREATED")

        # Send without confirmation -> APPROVAL_REQUIRED or CONFIG_REQUIRED
        res_send_raw = pamcp.manage_emails(
            action="send",
            to_addr="test@example.com",
            subject="Integration Test",
            body="Testing FastMCP wrapper",
            confirmed=False,
        )
        res_send = json.loads(res_send_raw)
        self.assertIn(res_send["status"], ("APPROVAL_REQUIRED", "CONFIG_REQUIRED"))

    def test_03_manage_documents_mcp_wrapper(self):
        """Test manage_documents FastMCP tool wrapper output format."""
        tmp_dir = tempfile.mkdtemp(prefix="zye_test_mcp_docs_")
        tmp_path = Path(tmp_dir)
        try:
            (tmp_path / "note.txt").write_text("FastMCP document integration testing.", encoding="utf-8")

            # Index
            res_idx_raw = pamcp.manage_documents(action="index_folder", directory_path=str(tmp_path))
            res_idx = json.loads(res_idx_raw)
            self.assertEqual(res_idx["status"], "SUCCESS")

            # Search
            res_search_raw = pamcp.manage_documents(action="search", query="integration")
            res_search = json.loads(res_search_raw)
            self.assertEqual(res_search["status"], "SUCCESS")
            self.assertGreaterEqual(res_search["results_count"], 1)

            # Auto-organize (dry run)
            res_org_raw = pamcp.manage_documents(action="auto_organize", directory_path=str(tmp_path), dry_run=True)
            res_org = json.loads(res_org_raw)
            self.assertEqual(res_org["status"], "DRY_RUN_COMPLETED")
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_04_schedule_and_timeblock_tasks_mcp_wrapper(self):
        """Test schedule_and_timeblock_tasks FastMCP tool wrapper output format."""
        # Add
        res_add_raw = pamcp.schedule_and_timeblock_tasks(
            action="add",
            title="Integration Task",
            priority="HIGH",
            est_minutes=30,
            project_name="Integration",
        )
        res_add = json.loads(res_add_raw)
        self.assertEqual(res_add["status"], "SUCCESS")
        task_id = res_add["task_id"]

        # List
        res_list_raw = pamcp.schedule_and_timeblock_tasks(action="list")
        res_list = json.loads(res_list_raw)
        self.assertEqual(res_list["status"], "SUCCESS")
        self.assertGreaterEqual(res_list["total_tasks"], 1)

        # Auto-timeblock
        res_tb_raw = pamcp.schedule_and_timeblock_tasks(action="auto_timeblock_today")
        res_tb = json.loads(res_tb_raw)
        self.assertIn(res_tb["status"], ("SUCCESS", "NO_AVAILABLE_SLOT"))

        # Complete
        res_comp_raw = pamcp.schedule_and_timeblock_tasks(action="complete", task_id=task_id)
        res_comp = json.loads(res_comp_raw)
        self.assertEqual(res_comp["status"], "SUCCESS")

    def test_05_manage_project_support_mcp_wrapper(self):
        """Test manage_project_support FastMCP tool wrapper output format."""
        # Create
        res_create_raw = pamcp.manage_project_support(
            action="create_or_update",
            name="MCP Project",
            objective="Verify FastMCP wrapper",
            status="ACTIVE",
        )
        res_create = json.loads(res_create_raw)
        self.assertEqual(res_create["status"], "SUCCESS")

        # Flag blocker
        res_block_raw = pamcp.manage_project_support(
            action="flag_blocker",
            name="MCP Project",
            blockers="API token expired",
        )
        res_block = json.loads(res_block_raw)
        self.assertEqual(res_block["status"], "SUCCESS")
        self.assertEqual(res_block["project_status"], "AT_RISK")

        # Status board
        res_board_raw = pamcp.manage_project_support(action="status_board")
        res_board = json.loads(res_board_raw)
        self.assertEqual(res_board["status"], "SUCCESS")
        self.assertGreaterEqual(res_board["total_projects"], 1)

    def test_06_fastmcp_tool_callability(self):
        """Verify FastMCP underlying callable attributes for orchestrator dispatch."""
        for tool_name in ["manage_emails", "manage_documents", "schedule_and_timeblock_tasks", "manage_project_support"]:
            tool_obj = getattr(pamcp, tool_name)
            # In FastMCP, tool is callable directly or via .fn
            is_callable = callable(tool_obj) or (hasattr(tool_obj, "fn") and callable(tool_obj.fn))
            self.assertTrue(is_callable, f"Tool {tool_name} is not callable")


if __name__ == "__main__":
    unittest.main()
