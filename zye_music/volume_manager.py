"""
ZYE AI — Music Volume and State Manager
=======================================

Handles volume calculations, range clamping [0, 100], relative steps,
and state-preserving mute/unmute functionality (Section 32/33).
"""

from __future__ import annotations

import logging
from typing import Tuple

logger = logging.getLogger("zye.music.volume")


class VolumeManager:
    """Manages volume adjustments and mute memory."""

    DEFAULT_STEP: int = 10
    MIN_VOLUME: int = 0
    MAX_VOLUME: int = 100

    def __init__(self, initial_volume: int = 80) -> None:
        self._current_volume: int = self.clamp(initial_volume)
        self._previous_volume_before_mute: int = self._current_volume
        self._is_muted: bool = False

    @classmethod
    def clamp(cls, volume: int) -> int:
        """Clamp volume within [0, 100]."""
        return max(cls.MIN_VOLUME, min(cls.MAX_VOLUME, volume))

    @property
    def current_volume(self) -> int:
        """Get current volume percentage."""
        return self._current_volume

    @property
    def is_muted(self) -> bool:
        """Check if currently muted."""
        return self._is_muted

    def set_volume(self, target_volume: int) -> int:
        """Set absolute volume and unmute if muted."""
        clamped = self.clamp(target_volume)
        self._current_volume = clamped
        if self._is_muted and clamped > 0:
            self._is_muted = False
        return self._current_volume

    def adjust_volume(self, delta: int) -> Tuple[int, int]:
        """
        Adjust volume relatively by delta.

        Returns:
            Tuple of (previous_volume, new_volume)
        """
        old_volume = self._current_volume
        new_volume = self.clamp(old_volume + delta)
        self._current_volume = new_volume
        if self._is_muted and new_volume > 0:
            self._is_muted = False
        return old_volume, new_volume

    def mute(self) -> Tuple[int, int]:
        """
        Mute playback, saving current volume level.

        Returns:
            Tuple of (saved_volume, 0)
        """
        if not self._is_muted:
            self._previous_volume_before_mute = self._current_volume if self._current_volume > 0 else 50
            self._current_volume = 0
            self._is_muted = True
            logger.info("Volume muted. Saved previous level: %d%%", self._previous_volume_before_mute)
        return self._previous_volume_before_mute, 0

    def unmute(self) -> Tuple[int, int]:
        """
        Unmute playback, restoring previous volume.

        Returns:
            Tuple of (0, restored_volume)
        """
        if self._is_muted:
            restored = self._previous_volume_before_mute if self._previous_volume_before_mute > 0 else 50
            self._current_volume = restored
            self._is_muted = False
            logger.info("Volume unmuted. Restored level: %d%%", restored)
            return 0, restored
        return self._current_volume, self._current_volume
