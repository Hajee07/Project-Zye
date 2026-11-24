"""Day 27 Unit Tests: FastMCP Tools & Voice Persona Integration.

Tests:
- Verification of 15 new Day 27 tools registered in ai_plugins_mcp (40 total)
- Execution of Day 27 tools (get_routing_decision, get_circuit_breaker_status, get_provider_cost_estimate, get_ai_infrastructure_report)
- Main orchestrator dispatch routing for Day 27 prefixes
- SYSTEM_PERSONA Protocol 18 compliance for Tamil, English, and Tanglish routing commands
"""

import unittest
from unittest.mock import MagicMock

import ai_plugins_mcp
from zye_brain.gemini_agent import SYSTEM_PERSONA


def run_coro(coro):
    """Run an async coroutine synchronously without creating a Windows Proactor loopback socket."""
    try:
        coro.send(None)
    except StopIteration as e:
        return e.value
    raise RuntimeError(f"Coroutine {coro} yielded unexpectedly")


class TestDay27MCPAndVoice(unittest.TestCase):
    """Test suite for Day 27 FastMCP tools and voice persona routing."""

    def test_01_all_40_tools_registered(self):
        """Verify all 40 tools across Days 25, 26, and 27 are registered in ai_plugins_mcp."""
        tm = getattr(ai_plugins_mcp.mcp, "_tool_manager", getattr(ai_plugins_mcp.mcp, "_tools", None))
        tools = getattr(tm, "_tools", tm)

        expected_day27 = [
            "get_provider_health",
            "get_all_provider_metrics",
            "get_provider_reliability_ranking",
            "get_routing_decision",
            "get_provider_status",
            "get_provider_cost_estimate",
            "get_provider_usage_report",
            "run_provider_benchmark",
            "get_provider_benchmark_report",
            "get_circuit_breaker_status",
            "get_failover_history",
            "get_concurrency_status",
            "set_routing_policy",
            "reset_provider_health",
            "get_ai_infrastructure_report",
        ]

        self.assertGreaterEqual(len(tools), 40)
        for tool_name in expected_day27:
            self.assertIn(tool_name, tools, f"Missing Day 27 tool: {tool_name}")

    def test_02_get_routing_decision_tool(self):
        """Verify get_routing_decision tool execution."""
        res = run_coro(ai_plugins_mcp.get_routing_decision(task="speed critical query", routing_mode="SPEED_FIRST"))
        self.assertEqual(res["status"], "success")
        self.assertIn("decision", res)
        self.assertEqual(res["decision"]["routing_mode"], "SPEED_FIRST")
        self.assertTrue(res["decision"]["selected_provider"])

    def test_03_get_circuit_breaker_status_tool(self):
        """Verify get_circuit_breaker_status tool execution."""
        res = run_coro(ai_plugins_mcp.get_circuit_breaker_status())
        self.assertEqual(res["status"], "success")
        self.assertIn("circuits", res)

    def test_04_get_provider_cost_estimate_tool(self):
        """Verify get_provider_cost_estimate tool execution."""
        res = run_coro(ai_plugins_mcp.get_provider_cost_estimate("chatgpt", "gpt-4o", 1000, 500))
        self.assertEqual(res["status"], "success")
        self.assertIn("estimate", res)
        self.assertEqual(res["estimate"]["cost_status"], "CALCULATED")

    def test_05_get_ai_infrastructure_report_tool(self):
        """Verify get_ai_infrastructure_report tool execution."""
        res = run_coro(ai_plugins_mcp.get_ai_infrastructure_report())
        self.assertEqual(res["status"], "success")
        self.assertIn("active_routing_policy", res)
        self.assertIn("circuit_breakers", res)
        self.assertIn("concurrency_pools", res)

    def test_06_orchestrator_routes_day27_tools(self):
        """Verify main.py dispatch routing directs get_routing_ and get_circuit_breaker_ to ai_plugins_mcp."""
        from unittest.mock import patch
        from main import ZyeMasterAgent
        agent = ZyeMasterAgent()

        with patch("ai_plugins_mcp.get_routing_decision") as mock_route:
            async def _fake_route(**kwargs):
                return {"status": "success", "mocked": True}
            mock_route.side_effect = _fake_route

            res = run_coro(agent._dispatch_tool_call("get_routing_decision", {}))
            self.assertEqual(res.get("status"), "success")

    def test_07_system_persona_protocol18_compliance(self):
        """Verify SYSTEM_PERSONA includes Protocol 18 for Day 27 intelligent routing commands."""
        self.assertIn("18. Day 27 Intelligent AI Routing", SYSTEM_PERSONA)
        self.assertIn("Fastest available AI", SYSTEM_PERSONA)
        self.assertIn("Cost kammiya irukkura AI", SYSTEM_PERSONA)
        self.assertIn("Circuit breaker status check pannu", SYSTEM_PERSONA)


if __name__ == "__main__":
    unittest.main()
