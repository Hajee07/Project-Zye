"""
ZYE AI — Audio Lifecycle Adapter
================================

Connects Gemini Live listening and output events to AudioDucker:
- When user begins speaking -> trigger duck()
- When assistant finishes turn / speech stops -> trigger unduck()
- When speech interrupted -> trigger unduck(force=True)
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional
from zye_music.audio_ducking import AudioDucker

logger = logging.getLogger("zye.music.lifecycle")


class AudioLifecycleAdapter:
    """Adapter receiving voice activity events and forwarding them to AudioDucker."""

    def __init__(self, ducker: Optional[AudioDucker] = None) -> None:
        self.ducker = ducker

    def set_ducker(self, ducker: AudioDucker) -> None:
        """Register or update active ducker."""
        self.ducker = ducker

    async def on_user_speech_started(self) -> None:
        """Called when user starts speaking (VAD / microphone active)."""
        if self.ducker:
            await self.ducker.duck()

    async def on_user_speech_ended(self) -> None:
        """Called when user stops speaking."""
        # Note: We keep ducked if the assistant is about to respond
        pass

    async def on_assistant_speech_started(self) -> None:
        """Called when assistant begins TTS audio playback."""
        if self.ducker:
            await self.ducker.duck()

    async def on_assistant_speech_ended(self) -> None:
        """Called when assistant finishes speaking."""
        if self.ducker:
            await self.ducker.unduck()

    async def on_interaction_complete(self) -> None:
        """Called when conversational turn is completely resolved."""
        if self.ducker:
            await self.ducker.unduck(force=True)

    async def on_interrupted(self) -> None:
        """Called when speech was interrupted by user."""
        if self.ducker:
            await self.ducker.unduck(force=True)
