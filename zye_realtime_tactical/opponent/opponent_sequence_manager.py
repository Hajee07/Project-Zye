"""
Opponent Sequence Manager (Day 36).
Thread-safe multi-opponent tracking with bounded in-memory circular buffers.
Strictly in RAM: zero persistent disk/database operations.
"""

from __future__ import annotations

import time
from typing import Dict, List, Optional

from zye_realtime_tactical.opponent.opponent_action_models import OpponentSequenceConfig, OpponentStatus
from zye_realtime_tactical.opponent.opponent_action_validator import OpponentActionValidator
from zye_realtime_tactical.opponent.opponent_lock_manager import OpponentLockManager
from zye_realtime_tactical.opponent.opponent_sequence_buffer import OpponentSequenceBuffer


class OpponentSequenceManager:
    """Manages isolated ring-buffers for multiple opponents in RAM."""

    def __init__(self) -> None:
        self._buffers: Dict[str, OpponentSequenceBuffer] = {}
        self._lock_manager = OpponentLockManager()

    def get_or_create_buffer(
        self,
        opponent_id: str,
        capacity: Optional[int] = None,
    ) -> OpponentSequenceBuffer:
        """
        Retrieves or allocates an in-memory sequence buffer for the specified opponent.
        Validates opponent_id syntax and applies configured capacity.
        """
        validated_id = OpponentActionValidator.validate_opponent_id(opponent_id)
        with self._lock_manager.acquire(validated_id):
            if validated_id not in self._buffers:
                cap = capacity if capacity is not None else OpponentSequenceConfig().max_buffer_capacity
                self._buffers[validated_id] = OpponentSequenceBuffer(
                    opponent_id=validated_id,
                    capacity=cap,
                )
            return self._buffers[validated_id]

    def get_buffer(self, opponent_id: str) -> Optional[OpponentSequenceBuffer]:
        """Returns existing buffer if initialized, else None."""
        clean_id = opponent_id.strip()
        with self._lock_manager.acquire(clean_id):
            return self._buffers.get(clean_id)

    def reset_opponent(self, opponent_id: str) -> bool:
        """
        Clears all buffered actions and resets counters for an opponent.
        Returns True if opponent existed and was reset, False otherwise.
        """
        clean_id = opponent_id.strip()
        with self._lock_manager.acquire(clean_id):
            if clean_id in self._buffers:
                self._buffers[clean_id].reset()
                return True
            return False

    def list_opponents(self) -> List[OpponentStatus]:
        """Returns list of active tracked opponent status snapshots."""
        statuses: List[OpponentStatus] = []
        for opponent_id, buf in list(self._buffers.items()):
            with self._lock_manager.acquire(opponent_id):
                statuses.append(buf.get_status())
        return statuses

    def get_status(self, opponent_id: str) -> Optional[OpponentStatus]:
        """Returns status snapshot for a single opponent if present."""
        clean_id = opponent_id.strip()
        with self._lock_manager.acquire(clean_id):
            buf = self._buffers.get(clean_id)
            if buf is not None:
                return buf.get_status()
            return None

    def cleanup_idle_opponents(self, max_idle_seconds: float = 3600.0) -> int:
        """Prunes buffers inactive for more than max_idle_seconds."""
        now = time.time()
        evicted = 0
        for opponent_id, buf in list(self._buffers.items()):
            with self._lock_manager.acquire(opponent_id):
                if now - buf.last_active_timestamp > max_idle_seconds:
                    del self._buffers[opponent_id]
                    evicted += 1
        return evicted
