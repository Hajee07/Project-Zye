"""Day 27 Unit Tests: Retry Engine, Rate Limiting & Concurrency Control.

Tests:
- Error classification into transient vs permanent
- Retry-After duration extraction from text and headers
- Exponential backoff with full jitter
- Token-bucket rate limiter capacity acquisition and cooldown locking
- Concurrency controller AIMD limits and slot release
- Bulkhead failover event recording
"""

import unittest

from zye_ai_plugins.resilience import (
    BulkheadManager,
    ConcurrencyControllerRegistry,
    ProviderConcurrencyPool,
    ProviderRateLimiter,
    RateLimiterRegistry,
    calculate_retry_delay,
    classify_provider_error,
    extract_retry_after,
)


class TestDay27RetryAndResilience(unittest.TestCase):
    """Test suite for retry, rate limiter, and concurrency controller."""

    def test_01_error_classification(self):
        """Verify proper classification of transient vs permanent errors."""
        # Transient errors
        ret_429, cat_429 = classify_provider_error(429, "Too many requests")
        self.assertTrue(ret_429)
        self.assertEqual(cat_429, "RATE_LIMITED")

        ret_503, cat_503 = classify_provider_error(503, "Service Unavailable")
        self.assertTrue(ret_503)
        self.assertEqual(cat_503, "SERVER_OVERLOAD")

        ret_net, cat_net = classify_provider_error(error_message="Connection timed out after 30s")
        self.assertTrue(ret_net)
        self.assertEqual(cat_net, "TRANSIENT_NETWORK")

        # Permanent errors
        ret_401, cat_401 = classify_provider_error(401, "Invalid API Key")
        self.assertFalse(ret_401)
        self.assertEqual(cat_401, "AUTH_ERROR")

        ret_ssrf, cat_ssrf = classify_provider_error(error_message="SSRF: Blocked private IP subnet 192.168.1.1")
        self.assertFalse(ret_ssrf)
        self.assertEqual(cat_ssrf, "SECURITY_BLOCKED")

    def test_02_retry_after_extraction(self):
        """Verify extraction of retry wait times from headers and text."""
        # From headers
        dur1 = extract_retry_after("Error", headers={"Retry-After": "4.5"})
        self.assertEqual(dur1, 4.5)

        # From regex in text
        dur2 = extract_retry_after("Rate limit exceeded. Please retry after 2.5s.")
        self.assertEqual(dur2, 2.5)

    def test_03_retry_delay_exponential_with_jitter(self):
        """Verify backoff calculation honors bounds and applies jitter."""
        d0 = calculate_retry_delay(attempt=0, base_delay=1.0, max_delay=8.0)
        d2 = calculate_retry_delay(attempt=2, base_delay=1.0, max_delay=8.0)
        self.assertGreaterEqual(d0, 0.5)
        self.assertLessEqual(d2, 8.0)

        # Explicit retry-after overrides backoff
        d_explicit = calculate_retry_delay(attempt=1, retry_after=3.0)
        self.assertEqual(d_explicit, 3.0)

    def test_04_token_bucket_rate_limiter(self):
        """Verify rate limiter capacity check, bucket consumption, and cooldown."""
        limiter = ProviderRateLimiter("test_prov", requests_per_minute=60, tokens_per_minute=1000)

        # Initial acquire succeeds
        self.assertTrue(limiter.acquire(100))

        # Cooldown locks provider
        limiter.trigger_cooldown(cooldown_seconds=10.0, reason="HTTP 429")
        can_proceed, wait_sec, reason = limiter.check_capacity(100)
        self.assertFalse(can_proceed)
        self.assertGreater(wait_sec, 0.0)
        self.assertIn("cooldown", reason)

    def test_05_concurrency_controller_aimd(self):
        """Verify AIMD adaptive concurrency adjustments."""
        pool = ProviderConcurrencyPool("test_aimd", initial_concurrency=4, min_concurrency=2, max_concurrency=8)

        # Acquire slots
        acq1, _ = pool.try_acquire()
        self.assertTrue(acq1)
        self.assertEqual(pool.active_requests, 1)

        # Release with failure triggers multiplicative decrease
        pool.release(success=False)
        self.assertEqual(pool.active_requests, 0)
        # Limit reduced: int(4 * 0.7) = 2
        self.assertEqual(pool.current_limit, 2)

    def test_06_bulkhead_failover_history(self):
        """Verify failover recording and retrieval."""
        bm = BulkheadManager()
        bm.record_failover("chatgpt", "claude", "ReadTimeout", "req_999", success=True)
        hist = bm.get_failover_history(limit=5)
        self.assertGreaterEqual(len(hist), 1)
        self.assertEqual(hist[0]["original_provider"], "chatgpt")
        self.assertEqual(hist[0]["fallback_provider"], "claude")


if __name__ == "__main__":
    unittest.main()
