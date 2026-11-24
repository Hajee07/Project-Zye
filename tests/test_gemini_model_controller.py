"""
Unit tests for GeminiModelController — gemini-3.8-flash model configuration and thinking levels.
"""

import unittest
from gemini_model_controller import GeminiModelController, DEFAULT_MODEL_ID


class TestGeminiModelController(unittest.TestCase):
    def setUp(self):
        self.mc = GeminiModelController(db_path=":memory:", auto_init=True)

    def test_01_default_model_and_thinking(self):
        self.assertEqual(self.mc.model_id, "gemini-3.8-flash")
        self.assertEqual(self.mc.thinking_level, "LOW")
        self.assertEqual(self.mc.thinking_mode, "MANUAL")

    def test_02_set_thinking_levels(self):
        self.assertTrue(self.mc.set_thinking_level("MEDIUM"))
        self.assertEqual(self.mc.thinking_level, "MEDIUM")

        self.assertTrue(self.mc.set_thinking_level("HIGH"))
        self.assertEqual(self.mc.thinking_level, "HIGH")

        self.assertTrue(self.mc.set_thinking_level("LOW"))
        self.assertEqual(self.mc.thinking_level, "LOW")

    def test_03_invalid_thinking_level_rejected(self):
        self.assertFalse(self.mc.set_thinking_level("EXTREME"))
        self.assertEqual(self.mc.thinking_level, "LOW")

    def test_04_set_model_id_validation(self):
        self.assertTrue(self.mc.set_model_id("gemini-2.5-pro"))
        self.assertEqual(self.mc.model_id, "gemini-2.5-pro")

        # Must start with gemini-
        self.assertFalse(self.mc.set_model_id("gpt-4o"))
        self.assertEqual(self.mc.model_id, "gemini-2.5-pro")

    def test_05_auto_complexity_classification(self):
        # High keywords
        self.assertEqual(self.mc.classify_complexity("run premortem adversarial failure analysis"), "HIGH")
        self.assertEqual(self.mc.classify_complexity("security audit and vulnerability assessment"), "HIGH")

        # Medium keywords
        self.assertEqual(self.mc.classify_complexity("orchestrate mcp workflow and debug tools"), "MEDIUM")
        self.assertEqual(self.mc.classify_complexity("generate test suite for database migration"), "MEDIUM")

        # Low keywords
        self.assertEqual(self.mc.classify_complexity("hello zye, how are you today?"), "LOW")

    def test_06_thinking_config_generation(self):
        cfg = self.mc.get_thinking_config(override_level="HIGH")
        self.assertIsNotNone(cfg)
        self.assertEqual(str(cfg.thinking_level), "ThinkingLevel.HIGH")

    def test_07_persistence_to_db(self):
        self.mc.set_thinking_level("HIGH")
        # Instantiate second controller on same memory DB
        mc2 = GeminiModelController(db_path=":memory:", auto_init=False)
        mc2._db_path = self.mc._db_path
        mc2.load_from_db()
        self.assertEqual(mc2.thinking_level, "HIGH")


if __name__ == "__main__":
    unittest.main()
