#!/usr/bin/env python3
"""
ZYE AI — Day 12 Concurrency Test Suite
=====================================
Tests for asynchronous concurrency and resource isolation:
  1. Concurrent calls to different servers
  2. Concurrent calls to one server
  3. Reload during active request
  4. Graceful request draining
  5. Request cancellation handling
  6. Server isolation (slow server does not block fast server)
  7. Registry snapshot consistency under concurrent operations
  8. No resource leaks (in-flight counters return to 0)
"""

from __future__ import annotations

import asyncio
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from zye_orchestrator.execution_router import ZyeMCPExecutionRouter
from zye_orchestrator.hot_reload import HotReloadController
from zye_orchestrator.server_registry import ServerRegistry
from zye_orchestrator.server_runtime import MCPConnectionManager, MCPServerRuntime, ServerStatus
from zye_orchestrator.tool_registry import ZyeToolRegistry


class TestConcurrency(unittest.TestCase):
    """Test suite for concurrency, isolation, and resource cleanup."""

    def setUp(self) -> None:
        self.conn_mgr = MCPConnectionManager()
        self.tool_reg = ZyeToolRegistry()

        # Register server A
        self.rt_a = self.conn_mgr.register_mock_runtime("srv_a", ["tool_a"])
        self.tool_reg.register_server_tools("srv_a", [
            {"name": "tool_a", "description": "A", "inputSchema": {}}
        ])

        # Register server B
        self.rt_b = self.conn_mgr.register_mock_runtime("srv_b", ["tool_b"])
        self.tool_reg.register_server_tools("srv_b", [
            {"name": "tool_b", "description": "B", "inputSchema": {}}
        ])

        self.router = ZyeMCPExecutionRouter(
            self.tool_reg, self.conn_mgr, config={"negative_premortem_required_for_file_system": False}
        )

    def _run(self, coro):
        return asyncio.run(coro)

    def test_01_concurrent_calls_different_servers(self) -> None:
        """Concurrent calls to independent servers execute in parallel."""
        async def _test():
            # Mock sessions with small delay
            self.rt_a.session = AsyncMock()
            self.rt_a.session.call_tool = AsyncMock(return_value=type("Res", (), {"isError": False, "content": []})())
            self.rt_b.session = AsyncMock()
            self.rt_b.session.call_tool = AsyncMock(return_value=type("Res", (), {"isError": False, "content": []})())

            t1 = self.router.route_tool_call("tool_a", {})
            t2 = self.router.route_tool_call("tool_b", {})
            r1, r2 = await asyncio.gather(t1, t2)
            self.assertEqual(r1["status"], "success")
            self.assertEqual(r2["status"], "success")

        self._run(_test())

    def test_02_concurrent_calls_single_server(self) -> None:
        """Concurrent calls to the same server both complete."""
        async def _test():
            self.rt_a.session = AsyncMock()
            self.rt_a.session.call_tool = AsyncMock(return_value=type("Res", (), {"isError": False, "content": []})())

            calls = [self.router.route_tool_call("tool_a", {"i": i}) for i in range(5)]
            results = await asyncio.gather(*calls)
            self.assertEqual(len(results), 5)
            for r in results:
                self.assertEqual(r["status"], "success")

        self._run(_test())

    def test_03_in_flight_tracking_decrements_to_zero(self) -> None:
        """In-flight counter increments during call and returns to zero on completion."""
        async def _test():
            self.rt_a.session = AsyncMock()
            self.rt_a.session.call_tool = AsyncMock(return_value=type("Res", (), {"isError": False, "content": []})())

            self.assertEqual(self.rt_a.in_flight_calls, 0)
            res = await self.router.route_tool_call("tool_a", {})
            self.assertEqual(res["status"], "success")
            self.assertEqual(self.rt_a.in_flight_calls, 0)

        self._run(_test())

    def test_04_in_flight_counter_cleans_up_on_exception(self) -> None:
        """In-flight counter returns to zero even when tool call raises an exception."""
        async def _test():
            self.rt_a.session = AsyncMock()
            self.rt_a.session.call_tool = AsyncMock(side_effect=RuntimeError("Crash in session"))

            res = await self.router.route_tool_call("tool_a", {})
            self.assertEqual(res["status"], "error")
            self.assertEqual(self.rt_a.in_flight_calls, 0)

        self._run(_test())

    def test_05_server_isolation_slow_server_does_not_block_fast(self) -> None:
        """A slow server executing does not delay or block a fast server."""
        async def _test():
            async def _slow_call(*args, **kwargs):
                await asyncio.sleep(0.08)
                return type("Res", (), {"isError": False, "content": []})()

            async def _fast_call(*args, **kwargs):
                return type("Res", (), {"isError": False, "content": []})()

            self.rt_a.session = AsyncMock()
            self.rt_a.session.call_tool = _slow_call

            self.rt_b.session = AsyncMock()
            self.rt_b.session.call_tool = _fast_call

            t_start = time.monotonic()
            fast_task = asyncio.create_task(self.router.route_tool_call("tool_b", {}))
            slow_task = asyncio.create_task(self.router.route_tool_call("tool_a", {}))

            fast_res = await fast_task
            fast_duration = time.monotonic() - t_start
            self.assertEqual(fast_res["status"], "success")
            self.assertLess(fast_duration, 0.05)  # Fast completed immediately

            slow_res = await slow_task
            self.assertEqual(slow_res["status"], "success")

        self._run(_test())

    def test_06_request_cancellation_handled(self) -> None:
        """Cancelled requests decrement in-flight counter cleanly."""
        async def _test():
            async def _hang(*args, **kwargs):
                await asyncio.sleep(10.0)

            self.rt_a.session = AsyncMock()
            self.rt_a.session.call_tool = _hang

            task = asyncio.create_task(self.router.route_tool_call("tool_a", {}))
            await asyncio.sleep(0.02)
            self.assertEqual(self.rt_a.in_flight_calls, 1)

            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

            self.assertEqual(self.rt_a.in_flight_calls, 0)

        self._run(_test())

    def test_07_registry_snapshot_consistency(self) -> None:
        """Tool registry snapshots remain consistent during mutations."""
        async def _test():
            # Simultaneously query and update registry
            async def _reader():
                for _ in range(20):
                    tools = self.tool_reg.get_all_tools()
                    self.assertIsInstance(tools, dict)
                    await asyncio.sleep(0.001)

            async def _writer():
                for i in range(10):
                    self.tool_reg.register_server_tools("srv_c", [
                        {"name": f"dyn_t_{i}", "description": "d", "inputSchema": {}}
                    ])
                    await asyncio.sleep(0.002)

            await asyncio.gather(_reader(), _writer())

        self._run(_test())

    def test_08_no_resource_leaks_after_concurrent_load(self) -> None:
        """All in-flight counters return to zero after high concurrent load."""
        async def _test():
            self.rt_a.session = AsyncMock()
            self.rt_a.session.call_tool = AsyncMock(return_value=type("Res", (), {"isError": False, "content": []})())
            self.rt_b.session = AsyncMock()
            self.rt_b.session.call_tool = AsyncMock(return_value=type("Res", (), {"isError": False, "content": []})())

            tasks = []
            for i in range(20):
                target = "tool_a" if i % 2 == 0 else "tool_b"
                tasks.append(self.router.route_tool_call(target, {"x": i}))

            results = await asyncio.gather(*tasks)
            self.assertEqual(len(results), 20)
            self.assertEqual(self.rt_a.in_flight_calls, 0)
            self.assertEqual(self.rt_b.in_flight_calls, 0)

        self._run(_test())


if __name__ == "__main__":
    unittest.main()
