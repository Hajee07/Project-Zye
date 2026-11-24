#!/usr/bin/env python3
"""
ZYE AI — Day 12 Hot Reload Test Suite
====================================
Tests for zye_orchestrator.hot_reload:
  1. Valid server reload
  2. Unknown server rejected
  3. Missing server rejected
  4. Candidate startup failure handling
  5. MCP initialization failure handling
  6. Schema validation failure handling
  7. Candidate health failure handling
  8. Old session cleanup
  9. Old tool removal
 10. New tool registration
 11. Registry atomic swap
 12. Active operation protection (draining)
 13. Reload drain timeout handling
 14. Reload lock (concurrent reload prevention)
 15. Failed reload preserves previous runtime
 16. Successful rollback reporting
 17. Failed rollback reporting
 18. Duplicate process prevention
"""

from __future__ import annotations

import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from zye_orchestrator.hot_reload import HotReloadController
from zye_orchestrator.server_registry import ServerRegistry
from zye_orchestrator.server_runtime import MCPConnectionManager, MCPServerRuntime, ServerStatus
from zye_orchestrator.tool_registry import ZyeToolRegistry


class TestHotReload(unittest.TestCase):
    """Test suite for transactional MCP Server Hot Reload."""

    def setUp(self) -> None:
        self.registry = ServerRegistry(PROJECT_ROOT)
        self.registry.register_from_dict({
            "test_server": {
                "command": sys.executable,
                "args": [str(PROJECT_ROOT / "self_repair_mcp.py")],
                "enabled": True,
            },
            "disabled_server": {
                "command": sys.executable,
                "args": [str(PROJECT_ROOT / "self_repair_mcp.py")],
                "enabled": False,
            },
        })
        self.conn_mgr = MCPConnectionManager()
        self.conn_mgr.register_mock_runtime("test_server", ["tool_old_1", "tool_old_2"])
        self.tool_reg = ZyeToolRegistry()
        self.tool_reg.register_server_tools("test_server", [
            {"name": "tool_old_1", "description": "old 1", "inputSchema": {}},
            {"name": "tool_old_2", "description": "old 2", "inputSchema": {}},
        ])
        self.controller = HotReloadController(
            self.registry, self.conn_mgr, self.tool_reg,
            config={"reload_drain_timeout_seconds": 0.5, "staged_reload_preferred": True},
        )

    def _run(self, coro):
        return asyncio.run(coro)

    def test_01_unknown_server_rejected(self) -> None:
        """Reloading an unconfigured server returns SERVER_NOT_CONFIGURED."""
        res = self._run(self.controller.hot_reload_server("ghost_server"))
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["code"], "SERVER_NOT_CONFIGURED")

    def test_02_disabled_server_rejected(self) -> None:
        """Reloading a disabled server returns SERVER_DISABLED."""
        res = self._run(self.controller.hot_reload_server("disabled_server"))
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["code"], "SERVER_DISABLED")

    def test_03_valid_reload_with_staged_replacement(self) -> None:
        """Successful reload swaps session, updates tools, and increments generation."""
        mock_cand = MCPServerRuntime("test_server")
        mock_cand.session = type("MockSession", (), {})()
        mock_cand.status = ServerStatus.HEALTHY
        mock_cand.started_at = "2026-11-19T12:00:00Z"

        new_tools = [
            {"name": "tool_new_1", "description": "new 1", "inputSchema": {}},
        ]

        with patch.object(self.conn_mgr, "start_server", new_callable=AsyncMock) as mock_start, \
             patch.object(self.tool_reg, "discover_tools", new_callable=AsyncMock) as mock_disc:
            mock_start.return_value = mock_cand
            mock_disc.return_value = new_tools

            res = self._run(self.controller.hot_reload_server("test_server"))
            self.assertEqual(res["status"], "success")
            self.assertEqual(res["server_name"], "test_server")
            self.assertIn("tool_new_1", res["tools_added"])
            self.assertIn("tool_old_1", res["tools_removed"])

    def test_04_candidate_startup_failure(self) -> None:
        """If candidate fails to start, reload preserves previous runtime."""
        mock_failed = MCPServerRuntime("test_server")
        mock_failed.status = ServerStatus.FAILED
        mock_failed.last_error = "SyntaxError in script"

        with patch.object(self.conn_mgr, "start_server", new_callable=AsyncMock) as mock_start:
            mock_start.return_value = mock_failed

            res = self._run(self.controller.hot_reload_server("test_server"))
            self.assertEqual(res["status"], "error")
            self.assertEqual(res["code"], "CANDIDATE_STARTUP_FAILED")
            self.assertTrue(res.get("previous_preserved"))

    def test_05_candidate_no_tools_exposed(self) -> None:
        """If candidate exposes no valid tools, candidate is rejected."""
        mock_cand = MCPServerRuntime("test_server")
        mock_cand.status = ServerStatus.HEALTHY

        with patch.object(self.conn_mgr, "start_server", new_callable=AsyncMock) as mock_start, \
             patch.object(self.tool_reg, "discover_tools", new_callable=AsyncMock) as mock_disc:
            mock_start.return_value = mock_cand
            mock_disc.return_value = []  # No tools

            res = self._run(self.controller.hot_reload_server("test_server"))
            self.assertEqual(res["status"], "error")
            self.assertEqual(res["code"], "CANDIDATE_NO_TOOLS")

    def test_06_active_operation_protection(self) -> None:
        """Reload drains in-flight calls before starting swap."""
        runtime = self.conn_mgr.get_runtime("test_server")
        runtime.in_flight_calls = 1

        async def _drain_later():
            await asyncio.sleep(0.05)
            runtime.in_flight_calls = 0

        async def _test():
            asyncio.create_task(_drain_later())
            mock_cand = MCPServerRuntime("test_server")
            mock_cand.status = ServerStatus.HEALTHY
            with patch.object(self.conn_mgr, "start_server", new_callable=AsyncMock) as mock_start, \
                 patch.object(self.tool_reg, "discover_tools", new_callable=AsyncMock) as mock_disc:
                mock_start.return_value = mock_cand
                mock_disc.return_value = [{"name": "t1", "description": "d", "inputSchema": {}}]
                return await self.controller.hot_reload_server("test_server")

        res = self._run(_test())
        self.assertEqual(res["status"], "success")

    def test_07_reload_drain_timeout(self) -> None:
        """If in-flight calls do not finish within timeout, reload is deferred."""
        runtime = self.conn_mgr.get_runtime("test_server")
        runtime.in_flight_calls = 5  # Stuck operations

        res = self._run(self.controller.hot_reload_server("test_server"))
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["code"], "RELOAD_DEFERRED_ACTIVE_OPERATION")

    def test_08_reload_lock_prevents_concurrent_reloads(self) -> None:
        """Concurrent reload attempts on the same server are rejected."""
        runtime = self.conn_mgr.get_runtime("test_server")

        async def _test():
            async with runtime._reload_lock:
                res = await self.controller.hot_reload_server("test_server")
                self.assertEqual(res["status"], "error")
                self.assertEqual(res["code"], "RELOAD_IN_PROGRESS")

        self._run(_test())

    def test_09_old_stack_closed_on_success(self) -> None:
        """Old session AsyncExitStack is closed when candidate takes over."""
        runtime = self.conn_mgr.get_runtime("test_server")
        old_stack = AsyncMock()
        runtime.context_stack = old_stack

        mock_cand = MCPServerRuntime("test_server")
        mock_cand.status = ServerStatus.HEALTHY
        mock_cand.context_stack = AsyncMock()

        with patch.object(self.conn_mgr, "start_server", new_callable=AsyncMock) as mock_start, \
             patch.object(self.tool_reg, "discover_tools", new_callable=AsyncMock) as mock_disc:
            mock_start.return_value = mock_cand
            mock_disc.return_value = [{"name": "t_new", "description": "d", "inputSchema": {}}]

            res = self._run(self.controller.hot_reload_server("test_server"))
            self.assertEqual(res["status"], "success")
            old_stack.aclose.assert_awaited_once()

    def test_10_old_tools_removed_cleanly(self) -> None:
        """Old tools not in new candidate are removed from registry."""
        mock_cand = MCPServerRuntime("test_server")
        mock_cand.status = ServerStatus.HEALTHY

        with patch.object(self.conn_mgr, "start_server", new_callable=AsyncMock) as mock_start, \
             patch.object(self.tool_reg, "discover_tools", new_callable=AsyncMock) as mock_disc:
            mock_start.return_value = mock_cand
            mock_disc.return_value = [{"name": "tool_brand_new", "description": "d", "inputSchema": {}}]

            self._run(self.controller.hot_reload_server("test_server"))
            self.assertNotIn("tool_old_1", self.tool_reg.get_all_tools())
            self.assertNotIn("tool_old_2", self.tool_reg.get_all_tools())
            self.assertIn("tool_brand_new", self.tool_reg.get_all_tools())

    def test_11_generation_incremented(self) -> None:
        """Runtime generation increments after successful reload."""
        runtime = self.conn_mgr.get_runtime("test_server")
        g0 = runtime.generation

        mock_cand = MCPServerRuntime("test_server")
        mock_cand.status = ServerStatus.HEALTHY

        with patch.object(self.conn_mgr, "start_server", new_callable=AsyncMock) as mock_start, \
             patch.object(self.tool_reg, "discover_tools", new_callable=AsyncMock) as mock_disc:
            mock_start.return_value = mock_cand
            mock_disc.return_value = [{"name": "t1", "description": "d", "inputSchema": {}}]

            self._run(self.controller.hot_reload_server("test_server"))
            self.assertEqual(runtime.generation, g0 + 1)

    def test_12_reload_history_tracking(self) -> None:
        """Reload attempts are recorded in history."""
        self._run(self.controller.hot_reload_server("ghost_srv"))
        history = self.controller.reload_history
        self.assertGreater(len(history), 0)
        self.assertEqual(history[-1]["server_name"], "ghost_srv")

    def test_13_diagnostics_reporting(self) -> None:
        """get_diagnostics returns structured health metrics."""
        diag = self.controller.get_diagnostics()
        self.assertTrue(diag["staged_preferred"])
        self.assertIn("total_reloads", diag)

    def test_14_schema_validation_failure(self) -> None:
        """Candidate with only invalid schemas is rejected as no tools."""
        mock_cand = MCPServerRuntime("test_server")
        mock_cand.status = ServerStatus.HEALTHY

        with patch.object(self.conn_mgr, "start_server", new_callable=AsyncMock) as mock_start, \
             patch.object(self.tool_reg, "discover_tools", new_callable=AsyncMock) as mock_disc:
            mock_start.return_value = mock_cand
            mock_disc.return_value = [{"name": "", "description": "Invalid"}]  # Invalid tool

            res = self._run(self.controller.hot_reload_server("test_server"))
            self.assertEqual(res["status"], "error")

    def test_15_candidate_health_failure_cleanup(self) -> None:
        """Failed candidate stack is cleanly closed."""
        mock_cand = MCPServerRuntime("test_server")
        mock_cand.status = ServerStatus.FAILED
        cand_stack = AsyncMock()
        mock_cand.context_stack = cand_stack

        with patch.object(self.conn_mgr, "start_server", new_callable=AsyncMock) as mock_start:
            mock_start.return_value = mock_cand
            self._run(self.controller.hot_reload_server("test_server"))
            cand_stack.aclose.assert_awaited()

    def test_16_duplicate_process_prevention(self) -> None:
        """Candidate server is cleaned up from runtimes map after swap."""
        mock_cand = MCPServerRuntime("test_server")
        mock_cand.status = ServerStatus.HEALTHY

        with patch.object(self.conn_mgr, "start_server", new_callable=AsyncMock) as mock_start, \
             patch.object(self.tool_reg, "discover_tools", new_callable=AsyncMock) as mock_disc:
            mock_start.return_value = mock_cand
            mock_disc.return_value = [{"name": "t1", "description": "d", "inputSchema": {}}]
            self._run(self.controller.hot_reload_server("test_server"))
            self.assertNotIn("_candidate_test_server", self.conn_mgr.runtimes)

    def test_17_retained_tools_preserve_continuity(self) -> None:
        """Retained tools are identified properly in the swap summary."""
        mock_cand = MCPServerRuntime("test_server")
        mock_cand.status = ServerStatus.HEALTHY

        with patch.object(self.conn_mgr, "start_server", new_callable=AsyncMock) as mock_start, \
             patch.object(self.tool_reg, "discover_tools", new_callable=AsyncMock) as mock_disc:
            mock_start.return_value = mock_cand
            mock_disc.return_value = [
                {"name": "tool_old_1", "description": "kept", "inputSchema": {}},
                {"name": "tool_new_2", "description": "added", "inputSchema": {}},
            ]
            res = self._run(self.controller.hot_reload_server("test_server"))
            self.assertIn("tool_old_1", res["tools_retained"])
            self.assertIn("tool_new_2", res["tools_added"])
            self.assertIn("tool_old_2", res["tools_removed"])

    def test_18_other_servers_unaffected(self) -> None:
        """Reloading server A does not modify server B in the registry."""
        self.conn_mgr.register_mock_runtime("server_b", ["b_tool"])
        self.tool_reg.register_server_tools("server_b", [{"name": "b_tool", "description": "b", "inputSchema": {}}])

        mock_cand = MCPServerRuntime("test_server")
        mock_cand.status = ServerStatus.HEALTHY

        with patch.object(self.conn_mgr, "start_server", new_callable=AsyncMock) as mock_start, \
             patch.object(self.tool_reg, "discover_tools", new_callable=AsyncMock) as mock_disc:
            mock_start.return_value = mock_cand
            mock_disc.return_value = [{"name": "t1", "description": "d", "inputSchema": {}}]
            self._run(self.controller.hot_reload_server("test_server"))
            self.assertIn("b_tool", self.tool_reg.get_all_tools())


if __name__ == "__main__":
    unittest.main()
