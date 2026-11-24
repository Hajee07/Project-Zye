"""
Stream Lock Manager.
Provides fine-grained per-stream concurrency controls and thread-safe stream registry synchronization.
"""

from __future__ import annotations

import threading
from typing import Dict


class StreamLockManager:
    """Manages independent RLock instances per stream to prevent cross-stream blocking."""

    def __init__(self) -> None:
        self._registry_lock = threading.RLock()
        self._stream_locks: Dict[str, threading.RLock] = {}

    def get_stream_lock(self, stream_name: str) -> threading.RLock:
        """Returns or creates a reentrant lock dedicated to the specified stream."""
        with self._registry_lock:
            if stream_name not in self._stream_locks:
                self._stream_locks[stream_name] = threading.RLock()
            return self._stream_locks[stream_name]

    def remove_stream_lock(self, stream_name: str) -> None:
        """Removes lock when a stream is deleted or cleaned up."""
        with self._registry_lock:
            self._stream_locks.pop(stream_name, None)

    def get_all_locked_stream_names(self) -> list[str]:
        """Returns list of all stream names with active locks."""
        with self._registry_lock:
            return list(self._stream_locks.keys())
