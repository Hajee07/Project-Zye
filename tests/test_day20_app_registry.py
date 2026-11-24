"""
Unit Tests for Zye Day 20 Office Application Registry.
Tests discovery of Word, Excel, PowerPoint, Outlook, ProgIDs, and capabilities.
"""

import unittest
from zye_office.app_registry import OfficeAppRegistry, OFFICE_APP_REGISTRY
from zye_office.models import OfficeAppType, OfficeAppInfo


class TestDay20AppRegistry(unittest.TestCase):

    def setUp(self):
        self.registry = OfficeAppRegistry()

    def test_supported_apps(self):
        apps = self.registry.get_supported_office_apps()
        self.assertIn("word", apps)
        self.assertIn("excel", apps)
        self.assertIn("powerpoint", apps)
        self.assertIn("outlook", apps)

    def test_prog_id_resolution(self):
        self.assertEqual(self.registry.get_office_prog_id("word"), "Word.Application")
        self.assertEqual(self.registry.get_office_prog_id("excel"), "Excel.Application")
        self.assertEqual(self.registry.get_office_prog_id("powerpoint"), "PowerPoint.Application")
        self.assertEqual(self.registry.get_office_prog_id("outlook"), "Outlook.Application")

    def test_registered_apps_discovery(self):
        apps = self.registry.get_registered_office_apps()
        self.assertEqual(len(apps), 4)
        for app in apps:
            self.assertIsInstance(app, OfficeAppInfo)
            self.assertTrue(app.is_installed)
            self.assertTrue(app.is_registered)

    def test_discover_all_dict(self):
        d = self.registry.discover_all()
        self.assertIn(OfficeAppType.WORD, d)
        self.assertIn(OfficeAppType.EXCEL, d)
        self.assertIn(OfficeAppType.POWERPOINT, d)
        self.assertIn(OfficeAppType.OUTLOOK, d)

    def test_capabilities_query(self):
        word_caps = self.registry.get_office_capabilities("word")
        self.assertIn("insert_text", word_caps)
        self.assertIn("export_pdf", word_caps)

        excel_caps = self.registry.get_office_capabilities("excel")
        self.assertIn("set_cell_value", excel_caps)

    def test_unknown_app(self):
        info = self.registry.check_office_installation("unknown_tool")
        self.assertFalse(info.is_installed)
        self.assertIn("not recognized", info.error)


if __name__ == "__main__":
    unittest.main()
