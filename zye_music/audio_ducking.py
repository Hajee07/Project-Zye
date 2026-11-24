"""
ZYE AI — Speech-Aware Audio Ducker
==================================

Speech-aware audio ducking engine implementing Section 34-36:
- Smooth volume reduction when user or assistant speaks.
- Asynchronous lock (`asyncio.Lock`) preventing concurrent race conditions.
- Strict depth tracking and idempotent operations.
- Non-blocking volume ramp restoration.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Callable, Optional

logger = logging.getLogger("zye.music.ducking")


class AudioDucker:
    """
    Coordinates smooth audio ducking when speech interactions occur.
    Ensures background music drops to a background level and restores safely.
    """

    def __init__(
        self,
        set_volume_fn: Callable[[int], None],
        get_volume_fn: Callable[[], int],
        ducked_volume_percentage: int = 20,
        ramp_duration_ms: int = 150,
    ) -> None:
        self._set_volume = set_volume_fn
        self._get_volume = get_volume_fn
        self._ducked_volume = max(0, min(100, ducked_volume_percentage))
        self._ramp_duration = max(10, ramp_duration_ms) / 1000.0

        self._lock: Optional[asyncio.Lock] = None
        self._active_loop: Optional[asyncio.AbstractEventLoop] = None
        self._is_ducked: bool = False
        self._original_volume: int = 80
        self._duck_depth_count: int = 0
        self._last_duck_timestamp: float = 0.0

    def _get_lock(self) -> asyncio.Lock:
        try:
            curr_loop = asyncio.get_running_loop()
        except RuntimeError:
            curr_loop = None
        if self._lock is None or self._active_loop != curr_loop:
            self._lock = asyncio.Lock()
            self._active_loop = curr_loop
        return self._lock

    @property
    def is_ducked(self) -> bool:
        """Check if audio is currently in ducked state."""
        return self._is_ducked

    async def duck(self) -> bool:
        """
        Duck volume down to the ducked volume percentage.
        Thread-safe and async-safe.
        """
        async with self._get_lock():
            self._duck_depth_count += 1
            if self._is_ducked:
                # Already ducked, simply maintain reference count
                return True

            current = self._get_volume()
            # If current volume is already lower than or equal to ducked volume, don't raise it
            if current <= self._ducked_volume:
                self._original_volume = current
                self._is_ducked = True
                return True

            self._original_volume = current
            self._last_duck_timestamp = time.monotonic()

            try:
                # Ramp down volume
                steps = 4
                step_sleep = self._ramp_duration / steps
                diff = current - self._ducked_volume
                for i in range(1, steps + 1):
                    vol = int(current - (diff * (i / steps)))
                    self._set_volume(vol)
                    await asyncio.sleep(step_sleep)

                self._set_volume(self._ducked_volume)
                self._is_ducked = True
                logger.debug("Audio ducked from %d%% to %d%%", current, self._ducked_volume)
                return True
            except Exception as e:
                logger.error("Failed to duck audio: %s", e)
                return False

    def duck_sync(self) -> bool:
        """Synchronously duck volume to ducked percentage."""
        self._duck_depth_count += 1
        if self._is_ducked:
            return True
        current = self._get_volume()
        if current <= self._ducked_volume:
            self._original_volume = current
            self._is_ducked = True
            return True
        self._original_volume = current
        self._set_volume(self._ducked_volume)
        self._is_ducked = True
        return True

    def unduck_sync(self, force: bool = False) -> bool:
        """Synchronously restore volume back to original level."""
        if not self._is_ducked:
            self._duck_depth_count = 0
            return True
        if not force:
            self._duck_depth_count = max(0, self._duck_depth_count - 1)
            if self._duck_depth_count > 0:
                return True
        self._duck_depth_count = 0
        self._set_volume(self._original_volume)
        self._is_ducked = False
        return True

    async def unduck(self, force: bool = False) -> bool:
        """
        Restore volume back to pre-ducked original level.
        If force=True, restores immediately regardless of reference count.
        """
        async with self._get_lock():
            if not self._is_ducked:
                self._duck_depth_count = 0
                return True

            if not force:
                self._duck_depth_count = max(0, self._duck_depth_count - 1)
                if self._duck_depth_count > 0:
                    # Still active speech interaction ongoing
                    return True

            self._duck_depth_count = 0
            target_vol = self._original_volume

            try:
                # Ramp up volume smoothly
                steps = 4
                step_sleep = self._ramp_duration / steps
                current = self._get_volume()
                diff = target_vol - current
                if diff > 0:
                    for i in range(1, steps + 1):
                        vol = int(current + (diff * (i / steps)))
                        self._set_volume(vol)
                        await asyncio.sleep(step_sleep)

                self._set_volume(target_vol)
                self._is_ducked = False
                logger.debug("Audio restored back to %d%%", target_vol)
                return True
            except Exception as e:
                logger.error("Failed to restore audio after ducking: %s", e)
                self._is_ducked = False
                return False
