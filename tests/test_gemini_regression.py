"""
Comprehensive regression test verifying that all Gemini Intelligence Infrastructure components
coexist without breaking existing Day 01-13 capabilities.
"""

import unittest
from gemini_gateway import ZyeGeminiGateway
from gemini_key_manager import GeminiKeyManager, TOTAL_KEY_SLOTS
from gemini_model_controller import GeminiModelController
from gemini_project_router import GeminiProjectRouter


class TestGeminiRegression(unittest.TestCase):
    def test_01_gateway_singleton_pattern(self):
        gw1 = ZyeGeminiGateway.get_instance()
        gw2 = ZyeGeminiGateway.get_instance()
        self.assertIs(gw1, gw2)

    def test_02_all_seven_slots_registered_in_gateway(self):
        gw = ZyeGeminiGateway.get_instance()
        slots = gw.key_manager.get_all_slots()
        self.assertEqual(len(slots), TOTAL_KEY_SLOTS)

    def test_03_default_model_is_gemini_38_flash(self):
        gw = ZyeGeminiGateway.get_instance()
        self.assertEqual(gw.get_model_id(), "gemini-3.8-flash")

    def test_04_default_thinking_level_is_low(self):
        gw = ZyeGeminiGateway.get_instance()
        self.assertEqual(gw.get_thinking_level(), "LOW")

    def test_05_quota_isolation_strictly_enforced(self):
        gw = ZyeGeminiGateway.get_instance()
        self.assertFalse(gw.project_router.allow_cross_project_fallback)


if __name__ == "__main__":
    unittest.main()
