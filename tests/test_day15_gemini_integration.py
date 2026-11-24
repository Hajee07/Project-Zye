"""Day 15 Unit Tests — 7-Project Gemini Gateway & Model Controller."""
import unittest


class TestGeminiGatewayInstance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from gemini_gateway import ZyeGeminiGateway
        cls.gw = ZyeGeminiGateway.get_instance()

    def test_instance_created(self):
        self.assertIsNotNone(self.gw)

    def test_has_project_router(self):
        self.assertIsNotNone(self.gw.project_router)

    def test_has_model_controller(self):
        self.assertIsNotNone(self.gw.model_controller)

    def test_cross_project_fallback_disabled(self):
        self.assertFalse(
            self.gw.project_router.allow_cross_project_fallback,
            "Cross-project fallback must be strictly disabled"
        )


class TestGeminiHealthStatus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from gemini_gateway import ZyeGeminiGateway
        cls.gw = ZyeGeminiGateway.get_instance()
        cls.hs = cls.gw.get_health_status()

    def test_health_status_returns_dict(self):
        self.assertIsInstance(self.hs, dict)

    def test_has_model_id(self):
        self.assertIn("model_id", self.hs)
        self.assertIsInstance(self.hs["model_id"], str)
        self.assertGreater(len(self.hs["model_id"]), 0)

    def test_has_thinking_level(self):
        self.assertIn("thinking_level", self.hs)
        self.assertIsInstance(self.hs["thinking_level"], str)

    def test_has_healthy_slots(self):
        self.assertIn("healthy_slots", self.hs)

    def test_has_total_slots(self):
        self.assertIn("total_slots", self.hs)

    def test_total_slots_is_7(self):
        self.assertEqual(self.hs["total_slots"], 7)

    def test_model_contains_gemini(self):
        model_id = self.hs["model_id"]
        self.assertIn("gemini", model_id.lower(),
                      f"Model ID should contain 'gemini': {model_id}")


class TestModelController(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from gemini_gateway import ZyeGeminiGateway
        cls.mc = ZyeGeminiGateway.get_instance().model_controller

    def test_model_id_is_string(self):
        self.assertIsInstance(self.mc.model_id, str)

    def test_thinking_level_is_string(self):
        self.assertIsInstance(self.mc.thinking_level, str)

    def test_thinking_level_valid(self):
        self.assertIn(
            self.mc.thinking_level.upper(),
            ("LOW", "MEDIUM", "HIGH", "NONE", "AUTO"),
            f"Unexpected thinking level: {self.mc.thinking_level}"
        )


class TestProjectRouter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from gemini_gateway import ZyeGeminiGateway
        cls.pr = ZyeGeminiGateway.get_instance().project_router

    def test_cross_project_fallback_is_false(self):
        self.assertFalse(self.pr.allow_cross_project_fallback)

    def test_router_has_slots(self):
        # Router must know about 7 project slots
        all_slots = self.pr.get_all_slots() if hasattr(self.pr, "get_all_slots") else None
        if all_slots is not None:
            self.assertEqual(len(all_slots), 7)


if __name__ == "__main__":
    unittest.main()
