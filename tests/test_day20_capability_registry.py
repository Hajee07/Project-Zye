"""
Unit Tests for Zye Day 20 Office Capability Registry.
Tests capability definitions, TOML loading, and per-application matrix queries.
"""

import unittest
from zye_office.capability_registry import OfficeCapabilityRegistry, CapabilityDef
from zye_office.models import OfficeAppType


class TestDay20CapabilityRegistry(unittest.TestCase):

    def setUp(self):
        self.registry = OfficeCapabilityRegistry()

    def test_default_capabilities_exist(self):
        all_caps = self.registry.get_all_capabilities()
        self.assertIn("com_bridge", all_caps)
        self.assertIn("document_inspection", all_caps)
        self.assertIn("pdf_export", all_caps)
        self.assertIn("ribbon_accelerator", all_caps)

    def test_is_supported_check(self):
        self.assertTrue(self.registry.is_supported(OfficeAppType.WORD, "document_inspection"))
        self.assertTrue(self.registry.is_supported(OfficeAppType.EXCEL, "formula_manipulation"))
        self.assertFalse(self.registry.is_supported(OfficeAppType.WORD, "formula_manipulation"))

    def test_list_capabilities_for_word(self):
        caps = self.registry.list_capabilities_for_app(OfficeAppType.WORD)
        cap_names = [c["name"] for c in caps]
        self.assertIn("com_bridge", cap_names)
        self.assertIn("document_inspection", cap_names)
        self.assertIn("pdf_export", cap_names)

    def test_list_capabilities_for_outlook(self):
        caps = self.registry.list_capabilities_for_app(OfficeAppType.OUTLOOK)
        cap_names = [c["name"] for c in caps]
        self.assertIn("email_drafting", cap_names)


if __name__ == "__main__":
    unittest.main()
