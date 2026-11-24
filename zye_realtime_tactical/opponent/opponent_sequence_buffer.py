"""
Opponent Sequence Buffer.
In-memory circular sequence buffer for an opponent using collections.deque(maxlen=1000).
Maintains action chronology, sample counters, and rollover statistics with zero disk lag.
"""

from __future__ import annotations

import time
from collections import deque
from typing import Any, List, Optional, Tuple, Union

from zye_realtime_tactical.opponent.opponent_action_models import (
    OpponentAction,
    OpponentSequenceConfig,
    OpponentStatus,
)
from zye_realtime_tactical.telemetry.telemetry_models import TimestampSource


class OpponentSequenceBuffer:
    """Bounded circular buffer storing an opponent's chronological actions."""

    def __init__(
        self,
        config_or_id: Union[OpponentSequenceConfig, str] = "default",
        capacity: Optional[int] = None,
        opponent_id: Optional[str] = None,
    ) -> None:
        if isinstance(config_or_id, OpponentSequenceConfig):
            self.config = config_or_id
            self.opponent_id = config_or_id.opponent_id
            self.capacity = config_or_id.capacity
        else:
            self.opponent_id = opponent_id or str(config_or_id)
            self.capacity = capacity or 1000
            self.config = OpponentSequenceConfig(
                opponent_id=self.opponent_id,
                capacity=self.capacity,
            )

        self._buffer: deque[OpponentAction] = deque(maxlen=self.capacity)
        self.total_actions_observed: int = 0
        self.overwritten_actions: int = 0
        self.first_action_timestamp: Optional[float] = None
        self.last_action_timestamp: Optional[float] = None
        self.timestamp_source: Optional[TimestampSource] = None
        self.created_at: float = time.time()
        self.last_activity_time: float = self.created_at
        self._sequence_counter: int = 0

    @property
    def size(self) -> int:
        """Returns the current number of items buffered in memory."""
        return len(self._buffer)

    @property
    def last_active_timestamp(self) -> float:
        """Returns last activity timestamp."""
        return self.last_activity_time

    def append(self, action: Union[OpponentAction, str], timestamp: Optional[float] = None) -> None:
        """Appends a single action to the circular buffer."""
        now = time.time()
        self.last_activity_time = now
        self.total_actions_observed += 1
        self._sequence_counter += 1

        if len(self._buffer) == self.capacity:
            self.overwritten_actions += 1

        if isinstance(action, OpponentAction):
            obj = action
        else:
            ts = timestamp if timestamp is not None else now
            obj = OpponentAction(
                action=str(action),
                timestamp=ts,
                sequence_number=self._sequence_counter,
            )

        if self.first_action_timestamp is None:
            self.first_action_timestamp = obj.timestamp
        self.last_action_timestamp = obj.timestamp

        self._buffer.append(obj)

    def append_batch(self, actions: List[OpponentAction]) -> None:
        """Appends multiple action objects efficiently using C-level deque.extend."""
        if not actions:
            return
        now = time.time()
        self.last_activity_time = now
        total_incoming = len(actions)
        current_len = len(self._buffer)
        overwriting = max(0, current_len + total_incoming - self.capacity)
        self.overwritten_actions += overwriting
        self.total_actions_observed += total_incoming
        self._sequence_counter += total_incoming

        if self.first_action_timestamp is None:
            self.first_action_timestamp = actions[0].timestamp
        self.last_action_timestamp = actions[-1].timestamp

        self._buffer.extend(actions)

    def extend(
        self,
        raw_actions: List[str],
        normalized_actions: List[str],
        timestamps: List[float],
        source: TimestampSource,
    ) -> int:
        """Appends a batch of actions atomically, maintaining sequence numbers and rollover."""
        self.timestamp_source = source
        for raw, norm, t in zip(raw_actions, normalized_actions, timestamps):
            action_obj = OpponentAction(
                action=norm,
                timestamp=t,
                raw_action=raw,
            )
            self.append(action_obj)
        return len(normalized_actions)

    def reset(self) -> None:
        """Clears all buffered actions and resets counters."""
        self._buffer.clear()
        self.total_actions_observed = 0
        self.overwritten_actions = 0
        self.first_action_timestamp = None
        self.last_action_timestamp = None
        self.last_activity_time = time.time()
        self._sequence_counter = 0

    def get_all_actions(self) -> List[str]:
        """Returns ordered list of action strings currently in buffer."""
        return [act.action for act in self._buffer]

    def get_all_timestamps(self) -> List[float]:
        """Returns ordered list of timestamps currently in buffer."""
        return [act.timestamp for act in self._buffer]

    def get_status(self) -> OpponentStatus:
        """Returns snapshot status of the opponent's circular buffer."""
        return OpponentStatus(
            opponent_id=self.opponent_id,
            current_action_count=len(self._buffer),
            capacity=self.capacity,
            total_actions_observed=self.total_actions_observed,
            total_ingested_actions=self.total_actions_observed,
            overwritten_actions=self.overwritten_actions,
            first_action_timestamp=self.first_action_timestamp,
            last_action_timestamp=self.last_action_timestamp,
            last_activity_time=self.last_activity_time,
            timestamp_source=self.timestamp_source,
        )
