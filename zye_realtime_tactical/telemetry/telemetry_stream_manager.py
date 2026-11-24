"""
Telemetry Stream Manager.
Maintains multiple independent named streams, coordinates per-stream locks,
enforces active stream limits, and provides lifecycle operations (create, list, reset, cleanup).
"""

from __future__ import annotations

import logging
import time
from typing import Dict, List, Optional

from zye_realtime_tactical.security.telemetry_access_policy import (
    TelemetryAccessPolicy,
    TelemetrySecurityError,
)
from zye_realtime_tactical.security.telemetry_resource_policy import TelemetryResourcePolicy
from zye_realtime_tactical.telemetry.ring_buffer import RingBuffer
from zye_realtime_tactical.telemetry.stream_lock_manager import StreamLockManager
from zye_realtime_tactical.telemetry.telemetry_models import StreamConfig, StreamStatus

logger = logging.getLogger("zye.realtime_tactical.stream_manager")


class TelemetryStreamManager:
    """Central registry and lifecycle manager for independent telemetry streams."""

    def __init__(self, lock_manager: Optional[StreamLockManager] = None) -> None:
        self.lock_manager = lock_manager or StreamLockManager()
        self._streams: Dict[str, RingBuffer] = {}

    def get_or_create_stream(
        self,
        stream_name: str,
        capacity: int = TelemetryResourcePolicy.DEFAULT_BUFFER_CAPACITY,
        anomaly_threshold: float = TelemetryResourcePolicy.DEFAULT_ANOMALY_THRESHOLD,
    ) -> RingBuffer:
        """Retrieves existing stream or creates a new bounded ring buffer under registry lock."""
        # Validate stream name
        is_valid, msg = TelemetryAccessPolicy.validate_stream_name(stream_name)
        if not is_valid:
            raise TelemetrySecurityError(f"Invalid stream name '{stream_name}': {msg}")

        stream_lock = self.lock_manager.get_stream_lock(stream_name)
        with stream_lock:
            with self.lock_manager._registry_lock:
                if stream_name in self._streams:
                    return self._streams[stream_name]

                # Check max active streams limit
                if len(self._streams) >= TelemetryResourcePolicy.MAX_ACTIVE_STREAMS:
                    # Attempt to clean up idle streams first
                    cleaned = self._cleanup_idle_streams_unlocked(TelemetryResourcePolicy.IDLE_STREAM_EXPIRY_SECONDS)
                    if len(self._streams) >= TelemetryResourcePolicy.MAX_ACTIVE_STREAMS:
                        raise TelemetrySecurityError(
                            f"Maximum active streams limit ({TelemetryResourcePolicy.MAX_ACTIVE_STREAMS}) reached."
                        )

                # Validate and clamp capacity within allowed bounds
                bounded_capacity = max(
                    TelemetryResourcePolicy.MIN_BUFFER_CAPACITY,
                    min(capacity, TelemetryResourcePolicy.MAX_BUFFER_CAPACITY),
                )

                config = StreamConfig(
                    stream_name=stream_name,
                    capacity=bounded_capacity,
                    anomaly_threshold=anomaly_threshold,
                    min_baseline_samples=TelemetryResourcePolicy.MIN_ANOMALY_BASELINE_SAMPLES,
                )
                new_buf = RingBuffer(config)
                self._streams[stream_name] = new_buf
                logger.info("Created telemetry ring buffer for stream '%s' (capacity=%d)", stream_name, bounded_capacity)
                return new_buf

    def get_stream(self, stream_name: str) -> Optional[RingBuffer]:
        """Returns existing stream if present, None otherwise."""
        with self.lock_manager._registry_lock:
            return self._streams.get(stream_name)

    def reset_stream(self, stream_name: str) -> bool:
        """Clears all historical observations and counters for the specified stream."""
        stream_lock = self.lock_manager.get_stream_lock(stream_name)
        with stream_lock:
            with self.lock_manager._registry_lock:
                stream = self._streams.get(stream_name)
                if stream is None:
                    return False
                stream.clear()
                logger.info("Reset telemetry stream '%s'", stream_name)
                return True

    def list_active_streams(self) -> List[StreamStatus]:
        """Returns runtime status for all active streams."""
        with self.lock_manager._registry_lock:
            active_names = list(self._streams.keys())

        statuses: List[StreamStatus] = []
        for name in active_names:
            lock = self.lock_manager.get_stream_lock(name)
            with lock:
                stream = self._streams.get(name)
                if stream is not None:
                    statuses.append(stream.get_status())
        return statuses

    def get_stream_status(self, stream_name: str) -> Optional[StreamStatus]:
        """Returns runtime status for a specific stream."""
        lock = self.lock_manager.get_stream_lock(stream_name)
        with lock:
            with self.lock_manager._registry_lock:
                stream = self._streams.get(stream_name)
                if stream is None:
                    return None
                return stream.get_status()

    def cleanup_idle_streams(self, max_idle_seconds: float = TelemetryResourcePolicy.IDLE_STREAM_EXPIRY_SECONDS) -> int:
        """Cleans up streams with no activity past the idle threshold."""
        with self.lock_manager._registry_lock:
            return self._cleanup_idle_streams_unlocked(max_idle_seconds)

    def _cleanup_idle_streams_unlocked(self, max_idle_seconds: float) -> int:
        now = time.time()
        to_remove = []
        for name, stream in self._streams.items():
            if now - stream.last_activity_time > max_idle_seconds:
                to_remove.append(name)

        for name in to_remove:
            self._streams.pop(name, None)
            self.lock_manager.remove_stream_lock(name)
            logger.info("Removed idle telemetry stream '%s' (idle %.1fs)", name, now - stream.last_activity_time)
        return len(to_remove)

    def clear_all(self) -> None:
        """Clears all streams and locks (used in testing/shutdown)."""
        with self.lock_manager._registry_lock:
            for s in self._streams.values():
                s.clear()
            self._streams.clear()
