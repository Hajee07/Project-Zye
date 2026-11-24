#!/usr/bin/env python3
"""
ZYE AI — Edge-TTS Neural Voice Engine v2.0
==========================================

Converts assistant responses to neural speech using Microsoft Edge-TTS:
- High-fidelity voice: en-IN-NeerjaNeural (default)
- English, Tamil, Tanglish and technical terminology support
- Chunked sentence synthesis for long responses
- Safe temporary MP3 lifecycle on Windows (close before write, safe unlink in finally)
- Seamless integration with Pygame playback
- Zero raw audio transmitted; cloud TTS privacy switch with console fallback
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from zye_voice.playback import ZyeAudioPlayback, PlaybackConfig

logger = logging.getLogger("zye_voice.edge_tts")

try:
    import edge_tts
    _EDGE_TTS_AVAILABLE = True
except ImportError:
    edge_tts = None  # type: ignore
    _EDGE_TTS_AVAILABLE = False


class TTSError(Exception):
    """Base exception for TTS operations."""
    pass


class TTSUnavailableError(TTSError):
    """Raised when edge-tts library is not installed."""
    pass


class TTSTimeoutError(TTSError):
    """Raised when voice generation exceeds timeout."""
    pass


@dataclass
class EdgeTTSConfig:
    """Master configuration for Edge-TTS neural speech engine."""
    enabled: bool = True
    provider: str = "edge_tts"
    voice: str = "en-IN-NeerjaNeural"
    format: str = "mp3"
    timeout_seconds: float = 30.0
    max_retries: int = 1
    retry_delay_seconds: float = 1.0
    max_text_chars: int = 4000
    allow_cloud_tts: bool = True
    rate: str = "+0%"
    volume: str = "+0%"
    pitch: str = "+0Hz"


def split_into_sentences(text: str, max_chars: int = 400) -> list[str]:
    """
    Split long text into sentence-based chunks without breaking mid-word
    or corrupting punctuation. Preserves sentence order.
    """
    if not text:
        return []

    # Split on sentence boundaries: periods, exclamation marks, question marks
    raw_sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    chunks: list[str] = []
    current_chunk = ""

    for sentence in raw_sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        if len(current_chunk) + len(sentence) + 1 <= max_chars:
            current_chunk = f"{current_chunk} {sentence}".strip()
        else:
            if current_chunk:
                chunks.append(current_chunk)
            if len(sentence) > max_chars:
                # Break long sentence cleanly at word boundaries
                words = sentence.split()
                sub_chunk = ""
                for w in words:
                    if len(sub_chunk) + len(w) + 1 <= max_chars:
                        sub_chunk = f"{sub_chunk} {w}".strip()
                    else:
                        if sub_chunk:
                            chunks.append(sub_chunk)
                        sub_chunk = w
                if sub_chunk:
                    current_chunk = sub_chunk
                else:
                    current_chunk = ""
            else:
                current_chunk = sentence

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


class ZyeEdgeTTSEngine:
    """
    Edge-TTS Neural Voice Engine managing async generation, sentence chunking,
    temporary MP3 lifecycle, and playback coordination.
    """

    def __init__(
        self,
        config: EdgeTTSConfig | None = None,
        playback: ZyeAudioPlayback | None = None,
    ) -> None:
        self.config = config or EdgeTTSConfig()
        self.playback = playback or ZyeAudioPlayback()
        self._available = _EDGE_TTS_AVAILABLE
        self.total_generated: int = 0
        self.total_errors: int = 0
        self.last_latency_ms: float = 0.0

    async def initialize(self) -> bool:
        """Initialize TTS engine and underlying playback system."""
        if not self.config.enabled:
            logger.info("Edge-TTS voice engine is disabled")
            return False

        if not self._available:
            logger.warning("edge-tts package is not installed")
            return False

        # Initialize audio playback
        self.playback.initialize()
        return True

    async def generate_audio(self, text: str) -> str | None:
        """
        Generate MP3 audio from text using Edge-TTS.
        Returns the path to a temporary MP3 file, or None on failure.
        Caller is responsible for cleaning up the temporary file.
        """
        if not text or not text.strip():
            logger.debug("generate_audio called with empty text")
            return None

        if not self.config.enabled or not self.config.allow_cloud_tts or not self._available:
            logger.info("Cloud TTS not permitted or unavailable; skipping audio generation")
            return None

        # Truncate if exceeds maximum allowed text length
        clean_text = text[: self.config.max_text_chars].strip()

        # Step 1: Create a temporary file and immediately close handle (Windows requirement)
        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tmp_path = tmp.name
        tmp.close()

        t0 = time.perf_counter()
        attempt = 0
        success = False

        while attempt <= self.config.max_retries and not success:
            attempt += 1
            try:
                communicate = edge_tts.Communicate(
                    clean_text,
                    voice=self.config.voice,
                    rate=self.config.rate,
                    volume=self.config.volume,
                    pitch=self.config.pitch,
                )
                await asyncio.wait_for(
                    communicate.save(tmp_path),
                    timeout=self.config.timeout_seconds,
                )
                success = True
                self.last_latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
                self.total_generated += 1
                return tmp_path
            except asyncio.TimeoutError:
                logger.warning(
                    "Edge-TTS synthesis timed out after %.1fs (attempt %d/%d)",
                    self.config.timeout_seconds,
                    attempt,
                    self.config.max_retries + 1,
                )
            except Exception as exc:
                logger.warning(
                    "Edge-TTS synthesis error on attempt %d/%d: %s",
                    attempt,
                    self.config.max_retries + 1,
                    exc,
                )
                if attempt <= self.config.max_retries:
                    await asyncio.sleep(self.config.retry_delay_seconds)

        self.total_errors += 1
        # Cleanup temporary file if generation failed
        self._safe_remove_file(tmp_path)
        return None

    async def speak(self, text: str) -> bool:
        """
        Synthesize speech from text and play it through the speaker.
        Always prints response in terminal as reliable fallback.
        Safely unloads and deletes the temporary MP3 in all circumstances.
        """
        if not text or not text.strip():
            return False

        # If long response, delegate to sentence-based chunks
        if len(text) > 400:
            return await self.speak_chunks(text)

        # Print to terminal
        print(f"\n[Zye] {text}\n", flush=True)

        if not self.config.allow_cloud_tts or not self.config.enabled:
            return True

        mp3_path = await self.generate_audio(text)
        if not mp3_path:
            logger.info("Speech audio unavailable; response delivered via terminal")
            return False

        try:
            return await self.playback.play_mp3(mp3_path)
        finally:
            self._safe_remove_file(mp3_path)

    async def say(self, text: str) -> Any:
        """Compatibility alias for speak()."""
        return await self.speak(text)

    async def speak_chunks(self, text: str) -> bool:
        """
        Split long response into natural sentence chunks and speak them sequentially.
        Ensures chunks do not overlap.
        """
        chunks = split_into_sentences(text, max_chars=350)
        if not chunks:
            return False

        print(f"\n[Zye] {text}\n", flush=True)

        overall_success = True
        for chunk in chunks:
            if not self.config.allow_cloud_tts or not self.config.enabled:
                break
            mp3_path = await self.generate_audio(chunk)
            if mp3_path:
                try:
                    played = await self.playback.play_mp3(mp3_path)
                    if not played:
                        overall_success = False
                finally:
                    self._safe_remove_file(mp3_path)
            else:
                overall_success = False

        return overall_success

    async def stop(self) -> None:
        """Stop current speech playback."""
        await self.playback.stop()

    async def close(self) -> None:
        """Close TTS engine and release resources."""
        await self.playback.close()

    def get_status(self) -> dict[str, Any]:
        """Return structured telemetry for TTS engine."""
        return {
            "enabled": self.config.enabled,
            "provider": self.config.provider,
            "voice": self.config.voice,
            "available": self._available,
            "allow_cloud_tts": self.config.allow_cloud_tts,
            "total_generated": self.total_generated,
            "total_errors": self.total_errors,
            "last_latency_ms": self.last_latency_ms,
            "playback": self.playback.get_status(),
        }

    @staticmethod
    def _safe_remove_file(file_path: str) -> None:
        """Safely delete a temporary file with retry to handle Windows file lock delays."""
        path = Path(file_path)
        if not path.is_file():
            return
        for _ in range(3):
            try:
                os.unlink(path)
                return
            except (PermissionError, OSError):
                time.sleep(0.05)
        logger.debug("Could not immediately remove temporary file: %s", file_path)
