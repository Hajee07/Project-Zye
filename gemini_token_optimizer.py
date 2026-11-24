"""
Gemini Token Optimizer — Zye Multi-Project Gemini Intelligence Infrastructure v2.0 (Section 12).
Implements local-first evaluation, prompt compression, response caching with TTL, and token estimation.
"""

from __future__ import annotations

import hashlib
import logging
import re
import threading
import time
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("zye.gemini.optimizer")


@dataclass
class CacheEntry:
    key: str
    response: str
    created_at: float
    expires_at: float


class GeminiTokenOptimizer:
    """
    Optimizes token usage through local-first triage, prompt compression,
    and in-memory response caching.
    """

    def __init__(
        self,
        cache_enabled: bool = True,
        compression_enabled: bool = True,
        local_first_enabled: bool = True,
        default_ttl_seconds: int = 300,
        max_cache_size: int = 500,
    ) -> None:
        self.cache_enabled = cache_enabled
        self.compression_enabled = compression_enabled
        self.local_first_enabled = local_first_enabled
        self.default_ttl = default_ttl_seconds
        self.max_cache_size = max_cache_size
        self._cache: dict[str, CacheEntry] = {}
        self._lock = threading.RLock()

    def can_resolve_locally(self, prompt: str) -> tuple[bool, str | None]:
        """
        Check if prompt can be safely resolved locally without calling Gemini.
        Returns (can_resolve, local_response).
        """
        if not self.local_first_enabled:
            return False, None

        clean = prompt.strip().lower()

        # 1. Simple math: e.g. "what is 2 + 2", "calculate 15 * 4"
        math_match = re.fullmatch(r"(?:what is|calculate|solve|eval)?\s*(-?\d+(?:\.\d+)?\s*[\+\-\*\/]\s*-?\d+(?:\.\d+)?)\??", clean)
        if math_match:
            expr = math_match.group(1)
            try:
                # Safe eval of simple 2-operand arithmetic only
                allowed = set("0123456789+-*/. ")
                if all(c in allowed for c in expr):
                    result = eval(expr, {"__builtins__": None}, {})
                    return True, str(result)
            except Exception:
                pass

        # 2. Basic time / date queries
        if clean in ("what time is it", "current time", "what is the time", "time now"):
            now_str = time.strftime("%I:%M %p")
            return True, f"The current time is {now_str}."

        if clean in ("what is the date", "what is today's date", "today's date", "current date"):
            date_str = time.strftime("%B %d, %Y")
            return True, f"Today is {date_str}."

        return False, None

    def compress_prompt(self, prompt: str, max_chars: int = 12000) -> str:
        """
        Compress prompt by normalizing whitespace, removing redundant filler phrasing,
        and safely windowing excessive context.
        """
        if not self.compression_enabled or not prompt:
            return prompt

        # 1. Normalize spaces per line and multiple empty lines
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in prompt.splitlines()]
        compressed = "\n".join(lines)
        compressed = re.sub(r"\n{3,}", "\n\n", compressed).strip()

        # 2. Window excessive context if beyond threshold (preserving head and tail)
        if len(compressed) > max_chars:
            head_len = int(max_chars * 0.6)
            tail_len = int(max_chars * 0.35)
            omitted = len(compressed) - (head_len + tail_len)
            compressed = (
                compressed[:head_len]
                + f"\n\n[... {omitted} characters truncated for token optimization ...]\n\n"
                + compressed[-tail_len:]
            )

        return compressed

    def generate_cache_key(
        self,
        prompt: str,
        model_id: str,
        thinking_level: str,
        system_instruction: str = "",
    ) -> str:
        """Compute deterministic SHA-256 hash for caching."""
        normalized = f"{prompt.strip()}|{model_id}|{thinking_level}|{system_instruction.strip()}"
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def get_cached_response(self, cache_key: str) -> str | None:
        """Retrieve unexpired cached response if available."""
        if not self.cache_enabled:
            return None

        with self._lock:
            entry = self._cache.get(cache_key)
            if not entry:
                return None

            now = time.time()
            if entry.expires_at < now:
                # Expired
                del self._cache[cache_key]
                return None

            logger.debug("Cache HIT for key: %s", cache_key[:12])
            return entry.response

    def store_cached_response(
        self,
        cache_key: str,
        response: str,
        ttl_seconds: int | None = None,
    ) -> None:
        """Store response in cache with TTL."""
        if not self.cache_enabled:
            return

        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        now = time.time()

        with self._lock:
            # Prune if cache is full
            if len(self._cache) >= self.max_cache_size:
                # Remove oldest expired or just first items
                expired = [k for k, v in self._cache.items() if v.expires_at < now]
                for k in expired:
                    del self._cache[k]

                if len(self._cache) >= self.max_cache_size:
                    # Remove first 10% keys
                    to_remove = list(self._cache.keys())[: max(1, self.max_cache_size // 10)]
                    for k in to_remove:
                        del self._cache[k]

            self._cache[cache_key] = CacheEntry(
                key=cache_key,
                response=response,
                created_at=now,
                expires_at=now + ttl,
            )

    def clear_cache(self) -> None:
        """Clear all cached responses."""
        with self._lock:
            self._cache.clear()

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """
        Fast token estimator: roughly 4 characters per token for English text.
        Conservative floor of 1 token for non-empty text.
        """
        if not text:
            return 0
        return max(1, len(text) // 4)
