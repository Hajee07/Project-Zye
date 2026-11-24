#!/usr/bin/env python3
"""
ZYE AI — Day 12 Execution Routing Test Suite
============================================
Tests for zye_orchestrator.execution_router:
  1. Correct tool routing to registered server
  2. Unregistered tool returns TOOL_NOT_FOUND
  3. Stale registry call blocked (generation mismatch)
  4. Server unavailable returns SERVER_UNAVAILABLE
  5. Negative Brain audit triggered for file system tools
  6. Negative Brain audit triggered for system modifying tools
  7. Pre-mortem tools exempt from self-recursion
  8. Missing Negative Brain blocks protected operations
  9. Execution Gate confirmation token enforced
 10. Result parsing handles both JSON and raw text content
"""

from __future__ import annotations

import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from zye_orchestrator.execution_router import ZyeMCPExecutionRouter
from zye_orchestrator.server_runtime import MCPConnectionManager, MCPServerRuntime, ServerStatus
from zye_orchestrator.tool_registry import ZyeToolRegistry


class TestExecutionRouting(unittest.TestCase):
    """Test suite for MCP Tool Execution Router and Pre-Mortem Enforcement."""

    def setUp(self) -> None:
        self.conn_mgr = MCPConnectionManager()
        self.tool_reg = ZyeToolRegistry()

        # Register server
        self.runtime = self.conn_mgr.register_mock_runtime("fs_server", [
            "read_file", "patch_own_code", "delete_file", "run_negative_premortem_brain"
        ])
        self.tool_reg.register_server_tools("fs_server", [
            {"name": "read_file", "description": "Read file", "inputSchema": {}},
            {"name": "patch_own_code", "description": "Patch code", "inputSchema": {}},
            {"name": "delete_file", "description": "Delete file", "inputSchema": {}},
            {"name": "run_negative_premortem_brain", "description": "Pre-mortem audit", "inputSchema": {}},
        ])

        # Execution Gate Mock
        self.mock_gate = MagicMock()
        self.mock_gate.evaluate = AsyncMock(return_value={"allowed": True})

        self.router = ZyeMCPExecutionRouter(
            tool_registry=self.tool_reg,
            connection_manager=self.conn_mgr,
            execution_gate=self.mock_gate,
            config={
                "negative_premortem_required_for_file_system": True,
                "negative_premortem_required_for_system_tools": True,
                "block_if_premortem_unavailable": True,
            },
        )

    def _run(self, coro):
        return asyncio.run(coro)

    def test_01_correct_tool_routing(self) -> None:
        """Registered tool routes to correct server and returns result."""
        async def _test():
            self.runtime.session = AsyncMock()
            mock_res = type("CallRes", (), {"isError": False, "content": [type("Text", (), {"text": '{"data": "file_contents"}'})()]})()
            self.runtime.session.call_tool = AsyncMock(return_value=mock_res)

            res = await self.router.route_tool_call("read_file", {"path": "a.txt"})
            self.assertEqual(res["status"], "success")
            self.assertEqual(res["data"], "file_contents")

        self._run(_test())

    def test_02_unregistered_tool_not_found(self) -> None:
        """Calling an unregistered tool returns TOOL_NOT_FOUND."""
        res = self._run(self.router.route_tool_call("nonexistent_tool", {}))
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["code"], "TOOL_NOT_FOUND")

    def test_03_stale_registry_call_blocked(self) -> None:
        """Calling with an outdated registry generation is blocked."""
        res = self._run(self.router.route_tool_call("read_file", {}, registry_generation=999))
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["code"], "STALE_REGISTRY")

    def test_04_server_unavailable_blocked(self) -> None:
        """Calling when server status is FAILED returns SERVER_UNAVAILABLE."""
        self.runtime.status = ServerStatus.FAILED
        res = self._run(self.router.route_tool_call("read_file", {}))
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["code"], "SERVER_UNAVAILABLE")

    def test_05_premortem_enforced_for_filesystem_operations(self) -> None:
        """patch_own_code triggers the execution gate pre-mortem check."""
        async def _test():
            self.runtime.session = AsyncMock()
            self.runtime.session.call_tool = AsyncMock(return_value=type("Res", (), {"isError": False, "content": []})())
            await self.router.route_tool_call("patch_own_code", {"target": "main.py"})
            self.mock_gate.evaluate.assert_awaited()

        self._run(_test())

    def test_06_execution_gate_denial_blocks_operation(self) -> None:
        """When execution gate denies operation, routing returns BLOCKED_BY_EXECUTION_GATE."""
        async def _test():
            self.mock_gate.evaluate = AsyncMock(return_value={
                "allowed": False,
                "reason": "Negative pre-mortem identified CRITICAL failure risk",
                "approval_token": "token_12345",
                "risk_class": "DESTRUCTIVE",
                "requires_confirmation": True,
            })
            res = await self.router.route_tool_call("delete_file", {"target": "data.db"})
            self.assertEqual(res["status"], "BLOCKED_BY_EXECUTION_GATE")
            self.assertTrue(res["requires_confirmation"])
            self.assertEqual(res["approval_token"], "token_12345")

        self._run(_test())

    def test_07_premortem_tools_exempt_from_self_recursion(self) -> None:
        """Calling run_negative_premortem_brain does NOT invoke the pre-mortem gate on itself."""
        async def _test():
            self.runtime.session = AsyncMock()
            self.runtime.session.call_tool = AsyncMock(return_value=type("Res", (), {"isError": False, "content": []})())
            await self.router.route_tool_call("run_negative_premortem_brain", {"task": "do something"})
            self.mock_gate.evaluate.assert_not_awaited()

        self._run(_test())

    def test_08_missing_premortem_fails_closed(self) -> None:
        """When pre-mortem gate is unavailable and block_if_premortem_unavailable=True, protected operation is blocked."""
        router_no_gate = ZyeMCPExecutionRouter(
            tool_registry=self.tool_reg,
            connection_manager=self.conn_mgr,
            execution_gate=None,
            config={"block_if_premortem_unavailable": True},
        )
        res = self._run(router_no_gate.route_tool_call("delete_file", {}))
        self.assertEqual(res["status"], "BLOCKED_PREMORTEM_UNAVAILABLE")

    def test_09_tool_error_response_handling(self) -> None:
        """When MCP tool returns isError=True, result reflects error code."""
        async def _test():
            self.runtime.session = AsyncMock()
            mock_res = type("CallRes", (), {
                "isError": True,
                "content": [type("Text", (), {"text": "File not found on disk"})()]
            })()
            self.runtime.session.call_tool = AsyncMock(return_value=mock_res)

            res = await self.router.route_tool_call("read_file", {"path": "missing.txt"})
            self.assertEqual(res["status"], "error")
            self.assertEqual(res["code"], "TOOL_RETURNED_ERROR")
            self.assertIn("File not found", res["message"])

        self._run(_test())

    def test_10_raw_text_content_parsed_cleanly(self) -> None:
        """Non-JSON text content is returned in data field."""
        async def _test():
            self.runtime.session = AsyncMock()
            mock_res = type("CallRes", (), {
                "isError": False,
                "content": [type("Text", (), {"text": "Plain text log output here"})()]
            })()
            self.runtime.session.call_tool = AsyncMock(return_value=mock_res)

            res = await self.router.route_tool_call("read_file", {})
            self.assertEqual(res["status"], "success")
            self.assertEqual(res["data"], "Plain text log output here")

        self._run(_test())


if __name__ == "__main__":
    unittest.main()
