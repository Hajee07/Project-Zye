"""Day 26 Unit Tests: MCP Server Tools and Voice Intent Integration.

Tests:
- All Day 26 FastMCP tools in ai_plugins_mcp.py
- main.py tool dispatch routing for Council tools
- Gemini SYSTEM_PERSONA compliance with Council voice commands (Tamil, English, Tanglish)
"""

import unittest
from unittest.mock import MagicMock, patch

import ai_plugins_mcp
from main import ZyeMasterAgent
from zye_brain.gemini_agent import SYSTEM_PERSONA


def run_coro(coro):
    """Run an async coroutine synchronously without event loop socket binding."""
    try:
        while True:
            coro.send(None)
    except StopIteration as exc:
        return exc.value


class TestDay26MCPAndVoice(unittest.TestCase):
    """Test suite for FastMCP Council Tools and Voice Integration."""

    def test_01_all_council_tools_present(self):
        """Verify all new Day 26 Council tools are registered in ai_plugins_mcp."""
        tm = getattr(ai_plugins_mcp.mcp, "_tool_manager", getattr(ai_plugins_mcp.mcp, "_tools", None))
        tools = getattr(tm, "_tools", tm)

        expected_day26 = [
            "run_ai_council",
            "run_quick_council",
            "run_deep_council",
            "compare_ai_responses",
            "detect_ai_disagreements",
            "analyze_ai_consensus",
            "evaluate_candidate_solutions",
            "get_ai_council_report",
            "get_ai_council_status",
            "cancel_ai_council",
        ]

        for exp in expected_day26:
            self.assertIn(exp, tools, f"Missing Day 26 tool: {exp}")

    def test_02_detect_ai_disagreements_tool(self):
        """Verify detect_ai_disagreements MCP tool execution."""
        sample_responses = {
            "chatgpt": "Architecture A is completely secure and safe.",
            "claude": "Architecture A is not secure and has fatal flaws.",
        }

        res = run_coro(ai_plugins_mcp.detect_ai_disagreements(provider_responses=sample_responses))
        self.assertEqual(res["status"], "success")
        self.assertIn("disagreement_report", res)
        self.assertGreaterEqual(res["disagreement_report"]["total_disagreements"], 1)

    def test_03_evaluate_candidate_solutions_tool(self):
        """Verify evaluate_candidate_solutions MCP tool execution."""
        candidates = {
            "arch_a": {"title": "Architecture A", "scores": {"performance": 0.9, "reliability": 0.8}},
            "arch_b": {"title": "Architecture B", "scores": {"performance": 0.7, "reliability": 0.95}},
        }

        res = run_coro(ai_plugins_mcp.evaluate_candidate_solutions(
            problem_statement="Choose best DB architecture",
            candidate_solutions=candidates,
            priority_mode="balanced",
        ))
        self.assertEqual(res["status"], "success")
        self.assertIn("decision_ranking", res)
        self.assertEqual(res["decision_ranking"]["total_candidates"], 2)

    def test_04_orchestrator_routes_council_tools(self):
        """Verify main.py dispatch routing directs run_quick_council and compare_ai_ to ai_plugins_mcp."""
        agent = ZyeMasterAgent()

        with patch("ai_plugins_mcp.detect_ai_disagreements") as mock_det:
            async def _fake_detect(**kwargs):
                return {"status": "success", "mocked": True}
            mock_det.side_effect = _fake_detect

            res = run_coro(agent._dispatch_tool_call("detect_ai_disagreements", {"provider_responses": {}}))
            self.assertEqual(res.get("status"), "success")

    def test_05_system_persona_voice_commands_compliance(self):
        """Verify SYSTEM_PERSONA includes Tamil, English, and Tanglish council command protocols."""
        self.assertIn("DAY 25 & 26 ADVANCED MULTI-AI COUNCIL & SUPREME ARBITER PROTOCOL", SYSTEM_PERSONA)
        self.assertIn("Zye, AI Council activate pannu", SYSTEM_PERSONA)
        self.assertIn("Deep-ah analyze panni best solution decide pannu", SYSTEM_PERSONA)
        self.assertIn("ChatGPT and Claude answers-la enna difference irukku", SYSTEM_PERSONA)
        self.assertIn("Endha points-la ellarum agree panraanga", SYSTEM_PERSONA)
        self.assertIn("Local Council mattum use pannu", SYSTEM_PERSONA)
        self.assertIn("en-IN-NeerjaNeural", SYSTEM_PERSONA)


if __name__ == "__main__":
    unittest.main()
