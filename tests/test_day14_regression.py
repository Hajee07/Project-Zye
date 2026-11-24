"""
Regression tests for Day 14 Personal Assistant.
Verifies that Day 14 subsystems coexist with Day 12 MCP Orchestrator,
Day 13 Negative Brain, and Gemini Gateway Slot 4.
"""

import unittest

from gemini_gateway import ZyeGeminiGateway
from zye_orchestrator.server_registry import ServerRegistry
from zye_intelligence.premortem import ZyeNegativePreMortem
import personal_assistant_mcp as pam


class TestDay14Regression(unittest.TestCase):
    def test_01_day12_mcp_orchestrator_registry_coexistence(self):
        reg = ServerRegistry()
        from main import MCP_SERVERS
        reg.register_from_dict(MCP_SERVERS)
        self.assertIn("personal_assistant", reg.configs)
        self.assertIn("autonomous_brain", reg.configs)
        self.assertIn("self_repair", reg.configs)

    def test_02_day13_negative_brain_accessible(self):
        brain = ZyeNegativePreMortem()
        self.assertIsNotNone(brain)
        self.assertTrue(callable(brain.run_audit))

    def test_03_gemini_gateway_slot4_routes_personal_assistant(self):
        gw = ZyeGeminiGateway.get_instance()
        slot = gw.project_router.route_workload("PERSONAL_ASSISTANT")
        self.assertEqual(slot, 4)
        self.assertFalse(gw.project_router.allow_cross_project_fallback)

    def test_04_all_ten_pam_tools_callable(self):
        tools = pam.mcp._tool_manager._tools
        self.assertEqual(len(tools), 10)
        for name, tool_obj in tools.items():
            self.assertTrue(callable(tool_obj.fn), f"Tool {name} must have a callable function")


if __name__ == "__main__":
    unittest.main()
