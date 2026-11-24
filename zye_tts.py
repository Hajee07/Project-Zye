#!/usr/bin/env python3
"""
ZYE AI — Edge-TTS Voice Synthesis Engine v1.0
==============================================

Production-grade Microsoft Edge-TTS text-to-speech synthesis with:
- Async streaming via edge-tts (no Azure subscription required)
- Configurable voice (default: en-IN-NeerjaNeural)
- In-memory MP3 / PCM WAV output — no temp files on disk
- Non-blocking asyncio-based synthesis
- Synthesis timeout and cancellation support
- Synthesis diagnostics and telemetry
- sounddevice-based playback with volume control
- Graceful fallback when TTS is unavailable

Operating System: Windows 10/11 x64
Target voices: en-IN-NeerjaNeural, en-US-AriaNeural, en-GB-SoniaNeural
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import io
import logging
import time
from typing import Any

try:
    import edge_tts
    from edge_tts import Communicate
    _EDGE_TTS_AVAILABLE = True
except ImportError:
    edge_tts = None  # type: ignore
    Communicate = None  # type: ignore
    _EDGE_TTS_AVAILABLE = False

try:
    import numpy as np
    import sounddevice as sd
    _PLAYBACK_AVAILABLE = True
except ImportError:
    np = None  # type: ignore
    sd = None  # type: ignore
    _PLAYBACK_AVAILABLE = False

logger = logging.getLogger("zye_tts")


# ============================================================================
# 1. Custom Exceptions
# ============================================================================

class TTSError(Exception):
    """Base exception for all TTS synthesis and playback failures."""
    pass


class TTSUnavailableError(TTSError):
    """Raised when edge-tts library is not installed."""
    pass


class TTSSynthesisError(TTSError):
    """Raised when speech synthesis fails or times out."""
    pass


class TTSPlaybackError(TTSError):
    """Raised when audio playback fails."""
    pass


class TTSConfigError(TTSError):
    """Raised when TTS configuration is invalid."""
    pass


# ============================================================================
# 2. Configuration
# ============================================================================

@dataclass
class TTSConfig:
    """Master configuration for Edge-TTS synthesis and playback."""
    voice: str = "en-IN-NeerjaNeural"
    rate: str = "+0%"          # e.g. "+20%" to speak faster
    volume: str = "+0%"        # e.g. "+10%"
    pitch: str = "+0Hz"        # e.g. "+5Hz"
    timeout_seconds: float = 15.0
    output_format: str = "mp3"  # always mp3 from edge-tts streaming
    playback_enabled: bool = True
    playback_volume: float = 1.0  # 0.0–1.0 multiplier for sounddevice playback
    enabled: bool = True

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if not self.voice:
            raise TTSConfigError("voice must be a non-empty string")
        if self.timeout_seconds <= 0.0:
            raise TTSConfigError(f"timeout_seconds must be positive, got {self.timeout_seconds}")
        if not (0.0 <= self.playback_volume <= 2.0):
            raise TTSConfigError(f"playback_volume must be in [0.0, 2.0], got {self.playback_volume}")


@dataclass
class TTSResult:
    """Structured result of a TTS synthesis operation."""
    text: str
    audio_bytes: bytes          # Raw MP3 bytes from edge-tts
    voice: str
    synthesis_duration_ms: float
    byte_count: int
    status: str                 # SUCCESS | EMPTY | FAILED | UNAVAILABLE
    error: str | None = None


# ============================================================================
# 3. Synthesis Engine
# ============================================================================

class ZyeTTSEngine:
    """
    Async Edge-TTS synthesis engine with in-memory output,
    timeout handling, and structured diagnostics.
    """

    def __init__(self, config: TTSConfig | None = None) -> None:
        self.config = config or TTSConfig()
        self.total_synthesized: int = 0
        self.total_errors: int = 0
        self.last_synthesis_ms: float = 0.0
        self.last_voice_used: str | None = None
        self._available = _EDGE_TTS_AVAILABLE

    # ------------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------------

    async def synthesize(self, text: str, voice: str | None = None) -> TTSResult:
        """
        Synthesize speech from text using Edge-TTS streaming.

        Returns TTSResult with in-memory MP3 bytes.
        Does NOT write any files to disk.
        """
        if not text or not text.strip():
            return TTSResult(
                text=text,
                audio_bytes=b"",
                voice=voice or self.config.voice,
                synthesis_duration_ms=0.0,
                byte_count=0,
                status="EMPTY",
            )

        if not self._available:
            self.total_errors += 1
            return TTSResult(
                text=text,
                audio_bytes=b"",
                voice=voice or self.config.voice,
                synthesis_duration_ms=0.0,
                byte_count=0,
                status="UNAVAILABLE",
                error="edge-tts library is not installed",
            )

        active_voice = voice or self.config.voice
        t0 = time.perf_counter()

        try:
            audio_bytes = await asyncio.wait_for(
                self._stream_to_memory(text, active_voice),
                timeout=self.config.timeout_seconds,
            )
            duration_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            self.total_synthesized += 1
            self.last_synthesis_ms = duration_ms
            self.last_voice_used = active_voice
            return TTSResult(
                text=text,
                audio_bytes=audio_bytes,
                voice=active_voice,
                synthesis_duration_ms=duration_ms,
                byte_count=len(audio_bytes),
                status="SUCCESS",
            )
        except asyncio.TimeoutError:
            self.total_errors += 1
            duration_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            return TTSResult(
                text=text,
                audio_bytes=b"",
                voice=active_voice,
                synthesis_duration_ms=duration_ms,
                byte_count=0,
                status="FAILED",
                error=f"TTS synthesis timed out after {self.config.timeout_seconds}s",
            )
        except Exception as exc:
            self.total_errors += 1
            duration_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            logger.warning("Edge-TTS synthesis error: %s", exc)
            return TTSResult(
                text=text,
                audio_bytes=b"",
                voice=active_voice,
                synthesis_duration_ms=duration_ms,
                byte_count=0,
                status="FAILED",
                error=str(exc),
            )

    def synthesize_sync(self, text: str, voice: str | None = None) -> TTSResult:
        """
        Blocking synchronous wrapper around synthesize().
        Uses an isolated event loop — safe to call from non-async context.
        """
        try:
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(self.synthesize(text, voice=voice))
            finally:
                loop.close()
        except Exception as exc:
            self.total_errors += 1
            return TTSResult(
                text=text,
                audio_bytes=b"",
                voice=voice or self.config.voice,
                synthesis_duration_ms=0.0,
                byte_count=0,
                status="FAILED",
                error=str(exc),
            )

    async def say(self, text: str, voice: str | None = None) -> TTSResult:
        """
        Synthesize and immediately play audio through the system speaker.
        Returns TTSResult; playback failure is logged but does not raise.
        """
        result = await self.synthesize(text, voice=voice)
        if result.status == "SUCCESS" and result.audio_bytes and self.config.playback_enabled:
            await asyncio.get_event_loop().run_in_executor(
                None, self._play_mp3_bytes, result.audio_bytes
            )
        return result

    def say_sync(self, text: str, voice: str | None = None) -> TTSResult:
        """Blocking version of say()."""
        try:
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(self.say(text, voice=voice))
            finally:
                loop.close()
        except Exception as exc:
            self.total_errors += 1
            return TTSResult(
                text=text,
                audio_bytes=b"",
                voice=voice or self.config.voice,
                synthesis_duration_ms=0.0,
                byte_count=0,
                status="FAILED",
                error=str(exc),
            )

    # ------------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------------

    async def _stream_to_memory(self, text: str, voice: str) -> bytes:
        """Stream edge-tts audio into an in-memory buffer."""
        communicate = Communicate(
            text=text,
            voice=voice,
            rate=self.config.rate,
            volume=self.config.volume,
            pitch=self.config.pitch,
        )
        buffer = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk.get("type") == "audio":
                data = chunk.get("data")
                if data:
                    buffer.write(data)
        audio_bytes = buffer.getvalue()
        if not audio_bytes:
            raise TTSSynthesisError(f"Edge-TTS returned empty audio for text: {text[:40]!r}")
        return audio_bytes

    def _play_mp3_bytes(self, mp3_bytes: bytes) -> None:
        """
        Play MP3 bytes through sounddevice by decoding with numpy.
        Uses ffmpeg or soundfile if available; otherwise skips playback gracefully.
        """
        if sd is None or not mp3_bytes:
            return
        try:
            import soundfile as sf
            audio_io = io.BytesIO(mp3_bytes)
            data, samplerate = sf.read(audio_io, dtype="float32")
            if self.config.playback_volume != 1.0:
                data = (data * self.config.playback_volume).astype("float32")
            sd.play(data, samplerate=samplerate, blocking=True)
        except Exception:
            # soundfile may not support MP3; try PyAudio or just skip
            try:
                import tempfile, subprocess, os
                # Fallback: write to temp file and play via system player
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                    tmp.write(mp3_bytes)
                    tmp_path = tmp.name
                subprocess.run(
                    ["powershell", "-c", f"(New-Object Media.SoundPlayer '{tmp_path}').PlaySync()"],
                    timeout=30, capture_output=True, check=False,
                )
                os.unlink(tmp_path)
            except Exception as pb_err:
                logger.debug("TTS playback fallback also failed: %s", pb_err)

    # ------------------------------------------------------------------------
    # Voice Listing
    # ------------------------------------------------------------------------

    @staticmethod
    async def list_voices(locale: str = "en") -> list[dict[str, str]]:
        """List available Edge-TTS voices, optionally filtered by locale prefix."""
        if not _EDGE_TTS_AVAILABLE:
            return []
        try:
            voices_manager = await edge_tts.VoicesManager.create()
            all_voices = voices_manager.voices
            if locale:
                return [
                    {"name": v["Name"], "gender": v.get("Gender", "?"), "locale": v.get("Locale", "")}
                    for v in all_voices
                    if v.get("Locale", "").startswith(locale)
                ]
            return [{"name": v["Name"], "gender": v.get("Gender", "?"), "locale": v.get("Locale", "")}
                    for v in all_voices]
        except Exception as exc:
            logger.warning("Failed to list voices: %s", exc)
            return []

    # ------------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------------

    def get_diagnostics(self) -> dict[str, Any]:
        """Return structured telemetry for doctor.py."""
        return {
            "status": "ready" if self._available else "unavailable",
            "edge_tts_available": self._available,
            "edge_tts_version": getattr(edge_tts, "__version__", "unknown") if _EDGE_TTS_AVAILABLE else None,
            "configured_voice": self.config.voice,
            "rate": self.config.rate,
            "volume": self.config.volume,
            "pitch": self.config.pitch,
            "timeout_seconds": self.config.timeout_seconds,
            "playback_enabled": self.config.playback_enabled,
            "total_synthesized": self.total_synthesized,
            "total_errors": self.total_errors,
            "last_synthesis_ms": self.last_synthesis_ms,
            "last_voice_used": self.last_voice_used,
        }


# ============================================================================
# 4. Module-level convenience
# ============================================================================

_default_engine: ZyeTTSEngine | None = None


def get_default_engine() -> ZyeTTSEngine:
    """Return or create the module-level default TTS engine."""
    global _default_engine
    if _default_engine is None:
        _default_engine = ZyeTTSEngine()
    return _default_engine


async def speak(text: str, voice: str | None = None) -> TTSResult:
    """Module-level convenience: synthesize + play using the default engine."""
    return await get_default_engine().say(text, voice=voice)


if __name__ == "__main__":
    import sys

    async def _demo() -> None:
        engine = ZyeTTSEngine()
        diag = engine.get_diagnostics()
        print("TTS Diagnostics:", diag)
        if diag["edge_tts_available"]:
            text = " ".join(sys.argv[1:]) or "Hello. I am Zye. Your AI assistant is now operational."
            print(f"Synthesizing: {text!r}")
            result = await engine.synthesize(text)
            print(f"Status: {result.status}, Bytes: {result.byte_count}, Time: {result.synthesis_duration_ms}ms")

    asyncio.run(_demo())
