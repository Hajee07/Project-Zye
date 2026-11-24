"""
End-to-End Integration tests for Day 13 Autonomous Intelligence System.
Tests full pipeline integration with main.py, ZyeMasterAgent, Execution Gate,
Negative Pre-Mortem Brain, Multi-Solution Decision Matrix, and MCP Orchestrator.
"""

from __future__ import annotations

import asyncio
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from main import ZyeMasterAgent
from zye_intelligence.autonomous_watchdog import ZyeAutonomousWatchdog
from zye_intelligence.decision_matrix import ZyeDecisionMatrix
from zye_intelligence.emergency_reflex import ZyeEmergencyReflex
from zye_intelligence.execution_gate import ZyeExecutionGate
from zye_intelligence.mission_controller import ZyeMissionController
from zye_intelligence.negative_audit import NegativeAuditEngine
from zye_intelligence.preflight import ZyeSystemPreflight
from zye_intelligence.premortem import ZyeNegativePreMortem


class TestDay13Integration(unittest.TestCase):
    def setUp(self) -> None:
        self.agent = ZyeMasterAgent()
        self.mc = ZyeMissionController()
        self.pf = ZyeSystemPreflight()
        self.brain = ZyeNegativePreMortem()
        self.dm = ZyeDecisionMatrix()
        self.reflex = ZyeEmergencyReflex(mission_controller=self.mc)
        self.gate = ZyeExecutionGate(
            premortem_brain=self.brain,
            preflight=self.pf,
            mission_controller=self.mc,
        )

    def tearDown(self) -> None:
        asyncio.run(self.agent.shutdown())

    def test_01_main_agent_boot(self) -> None:
        """Verify ZyeMasterAgent boots and initializes Day 12/13 registries."""
        async def _test():
            with patch.object(self.agent, "connect_all_skills", new_callable=AsyncMock) as mock_conn, \
                 patch.object(self.agent, "discover_server_tools", new_callable=AsyncMock) as mock_disc:
                mock_conn.return_value = {"self_repair": "connected"}
                mock_disc.return_value = {"discovered": {}, "total_tools": 2}
                boot_res = await self.agent.boot()
                self.assertEqual(boot_res["status"], "success")
                self.assertTrue(self.agent._booted)
        asyncio.run(_test())

    def test_02_negative_brain_registration(self) -> None:
        """Verify autonomous_brain MCP server registers run_negative_premortem_brain tool."""
        self.agent.register_mock_session("autonomous_brain", [
            "run_negative_premortem_brain", "compare_and_decide_solutions",
            "set_mission_mode", "get_current_mission",
            "autonomous_identify_problems", "execute_emergency_reflex",
        ])
        tools = self.agent.list_mcp_tools(server_name="autonomous_brain")
        tool_names = [t.get("public_name") or t.get("original_name") or t.get("name") for t in tools]
        self.assertIn("run_negative_premortem_brain", tool_names)
        self.assertIn("compare_and_decide_solutions", tool_names)

    def test_03_gemini_integration(self) -> None:
        """Verify Gemini function declarations are built from registered tools."""
        self.agent.register_mock_session("autonomous_brain", ["run_negative_premortem_brain"])
        declarations = asyncio.run(self.agent.rebuild_gemini_tool_registry())
        self.assertGreater(len(declarations), 0)

    def test_04_preflight_integration(self) -> None:
        """Verify preflight report is accessible and contains required telemetry keys."""
        report = self.pf.generate_preflight_report(["main.py"])
        self.assertIn("system_status", report)
        self.assertIn("free_ram_gb", report)
        self.assertIn("target_diagnostics", report)

    def test_05_decision_matrix_integration(self) -> None:
        """Verify decision matrix ranks candidates within master agent workflow."""
        candidates = [
            {"name": "Method_A", "description": "Quick fix", "reliability": 7.0, "speed": 9.0, "safety": 5.0, "simplicity": 8.0},
            {"name": "Method_B", "description": "Safe fix", "reliability": 9.0, "speed": 6.0, "safety": 9.0, "simplicity": 7.0},
        ]
        res = self.dm.compare_solutions("Fix logic", candidates, priority_mode="maximum_safety")
        self.assertEqual(res["recommended_best_solution"]["name"], "Method_B")

    def test_06_mission_selection_integration(self) -> None:
        """Verify mission transition and querying."""
        self.mc.set_mission("DEEP_ENGINEERING", custom_objective="Integration test", force=True)
        m = self.mc.get_current_mission()
        self.assertEqual(m["mission"], "DEEP_ENGINEERING")
        self.mc.set_mission("NORMAL_ASSISTANT", force=True)

    def test_07_tool_execution_gate_integration(self) -> None:
        """Verify execution gate blocks destructive actions without approval token."""
        gate_res = asyncio.run(self.gate.evaluate("delete_file", {"path": "test.txt"}))
        self.assertFalse(gate_res["allowed"])
        self.assertTrue(gate_res["requires_confirmation"])

    def test_08_watchdog_lifecycle_integration(self) -> None:
        """Verify watchdog can be started and stopped cleanly without hanging."""
        wd = ZyeAutonomousWatchdog(mission_controller=self.mc, config={"interval_seconds": 0.05})
        async def _test():
            await wd.start()
            self.assertTrue(wd._running)
            await asyncio.sleep(0.08)
            await wd.stop()
            self.assertFalse(wd._running)
        asyncio.run(_test())

    def test_09_emergency_reflex_integration(self) -> None:
        """Verify emergency reflex executes allowlisted response."""
        res = asyncio.run(self.reflex.execute("ram_overload_relief"))
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["emergency_handled"], "ram_overload_relief")

    def test_10_day12_mcp_routing_integration(self) -> None:
        """Verify Day 12 MCP execution router and recovery controller interaction."""
        self.agent.register_mock_session("self_repair", ["read_recent_error_logs"])
        status = self.agent.get_mcp_orchestrator_status()
        self.assertEqual(status["status"], "READY")

    def test_11_self_correcting_audit_engine(self) -> None:
        """Verify NegativeAuditEngine produces hardened steps for file operation."""
        engine = NegativeAuditEngine(preflight=self.pf, premortem_brain=self.brain)
        rep = asyncio.run(engine.audit_task("Edit file main.py", targets=["main.py"]))
        self.assertIn(rep.overall_failure_risk, ("LOW", "MEDIUM", "HIGH", "CRITICAL"))
        self.assertGreater(len(rep.corrected_hardened_steps), 0)

    def test_12_graceful_shutdown(self) -> None:
        """Verify master agent shutdown terminates sessions cleanly."""
        async def _test():
            with patch.object(self.agent, "connect_all_skills", new_callable=AsyncMock), \
                 patch.object(self.agent, "discover_server_tools", new_callable=AsyncMock):
                await self.agent.boot()
                await self.agent.shutdown()
                self.assertFalse(self.agent.health_monitor.is_running)
        asyncio.run(_test())


if __name__ == "__main__":
    unittest.main()
