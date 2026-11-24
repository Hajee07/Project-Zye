"""
Search Cache Engine.
Maintains in-memory TTL-bounded search results, reduces duplicate web queries,
and supports force-refresh triggers.
"""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Any

logger = logging.getLogger("zye.computer_intelligence.search_cache")

DEFAULT_CACHE_TTL_SECONDS = 300.0  # 5 minutes


class SearchCache:
    """In-memory key-value cache with per-item expiration timestamps."""

    def __init__(self, default_ttl: float = DEFAULT_CACHE_TTL_SECONDS) -> None:
        self.default_ttl = default_ttl
        self._store: dict[str, tuple[float, Any]] = {}

    @staticmethod
    def generate_cache_key(query: str, mode: str, domain: str | None = None) -> str:
        """Computes deterministic MD5 hash for query configuration."""
        raw = f"{query.strip().lower()}|{mode.lower()}|{domain or ''}"
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    def get(self, key: str) -> Any | None:
        """Retrieves cached value if not expired."""
        if key not in self._store:
            return None

        expiry, val = self._store[key]
        if time.time() > expiry:
            del self._store[key]
            return None

        return val

    def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        """Stores item with specified or default TTL."""
        item_ttl = ttl if ttl is not None else self.default_ttl
        expiry = time.time() + item_ttl
        self._store[key] = (expiry, value)

    def clear(self) -> None:
        """Flushes all cached entries."""
        self._store.clear()

    def prune_expired(self) -> int:
        """Removes expired entries and returns count of purged items."""
        now = time.time()
        expired_keys = [k for k, (exp, _) in self._store.items() if now > exp]
        for k in expired_keys:
            del self._store[k]
        return len(expired_keys)
