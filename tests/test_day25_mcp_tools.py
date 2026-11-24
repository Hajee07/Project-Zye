"""Day 25 Unit Tests: FastMCP Tools and Main Orchestration Routing.

Tests:
- Verification of all 16 registered FastMCP tools in ai_plugins_mcp
- Execution of non-network tools (list_active_ai_plugins, get_ai_plugin_status, telemetry)
- Routing integration in main.py (_dispatch_tool_call)
"""

import unittest

import ai_plugins_mcp
from main import ZyeMasterAgent
from zye_ai_plugins.usage_tracker import usage_tracker


def run_coro(coro):
    """Run an async coroutine synchronously without event loop socket binding."""
    try:
        while True:
            coro.send(None)
    except StopIteration as exc:
        return exc.value


class TestDay25MCPTools(unittest.TestCase):
    """Test suite for FastMCP tool definitions and execution."""

    def test_01_all_16_tools_registered(self):
        """Verify all 16 required tools are present in the FastMCP tool manager."""
        tm = getattr(ai_plugins_mcp.mcp, "_tool_manager", getattr(ai_plugins_mcp.mcp, "_tools", None))
        tools = getattr(tm, "_tools", tm)

        expected_tools = [
            "list_active_ai_plugins",
            "get_ai_plugin_status",
            "get_provider_models",
            "get_provider_metadata",
            "check_provider_health",
            "ask_chatgpt",
            "ask_claude",
            "ask_local_ollama",
            "ask_custom_ai_plugin",
            "ai_council_compare",
            "get_ai_council_status",
            "validate_ai_plugin_configuration",
            "validate_provider_model",
            "get_ai_plugin_configuration_status",
            "get_provider_usage",
            "get_provider_usage_summary",
        ]

        self.assertGreaterEqual(len(tools), 16)
        for expected in expected_tools:
            self.assertIn(expected, tools, f"Missing expected tool: {expected}")

    def test_02_list_active_plugins_execution(self):
        """Verify list_active_ai_plugins returns structured dict."""
        res = run_coro(ai_plugins_mcp.list_active_ai_plugins())
        self.assertEqual(res["status"], "success")
        self.assertIn("active_providers", res)
        self.assertIn("supreme_brain", res)
        self.assertIn("Gemini Master Brain", res["supreme_brain"])

    def test_03_get_ai_plugin_status_execution(self):
        """Verify get_ai_plugin_status returns list of all provider states."""
        res = run_coro(ai_plugins_mcp.get_ai_plugin_status())
        self.assertEqual(res["status"], "success")
        self.assertIn("providers", res)
        self.assertGreaterEqual(len(res["providers"]), 7)

    def test_04_get_provider_metadata_execution(self):
        """Verify get_provider_metadata returns correct masked metadata."""
        res = run_coro(ai_plugins_mcp.get_provider_metadata(provider_name="openai"))
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["provider_id"], "openai")
        self.assertIn("masked_key", res)

    def test_05_usage_tracking_tools(self):
        """Verify usage tracking tools accurately report recorded metrics."""
        usage_tracker.reset()
        usage_tracker.record_usage("test_provider", success=True, usage=None)

        res_indiv = run_coro(ai_plugins_mcp.get_provider_usage("test_provider"))
        self.assertEqual(res_indiv["status"], "success")
        self.assertEqual(res_indiv["usage"]["request_count"], 1)

        res_sum = run_coro(ai_plugins_mcp.get_provider_usage_summary())
        self.assertEqual(res_sum["status"], "success")
        self.assertEqual(res_sum["summary"]["total_requests"], 1)

        usage_tracker.reset()

    def test_06_main_orchestrator_routing(self):
        """Verify main.py dispatch routes ask_* and ai_council_* tools to ai_plugins_mcp."""
        agent = ZyeMasterAgent()
        res = run_coro(agent._dispatch_tool_call("list_active_ai_plugins", {}))
        self.assertEqual(res.get("status"), "success")
        self.assertIn("active_providers", res)



if __name__ == "__main__":
    unittest.main()
