"""
Unit Tests for Zye Day 20 Office Integration Health.
Tests diagnostic checks across all 7 Office subsystems and status reporting.
"""

import unittest
from zye_office.integration_health import OfficeIntegrationHealth
from zye_office.com_worker import STACOMWorker


class TestDay20IntegrationHealth(unittest.TestCase):

    def setUp(self):
        self.health = OfficeIntegrationHealth(worker=STACOMWorker.get_instance())

    def test_run_health_check(self):
        res = self.health.run_health_check()
        self.assertIn("status", res)
        self.assertEqual(res["status"], "healthy")
        self.assertIn("checks", res)

        checks = res["checks"]
        self.assertIn("com_subsystem", checks)
        self.assertEqual(checks["com_subsystem"]["status"], "PASS")

        self.assertIn("sta_worker", checks)
        self.assertEqual(checks["sta_worker"]["status"], "PASS")

        self.assertIn("application_discovery", checks)
        self.assertEqual(checks["application_discovery"]["status"], "PASS")

        self.assertIn("session_manager", checks)
        self.assertEqual(checks["session_manager"]["status"], "PASS")

        self.assertIn("operation_registry", checks)
        self.assertEqual(checks["operation_registry"]["status"], "PASS")

        self.assertIn("capability_registry", checks)
        self.assertEqual(checks["capability_registry"]["status"], "PASS")

        self.assertIn("export_subsystem", checks)
        self.assertEqual(checks["export_subsystem"]["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
