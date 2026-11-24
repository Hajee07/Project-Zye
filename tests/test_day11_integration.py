"""Integration tests for Zye Day 11 Autonomous Intelligence & Dual-Brain System."""

import asyncio
import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from autonomous_decision_mcp import mcp
from main import MCP_SERVERS, ZyeMasterAgent, ZyeVoiceLoop
from zye_autonomy.decision_matrix import ZyeDecisionMatrix
from zye_autonomy.emergency_reflex import ZyeEmergencyReflex
from zye_autonomy.execution_gate import ZyeExecutionGate
from zye_autonomy.mission_profiles import ZyeMissionController
from zye_autonomy.preflight import ZyeSystemPreflight
from zye_autonomy.premortem import ZyeNegativePreMortem
from zye_autonomy.watchdog import ZyeAutonomousWatchdog
from zye_brain.gemini_agent import SYSTEM_PERSONA


class TestDay11Integration(unittest.TestCase):
    def test_01_autonomous_brain_registered_in_mcp_servers(self):
        self.assertIn("autonomous_brain", MCP_SERVERS)
        config = MCP_SERVERS["autonomous_brain"]
        self.assertTrue(any("autonomous_decision_mcp.py" in arg for arg in config["args"]))

    def test_02_master_agent_registers_all_6_autonomy_tools(self):
        agent = ZyeMasterAgent()
        autonomy_tools = [
            "run_negative_premortem_brain", "compare_and_decide_solutions",
            "set_mission_mode", "get_current_mission",
            "autonomous_identify_problems", "execute_emergency_reflex",
        ]
        agent.register_mock_session("autonomous_brain", autonomy_tools)
        for t in autonomy_tools:
            self.assertEqual(agent.tool_to_server.get(t), "autonomous_brain")

    def test_03_gemini_system_persona_includes_day11_protocol(self):
        self.assertIn("MANDATORY PRE-MORTEM & AUTONOMOUS DECISION PROTOCOL", SYSTEM_PERSONA)
        self.assertIn("NEGATIVE PRE-MORTEM FIRST", SYSTEM_PERSONA)
        self.assertIn("SELF-CORRECT BEFORE ACTING", SYSTEM_PERSONA)
        self.assertIn("COMPARE AND RECOMMEND", SYSTEM_PERSONA)
        self.assertIn("MISSION ADAPTATION", SYSTEM_PERSONA)
        self.assertIn("TOOL SAFETY", SYSTEM_PERSONA)

    def test_04_mcp_premortem_tool(self):
        from autonomous_decision_mcp import run_negative_premortem_brain

        async def _run():
            raw = await run_negative_premortem_brain(
                task_description="Delete old logs",
                proposed_steps=["rm -f logs/old.log"],
                target_files_or_paths=["logs/old.log"],
            )
            data = json.loads(raw)
            self.assertIn("overall_failure_risk", data)
            self.assertIn(data["overall_failure_risk"], ["LOW", "MEDIUM", "HIGH", "CRITICAL"])
            self.assertIsInstance(data["corrected_hardened_steps"], list)
        asyncio.run(_run())

    def test_05_mcp_decision_matrix_tool(self):
        from autonomous_decision_mcp import compare_and_decide_solutions

        raw = compare_and_decide_solutions(
            problem_statement="Choose strategy",
            candidate_solutions=[
                {"name": "Option1", "description": "Quick", "reliability": 7, "speed": 9, "safety": 8, "simplicity": 8},
                {"name": "Option2", "description": "Thorough", "reliability": 9, "speed": 6, "safety": 9, "simplicity": 6},
            ],
            priority_mode="balanced",
        )
        data = json.loads(raw)
        self.assertIn("recommended_best_solution", data)
        self.assertEqual(data["priority_mode"], "balanced")

    def test_06_mcp_mission_tools(self):
        from autonomous_decision_mcp import get_current_mission, set_mission_mode

        set_raw = set_mission_mode("DEEP_ENGINEERING", "Integration test")
        set_data = json.loads(set_raw)
        self.assertEqual(set_data["status"], "SUCCESS")
        self.assertEqual(set_data["mission_state"]["mission"], "DEEP_ENGINEERING")

        get_raw = get_current_mission()
        get_data = json.loads(get_raw)
        self.assertEqual(get_data["mission"], "DEEP_ENGINEERING")

        # Restore default
        set_mission_mode("NORMAL_ASSISTANT", "Restore default")

    def test_07_mcp_watchdog_tool(self):
        from autonomous_decision_mcp import autonomous_identify_problems

        async def _run():
            raw = await autonomous_identify_problems()
            data = json.loads(raw)
            self.assertIn("problems_detected", data)
            self.assertIn("problems", data)
            self.assertIsInstance(data["problems"], list)
        asyncio.run(_run())

    def test_08_mcp_emergency_reflex_tool(self):
        from autonomous_decision_mcp import execute_emergency_reflex

        async def _run():
            # Unknown type rejected
            rej_raw = await execute_emergency_reflex("invalid_type")
            rej = json.loads(rej_raw)
            self.assertEqual(rej["status"], "REJECTED")

            # RAM relief handled
            ram_raw = await execute_emergency_reflex("ram_overload_relief")
            ram = json.loads(ram_raw)
            self.assertIn(ram["status"], ["SUCCESS", "PARTIAL"])
        asyncio.run(_run())

    def test_09_voice_loop_initializes_autonomy_subsystems(self):
        with patch.object(ZyeVoiceLoop, "_speak", new=AsyncMock()):
            loop = ZyeVoiceLoop()
            self.assertIsNotNone(loop.execution_gate)
            self.assertIsNotNone(loop.mission_controller)
            self.assertIsNotNone(loop.preflight)
            self.assertIsNotNone(loop.premortem_brain)
            self.assertIsNotNone(loop.decision_matrix)
            self.assertIsNotNone(loop.emergency_reflex)
            self.assertIsNotNone(loop.watchdog)

    def test_10_voice_loop_dispatch_intercepted_by_execution_gate(self):
        with patch.object(ZyeVoiceLoop, "_speak", new=AsyncMock()):
            loop = ZyeVoiceLoop()
            # Intercept destructive tool
            async def _run():
                # We can call loop.brain.tool_dispatcher directly
                dispatch_fn = loop.brain.tool_dispatcher
                self.assertIsNotNone(dispatch_fn)

                # Attempt destructive operation without token
                res = await dispatch_fn("delete_file", {"path": "important.db"})
                self.assertEqual(res.get("status"), "BLOCKED_BY_EXECUTION_GATE")
                self.assertTrue(res.get("requires_confirmation"))
                self.assertIsNotNone(res.get("approval_token"))
            asyncio.run(_run())

    def test_11_voice_loop_watchdog_background_and_shutdown(self):
        with patch.object(ZyeVoiceLoop, "_speak", new=AsyncMock()), \
             patch("sounddevice.InputStream", MagicMock()):
            loop = ZyeVoiceLoop()

            async def _run():
                # Test shutdown cleans up watchdog and resources
                await loop._shutdown()
                self.assertFalse(loop._running)
                if hasattr(loop, "watchdog") and loop.watchdog:
                    self.assertFalse(loop.watchdog._running)
            asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()
