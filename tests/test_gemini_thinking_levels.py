"""
Unit tests for adaptive thinking levels (LOW, MEDIUM, HIGH) resolution and mode switching.
"""

import unittest
from gemini_model_controller import GeminiModelController


class TestGeminiThinkingLevels(unittest.TestCase):
    def setUp(self):
        self.mc = GeminiModelController(db_path=":memory:", auto_init=True)

    def test_01_manual_mode_fixed_level(self):
        self.mc.set_thinking_level("LOW", mode="MANUAL")
        # Even with high complexity prompt, manual mode keeps configured level
        res = self.mc.resolve_thinking_level(prompt="adversarial premortem security audit")
        self.assertEqual(res, "LOW")

    def test_02_auto_mode_adapts_to_prompt(self):
        self.mc.set_thinking_mode("AUTO")
        res_high = self.mc.resolve_thinking_level(prompt="adversarial premortem risk assessment")
        self.assertEqual(res_high, "HIGH")

        res_med = self.mc.resolve_thinking_level(prompt="orchestrate mcp workflow tools")
        self.assertEqual(res_med, "MEDIUM")

        res_low = self.mc.resolve_thinking_level(prompt="tell me a joke")
        self.assertEqual(res_low, "LOW")

    def test_03_workload_adaptive_thinking(self):
        self.mc.set_thinking_mode("AUTO")
        res1 = self.mc.resolve_thinking_level(workload="PREMORTEM")
        self.assertEqual(res1, "HIGH")

        res2 = self.mc.resolve_thinking_level(workload="MCP_ORCHESTRATOR")
        self.assertEqual(res2, "MEDIUM")

        res3 = self.mc.resolve_thinking_level(workload="INTERACTION")
        self.assertEqual(res3, "LOW")

    def test_04_explicit_override_has_highest_precedence(self):
        self.mc.set_thinking_level("LOW", mode="MANUAL")
        res = self.mc.resolve_thinking_level(
            prompt="tell me a joke",
            workload="INTERACTION",
            override_level="HIGH",
        )
        self.assertEqual(res, "HIGH")


if __name__ == "__main__":
    unittest.main()
