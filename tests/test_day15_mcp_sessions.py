"""Day 15 Unit Tests — MCP Session Manager & Subprocess Lifecycle."""
import unittest

from zye_orchestrator.session_manager import MCPSessionManager, MCPSessionState
from zye_orchestrator.server_runtime import MCPConnectionManager


class TestMCPSessionState(unittest.TestCase):
    def test_has_stopped_state(self):
        self.assertIn("STOPPED", [s.value for s in MCPSessionState])

    def test_has_starting_state(self):
        self.assertIn("STARTING", [s.value for s in MCPSessionState])

    def test_has_healthy_state(self):
        self.assertIn("HEALTHY", [s.value for s in MCPSessionState])

    def test_has_degraded_state(self):
        self.assertIn("DEGRADED", [s.value for s in MCPSessionState])

    def test_has_failed_state(self):
        self.assertIn("FAILED", [s.value for s in MCPSessionState])

    def test_minimum_five_states(self):
        self.assertGreaterEqual(len(list(MCPSessionState)), 5)

    def test_all_expected_states(self):
        states = {s.value for s in MCPSessionState}
        expected = {"STOPPED", "STARTING", "HEALTHY", "DEGRADED", "FAILED"}
        self.assertTrue(expected.issubset(states), f"Missing states: {expected - states}")


class TestMCPSessionManagerInit(unittest.TestCase):
    def test_creates_instance_no_args(self):
        sm = MCPSessionManager()
        self.assertIsNotNone(sm)

    def test_creates_instance_with_connection_manager(self):
        cm = MCPConnectionManager()
        sm = MCPSessionManager(cm)
        self.assertIsNotNone(sm)

    def test_connection_manager_property(self):
        cm = MCPConnectionManager()
        sm = MCPSessionManager(cm)
        self.assertIs(sm.connection_manager, cm)

    def test_runtimes_property_returns_dict(self):
        sm = MCPSessionManager()
        self.assertIsInstance(sm.runtimes, dict)

    def test_runtimes_empty_on_fresh_manager(self):
        sm = MCPSessionManager()
        self.assertEqual(len(sm.runtimes), 0)

    def test_not_shutting_down_initially(self):
        sm = MCPSessionManager()
        self.assertFalse(sm._shutting_down)


class TestSessionState(unittest.TestCase):
    def test_unknown_server_returns_stopped(self):
        sm = MCPSessionManager()
        state = sm.get_session_state("nonexistent_server_xyz")
        self.assertEqual(state, MCPSessionState.STOPPED)

    def test_get_session_state_no_crash(self):
        sm = MCPSessionManager()
        try:
            state = sm.get_session_state("any_server")
            self.assertIsInstance(state, MCPSessionState)
        except Exception as e:
            self.fail(f"get_session_state raised unexpectedly: {e}")


class TestSessionDiagnostics(unittest.TestCase):
    def test_get_all_session_diagnostics_returns_list(self):
        sm = MCPSessionManager()
        diag = sm.get_all_session_diagnostics()
        self.assertIsInstance(diag, list)

    def test_get_all_session_diagnostics_empty_on_fresh(self):
        sm = MCPSessionManager()
        diag = sm.get_all_session_diagnostics()
        self.assertEqual(len(diag), 0)

    def test_session_locks_dict_exists(self):
        sm = MCPSessionManager()
        self.assertIsInstance(sm._session_locks, dict)


if __name__ == "__main__":
    unittest.main()
