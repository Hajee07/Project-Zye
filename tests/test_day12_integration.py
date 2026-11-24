#!/usr/bin/env python3
"""
ZYE AI — Day 12 Master Integration Test Suite
============================================
Comprehensive end-to-end integration tests:
  1. Master agent boot sequence
  2. Multi-server registration
  3. Dynamic tool discovery
  4. Gemini FunctionDeclaration generation
  5. Tool invocation and result parsing
  6. Negative Brain pre-mortem gate integration
  7. Mission Controller integration
  8. Host-level hot reload workflow
  9. Recovery controller crash detection and backoff
 10. Registry refresh on reload
 11. Voice orchestrator loop preservation
 12. Background watchdog coordination
 13. Clean shutdown of all subsystems
"""

from __future__ import annotations

import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from main import ZyeMasterAgent, ZyeVoiceLoop


class TestDay12Integration(unittest.TestCase):
    """End-to-end master integration tests for Day 12."""

    def setUp(self) -> None:
        self.agent = ZyeMasterAgent(root=PROJECT_ROOT)

    def tearDown(self) -> None:
        self._run(self.agent.shutdown())

    def _run(self, coro):
        return asyncio.run(coro)

    def test_01_master_agent_boot(self) -> None:
        """agent.boot() initializes skills, tool registry, and health monitor."""
        async def _test():
            with patch.object(self.agent, "connect_all_skills", new_callable=AsyncMock) as mock_conn, \
                 patch.object(self.agent, "discover_server_tools", new_callable=AsyncMock) as mock_disc:
                mock_conn.return_value = {"self_repair": "connected"}
                mock_disc.return_value = {"discovered": {}, "total_tools": 2}

                res = await self.agent.boot()
                self.assertEqual(res["status"], "success")
                self.assertTrue(self.agent.health_monitor.is_running)

        self._run(_test())

    def test_02_mock_sessions_and_dynamic_discovery(self) -> None:
        """Mock sessions register into connection manager and tool registry."""
        self.agent.register_mock_session("self_repair", ["read_recent_error_logs", "read_own_source_code"])
        self.agent.register_mock_session("autonomous_brain", ["run_negative_premortem_brain", "get_current_mission"])

        self.assertEqual(self.agent.tool_registry.tool_count, 4)
        self.assertIn("self_repair", self.agent.sessions)
        self.assertIn("autonomous_brain", self.agent.sessions)

    def test_03_gemini_tool_declaration_rebuild(self) -> None:
        """rebuild_gemini_tool_registry generates tool declarations."""
        self.agent.register_mock_session("self_repair", ["read_recent_error_logs"])
        decls = self._run(self.agent.rebuild_gemini_tool_registry())
        self.assertGreater(len(decls), 0)

    def test_04_call_mcp_with_recovery_success(self) -> None:
        """call_mcp_with_recovery invokes registered tool and returns response."""
        self.agent.register_mock_session("self_repair", ["read_recent_error_logs"])
        res = self._run(self.agent.call_mcp_with_recovery("read_recent_error_logs", {}))
        self.assertIn(res.get("status"), ("success", "ok"))

    def test_05_negative_brain_tool_available(self) -> None:
        """autonomous_brain tools are routable through agent."""
        self.agent.register_mock_session("autonomous_brain", ["run_negative_premortem_brain"])
        route = self.agent.tool_registry.get_tool_route("run_negative_premortem_brain")
        self.assertEqual(route, ("autonomous_brain", "run_negative_premortem_brain"))

    def test_06_mission_controller_accessible(self) -> None:
        """Mission Controller state can be read alongside orchestrator."""
        from zye_autonomy.mission_profiles import ZyeMissionController
        mc = ZyeMissionController()
        mission = mc.get_current_mission()
        self.assertIn("mission", mission)

    def test_07_hot_reload_workflow(self) -> None:
        """hot_reload_server succeeds and updates generation."""
        self.agent.register_mock_session("self_repair", ["read_recent_error_logs"])
        g0 = self.agent.server_generations.get("self_repair", 0)

        with patch.object(self.agent, "_start_mcp_session", new_callable=AsyncMock) as mock_start:
            mock_start.return_value = ["read_recent_error_logs", "new_patch_tool"]
            res = self._run(self.agent.hot_reload_server("self_repair"))
            self.assertEqual(res["status"], "success")
            self.assertEqual(res["generation"], g0 + 1)
            self.assertIn("new_patch_tool", self.agent.server_tools["self_repair"])

    def test_08_recovery_controller_records_failure_and_success(self) -> None:
        """Recovery controller updates circuit state on crash."""
        self.agent.register_mock_session("self_repair", ["read_recent_error_logs"])
        self.agent.recovery_ctrl.record_failure("self_repair", "crash")
        status = self.agent.recovery_ctrl.get_recovery_status("self_repair")
        self.assertEqual(status["consecutive_failures"], 1)

        self.agent.recovery_ctrl.record_success("self_repair")
        status_after = self.agent.recovery_ctrl.get_recovery_status("self_repair")
        self.assertEqual(status_after["consecutive_failures"], 0)

    def test_09_host_level_diagnostics_tools(self) -> None:
        """All host-level MCP diagnostic tools return structured outputs."""
        self.agent.register_mock_session("self_repair", ["read_recent_error_logs"])

        status = self.agent.get_mcp_orchestrator_status()
        self.assertIn("registered_servers", status)

        servers = self.agent.list_mcp_servers()
        self.assertIsInstance(servers, list)

        tools = self.agent.list_mcp_tools()
        self.assertIsInstance(tools, list)

        health = self.agent.get_mcp_server_health("self_repair")
        self.assertEqual(health["server_name"], "self_repair")

        history = self.agent.get_mcp_recovery_history()
        self.assertIsInstance(history, list)

    def test_10_voice_loop_orchestrator_preservation(self) -> None:
        """ZyeVoiceLoop instantiates with orchestrator agent."""
        vl = ZyeVoiceLoop()
        self.assertIsNotNone(vl.agent)
        self.assertTrue(hasattr(vl.agent, "registry"))
        self.assertTrue(hasattr(vl.agent, "tool_registry"))
        self.assertTrue(hasattr(vl.agent, "hot_reload_server"))

    def test_11_voice_loop_shutdown_cleans_resources(self) -> None:
        """Voice loop shutdown cleanly stops agent."""
        async def _test():
            vl = ZyeVoiceLoop()
            await vl._shutdown()
            self.assertEqual(vl.state, "OFFLINE")

        self._run(_test())

    def test_12_proactive_watchdog_coexists(self) -> None:
        """Autonomous watchdog can run alongside MCP orchestrator."""
        from zye_autonomy.watchdog import ZyeAutonomousWatchdog
        wd = ZyeAutonomousWatchdog()
        self.assertFalse(wd._running)

    def test_13_full_shutdown_lifecycle(self) -> None:
        """Full agent shutdown releases sessions, stacks, and health monitor."""
        async def _test():
            self.agent.register_mock_session("s1", ["t1"])
            await self.agent.health_monitor.start()
            await self.agent.shutdown()
            self.assertFalse(self.agent.health_monitor.is_running)
            self.assertEqual(len(self.agent.sessions), 0)

        self._run(_test())


if __name__ == "__main__":
    unittest.main()
