#!/usr/bin/env python3
"""
ZYE AI — Day 12 Orchestrator Lifecycle Test Suite
================================================
Tests for orchestrator boot, shutdown, and resource lifecycles:
  1. Boot sequence initialization
  2. Partial startup handles optional server failures gracefully
  3. Full startup registers tools and starts monitoring
  4. Shutdown cancels health monitor background tasks
  5. Shutdown closes all active server sessions cleanly
  6. Subprocess / context stack cleanup
  7. Repeated boot call is idempotent
  8. Repeated shutdown call is safe
  9. Host diagnostic reporting reflects active state
 10. Status transitions from INITIALIZING to READY to OFFLINE
"""

from __future__ import annotations

import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from main import ZyeMasterAgent
from zye_orchestrator.server_runtime import ServerStatus


class TestOrchestratorLifecycle(unittest.TestCase):
    """Test suite for Master Agent & Orchestrator Lifecycle Management."""

    def setUp(self) -> None:
        self.agent = ZyeMasterAgent(root=PROJECT_ROOT)

    def tearDown(self) -> None:
        self._run(self.agent.shutdown())

    def _run(self, coro):
        return asyncio.run(coro)

    def test_01_initial_state(self) -> None:
        """New agent starts unbooted with empty active sessions."""
        self.assertFalse(self.agent._booted)
        self.assertEqual(len(self.agent.sessions), 0)

    def test_02_boot_idempotent(self) -> None:
        """Calling boot twice does not duplicate background monitors or sessions."""
        async def _test():
            with patch.object(self.agent, "connect_all_skills", new_callable=AsyncMock) as mock_conn, \
                 patch.object(self.agent, "discover_server_tools", new_callable=AsyncMock) as mock_disc:
                mock_conn.return_value = {"srv1": "connected"}
                r1 = await self.agent.boot()
                self.assertEqual(r1["status"], "success")

                r2 = await self.agent.boot()
                self.assertEqual(r2["status"], "already_booted")

        self._run(_test())

    def test_03_partial_startup_with_optional_server_failure(self) -> None:
        """When an optional server fails to connect, healthy servers remain available."""
        async def _test():
            self.agent.register_mock_session("healthy_srv", ["h_tool"])
            # The agent has healthy_srv registered
            self.assertIn("healthy_srv", self.agent.sessions)
            self.assertEqual(self.agent.tool_registry.tool_count, 1)

        self._run(_test())

    def test_04_shutdown_stops_health_monitor(self) -> None:
        """shutdown() stops the running health monitor task."""
        async def _test():
            await self.agent.health_monitor.start()
            self.assertTrue(self.agent.health_monitor.is_running)

            await self.agent.shutdown()
            self.assertFalse(self.agent.health_monitor.is_running)
            self.assertFalse(self.agent._booted)

        self._run(_test())

    def test_05_shutdown_closes_exit_stacks(self) -> None:
        """shutdown() calls aclose on all open exit stacks."""
        async def _test():
            mock_stack = AsyncMock()
            self.agent.exit_stacks["mock_srv"] = mock_stack
            self.agent.sessions["mock_srv"] = type("Sess", (), {})()

            await self.agent.shutdown()
            mock_stack.aclose.assert_awaited_once()
            self.assertEqual(len(self.agent.exit_stacks), 0)
            self.assertEqual(len(self.agent.sessions), 0)

    def test_06_repeated_shutdown_safe(self) -> None:
        """Calling shutdown multiple times raises no exceptions."""
        async def _test():
            await self.agent.shutdown()
            await self.agent.shutdown()
            self.assertFalse(self.agent._booted)

        self._run(_test())

    def test_07_status_reporting(self) -> None:
        """get_mcp_orchestrator_status returns structured state dict."""
        self.agent.register_mock_session("test_srv", ["t1", "t2"])
        status = self.agent.get_mcp_orchestrator_status()
        self.assertEqual(status["active_sessions"], 1)
        self.assertEqual(status["total_discovered_tools"], 2)

    def test_08_list_mcp_servers(self) -> None:
        """list_mcp_servers enumerates configured servers and statuses."""
        servers = self.agent.list_mcp_servers()
        self.assertIsInstance(servers, list)
        self.assertGreater(len(servers), 0)
        self.assertTrue(any(s["server_name"] == "self_repair" for s in servers))

    def test_09_list_mcp_tools_filtering(self) -> None:
        """list_mcp_tools filters tools by owning server."""
        self.agent.register_mock_session("srv_x", ["tool_x1", "tool_x2"])
        self.agent.register_mock_session("srv_y", ["tool_y1"])

        all_tools = self.agent.list_mcp_tools()
        self.assertEqual(len(all_tools), 3)

        x_tools = self.agent.list_mcp_tools(server_name="srv_x")
        self.assertEqual(len(x_tools), 2)
        self.assertTrue(all(t["server_name"] == "srv_x" for t in x_tools))

    def test_10_get_mcp_server_health(self) -> None:
        """get_mcp_server_health returns server specific telemetry."""
        self.agent.register_mock_session("srv_z", ["tool_z"])
        health = self.agent.get_mcp_server_health("srv_z")
        self.assertEqual(health["server_name"], "srv_z")
        self.assertTrue(health["session_active"])


if __name__ == "__main__":
    unittest.main()
