"""Day 15 Unit Tests — Full Day 01-14 Regression Suite.
Confirms that adding Day 15 hasn't broken any prior Day's imports or key APIs.
"""
import importlib
import unittest


class TestCoreModuleImports(unittest.TestCase):
    """Every core module must import without error."""

    def _import(self, module_name):
        try:
            mod = importlib.import_module(module_name)
            self.assertIsNotNone(mod)
        except ImportError as e:
            self.fail(f"Failed to import '{module_name}': {e}")

    def test_import_main(self):
        self._import("main")

    def test_import_autonomous_decision_mcp(self):
        self._import("autonomous_decision_mcp")

    def test_import_personal_assistant_mcp(self):
        self._import("personal_assistant_mcp")

    def test_import_self_repair_mcp(self):
        self._import("self_repair_mcp")

    def test_import_zye_guard(self):
        self._import("zye_guard")

    def test_import_gemini_gateway(self):
        self._import("gemini_gateway")

    def test_import_zye_orchestrator(self):
        self._import("zye_orchestrator")

    def test_import_zye_autonomy(self):
        self._import("zye_autonomy")

    def test_import_zye_intelligence(self):
        self._import("zye_intelligence")

    def test_import_zye_personal_assistant(self):
        self._import("zye_personal_assistant")

    def test_import_zye_brain(self):
        self._import("zye_brain")


class TestDay12AttributesPreserved(unittest.TestCase):
    """ZyeMasterAgent must retain all Day 12 core attributes."""

    @classmethod
    def setUpClass(cls):
        main_mod = importlib.import_module("main")
        cls.agent = main_mod.ZyeMasterAgent(root="d:/Zye")

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


class TestDay15AttributesPreserved(unittest.TestCase):
    """ZyeMasterAgent must have all new Day 15 attributes."""

    @classmethod
    def setUpClass(cls):
        main_mod = importlib.import_module("main")
        cls.agent = main_mod.ZyeMasterAgent(root="d:/Zye")

    def test_has_session_manager(self):
        self.assertIsNotNone(self.agent.session_manager)

    def test_has_safety_gateway(self):
        self.assertIsNotNone(self.agent.safety_gateway)

    def test_has_tool_dispatcher(self):
        self.assertIsNotNone(self.agent.tool_dispatcher)

    def test_has_audit_logger(self):
        self.assertIsNotNone(self.agent.audit_logger)

    def test_has_background_task_manager(self):
        self.assertIsNotNone(self.agent.background_task_manager)


class TestVoiceOrchestratorAlias(unittest.TestCase):
    def test_alias_exists(self):
        main_mod = importlib.import_module("main")
        self.assertTrue(
            hasattr(main_mod, "ZyeVoiceOrchestrator"),
            "ZyeVoiceOrchestrator alias must still exist in main.py"
        )


class TestMCPServerRegistration(unittest.TestCase):
    """personal_assistant server must still be registered."""

    def test_personal_assistant_in_mcp_servers(self):
        main_mod = importlib.import_module("main")
        mcp_servers = main_mod.MCP_SERVERS
        self.assertIn("personal_assistant", mcp_servers,
                      "personal_assistant MCP server must remain registered")

    def test_self_repair_in_mcp_servers(self):
        main_mod = importlib.import_module("main")
        mcp_servers = main_mod.MCP_SERVERS
        self.assertIn("self_repair", mcp_servers)

    def test_autonomous_decision_in_mcp_servers(self):
        main_mod = importlib.import_module("main")
        mcp_servers = main_mod.MCP_SERVERS
        self.assertIn("autonomous_decision", mcp_servers)


class TestDay13ModulesIntact(unittest.TestCase):
    """Day 13 Negative Brain and Mission Controller must still work."""

    def test_negative_premortem_importable(self):
        from zye_autonomy.premortem_engine import ZyeNegativePreMortem, _generate_offline_fmea
        self.assertIsNotNone(ZyeNegativePreMortem)
        self.assertTrue(callable(_generate_offline_fmea))

    def test_mission_controller_importable(self):
        from zye_autonomy.mission_controller import ZyeMissionController, MISSION_PROFILES
        self.assertEqual(len(MISSION_PROFILES), 5)

    def test_decision_matrix_importable(self):
        from zye_autonomy.decision_matrix import ZyeDecisionMatrix, PRIORITY_WEIGHTS
        self.assertEqual(len(PRIORITY_WEIGHTS), 4)

    def test_watchdog_importable(self):
        from zye_autonomy.system_monitor import ZyeAutonomousWatchdog
        self.assertIsNotNone(ZyeAutonomousWatchdog)

    def test_emergency_reflex_importable(self):
        from zye_autonomy.emergency_reflexes import ZyeEmergencyReflex
        self.assertIsNotNone(ZyeEmergencyReflex)


class TestDay14PersonalAssistantIntact(unittest.TestCase):
    """Day 14 Personal Assistant module must still import."""

    def test_personal_assistant_imports(self):
        try:
            mod = importlib.import_module("personal_assistant_mcp")
            self.assertIsNotNone(mod)
        except ImportError as e:
            self.fail(f"personal_assistant_mcp failed to import: {e}")

    def test_zye_personal_assistant_package(self):
        try:
            mod = importlib.import_module("zye_personal_assistant")
            self.assertIsNotNone(mod)
        except ImportError as e:
            self.fail(f"zye_personal_assistant package failed: {e}")


if __name__ == "__main__":
    unittest.main()
