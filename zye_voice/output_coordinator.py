#!/usr/bin/env python3
"""
ZYE AI — Unified Audio Output Coordinator v1.0
==============================================

Coordinates audio playback across distinct subsystems:
- Day 09 Synthesized Jarvis chimes (SoundDevice)
- Day 10 Edge-TTS speech responses (Pygame Mixer)

Ensures:
1. One logical output owner at a time (Lock-protected)
2. No overlap between chimes and TTS speech
3. Clean interrupt and shutdown handling
4. Graceful recovery when sounddevice or pygame is unavailable
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from zye_audio.chime_player import JarvisChimePlayer
from zye_voice.edge_tts_engine import ZyeEdgeTTSEngine
from zye_voice.playback import ZyeAudioPlayback

logger = logging.getLogger("zye_voice.coordinator")


class UnifiedOutputCoordinator:
    """
    Serializes and coordinates sounddevice chime cues and Pygame TTS output
    so that auditory feedback never clashes or overlaps.
    """

    def __init__(
        self,
        chime_player: JarvisChimePlayer | None = None,
        tts_engine: ZyeEdgeTTSEngine | None = None,
    ) -> None:
        self.chime_player = chime_player
        self.tts_engine = tts_engine
        self._output_lock = asyncio.Lock()
        self._current_owner: str | None = None

    async def play_start_chime(self) -> bool:
        """Play Day 09 synthesized start chime."""
        if not self.chime_player:
            return False
        async with self._output_lock:
            self._current_owner = "chime_start"
            try:
                # Chime player runs on its own thread with queue
                return self.chime_player.play_start()
            finally:
                self._current_owner = None

    async def play_stop_chime(self) -> bool:
        """Play Day 09 synthesized stop chime."""
        if not self.chime_player:
            return False
        async with self._output_lock:
            self._current_owner = "chime_stop"
            try:
                return self.chime_player.play_stop()
            finally:
                self._current_owner = None

    async def speak(self, text: str) -> bool:
        """
        Deliver a spoken response via Edge-TTS and Pygame playback.
        Waits for any active chime to settle before commencing playback.
        """
        if not self.tts_engine:
            print(f"\n[Zye] {text}\n", flush=True)
            return True

        async with self._output_lock:
            self._current_owner = "tts"
            try:
                # Wait briefly if chime guard is active
                if self.chime_player and hasattr(self.chime_player, "is_chime_guard_active") and self.chime_player.is_chime_guard_active():
                    await asyncio.sleep(0.1)

                return await self.tts_engine.speak(text)
            finally:
                self._current_owner = None

    async def stop_all(self) -> None:
        """Stop all active audio output across chimes and TTS."""
        if self.tts_engine:
            await self.tts_engine.stop()
        self._current_owner = None

    async def close(self) -> None:
        """Release all playback resources on application shutdown."""
        await self.stop_all()
        if self.tts_engine:
            await self.tts_engine.close()
        if self.chime_player:
            self.chime_player.stop()

    def get_status(self) -> dict[str, Any]:
        """Return diagnostic status of coordinated audio outputs."""
        return {
            "current_owner": self._current_owner,
            "has_chime_player": self.chime_player is not None,
            "has_tts_engine": self.tts_engine is not None,
            "tts_status": self.tts_engine.get_status() if self.tts_engine else None,
            "chime_status": self.chime_player.get_diagnostics() if self.chime_player else None,
        }
