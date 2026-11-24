"""Day 15 Unit Tests — ZyeMasterAgent Orchestrator Subsystems."""
import asyncio
import importlib
import unittest


class TestZyeMasterAgentAttributes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.main_mod = importlib.import_module("main")
        cls.ZyeMasterAgent = cls.main_mod.ZyeMasterAgent
        cls.agent = cls.ZyeMasterAgent(root="d:/Zye")

    def test_agent_created(self):
        self.assertIsNotNone(self.agent)

    # --- Core Day 12 attributes ---
    def test_has_registry(self):
        self.assertIsNotNone(self.agent.registry)

    def test_has_conn_mgr(self):
        self.assertIsNotNone(self.agent.conn_mgr)

    def test_has_tool_registry(self):
        self.assertIsNotNone(self.agent.tool_registry)

    def test_has_recovery_ctrl(self):
        self.assertIsNotNone(self.agent.recovery_ctrl)

    def test_has_hot_reload_ctrl(self):
        self.assertIsNotNone(self.agent.hot_reload_ctrl)

    def test_has_execution_router(self):
        self.assertIsNotNone(self.agent.execution_router)

    def test_has_health_monitor(self):
        self.assertIsNotNone(self.agent.health_monitor)

    # --- Day 15 new attributes ---
    def test_has_session_manager(self):
        self.assertIsNotNone(self.agent.session_manager)

    def test_has_shutdown_event(self):
        self.assertIsInstance(self.agent.shutdown_event, asyncio.Event)

    def test_has_audit_logger(self):
        self.assertIsNotNone(self.agent.audit_logger)

    def test_has_safety_gateway(self):
        self.assertIsNotNone(self.agent.safety_gateway)

    def test_has_tool_dispatcher(self):
        self.assertIsNotNone(self.agent.tool_dispatcher)

    def test_has_background_task_manager(self):
        self.assertIsNotNone(self.agent.background_task_manager)


class TestZyeVoiceOrchestratorAlias(unittest.TestCase):
    def test_alias_exists_in_main_module(self):
        main_mod = importlib.import_module("main")
        self.assertTrue(
            hasattr(main_mod, "ZyeVoiceOrchestrator"),
            "ZyeVoiceOrchestrator alias must exist in main.py"
        )

    def test_alias_is_class(self):
        main_mod = importlib.import_module("main")
        alias = main_mod.ZyeVoiceOrchestrator
        self.assertTrue(callable(alias) or isinstance(alias, type))


class TestShutdownEvent(unittest.TestCase):
    def test_shutdown_event_not_set_initially(self):
        main_mod = importlib.import_module("main")
        agent = main_mod.ZyeMasterAgent(root="d:/Zye")
        self.assertFalse(agent.shutdown_event.is_set())

    def test_shutdown_event_can_be_set(self):
        main_mod = importlib.import_module("main")
        agent = main_mod.ZyeMasterAgent(root="d:/Zye")
        agent.shutdown_event.set()
        self.assertTrue(agent.shutdown_event.is_set())


class TestSessionManagerType(unittest.TestCase):
    def test_session_manager_is_correct_type(self):
        from zye_orchestrator.session_manager import MCPSessionManager
        main_mod = importlib.import_module("main")
        agent = main_mod.ZyeMasterAgent(root="d:/Zye")
        self.assertIsInstance(agent.session_manager, MCPSessionManager)


if __name__ == "__main__":
    unittest.main()
