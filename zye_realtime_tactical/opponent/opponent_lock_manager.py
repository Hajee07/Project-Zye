"""
Opponent Lock Manager.
Provides independent reentrant synchronization per opponent to prevent cross-opponent contention.
"""

from __future__ import annotations

import threading
from typing import Dict


class OpponentLockManager:
    """Manages independent RLock instances per tracked opponent."""

    def __init__(self) -> None:
        self._registry_lock = threading.RLock()
        self._opponent_locks: Dict[str, threading.RLock] = {}

    def get_opponent_lock(self, opponent_id: str) -> threading.RLock:
        """Returns or creates a reentrant lock dedicated to the opponent."""
        with self._registry_lock:
            if opponent_id not in self._opponent_locks:
                self._opponent_locks[opponent_id] = threading.RLock()
            return self._opponent_locks[opponent_id]

    def acquire(self, opponent_id: str) -> threading.RLock:
        """Alias returning the reentrant lock for context manager usage."""
        return self.get_opponent_lock(opponent_id)

    def remove_opponent_lock(self, opponent_id: str) -> None:
        """Removes lock when an opponent buffer is cleared or cleaned up."""
        with self._registry_lock:
            self._opponent_locks.pop(opponent_id, None)
