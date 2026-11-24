"""
Unit Tests for Zye Day 20 Office Master FastMCP Server.
Tests tool registration, schema definitions, and safe execution of tools.
"""

import unittest
import office_master_mcp


class TestDay20MCPServer(unittest.TestCase):

    def setUp(self):
        self.server = office_master_mcp.mcp
        if hasattr(self.server, "_tool_manager"):
            self.tool_names = list(self.server._tool_manager._tools.keys())
        else:
            self.tool_names = list(self.server._tools.keys())

    def test_registered_tools_count(self):
        office_tools = [t for t in self.tool_names if t.startswith("office_")]
        self.assertEqual(len(office_tools), 12)

    def test_expected_tools_present(self):
        expected = [
            "office_connect",
            "office_disconnect",
            "office_get_session_details",
            "office_list_sessions",
            "office_inspect_document",
            "office_execute_operation",
            "office_export_pdf",
            "office_accelerate_ribbon",
            "office_health_check",
            "office_check_installation",
            "office_list_capabilities",
            "office_list_operations",
        ]
        for tool in expected:
            self.assertIn(tool, self.tool_names)

    def test_health_check_tool_execution(self):
        res = office_master_mcp.office_health_check()
        self.assertIn("status", res)
        self.assertEqual(res["status"], "healthy")

    def test_check_installation_tool(self):
        res = office_master_mcp.office_check_installation()
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["installed_count"], 4)

    def test_list_capabilities_tool(self):
        res = office_master_mcp.office_list_capabilities()
        self.assertEqual(res["status"], "SUCCESS")
        self.assertIn("capabilities", res)

    def test_list_operations_tool(self):
        res = office_master_mcp.office_list_operations()
        self.assertEqual(res["status"], "SUCCESS")
        self.assertGreaterEqual(len(res["operations"]), 14)


if __name__ == "__main__":
    unittest.main()
