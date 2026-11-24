"""Smart Rate-Limit and Quota Manager with Token Bucket Algorithm (Day 27).

Tracks per-provider request rate limits, token quotas, and backoff cooldowns:
- Token-bucket algorithm for request and token smoothing
- Independent tracking per provider (ChatGPT, Claude, Ollama, etc.)
- Dynamic cooldown enforcement when a 429 response is detected
- Never replaces or alters Gemini Master Brain's 7-key quota manager
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("zye.ai_plugins.rate_limiter")


class ProviderRateLimiter:
    """Token-bucket rate limiter for an individual provider."""

    def __init__(
        self,
        provider_id: str,
        requests_per_minute: int = 60,
        tokens_per_minute: int = 40_000,
    ):
        self.provider_id = provider_id
        self.rpm_limit = requests_per_minute
        self.tpm_limit = tokens_per_minute

        # Token buckets
        self.request_tokens: float = float(requests_per_minute)
        self.token_tokens: float = float(tokens_per_minute)

        self.last_refill_time: float = time.monotonic()
        self.cooldown_until: float = 0.0
        self.cooldown_reason: Optional[str] = None
        self.total_throttled: int = 0
        self._lock = threading.Lock()

    def _refill(self, now: float) -> None:
        """Replenish tokens based on elapsed monotonic time."""
        elapsed = now - self.last_refill_time
        if elapsed <= 0:
            return

        self.last_refill_time = now

        # Add fractional tokens for elapsed seconds
        rpm_refill = (self.rpm_limit / 60.0) * elapsed
        tpm_refill = (self.tpm_limit / 60.0) * elapsed

        self.request_tokens = min(float(self.rpm_limit), self.request_tokens + rpm_refill)
        self.token_tokens = min(float(self.tpm_limit), self.token_tokens + tpm_refill)

    def check_capacity(self, estimated_tokens: int = 100) -> Tuple[bool, float, str]:
        """Check if request can proceed immediately, or return required wait time."""
        with self._lock:
            now = time.monotonic()

            # 1. Check Cooldown
            if now < self.cooldown_until:
                wait_sec = self.cooldown_until - now
                return False, round(wait_sec, 2), f"In rate-limit cooldown ({self.cooldown_reason})"

            self._refill(now)

            # 2. Check Request Bucket
            if self.request_tokens < 1.0:
                self.total_throttled += 1
                wait_sec = (1.0 - self.request_tokens) / (self.rpm_limit / 60.0)
                return False, round(wait_sec, 2), "RPM limit exceeded"

            # 3. Check Token Bucket
            if self.token_tokens < estimated_tokens:
                self.total_throttled += 1
                wait_sec = (estimated_tokens - self.token_tokens) / (self.tpm_limit / 60.0)
                return False, round(wait_sec, 2), "TPM limit exceeded"

            return True, 0.0, "Capacity available"

    def acquire(self, estimated_tokens: int = 100) -> bool:
        """Attempt to consume tokens. Returns True if successfully acquired."""
        with self._lock:
            now = time.monotonic()

            if now < self.cooldown_until:
                return False

            self._refill(now)

            if self.request_tokens >= 1.0 and self.token_tokens >= estimated_tokens:
                self.request_tokens -= 1.0
                self.token_tokens -= estimated_tokens
                return True

            self.total_throttled += 1
            return False

    def trigger_cooldown(self, cooldown_seconds: float = 15.0, reason: str = "HTTP 429 received") -> None:
        """Lock provider into cooldown state following rate limit error."""
        with self._lock:
            now = time.monotonic()
            self.cooldown_until = now + cooldown_seconds
            self.cooldown_reason = reason
            self.request_tokens = 0.0  # Empty bucket
            logger.warning(
                "RateLimiter for '%s' locked into cooldown for %.1fs. Reason: %s",
                self.provider_id,
                cooldown_seconds,
                reason,
            )

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            now = time.monotonic()
            self._refill(now)
            in_cooldown = now < self.cooldown_until
            remaining_cooldown = max(0.0, self.cooldown_until - now) if in_cooldown else 0.0
            return {
                "provider_id": self.provider_id,
                "rpm_limit": self.rpm_limit,
                "tpm_limit": self.tpm_limit,
                "available_request_tokens": round(self.request_tokens, 1),
                "available_token_tokens": round(self.token_tokens, 1),
                "in_cooldown": in_cooldown,
                "cooldown_remaining_seconds": round(remaining_cooldown, 2),
                "total_throttled": self.total_throttled,
            }


class RateLimiterRegistry:
    """Singleton managing rate limiters across all AI providers."""

    _instance: Optional[RateLimiterRegistry] = None
    _lock = threading.Lock()

    def __init__(self):
        self._limiters: Dict[str, ProviderRateLimiter] = {}
        # Conservative defaults for external APIs
        self._defaults = {
            "openai": (120, 60_000),
            "chatgpt": (120, 60_000),
            "anthropic": (100, 50_000),
            "claude": (100, 50_000),
            "ollama": (300, 100_000),
            "perplexity": (60, 30_000),
            "deepseek": (100, 50_000),
            "groq": (120, 60_000),
            "openrouter": (100, 50_000),
            "custom": (60, 30_000),
        }

    @classmethod
    def get_instance(cls) -> RateLimiterRegistry:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def get_limiter(self, provider_id: str) -> ProviderRateLimiter:
        pid = provider_id.lower().strip()
        if pid not in self._limiters:
            with self._lock:
                if pid not in self._limiters:
                    rpm, tpm = self._defaults.get(pid, (60, 30_000))
                    self._limiters[pid] = ProviderRateLimiter(pid, rpm, tpm)
        return self._limiters[pid]

    def check_capacity(self, provider_id: str, estimated_tokens: int = 100) -> Tuple[bool, float, str]:
        return self.get_limiter(provider_id).check_capacity(estimated_tokens)

    def acquire(self, provider_id: str, estimated_tokens: int = 100) -> bool:
        return self.get_limiter(provider_id).acquire(estimated_tokens)

    def record_429(self, provider_id: str, cooldown_seconds: float = 15.0) -> None:
        self.get_limiter(provider_id).trigger_cooldown(cooldown_seconds)

    def get_all_statuses(self) -> Dict[str, Dict[str, Any]]:
        return {pid: limiter.to_dict() for pid, limiter in self._limiters.items()}


def get_rate_limiter() -> RateLimiterRegistry:
    return RateLimiterRegistry.get_instance()
