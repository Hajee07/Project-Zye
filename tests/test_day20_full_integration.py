"""
Unit Tests for Zye Day 20 Full Integration.
Verifies end-to-end integration across all Day 20 Office Live COM Automation components.
"""

import unittest
import office_master_mcp
from zye_office import (
    OfficeAppRegistry,
    STACOMWorker,
    OfficeSessionManager,
    OfficeStateInspector,
    OfficeCapabilityRegistry,
    OfficeOperationRegistry,
    OfficeIntegrationHealth,
)


class TestDay20FullIntegration(unittest.TestCase):

    def test_full_office_subsystem_initialization(self):
        worker = STACOMWorker.get_instance()
        self.assertTrue(worker.is_alive())

        reg = OfficeAppRegistry()
        apps = reg.get_registered_office_apps()
        self.assertEqual(len(apps), 4)

        sm = OfficeSessionManager()
        self.assertIsNotNone(sm)

        si = OfficeStateInspector()
        self.assertIsNotNone(si)

        creg = OfficeCapabilityRegistry()
        self.assertGreaterEqual(len(creg.get_all_capabilities()), 8)

        oreg = OfficeOperationRegistry()
        self.assertGreaterEqual(len(oreg.list_operations()), 14)

        health = OfficeIntegrationHealth(worker=worker, registry=reg, session_manager=sm, op_registry=oreg, cap_registry=creg)
        h_res = health.run_health_check()
        self.assertEqual(h_res["status"], "healthy")

    def test_mcp_and_doctor_alignment(self):
        # All MCP tools registered and callable
        tools = list(office_master_mcp.mcp._tool_manager._tools.keys() if hasattr(office_master_mcp.mcp, '_tool_manager') else office_master_mcp.mcp._tools.keys())
        office_tools = [t for t in tools if t.startswith("office_")]
        self.assertEqual(len(office_tools), 12)

        inst = office_master_mcp.office_check_installation()
        self.assertEqual(inst["status"], "SUCCESS")
        self.assertEqual(inst["installed_count"], 4)


if __name__ == "__main__":
    unittest.main()
