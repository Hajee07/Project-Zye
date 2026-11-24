"""Day 15 Unit Tests — Live MCP Hot Reload Engine."""
import pathlib
import unittest

from zye_orchestrator.hot_reload import HotReloadController
from zye_orchestrator.server_registry import ServerRegistry
from zye_orchestrator.server_runtime import MCPConnectionManager
from zye_orchestrator.tool_registry import ZyeToolRegistry

ROOT = pathlib.Path("d:/Zye")


class TestHotReloadControllerInit(unittest.TestCase):
    def _make_hrc(self):
        return HotReloadController(
            server_registry=ServerRegistry(ROOT),
            connection_manager=MCPConnectionManager(),
            tool_registry=ZyeToolRegistry(),
        )

    def test_creates_instance(self):
        hrc = self._make_hrc()
        self.assertIsNotNone(hrc)

    def test_drain_timeout_is_numeric(self):
        hrc = self._make_hrc()
        self.assertIsInstance(hrc._drain_timeout, float)
        self.assertGreater(hrc._drain_timeout, 0.0)

    def test_drain_timeout_default_15(self):
        hrc = self._make_hrc()
        self.assertAlmostEqual(hrc._drain_timeout, 15.0)

    def test_staged_preferred_is_bool(self):
        hrc = self._make_hrc()
        self.assertIsInstance(hrc._staged_preferred, bool)

    def test_staged_preferred_default_true(self):
        hrc = self._make_hrc()
        self.assertTrue(hrc._staged_preferred)

    def test_reload_history_is_list(self):
        hrc = self._make_hrc()
        self.assertIsInstance(hrc._reload_history, list)

    def test_reload_history_initially_empty(self):
        hrc = self._make_hrc()
        self.assertEqual(len(hrc._reload_history), 0)

    def test_reload_history_property(self):
        hrc = self._make_hrc()
        h = hrc.reload_history
        self.assertIsInstance(h, list)


class TestHotReloadControllerCustomConfig(unittest.TestCase):
    def test_custom_drain_timeout(self):
        hrc = HotReloadController(
            server_registry=ServerRegistry(ROOT),
            connection_manager=MCPConnectionManager(),
            tool_registry=ZyeToolRegistry(),
            config={"reload_drain_timeout_seconds": 30.0},
        )
        self.assertAlmostEqual(hrc._drain_timeout, 30.0)

    def test_custom_staged_preferred_false(self):
        hrc = HotReloadController(
            server_registry=ServerRegistry(ROOT),
            connection_manager=MCPConnectionManager(),
            tool_registry=ZyeToolRegistry(),
            config={"staged_reload_preferred": False},
        )
        self.assertFalse(hrc._staged_preferred)


class TestHotReloadInvalidServer(unittest.TestCase):
    def test_reload_history_max_50(self):
        """Reload history should not grow beyond 50 entries."""
        hrc = HotReloadController(
            server_registry=ServerRegistry(ROOT),
            connection_manager=MCPConnectionManager(),
            tool_registry=ZyeToolRegistry(),
        )
        # Manually inject 60 entries
        for i in range(60):
            hrc._reload_history.append({"server": f"test_{i}", "status": "ok"})
        # Trigger trim by calling _record_history
        hrc._record_history("extra_server", {"status": "ok"})
        self.assertLessEqual(len(hrc._reload_history), 50)


if __name__ == "__main__":
    unittest.main()
