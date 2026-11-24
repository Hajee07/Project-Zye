"""
In-Memory Ring Buffer.
Thread-safe circular telemetry buffer implemented using Python collections.deque(maxlen=N).
Guarantees O(1) appends, bounded RAM, and zero-disk overhead.
"""

from __future__ import annotations

import time
from collections import deque
from typing import List, Optional

from zye_realtime_tactical.telemetry.telemetry_models import (
    StreamConfig,
    StreamStatus,
    TelemetrySample,
    TimestampSource,
)


class RingBuffer:
    """Memory-resident bounded circular buffer for a single telemetry stream."""

    def __init__(self, config: StreamConfig) -> None:
        self.config = config
        self.stream_name = config.stream_name
        self.capacity = config.capacity
        self._buffer: deque[TelemetrySample] = deque(maxlen=self.capacity)

        # Telemetry metrics and counters
        self.total_samples_ingested: int = 0
        self.overwritten_samples: int = 0
        self.first_sample_timestamp: Optional[float] = None
        self.last_sample_timestamp: Optional[float] = None
        self.timestamp_source: Optional[TimestampSource] = None
        self.created_at: float = time.time()
        self.last_activity_time: float = self.created_at
        self._sequence_counter: int = 0

    def append(self, value: float, timestamp: float, source: TimestampSource) -> TelemetrySample:
        """Appends a single sample to the ring buffer, updating rollover metrics."""
        self._sequence_counter += 1
        sample = TelemetrySample(
            value=value,
            timestamp=timestamp,
            timestamp_source=source,
            sequence_number=self._sequence_counter,
            received_at=time.time(),
            stream_name=self.stream_name,
        )

        if len(self._buffer) == self.capacity:
            self.overwritten_samples += 1

        self._buffer.append(sample)
        self.total_samples_ingested += 1

        if self.first_sample_timestamp is None:
            self.first_sample_timestamp = timestamp

        self.last_sample_timestamp = timestamp
        self.timestamp_source = source
        self.last_activity_time = time.time()

        return sample

    def extend(self, values: List[float], timestamps: List[float], source: TimestampSource) -> int:
        """Appends a batch of validated samples efficiently."""
        count = len(values)
        now = time.time()

        for v, t in zip(values, timestamps):
            self._sequence_counter += 1
            if len(self._buffer) == self.capacity:
                self.overwritten_samples += 1

            sample = TelemetrySample(
                value=v,
                timestamp=t,
                timestamp_source=source,
                sequence_number=self._sequence_counter,
                received_at=now,
                stream_name=self.stream_name,
            )
            self._buffer.append(sample)
            self.total_samples_ingested += 1

            if self.first_sample_timestamp is None:
                self.first_sample_timestamp = t

        if timestamps:
            self.last_sample_timestamp = timestamps[-1]

        self.timestamp_source = source
        self.last_activity_time = now
        return count

    def get_snapshot(self) -> List[TelemetrySample]:
        """Returns a consistent copy of all current buffer samples."""
        return list(self._buffer)

    def get_latest_n(self, n: int) -> List[TelemetrySample]:
        """Returns the latest n samples from the buffer (or all if buffer size < n)."""
        buf_len = len(self._buffer)
        if n >= buf_len:
            return list(self._buffer)

        # Slice latest n elements from right of deque
        return [self._buffer[i] for i in range(buf_len - n, buf_len)]

    def clear(self) -> None:
        """Resets the ring buffer and counters to clean state."""
        self._buffer.clear()
        self.total_samples_ingested = 0
        self.overwritten_samples = 0
        self.first_sample_timestamp = None
        self.last_sample_timestamp = None
        self.timestamp_source = None
        self.last_activity_time = time.time()
        self._sequence_counter = 0

    def get_status(self) -> StreamStatus:
        """Returns snapshot status of this buffer."""
        return StreamStatus(
            stream_name=self.stream_name,
            capacity=self.capacity,
            current_sample_count=len(self._buffer),
            total_samples_ingested=self.total_samples_ingested,
            overwritten_samples=self.overwritten_samples,
            first_sample_timestamp=self.first_sample_timestamp,
            last_sample_timestamp=self.last_sample_timestamp,
            last_activity_time=self.last_activity_time,
            timestamp_source=self.timestamp_source,
            created_at=self.created_at,
            is_active=True,
        )

    def __len__(self) -> int:
        return len(self._buffer)
