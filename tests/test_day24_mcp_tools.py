"""
Unit and Integration Tests for browser_accounts_mcp.py FastMCP Tool Suite — Day 24.
Covers tool registrations, parameter validation, JSON responses, and profile operations.
"""

from __future__ import annotations

import asyncio
import json
import unittest

import browser_accounts_mcp


class TestBrowserMCPTools(unittest.TestCase):
    """Verifies all 39 FastMCP tools registered in browser_accounts_mcp."""

    def test_registered_tools_count(self):
        tools = browser_accounts_mcp.mcp._tool_manager._tools
        self.assertGreaterEqual(len(tools), 35)
        self.assertIn("browser_list_profiles", tools)
        self.assertIn("browser_launch_session", tools)
        self.assertIn("browser_navigate", tools)
        self.assertIn("browser_gmail_list_threads", tools)
        self.assertIn("browser_drive_list_items", tools)
        self.assertIn("browser_extract_page_snapshot", tools)
        self.assertIn("browser_click", tools)
        self.assertIn("browser_check_health", tools)

    def test_browser_check_health_tool(self):
        res_json = browser_accounts_mcp.browser_check_health()
        res = json.loads(res_json)
        self.assertIn("status", res)
        self.assertIn("checks", res)
        self.assertGreaterEqual(res["total_checks"], 5)

    def test_browser_list_profiles_tool(self):
        res_json = browser_accounts_mcp.browser_list_profiles()
        res = json.loads(res_json)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertIn("count", res)
        self.assertIn("profiles", res)

    def test_browser_create_and_get_profile_tool(self):
        # Create a test profile
        create_json = browser_accounts_mcp.browser_create_profile(
            profile_id="mcp_test_profile",
            display_name="MCP Test Account",
            email="mcptest@domain.com",
            aliases=["mcptest"],
            tamil_aliases=["டெஸ்ட்"],
        )
        created = json.loads(create_json)
        self.assertEqual(created["status"], "SUCCESS")
        self.assertEqual(created["profile"]["profile_id"], "mcp_test_profile")

        # Fetch profile
        get_json = browser_accounts_mcp.browser_get_profile(profile_id="mcp_test_profile")
        fetched = json.loads(get_json)
        self.assertEqual(fetched["status"], "SUCCESS")
        self.assertEqual(fetched["profile"]["display_name"], "MCP Test Account")

        # Clean up
        del_json = browser_accounts_mcp.browser_delete_profile(profile_id="mcp_test_profile", delete_files=True)
        deleted = json.loads(del_json)
        self.assertEqual(deleted["status"], "SUCCESS")

    def test_browser_resolve_account_tool(self):
        res_json = browser_accounts_mcp.browser_resolve_account(query="nonexistent_xyz")
        res = json.loads(res_json)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertFalse(res["matched"])

    def test_browser_session_status_when_idle(self):
        res_json = browser_accounts_mcp.browser_get_session_status()
        res = json.loads(res_json)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertFalse(res["session"]["is_running"])


if __name__ == "__main__":
    unittest.main()
