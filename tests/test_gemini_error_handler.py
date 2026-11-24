"""
Unit tests for GeminiErrorHandler — Status code parsing, exponential backoff with jitter, and error sanitization.
"""

import unittest
from gemini_error_handler import GeminiErrorHandler


class TestGeminiErrorHandler(unittest.TestCase):
    def setUp(self):
        self.handler = GeminiErrorHandler(db_path=":memory:", max_retries=3, base_backoff_seconds=1.0)

    def test_01_parse_status_code_from_message(self):
        self.assertEqual(self.handler.parse_status_code(Exception("429 Resource has been exhausted")), 429)
        self.assertEqual(self.handler.parse_status_code(Exception("401 Unauthorized access")), 401)
        self.assertEqual(self.handler.parse_status_code(Exception("403 Permission denied")), 403)
        self.assertEqual(self.handler.parse_status_code(Exception("503 Service Unavailable")), 503)

    def test_02_extract_retry_after(self):
        exc = Exception("Rate limit reached. Retry-After: 45")
        delay = self.handler.extract_retry_after(exc)
        self.assertEqual(delay, 45.0)

    def test_03_sanitize_message_strips_api_keys(self):
        msg = "Invalid request with key=AIzaSyA1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6Q"
        sanitized = self.handler.sanitize_message(msg)
        self.assertNotIn("AIzaSyA1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6Q", sanitized)
        self.assertIn("[REDACTED", sanitized)

    def test_04_evaluate_429_returns_retryable_backoff(self):
        exc = Exception("429 Quota exhausted")
        res = self.handler.evaluate_error(exc, slot_id=2, retry_count=0)
        self.assertEqual(res.status_code, 429)
        self.assertEqual(res.error_type, "RESOURCE_EXHAUSTED")
        self.assertTrue(res.retryable)
        self.assertGreater(res.retry_delay_seconds, 0.5)

    def test_05_evaluate_401_returns_non_retryable(self):
        exc = Exception("401 Invalid API Key")
        res = self.handler.evaluate_error(exc, slot_id=1, retry_count=0)
        self.assertEqual(res.status_code, 401)
        self.assertFalse(res.retryable)
        self.assertEqual(res.action, "AUTH_ALERT")

    def test_06_evaluate_max_retries_exceeded(self):
        exc = Exception("503 Server Error")
        res = self.handler.evaluate_error(exc, slot_id=1, retry_count=3)
        self.assertFalse(res.retryable)
        self.assertEqual(res.action, "FAIL")


if __name__ == "__main__":
    unittest.main()
