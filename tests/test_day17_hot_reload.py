"""
Unit tests for Host Orchestrator Hot Reload & Server Recovery (Day 17).
Verifies live MCP session swap, server generation incrementing, active call draining,
tool registry refreshment, and non-idempotent recovery barriers.
"""

from __future__ import annotations

import unittest
from unittest.mock import patch

from main import ZyeMasterAgent, is_safe_to_replay


def run_coro(coro):
    """Step a coroutine to completion without requiring Windows network loopback sockets."""
    stack = [coro]
    res = None
    while stack:
        top = stack[-1]
        try:
            val = top.send(res)
            res = None
            if hasattr(val, "send"):
                stack.append(val)
        except StopIteration as exc:
            stack.pop()
            res = exc.value
    return res


class MockAsyncLock:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None


class TestDay17HotReload(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.agent = ZyeMasterAgent()
        cls.agent._get_server_lock = lambda name: MockAsyncLock()

    def test_untrusted_server_hot_reload_rejected(self) -> None:
        """Verify hot reload rejects servers not in MCP_SERVERS allowlist."""
        res = run_coro(self.agent.hot_reload_server("untrusted_rogue_server"))
        self.assertEqual(res.get("status"), "error")
        self.assertEqual(res.get("code"), "SERVER_NOT_CONFIGURED")

    def test_register_mock_session_and_tool_mapping(self) -> None:
        """Verify mock session registration establishes tools and server generations."""
        self.agent.register_mock_session("system_os", ["control_volume", "set_brightness"])
        self.assertIn("system_os", self.agent.sessions)
        self.assertEqual(self.agent.tool_to_server.get("control_volume"), "system_os")
        self.assertEqual(self.agent.tool_to_server.get("set_brightness"), "system_os")
        self.assertEqual(self.agent.server_generations.get("system_os"), 1)

    def test_hot_reload_generation_increment(self) -> None:
        """Verify hot-reloading a registered server increments generation ID."""
        self.agent.register_mock_session("windows_control", ["open_any_app"])
        initial_gen = self.agent.server_generations["windows_control"]

        async def _mock_start(server_name, stack):
            return ["open_any_app", "manage_window"]

        with patch.object(self.agent, "_start_mcp_session", side_effect=_mock_start):
            res = run_coro(self.agent.hot_reload_server("windows_control"))
            self.assertEqual(res.get("status"), "success")
            self.assertEqual(self.agent.server_generations["windows_control"], initial_gen + 1)
            self.assertEqual(self.agent.tool_to_server.get("manage_window"), "windows_control")

    def test_safe_to_replay_idempotency_barrier(self) -> None:
        """Verify safe replay rules prevent auto-replaying destructive operations."""
        self.assertFalse(is_safe_to_replay("terminate_process"))
        self.assertFalse(is_safe_to_replay("empty_recycle_bin"))
        self.assertFalse(is_safe_to_replay("shutdown_windows"))
        self.assertFalse(is_safe_to_replay("send_whatsapp_message"))
        self.assertFalse(is_safe_to_replay("patch_own_code"))

        self.assertTrue(is_safe_to_replay("list_running_processes"))
        self.assertTrue(is_safe_to_replay("get_battery_status"))
        self.assertTrue(is_safe_to_replay("preview_recycle_bin"))


if __name__ == "__main__":
    unittest.main()
