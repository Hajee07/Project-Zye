#!/usr/bin/env python3
"""
ZYE AI — Pygame Audio Playback Engine v1.0
==========================================

Handles local MP3 audio playback using Pygame Mixer:
- Thread-safe, non-blocking playback loop within AsyncIO
- Serialized playback using AsyncIO Lock to prevent audio overlap
- Playback cancellation and interruption support
- Explicit file unloading to prevent Windows file locks on temporary files
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger("zye_voice.playback")

try:
    import pygame
    _PYGAME_AVAILABLE = True
except ImportError:
    pygame = None  # type: ignore
    _PYGAME_AVAILABLE = False


class PlaybackError(Exception):
    """Base exception for playback errors."""
    pass


class PlaybackDeviceUnavailableError(PlaybackError):
    """Raised when the audio output device cannot be initialized."""
    pass


@dataclass
class PlaybackConfig:
    """Configuration for Pygame Mixer playback."""
    enabled: bool = True
    mixer_frequency: int = 44100
    mixer_size: int = -16
    mixer_channels: int = 2
    mixer_buffer: int = 512
    poll_interval_seconds: float = 0.05


class ZyeAudioPlayback:
    """
    Manages audio playback of synthesized MP3 speech responses using Pygame mixer.
    Ensures safe resource release, cancellation, and lock-protected serialization.
    """

    def __init__(self, config: PlaybackConfig | None = None) -> None:
        self.config = config or PlaybackConfig()
        self._lock = asyncio.Lock()
        self._stop_requested = False
        self._is_playing = False
        self._current_file: str | None = None
        self._initialized = False

    def initialize(self) -> bool:
        """Initialize the Pygame mixer once if available."""
        if not self.config.enabled:
            logger.info("Pygame audio playback is disabled in configuration")
            return False

        if not _PYGAME_AVAILABLE:
            logger.warning("pygame package is not installed; playback unavailable")
            return False

        if self._initialized:
            return True

        try:
            if not pygame.mixer.get_init():
                try:
                    pygame.mixer.init(
                        frequency=self.config.mixer_frequency,
                        size=self.config.mixer_size,
                        channels=self.config.mixer_channels,
                        buffer=self.config.mixer_buffer,
                    )
                except Exception as p_err:
                    logger.debug("Hardware audio init failed (%s); using dummy SDL audio driver", p_err)
                    os.environ["SDL_AUDIODRIVER"] = "dummy"
                    pygame.mixer.init(
                        frequency=self.config.mixer_frequency,
                        size=self.config.mixer_size,
                        channels=self.config.mixer_channels,
                        buffer=self.config.mixer_buffer,
                    )
            self._initialized = True
            logger.info(
                "Pygame mixer initialized (freq=%d, channels=%d, buffer=%d)",
                self.config.mixer_frequency,
                self.config.mixer_channels,
                self.config.mixer_buffer,
            )
            return True
        except Exception as exc:
            logger.warning("Failed to initialize Pygame mixer: %s", exc)
            self._initialized = False
            return False

    async def play_mp3(self, file_path: str) -> bool:
        """
        Play an MP3 file to completion. Blocks asynchronously without freezing the loop.
        Acquires an internal lock so multiple speak requests queue up sequentially.
        """
        if not self.config.enabled or not _PYGAME_AVAILABLE:
            logger.debug("Playback skipped: disabled or unavailable")
            return False

        if not Path(file_path).is_file():
            logger.warning("MP3 file not found for playback: %s", file_path)
            return False

        if not self._initialized:
            if not self.initialize():
                return False

        async with self._lock:
            self._stop_requested = False
            self._is_playing = True
            self._current_file = file_path
            try:
                # Load and play on background thread if needed, or directly
                pygame.mixer.music.load(file_path)
                pygame.mixer.music.play()

                while pygame.mixer.music.get_busy() and not self._stop_requested:
                    await asyncio.sleep(self.config.poll_interval_seconds)

                return not self._stop_requested
            except Exception as exc:
                logger.warning("Error during MP3 playback of %s: %s", file_path, exc)
                return False
            finally:
                try:
                    if pygame.mixer.get_init():
                        pygame.mixer.music.stop()
                        pygame.mixer.music.unload()
                except Exception as unload_exc:
                    logger.debug("Pygame unload error: %s", unload_exc)
                self._is_playing = False
                self._current_file = None

    async def wait_until_finished(self) -> None:
        """Wait until current playback session concludes."""
        while self._is_playing:
            await asyncio.sleep(self.config.poll_interval_seconds)

    async def stop(self) -> None:
        """Interrupt and stop current playback immediately."""
        self._stop_requested = True
        if _PYGAME_AVAILABLE and self._initialized:
            try:
                if pygame.mixer.get_init():
                    pygame.mixer.music.stop()
                    pygame.mixer.music.unload()
            except Exception as exc:
                logger.debug("Stop audio error: %s", exc)
        self._is_playing = False
        self._current_file = None

    async def close(self) -> None:
        """Close playback engine and release mixer resources."""
        await self.stop()
        if _PYGAME_AVAILABLE and self._initialized:
            try:
                if pygame.mixer.get_init():
                    pygame.mixer.quit()
            except Exception as exc:
                logger.debug("Error quitting Pygame mixer: %s", exc)
        self._initialized = False

    def get_status(self) -> dict[str, Any]:
        """Return structured telemetry for playback subsystem."""
        mixer_init = False
        if _PYGAME_AVAILABLE and pygame.mixer:
            mixer_init = bool(pygame.mixer.get_init())
        return {
            "enabled": self.config.enabled,
            "pygame_available": _PYGAME_AVAILABLE,
            "mixer_initialized": mixer_init,
            "is_playing": self._is_playing,
            "current_file": self._current_file,
            "frequency": self.config.mixer_frequency,
            "channels": self.config.mixer_channels,
        }
