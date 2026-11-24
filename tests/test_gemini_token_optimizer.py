"""
Unit tests for GeminiTokenOptimizer — local-first triage, prompt compression, response caching, and TTL.
"""

import time
import unittest
from gemini_token_optimizer import GeminiTokenOptimizer


class TestGeminiTokenOptimizer(unittest.TestCase):
    def setUp(self):
        self.optimizer = GeminiTokenOptimizer(cache_enabled=True, compression_enabled=True, local_first_enabled=True)

    def test_01_local_first_arithmetic(self):
        can_res, ans = self.optimizer.can_resolve_locally("what is 42 * 2")
        self.assertTrue(can_res)
        self.assertEqual(ans, "84")

        can_res, ans = self.optimizer.can_resolve_locally("100 / 4")
        self.assertTrue(can_res)
        self.assertEqual(ans, "25.0")

    def test_02_local_first_time_date(self):
        can_res, ans = self.optimizer.can_resolve_locally("what time is it")
        self.assertTrue(can_res)
        self.assertIn("current time is", ans)

        can_res, ans = self.optimizer.can_resolve_locally("what is today's date")
        self.assertTrue(can_res)
        self.assertIn("Today is", ans)

    def test_03_non_local_queries_fall_through(self):
        can_res, ans = self.optimizer.can_resolve_locally("Write an essay on photosynthesis")
        self.assertFalse(can_res)
        self.assertIsNone(ans)

    def test_04_prompt_compression(self):
        raw = "Hello   world!  \n\n\n\nThis   is   a   test."
        compressed = self.optimizer.compress_prompt(raw)
        self.assertEqual(compressed, "Hello world!\n\nThis is a test.")

    def test_05_caching_and_expiration(self):
        key = self.optimizer.generate_cache_key("test prompt", "gemini-3.8-flash", "LOW")
        self.optimizer.store_cached_response(key, "cached response", ttl_seconds=0.05)

        # Immediate hit
        hit = self.optimizer.get_cached_response(key)
        self.assertEqual(hit, "cached response")

        # Wait for expiration
        time.sleep(0.08)
        expired = self.optimizer.get_cached_response(key)
        self.assertIsNone(expired)

    def test_06_estimate_tokens(self):
        self.assertEqual(self.optimizer.estimate_tokens(""), 0)
        self.assertEqual(self.optimizer.estimate_tokens("word"), 1)
        self.assertEqual(self.optimizer.estimate_tokens("a" * 400), 100)


if __name__ == "__main__":
    unittest.main()
