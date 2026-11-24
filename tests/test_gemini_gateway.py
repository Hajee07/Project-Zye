"""
Unit tests for ZyeGeminiGateway — Central Gemini LLM entry point and execution pipeline.
Each test creates a fully isolated gateway instance with fresh subcomponents and unique temp DB.
"""

import os
import tempfile
import unittest
from unittest.mock import MagicMock

from gemini_error_handler import GeminiErrorHandler
from gemini_gateway import ZyeGeminiGateway
from gemini_key_manager import GeminiKeyManager
from gemini_model_controller import GeminiModelController
from gemini_project_router import GeminiProjectRouter
from gemini_task_decomposer import GeminiTaskDecomposer
from gemini_token_optimizer import GeminiTokenOptimizer
from gemini_usage_tracker import GeminiUsageTracker


class TestGeminiGateway(unittest.TestCase):
    def setUp(self):
        # Use a unique temp file DB per test to avoid shared :memory: contamination
        self._tmp_db_fd, self._tmp_db_path = tempfile.mkstemp(suffix=".sqlite", prefix="zye_test_gw_")
        os.close(self._tmp_db_fd)

        # Fresh key manager with no auto-load
        self.km = GeminiKeyManager(db_path=self._tmp_db_path, auto_load=False)
        slot1 = self.km.get_slot(1)
        slot1.auth_status = "CONFIGURED"
        slot1.key_health = "HEALTHY"
        slot1.enabled = True
        slot1.api_key = "AIzaSyDummyKeyForTestingPurposesOnly123"

        self.mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Mocked Gemini Response Text"
        mock_response.function_calls = None
        mock_response.candidates = []
        mock_response.usage_metadata = MagicMock(
            prompt_token_count=15,
            candidates_token_count=25,
            total_token_count=40,
            thinking_token_count=0,
            cached_content_token_count=0,
        )
        self.mock_client.models.generate_content.return_value = mock_response
        slot1.client = self.mock_client

        # Fresh model controller with explicit defaults (no DB load contamination)
        self.model_controller = GeminiModelController(db_path=self._tmp_db_path, auto_init=True)
        # Force defaults in case DB was pre-populated
        self.model_controller._model_id = "gemini-3.8-flash"
        self.model_controller._thinking_level = "LOW"

        self.gateway = ZyeGeminiGateway(
            db_path=self._tmp_db_path,
            key_manager=self.km,
            model_controller=self.model_controller,
        )

    def tearDown(self):
        # Clean up temp DB
        try:
            os.unlink(self._tmp_db_path)
        except Exception:
            pass

    def test_01_local_first_triage(self):
        res = self.gateway.generate_response("what is 10 + 20")
        self.assertEqual(res["status"], "LOCAL")
        self.assertEqual(res["text"], "30")
        self.assertEqual(res["tokens_used"], 0)
        # Verify client was not called
        self.mock_client.models.generate_content.assert_not_called()

    def test_02_generate_response_successful(self):
        res = self.gateway.generate_response(prompt="Explain quantum entanglement", workload="GENERAL")
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["text"], "Mocked Gemini Response Text")
        self.assertEqual(res["slot_id"], 1)
        self.assertEqual(res["tokens_used"], 40)
        self.mock_client.models.generate_content.assert_called_once()

    def test_03_response_caching(self):
        # First call triggers API
        res1 = self.gateway.generate_response(prompt="Static encyclopedic question", workload="GENERAL")
        self.assertEqual(res1["status"], "SUCCESS")

        # Second identical call hits cache
        res2 = self.gateway.generate_response(prompt="Static encyclopedic question", workload="GENERAL")
        self.assertEqual(res2["status"], "CACHED")
        self.assertEqual(res2["text"], "Mocked Gemini Response Text")
        self.assertEqual(self.mock_client.models.generate_content.call_count, 1)

    def test_04_rate_limited_slot_returns_error(self):
        self.gateway.project_router.mark_rate_limited(1, retry_after_seconds=60.0)
        res = self.gateway.generate_response(prompt="Any query", workload="GENERAL")
        self.assertEqual(res["status"], "RATE_LIMITED")

    def test_05_classify_content_helper(self):
        self.mock_client.models.generate_content.return_value.text = "TECHNICAL"
        self.mock_client.models.generate_content.return_value.candidates = []
        category = self.gateway.classify_content("Bug report", ["TECHNICAL", "BILLING", "GENERAL"])
        self.assertEqual(category, "TECHNICAL")

    def test_06_summarize_content_helper(self):
        self.mock_client.models.generate_content.return_value.text = "Short summary."
        self.mock_client.models.generate_content.return_value.candidates = []
        summary = self.gateway.summarize_content("Long document content here...")
        self.assertEqual(summary, "Short summary.")

    def test_07_get_health_status(self):
        health = self.gateway.get_health_status()
        self.assertEqual(health["total_slots"], 7)
        self.assertEqual(health["model_id"], "gemini-3.8-flash")
        self.assertEqual(health["thinking_level"], "LOW")


if __name__ == "__main__":
    unittest.main()
