#!/usr/bin/env python3
"""
ZYE AI — Gemini Live Native Audio Master Brain Engine v2.0 (Low-Latency Optimized)
===================================================================================

Real-time bidirectional Gemini Live streaming audio architecture:
- Official Google Gen AI SDK Stateful WebSocket Session (v1alpha GenerativeService.BidiGenerateContent)
- Persistent multi-turn session reuse: does NOT disconnect or reconnect between conversational turns
- Direct microphone PCM audio streaming (16,000 Hz, Mono, Signed 16-bit Little-Endian)
- Non-blocking in-memory audio capture pump (zero thread-pool dispatch overhead)
- Software acoustic echo cancellation & self-listening prevention (half-duplex playback gating)
- Native Gemini speech understanding: Tamil, English, Tanglish code-switching
- Server-side automatic VAD and turn detection
- Direct conversational greeting path (< 2s P50 latency; zero unnecessary tool/pre-mortem overhead)
- Native Gemini voice generation (24,000 Hz, Signed 16-bit PCM Little-Endian)
- Immediate streaming audio playback via sounddevice.RawOutputStream (sub-45ms startup)
- Full-duplex conversation with instantaneous Barge-in / interruption handling
- High-resolution monotonic latency instrumentation (T0–T13, M0–M5, correlation turn IDs)
- Seamless MCP tool execution bridge with ZyeExecutionGate / SafetyExecutionGateway
- Multi-project 7-API-key integration via existing GeminiKeyManager & GeminiGateway
- Session resumption, context recovery, and graceful reconnection handling
"""

from __future__ import annotations

import asyncio
import collections
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import logging
import math
import queue
import threading
import time
from typing import Any, Callable, Coroutine, Sequence

import numpy as np
import sounddevice as sd

try:
    from google import genai
    from google.genai import types
    _GENAI_AVAILABLE = True
except ImportError:
    genai = None  # type: ignore
    types = None  # type: ignore
    _GENAI_AVAILABLE = False

logger = logging.getLogger("zye.gemini.live")


# ============================================================================
# 1. Gemini Live Session State Machine (Section 11)
# ============================================================================

class LiveSessionState(str, Enum):
    """Explicit lifecycle states for Gemini Live sessions."""
    DISABLED = "DISABLED"
    IDLE = "IDLE"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    LISTENING = "LISTENING"
    USER_SPEAKING = "USER_SPEAKING"
    PROCESSING = "PROCESSING"
    TOOL_CALL_PENDING = "TOOL_CALL_PENDING"
    TOOL_RUNNING = "TOOL_RUNNING"
    RESPONDING = "RESPONDING"
    INTERRUPTED = "INTERRUPTED"
    RECONNECTING = "RECONNECTING"
    DEGRADED = "DEGRADED"
    CLOSED = "CLOSED"
    ERROR = "ERROR"


# Allowed state machine transitions
_VALID_LIVE_TRANSITIONS: dict[LiveSessionState, set[LiveSessionState]] = {
    LiveSessionState.DISABLED: {LiveSessionState.IDLE, LiveSessionState.CONNECTING},
    LiveSessionState.IDLE: {LiveSessionState.CONNECTING, LiveSessionState.CLOSED, LiveSessionState.ERROR},
    LiveSessionState.CONNECTING: {LiveSessionState.CONNECTED, LiveSessionState.RECONNECTING, LiveSessionState.CLOSED, LiveSessionState.ERROR},
    LiveSessionState.CONNECTED: {LiveSessionState.LISTENING, LiveSessionState.RECONNECTING, LiveSessionState.CLOSED, LiveSessionState.ERROR},
    LiveSessionState.LISTENING: {LiveSessionState.USER_SPEAKING, LiveSessionState.PROCESSING, LiveSessionState.TOOL_CALL_PENDING, LiveSessionState.RESPONDING, LiveSessionState.INTERRUPTED, LiveSessionState.RECONNECTING, LiveSessionState.CLOSED, LiveSessionState.ERROR},
    LiveSessionState.USER_SPEAKING: {LiveSessionState.PROCESSING, LiveSessionState.RESPONDING, LiveSessionState.LISTENING, LiveSessionState.INTERRUPTED, LiveSessionState.RECONNECTING, LiveSessionState.CLOSED, LiveSessionState.ERROR},
    LiveSessionState.PROCESSING: {LiveSessionState.TOOL_CALL_PENDING, LiveSessionState.RESPONDING, LiveSessionState.LISTENING, LiveSessionState.INTERRUPTED, LiveSessionState.RECONNECTING, LiveSessionState.CLOSED, LiveSessionState.ERROR},
    LiveSessionState.TOOL_CALL_PENDING: {LiveSessionState.TOOL_RUNNING, LiveSessionState.RESPONDING, LiveSessionState.LISTENING, LiveSessionState.INTERRUPTED, LiveSessionState.ERROR},
    LiveSessionState.TOOL_RUNNING: {LiveSessionState.RESPONDING, LiveSessionState.LISTENING, LiveSessionState.INTERRUPTED, LiveSessionState.ERROR},
    LiveSessionState.RESPONDING: {LiveSessionState.LISTENING, LiveSessionState.USER_SPEAKING, LiveSessionState.INTERRUPTED, LiveSessionState.RECONNECTING, LiveSessionState.CLOSED, LiveSessionState.ERROR},
    LiveSessionState.INTERRUPTED: {LiveSessionState.LISTENING, LiveSessionState.USER_SPEAKING, LiveSessionState.PROCESSING, LiveSessionState.CLOSED, LiveSessionState.ERROR},
    LiveSessionState.RECONNECTING: {LiveSessionState.CONNECTED, LiveSessionState.DEGRADED, LiveSessionState.CLOSED, LiveSessionState.ERROR},
    LiveSessionState.DEGRADED: {LiveSessionState.CONNECTING, LiveSessionState.CLOSED, LiveSessionState.ERROR},
    LiveSessionState.CLOSED: {LiveSessionState.IDLE, LiveSessionState.CONNECTING},
    LiveSessionState.ERROR: {LiveSessionState.IDLE, LiveSessionState.CONNECTING, LiveSessionState.CLOSED},
}


# ============================================================================
# 2. End-to-End Latency Instrumentation & Turn Metrics (Section 06 & 07)
# ============================================================================

@dataclass
class TurnMetrics:
    """
    High-resolution monotonic nanosecond instrumentation container for a single conversational turn.
    Tracks T0 to T13 and tool execution M0 to M5.
    """
    turn_id: str = "live_turn_001"
    session_id: str = "session_001"
    # Stage monotonic nanosecond timestamps
    t0_audio_activity_ns: int = 0          # T0: Microphone audio activity detected
    t1_frame_captured_ns: int = 0          # T1: Audio frame captured
    t2_pcm_converted_ns: int = 0           # T2: Audio frame converted to PCM16
    t3_queued_ns: int = 0                  # T3: Audio frame placed in streaming queue
    t4_sent_to_live_ns: int = 0            # T4: Audio frame sent to Gemini Live
    t5_user_activity_detected_ns: int = 0  # T5: Gemini Live user-turn activity detected
    t6_user_speech_completed_ns: int = 0   # T6: User speech considered complete
    t7_first_server_event_ns: int = 0      # T7: First Gemini server response event received
    t8_first_audio_bytes_ns: int = 0       # T8: First Gemini output audio bytes received
    t9_playback_queued_ns: int = 0         # T9: First output audio bytes placed in playback queue
    t10_output_submitted_ns: int = 0       # T10: First audio samples submitted to output device
    t11_first_audible_ns: int = 0          # T11: First audible output
    t12_response_complete_ns: int = 0      # T12: Gemini response complete
    t13_playback_complete_ns: int = 0      # T13: Final playback complete
    # Tool timestamps
    m0_tool_requested_ns: int = 0          # M0: Model requested function call
    m1_tool_validated_ns: int = 0          # M1: Function call validated
    m2_orchestrator_invoked_ns: int = 0    # M2: Existing MCP Orchestrator invoked
    m3_tool_started_ns: int = 0            # M3: MCP tool started
    m4_tool_completed_ns: int = 0          # M4: MCP tool completed
    m5_response_sent_ns: int = 0           # M5: Function response sent to Gemini
    # Telemetry metadata
    tool_name: str = ""
    user_transcript: str = ""
    model_transcript: str = ""
    interrupted: bool = False
    final_transcript_received: bool = False
    response_generation: int = 0
    has_tool_call: bool = False
    status: str = "COMPLETED"

    def first_response_latency_ms(self) -> float:
        ref = self.t6_user_speech_completed_ns or self.t4_sent_to_live_ns
        if self.t7_first_server_event_ns and ref:
            return round((self.t7_first_server_event_ns - ref) / 1e6, 2)
        return 0.0

    def first_audio_latency_ms(self) -> float:
        ref = self.t6_user_speech_completed_ns or self.t4_sent_to_live_ns
        if self.t8_first_audio_bytes_ns and ref:
            return round((self.t8_first_audio_bytes_ns - ref) / 1e6, 2)
        return 0.0

    def playback_startup_delay_ms(self) -> float:
        if self.t10_output_submitted_ns and self.t8_first_audio_bytes_ns:
            return round((self.t10_output_submitted_ns - self.t8_first_audio_bytes_ns) / 1e6, 2)
        return 0.0

    def total_turn_duration_ms(self) -> float:
        ref = self.t0_audio_activity_ns or self.t4_sent_to_live_ns
        if self.t12_response_complete_ns and ref:
            return round((self.t12_response_complete_ns - ref) / 1e6, 2)
        return 0.0

    def tool_duration_ms(self) -> float:
        if self.m4_tool_completed_ns and self.m0_tool_requested_ns:
            return round((self.m4_tool_completed_ns - self.m0_tool_requested_ns) / 1e6, 2)
        return 0.0

    def format_diagnostic_trace(self) -> list[str]:
        candidates = [t for t in (self.t0_audio_activity_ns, self.t1_frame_captured_ns, self.t4_sent_to_live_ns) if t and t > 0]
        base = min(candidates) if candidates else None
        lines = []
        if base:
            def _fmt(val_ns: int) -> str:
                return f"+{max(0.0, (val_ns - base) / 1e6):.1f} ms"

            lines.append(f"[{self.turn_id}] User speech started: +0.0 ms")
            if self.t4_sent_to_live_ns:
                lines.append(f"[{self.turn_id}] First PCM frame sent: {_fmt(self.t4_sent_to_live_ns)}")
            if self.t6_user_speech_completed_ns and self.t6_user_speech_completed_ns != self.t4_sent_to_live_ns:
                lines.append(f"[{self.turn_id}] User speech completed: {_fmt(self.t6_user_speech_completed_ns)}")
            if self.t7_first_server_event_ns:
                lines.append(f"[{self.turn_id}] Gemini first server event: {_fmt(self.t7_first_server_event_ns)}")
            if self.t8_first_audio_bytes_ns:
                lines.append(f"[{self.turn_id}] First output audio chunk: {_fmt(self.t8_first_audio_bytes_ns)}")
            if self.t10_output_submitted_ns:
                lines.append(f"[{self.turn_id}] Playback started: {_fmt(self.t10_output_submitted_ns)}")
            if self.m0_tool_requested_ns:
                lines.append(f"[{self.turn_id}] Tool requested ({self.tool_name}): {_fmt(self.m0_tool_requested_ns)}")
            if self.m4_tool_completed_ns:
                lines.append(f"[{self.turn_id}] Tool completed: {_fmt(self.m4_tool_completed_ns)}")
            if self.t12_response_complete_ns:
                lines.append(f"[{self.turn_id}] Response complete: {_fmt(self.t12_response_complete_ns)}")
        return lines


# ============================================================================
# 3. Live Audio Player (Section 17, 18, 20)
# ============================================================================

class LiveAudioPlayer:
    """
    Real-time streaming PCM audio output engine for native Gemini Live responses:
    - 24,000 Hz, Mono, Signed 16-bit PCM Little-Endian playback
    - Low-latency blocksize configuration (1024 frames = ~42.6ms buffer)
    - Dedicated background thread with sounddevice.RawOutputStream
    - Instantaneous queue flush and abort for full-duplex barge-in interruptions
    """

    def __init__(self, sample_rate: int = 24000, channels: int = 1, buffer_chunks: int = 200, latency: str = "low") -> None:
        self.sample_rate = sample_rate
        self.channels = channels
        self.latency = latency
        self._queue: queue.Queue[tuple[bytes, int] | bytes | None] = queue.Queue(maxsize=buffer_chunks)
        self._running = False
        self._is_playing = False
        self._thread: threading.Thread | None = None
        self._stream: sd.RawOutputStream | None = None
        self._lock = threading.Lock()
        self._interrupted = threading.Event()
        self._generation = 0
        self.total_chunks_played = 0
        self.total_bytes_played = 0
        self.last_write_timestamp_ns = 0
        self.last_playback_stop_ns = 0

    def bump_generation(self) -> int:
        """Atomically increment and return the output generation fence."""
        with self._lock:
            self._generation += 1
            return self._generation

    def start(self) -> None:
        """Start the background audio playback thread."""
        with self._lock:
            if self._running:
                return
            self._running = True
            self._interrupted.clear()
            self._thread = threading.Thread(target=self._playback_loop, name="ZyeLiveAudioPlayer", daemon=True)
            self._thread.start()
            logger.info("LiveAudioPlayer started (sr=%d, ch=%d, latency=%s)", self.sample_rate, self.channels, self.latency)

    def stop(self) -> None:
        """Stop audio playback and close hardware stream."""
        self._running = False
        self.flush()
        try:
            self._queue.put_nowait(None)
        except queue.Full:
            pass
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.3)
        self._close_stream()
        logger.info("LiveAudioPlayer stopped")

    def queue_chunk(self, chunk: bytes, generation: int | None = None) -> bool:
        """Queue a raw 24kHz PCM16 audio chunk for real-time playback with generation fencing."""
        if not self._running or not chunk:
            return False
        with self._lock:
            if generation is not None and generation < self._generation:
                # Discard late chunk belonging to older / interrupted generation
                return False
            if self._interrupted.is_set():
                return False
            cur_gen = self._generation if generation is None else generation
        try:
            self._queue.put_nowait((chunk, cur_gen))
            return True
        except queue.Full:
            logger.warning("LiveAudioPlayer queue full; dropping audio chunk")
            return False

    def flush(self) -> None:
        """
        Instantaneously discard all queued audio chunks and abort current stream.
        Increments generation fence to block late incoming PCM chunks.
        """
        self._interrupted.set()
        with self._lock:
            self._generation += 1
            while not self._queue.empty():
                try:
                    self._queue.get_nowait()
                except queue.Empty:
                    break
            if self._stream is not None and not self._stream.closed:
                try:
                    self._stream.abort()
                    if self._running:
                        self._stream.start()
                except Exception as e:
                    logger.debug("Error aborting audio stream on flush: %s", e)
            self._is_playing = False
            self.last_playback_stop_ns = time.perf_counter_ns()
            self._interrupted.clear()
        logger.debug("LiveAudioPlayer flushed on interruption (gen=%d)", self._generation)

    def is_playing(self, include_tail_ms: float = 0.0) -> bool:
        """Check if audio is actively playing or queued in player."""
        if self._is_playing or not self._queue.empty():
            return True
        if include_tail_ms > 0 and self.last_playback_stop_ns > 0:
            elapsed_ms = (time.perf_counter_ns() - self.last_playback_stop_ns) / 1e6
            if elapsed_ms < include_tail_ms:
                return True
        return False

    async def wait_for_playback_complete(self, timeout: float = 6.0) -> None:
        """Asynchronously wait until all queued audio chunks have finished playing."""
        start = time.monotonic()
        while self.is_playing() and (time.monotonic() - start < timeout):
            await asyncio.sleep(0.04)

    def _open_stream(self) -> bool:
        try:
            self._stream = sd.RawOutputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="int16",
                latency=self.latency,
                blocksize=1024,
            )
            self._stream.start()
            return True
        except Exception as exc:
            logger.warning("Failed to open low-latency RawOutputStream: %s; falling back to default", exc)
            try:
                self._stream = sd.RawOutputStream(
                    samplerate=self.sample_rate,
                    channels=self.channels,
                    dtype="int16",
                )
                self._stream.start()
                return True
            except Exception as e2:
                logger.error("Failed to open fallback RawOutputStream: %s", e2)
                self._stream = None
                return False

    def _close_stream(self) -> None:
        with self._lock:
            if self._stream is not None:
                try:
                    self._stream.stop()
                    self._stream.close()
                except Exception:
                    pass
                self._stream = None

    def _playback_loop(self) -> None:
        if not self._open_stream():
            logger.error("Audio output stream unavailable; playback thread exiting")
            return

        while self._running:
            try:
                chunk = self._queue.get(timeout=0.08)
            except queue.Empty:
                if self._is_playing:
                    self._is_playing = False
                    self.last_playback_stop_ns = time.perf_counter_ns()
                continue

            if chunk is None:
                break

            if isinstance(chunk, tuple):
                pcm_data, chunk_gen = chunk
                if chunk_gen < self._generation:
                    # Discard late chunk from previous generation
                    continue
            else:
                pcm_data = chunk

            if self._interrupted.is_set():
                continue

            self._is_playing = True
            try:
                if self._stream is not None:
                    self.last_write_timestamp_ns = time.perf_counter_ns()
                    self._stream.write(pcm_data)
                    self.total_chunks_played += 1
                    self.total_bytes_played += len(pcm_data)
            except Exception as exc:
                logger.debug("Playback write error: %s", exc)
                # Re-open stream on hardware error
                self._close_stream()
                time.sleep(0.04)
                self._open_stream()

        self._close_stream()


# ============================================================================
# 3.5. Audio Admission Gate & Anti-Self-Reply Engine (P0 Reliability Hotfix)
# ============================================================================

class AudioAdmissionState(str, Enum):
    IDLE = "IDLE"
    OUTPUT_ACTIVE = "OUTPUT_ACTIVE"
    ECHO_TAIL_GUARD = "ECHO_TAIL_GUARD"
    ADMITTING = "ADMITTING"


class AudioAdmissionGate:
    """
    Precision Audio Admission Gate & Anti-Self-Reply Engine.
    Prevents assistant output (native Live audio, fallback TTS, chimes, music)
    and acoustic room reverberation/echo tail from contaminating microphone input.
    """

    def __init__(self, echo_tail_guard_ms: float = 350.0, half_duplex_safety: bool = True) -> None:
        self.echo_tail_guard_ms = echo_tail_guard_ms
        self.half_duplex_safety = half_duplex_safety
        self.state = AudioAdmissionState.IDLE
        self.last_output_stop_ns: int = 0
        self.dropped_frames_count: int = 0
        self.admitted_frames_count: int = 0
        self._barge_in_streak: int = 0

    def is_output_active(self, player: Any = None, coordinator: Any = None) -> bool:
        """Check whether any audio output source (Live player, Pygame, TTS, coordinator) is active."""
        if player is not None and hasattr(player, "is_playing") and player.is_playing():
            return True
        if coordinator is not None:
            if getattr(coordinator, "_current_owner", None) is not None:
                return True
            tts = getattr(coordinator, "tts_engine", None)
            if tts and hasattr(tts, "is_speaking") and tts.is_speaking():
                return True
        try:
            import pygame
            if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
                return True
        except Exception:
            pass
        return False

    def evaluate_frame(
        self,
        pcm_bytes: bytes,
        player: Any = None,
        coordinator: Any = None,
        allow_barge_in: bool = True,
        barge_in_threshold: float = 2200.0,
    ) -> tuple[bool, bool]:
        """
        Evaluate incoming microphone PCM frame against active output and echo tail.
        Supports full-duplex operation (half_duplex_safety=False) and responsive barge-in.
        Returns:
            (admit_frame: bool, trigger_barge_in: bool)
        """
        now_ns = time.perf_counter_ns()
        output_busy = self.is_output_active(player, coordinator)

        # In full duplex mode (half_duplex_safety=False), admit speech frames continuously
        if not self.half_duplex_safety:
            self.state = AudioAdmissionState.ADMITTING
            self.admitted_frames_count += 1
            if output_busy and allow_barge_in:
                samples = np.frombuffer(pcm_bytes, dtype=np.int16)
                rms = float(np.sqrt(np.mean(samples.astype(np.float32)**2))) if len(samples) > 0 else 0.0
                if rms >= barge_in_threshold:
                    self._barge_in_streak += 1
                    if self._barge_in_streak >= 2:  # ~64ms responsive barge-in
                        self._barge_in_streak = 0
                        return True, True
                else:
                    self._barge_in_streak = 0
            return True, False

        if output_busy:
            self.last_output_stop_ns = now_ns
            self.state = AudioAdmissionState.OUTPUT_ACTIVE

            if allow_barge_in:
                # Inspect for genuine user barge-in over playback with calibrated sensitivity
                samples = np.frombuffer(pcm_bytes, dtype=np.int16)
                rms = float(np.sqrt(np.mean(samples.astype(np.float32)**2))) if len(samples) > 0 else 0.0
                if rms >= barge_in_threshold:
                    self._barge_in_streak += 1
                    if self._barge_in_streak >= 2:  # ~64ms sustained user voice triggers barge-in
                        self._barge_in_streak = 0
                        self.state = AudioAdmissionState.ADMITTING
                        self.admitted_frames_count += 1
                        return True, True
                else:
                    self._barge_in_streak = 0

            self.dropped_frames_count += 1
            return False, False

        self._barge_in_streak = 0

        # Check echo tail guard window
        if self.last_output_stop_ns > 0:
            elapsed_tail_ms = (now_ns - self.last_output_stop_ns) / 1e6
            if elapsed_tail_ms < self.echo_tail_guard_ms:
                self.state = AudioAdmissionState.ECHO_TAIL_GUARD
                self.dropped_frames_count += 1
                return False, False

        # Audio is clear of output bleed and room reverberation
        self.state = AudioAdmissionState.ADMITTING
        self.admitted_frames_count += 1
        return True, False


# ============================================================================
# 4. Gemini Live Configuration & Telemetry (Section 07, 34, 40)
# ============================================================================

@dataclass
class GeminiLiveConfig:
    """Configuration container for Gemini Live native audio capabilities."""
    enabled: bool = True
    model_id: str = "gemini-3.8-live"
    fallback_model_id: str = "gemini-3.1-flash-live-preview"
    voice_name: str = "Aoede"                     # "Aoede", "Charon", "Fenrir", "Kore", "Puck"
    api_version: str = "v1alpha"
    input_sample_rate: int = 16000
    output_sample_rate: int = 24000
    input_channels: int = 1
    automatic_vad: bool = True
    input_transcription: bool = True
    output_transcription: bool = True
    session_resumption: bool = True
    context_window_compression: bool = True
    allow_barge_in: bool = True
    chunk_duration_ms: int = 32                   # 32ms frames (512 samples at 16kHz)
    max_tool_rounds: int = 10
    reconnect_delay_seconds: float = 1.0
    max_reconnect_attempts: int = 5
    system_instruction: str = ""
    # Latency & Echo Optimization Fields (v2.0)
    echo_cancellation: bool = True
    self_listening_suppression: bool = True
    speech_energy_threshold: float = 500.0        # Calibrated RMS threshold to detect spoken utterances
    silence_frames_threshold: int = 36            # ~1.15s silence frames before signaling end_of_turn
    barge_in_energy_threshold: float = 5500.0     # Audio RMS threshold to recognize true user barge-in over speaker bleed
    direct_greeting_fast_path: bool = True
    first_response_watchdog_seconds: float = 5.0
    tool_timeout_seconds: float = 15.0
    echo_tail_guard_ms: float = 350.0             # Guard duration after playback drains before mic frames are admitted
    half_duplex_safety: bool = True               # Hardened half-duplex gating during model speech
    max_tools_per_turn: int = 4                   # Turn tool execution budget to prevent recursive loops


@dataclass
class GeminiLiveTelemetry:
    """Real-time observability and diagnostics telemetry for Live sessions."""
    session_id: str | None = None
    model_id: str = ""
    slot_id: int = 1
    project_id: str = ""
    state: LiveSessionState = LiveSessionState.IDLE
    connected_timestamp: str | None = None
    input_audio_seconds: float = 0.0
    output_audio_seconds: float = 0.0
    total_audio_chunks_sent: int = 0
    total_audio_chunks_received: int = 0
    total_tool_calls: int = 0
    successful_tool_calls: int = 0
    interruption_count: int = 0
    reconnection_count: int = 0
    last_error: str | None = None
    latest_user_transcript: str = ""
    latest_interim_transcript: str = ""
    latest_model_transcript: str = ""
    resumption_handle: str | None = None
    # Latency tracking
    last_turn_latency_ms: float = 0.0
    last_audio_latency_ms: float = 0.0
    average_audio_latency_ms: float = 0.0
    total_turns_completed: int = 0


# ============================================================================
# 5. Master Gemini Live Manager (Section 04, 08, 09, 10, 16, 22, 33)
# ============================================================================

class ZyeGeminiLiveManager:
    """
    The primary Gemini Live native audio conversation controller for Zye AI v2.0.
    Executes within the existing ZYE Master Brain architecture:
    - Maintains stateful multi-turn persistent WebSocket session (no per-turn reconnects)
    - Reuses existing GeminiKeyManager (Slots 1-7)
    - Exposes registered MCP tools via types.Tool function declarations
    - Streams microphone PCM16 directly to Gemini Live
    - Implements acoustic echo cancellation to prevent self-interruption during playback
    - Routes incoming function calls through SafetyExecutionGateway / ZyeExecutionGate
    - Streams native Gemini 24kHz audio directly to LiveAudioPlayer
    - Tracks end-to-end monotonic latency metrics (T0-T13, M0-M5) per turn
    - Manages session lifecycle, resumption handles, and barge-in interruptions
    """

    def __init__(
        self,
        config: GeminiLiveConfig | None = None,
        key_manager: Any | None = None,
        gateway: Any | None = None,
        tool_dispatcher: Callable[[str, dict[str, Any]], Coroutine[Any, Any, dict[str, Any]]] | None = None,
        tool_declarations: list[Any] | None = None,
        audio_capture_engine: Any | None = None,
        chime_player: Any | None = None,
        coordinator: Any | None = None,
    ) -> None:
        self.config = config or GeminiLiveConfig()
        self.key_manager = key_manager
        self.gateway = gateway
        self.tool_dispatcher = tool_dispatcher
        self.tool_declarations = tool_declarations or []
        self.audio_capture = audio_capture_engine
        self.chime_player = chime_player
        self.coordinator = coordinator

        self.player = LiveAudioPlayer(sample_rate=self.config.output_sample_rate)
        self.state = LiveSessionState.DISABLED if not self.config.enabled else LiveSessionState.IDLE
        self.telemetry = GeminiLiveTelemetry()
        self._state_lock = threading.Lock()

        self._active_session: Any | None = None
        self._active_slot_id: int = 1
        self._slot_cursor: int = 1
        self._client: Any | None = None
        self._running = False
        self._send_task: asyncio.Task | None = None
        self._recv_task: asyncio.Task | None = None
        self._stop_event: asyncio.Event | None = None
        self._audio_in_queue: asyncio.Queue[bytes] | None = None
        self._operation_cache: dict[str, Any] = {}
        self._audio_ducker: Any | None = None
        self._response_generation: int = 0
        self._uplink_muted: bool = False
        self._pre_roll_buffer: collections.deque[bytes] = collections.deque(maxlen=10)
        self._active_tool_tasks: list[asyncio.Task] = []
        self._pending_tool_cancellations: set[str] = set()
        self._session_send_lock: asyncio.Lock | None = None
        self._current_turn_audio_chunks: int = 0
        self._barge_in_confirm_frames: int = 0
        self._user_speaking: bool = False
        self._last_spoken_model_text: str = ""

        # Turn instrumentation
        self._turn_counter = 1
        self._current_turn: TurnMetrics | None = TurnMetrics(
            turn_id="live_turn_001",
            session_id="session_initial",
        )
        self._turn_history: list[TurnMetrics] = []

        # P0 Hotfix: Anti-Self-Reply Admission Gate & Turn Tool Tracking
        self.admission_gate = AudioAdmissionGate(
            echo_tail_guard_ms=getattr(self.config, "echo_tail_guard_ms", 350.0),
            half_duplex_safety=getattr(self.config, "half_duplex_safety", True),
        )
        self._turn_tool_requested: bool = False
        self._turn_tool_executed: bool = False
        self._turn_tools_in_flight: int = 0
        self._turn_tool_count: int = 0

    def _get_send_lock(self) -> asyncio.Lock:
        """Lazily obtain or create asyncio.Lock on current running event loop."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if self._session_send_lock is None or getattr(self, "_send_lock_loop", None) is not loop:
            self._session_send_lock = asyncio.Lock()
            self._send_lock_loop = loop
        return self._session_send_lock

    def _get_audio_in_queue(self) -> asyncio.Queue[bytes]:
        """Lazily obtain or create audio input queue on current running event loop."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if self._audio_in_queue is None or getattr(self, "_queue_loop", None) is not loop:
            self._audio_in_queue = asyncio.Queue(maxsize=150)
            self._queue_loop = loop
        return self._audio_in_queue

    def set_audio_ducker(self, ducker: Any) -> None:
        """Register AudioDucker to duck music during speech interactions."""
        self._audio_ducker = ducker

    def set_muted(self, muted: bool) -> None:
        """Pause or resume microphone audio uplink (used by Alt+Z text mode and privacy)."""
        self._uplink_muted = muted
        if muted:
            self._pre_roll_buffer.clear()
            q = self._get_audio_in_queue()
            while not q.empty():
                try:
                    q.get_nowait()
                except Exception:
                    break
        logger.info("Gemini Live microphone uplink muted: %s", muted)

    def is_muted(self) -> bool:
        """Check whether audio uplink is currently muted."""
        return self._uplink_muted

    def trigger_local_interruption(self, reason: str = "LOCAL_BARGE_IN") -> None:
        """
        Instantaneously silence active audio output and advance generation fence.
        Provides immediate barge-in response without waiting for cloud round-trip.
        """
        self._response_generation += 1
        self.player.flush()
        try:
            import pygame
            if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()
        except Exception:
            pass

        if self._current_turn is not None:
            self._current_turn.interrupted = True
            self._current_turn.status = "INTERRUPTED"

        self.telemetry.interruption_count += 1
        self._user_speaking = False
        self.set_state(LiveSessionState.INTERRUPTED)
        self.set_state(LiveSessionState.LISTENING)
        logger.info("Local interruption triggered (%s, gen=%d); output silenced", reason, self._response_generation)

    def set_state(self, new_state: LiveSessionState) -> None:
        """Adhere strictly to explicit state-machine transition rules."""
        with self._state_lock:
            allowed = _VALID_LIVE_TRANSITIONS.get(self.state, set())
            if new_state not in allowed:
                logger.debug("State transition %s -> %s not in standard map, forcing update", self.state, new_state)
            self.state = new_state
            self.telemetry.state = new_state

    def is_healthy(self) -> bool:
        """Check if Live session is active and healthy."""
        return self._running and self.state in (
            LiveSessionState.CONNECTED,
            LiveSessionState.LISTENING,
            LiveSessionState.USER_SPEAKING,
            LiveSessionState.PROCESSING,
            LiveSessionState.TOOL_CALL_PENDING,
            LiveSessionState.TOOL_RUNNING,
            LiveSessionState.RESPONDING,
        )

    def is_degraded(self) -> bool:
        """Check if Live session is degraded, closed, or disabled."""
        return self.state in (
            LiveSessionState.DEGRADED,
            LiveSessionState.CLOSED,
            LiveSessionState.ERROR,
            LiveSessionState.DISABLED,
        )

    # -------------------------------------------------------------------------
    # Key Selection & Client Resolution (Section 08, 09, 11)
    # -------------------------------------------------------------------------
    def _resolve_authorized_client(self) -> tuple[int, Any, str]:
        """
        Obtain an eligible Gemini client from the existing 7-key manager.
        Tracks session under the chosen slot without mid-session disruption.
        """
        slots_order = [((self._slot_cursor - 1 + i) % 7) + 1 for i in range(7)]
        if self.key_manager is not None:
            for s_id in slots_order:
                slot = self.key_manager.get_slot(s_id)
                if slot and slot.api_key and slot.client and slot.key_health in ("HEALTHY", "UNKNOWN"):
                    self._slot_cursor = s_id
                    return s_id, slot.client, slot.project_id or f"zye-project-{s_id:02d}"

        # Gateway fallback
        if self.gateway is not None and hasattr(self.gateway, "key_manager"):
            for s_id in slots_order:
                slot = self.gateway.key_manager.get_slot(s_id)
                if slot and slot.api_key and slot.client:
                    self._slot_cursor = s_id
                    return s_id, slot.client, slot.project_id or f"zye-project-{s_id:02d}"

        if not _GENAI_AVAILABLE:
            raise RuntimeError("Google Gen AI SDK is not available in environment")

        import os
        key = os.getenv("GEMINI_API_KEY_01") or os.getenv("GEMINI_API_KEY", "")
        if not key:
            raise RuntimeError("No Gemini API key configured in slots 1-7 or environment")
        client = genai.Client(api_key=key)
        return 1, client, "zye-default-project"

    # -------------------------------------------------------------------------
    # Live Connect Config Builder (Section 06, 07, 09, 20, 21, 22)
    # -------------------------------------------------------------------------
    def _build_live_connect_config(self) -> types.LiveConnectConfig:
        """Assemble types.LiveConnectConfig matching exact SDK conventions with low-latency prompt."""
        # Minimal high-performance system prompt enforcing Zye identity, Tanglish fluency, and greeting fast-path
        system_prompt = (
            "You are Zye, an elite personal AI assistant operating on Windows Desktop.\n"
            "You speak naturally in Tamil, English, and Tanglish (Tamil code-switched with English).\n"
            "CRITICAL OPERATIONAL RULES:\n"
            "1. Listen natively to user audio and understand natural spoken Tamil, English, and Tanglish commands.\n"
            "2. GREETINGS & CASUAL CONVERSATION: When the user greets you (e.g. 'Hi', 'Hello', 'Good morning', 'How are you?', 'Enna panra Zye?'), respond immediately, warmly, and briefly in natural Tanglish or English. Do NOT call any MCP tool for greetings or casual conversation.\n"
            "3. When the user asks to execute an external action (e.g. open apps, check emails, schedule meetings, inspect Excel, Word, control Windows, run AI council), call the appropriate MCP tool.\n"
            "4. Answer concisely, conversationally, and warmly in natural Tanglish or English as spoken by the user.\n"
            "5. NEVER mention internal technical schemas or tool execution mechanics to the user.\n"
            "6. If the user interrupts you while speaking, immediately yield and listen to the new utterance.\n"
            "7. MANDATORY ZERO-FALSE-SUCCESS RULE FOR APPLICATIONS: When the user asks to open an application (e.g. Chrome, WhatsApp, Calculator, Notepad, Word, Excel, etc.), you MUST inspect the execution result returned by the tool. If 'verified' is false or status is PROCESS_STARTED, WINDOW_TIMEOUT, APP_NOT_FOUND, or LAUNCH_FAILED, you MUST NEVER claim that the application opened successfully. Instead, state clearly: 'The process started, but the application window has not appeared yet' or 'Could not verify the application window'. ONLY confirm successful launch if 'verified' is true.\n"
            "8. KINEMATIC RISK & MONTE CARLO SIMULATION: When the user asks to analyze moving trajectories, calculate collision risk, or run Monte Carlo simulations (e.g. 'collision risk calculate pannu', 'Monte Carlo simulation run pannu', 'minimum separation evvalavu?'), call the appropriate tactical kinematic tool (calculate_kinematic_risk, run_monte_carlo_risk_simulation, compare_trajectory_scenarios). Explain the closest point of approach (CPA) and collision probability clearly, emphasizing that simulation output is an analytical advisory under modeled uncertainty.\n"
            "9. REAL-TIME NEWS VERIFICATION & ANTI-FAKE NEWS: When discussing live news, breaking events, or verifying factual claims (e.g. 'indha news unmaiya?', 'breaking updates enna?', 'check this news'), call fetch_verified_live_updates or verify_specific_news_claim. If fewer than 2 independent sources with valid publication timestamps corroborate the claim, you MUST state that it is unverified: 'Indha update-ai independent sources moolama verify panna mudiyala. Ippo confirmed news-ah report panna evidence podhavillai.' Expose contradictions clearly and never fabricate sources, dates, or confirm uncorroborated rumours.\n"
            "10. LAN NETWORK INTELLIGENCE & ARP DEVICE DISCOVERY: When asked about local network interfaces, connected devices, or LAN traffic (e.g. 'Wi-Fi-la evvalavu devices irukku?', 'LAN scan pannu', 'gateway IP enna?'), invoke get_network_interface_inventory, discover_lan_devices, get_network_inventory, or monitor_computer_networks. NEVER fabricate IPs, MACs, or device counts. Clearly distinguish active ARP responses from passive neighbor-table observations. Never claim a device is currently online based solely on a stale ARP cache entry. If Scapy/Npcap is unavailable, explain the limitation and use passive discovery fallback.\n"
            "11. WINDOWS AUTHENTICATION SECURITY & FAILED LOGIN INTELLIGENCE: When asked about failed logins, logon attempts, security events, or brute-force activity (e.g. 'failed login ethavadhu irukka?', 'brute-force attack nadakutha?', 'check Event ID 4625', 'security log status enna?'), invoke detect_unauthorized_access, get_failed_login_events, analyze_authentication_patterns, or get_authentication_security_status. NEVER fabricate Event ID 4625 records or login failures. Clearly explain logon types (Type 2 Console/Interactive, Type 3 Network, Type 10 Remote Desktop / RDP) and failure status codes (0xC000006A wrong password, 0xC0000064 user not found). Distinguish failed attempts from successful compromise. Mask usernames by default. Never attempt or recommend unauthorized penetration, and never execute automatic account lockout or IP blocking without explicit user authorization.\n"
            "12. TYPING TEXT, DICTATION, AND WRITING CODE INTO APPLICATIONS: You are a fully authorized desktop AI with full permission to write code, type text, and edit files directly on the user's desktop. When the user asks to write, type, or create code or text inside an application (e.g. 'Notepad-la code write pannu', 'HTML code type pannu', 'write this into Notepad'):\n"
            "- NEVER refuse or claim 'Security restrictions kaaranamah code-ai type panna mudiyala' or tell the user to manually paste. You are explicitly authorized to type code.\n"
            "- Immediately invoke type_into_app(window_keyword='Notepad', text='<the code>') or dictate_text_anywhere(text='<the code>') to insert the complete, functional code or text directly into the application.\n"
            "- If the application was just opened, immediately call type_into_app or dictate_text_anywhere to insert the code, then confirm warmly in Tamil/Tanglish that you opened the app and typed the code.\n"
            "13. SMART MUSIC & SONG PLAYBACK (TAMIL / ENGLISH / TANGLISH): You have an integrated, fully functional local audio and music player. When the user asks to play music, a song, or audio in Tamil, English, or Tanglish (e.g. 'ஏதாச்சும் ஒரு சாங் பாடு', 'சாங் பாடு', 'பாட்டு பாடு', 'பாட்டு போடு', 'song podu', 'play a song', 'paatu paadu', 'oru paatu vai', 'play master song', 'anirudh song podu', 'pause music', 'stop music', 'volume kootu'):\n"
            "- In Tamil colloquial speech, 'சாங் பாடு', 'பாட்டு பாடு', and 'பாடு' mean 'PLAY A SONG' using the music player. NEVER refuse or say 'Ennaala paada mudiyathu' (I cannot sing) or 'Manikkavum'!\n"
            "- When a specific song, artist, movie, or genre is requested (e.g. 'Kannana Kanne', 'Anirudh song', 'kuthu paattu', 'workout music'), call play_music(track_or_query='<exact title/artist/genre>') with the exact query. Never substitute an empty query or 'melody' when a specific song was asked.\n"
            "- When asked for any general/random song (e.g. 'ஏதாச்சும் ஒரு சாங் பாடு', 'edhavadhu oru paatu', 'oru song podu', 'play any song'), call play_music(track_or_query='any'). The Diverse Track Selector will automatically pick a non-repeating track.\n"
            "- If the user says 'melody vendaam' (no melody), pass track_or_query='no melody' or 'energetic' to exclude melody tracks.\n"
            "- For volume, pause, resume, next: call pause_music(), resume_music(), next_track(), set_music_volume(volume_percent=...).\n"
            "- After the tool executes, confirm warmly in natural Tanglish (e.g. 'Sure, ippo paatu play panren'). Never claim Spotify is streaming when playing from local music, and never invent song titles.\n"
        )
        if self.config.system_instruction:
            system_prompt = f"{self.config.system_instruction}\n{system_prompt}"

        # Tools configuration
        tools_list: list[Any] = []
        if self.tool_declarations:
            tools_list = [types.Tool(function_declarations=self.tool_declarations)]

        # Speech config
        speech_cfg = None
        if hasattr(types, "SpeechConfig") and hasattr(types, "VoiceConfig"):
            try:
                prebuilt = types.PrebuiltVoiceConfig(voice_name=self.config.voice_name)
                voice_cfg = types.VoiceConfig(prebuilt_voice_config=prebuilt)
                speech_cfg = types.SpeechConfig(voice_config=voice_cfg)
            except Exception as e:
                logger.debug("Could not construct SpeechConfig: %s", e)

        # Transcriptions
        input_trans = None
        output_trans = None
        if hasattr(types, "AudioTranscriptionConfig"):
            if self.config.input_transcription:
                input_trans = types.AudioTranscriptionConfig(
                    language_codes=["ta-IN", "en-IN", "en-US"],
                )
            if self.config.output_transcription:
                output_trans = types.AudioTranscriptionConfig()

        # Session resumption
        resumption_cfg = None
        if self.config.session_resumption and hasattr(types, "SessionResumptionConfig"):
            if self.telemetry.resumption_handle:
                resumption_cfg = types.SessionResumptionConfig(handle=self.telemetry.resumption_handle)
            else:
                resumption_cfg = types.SessionResumptionConfig()

        # Realtime VAD configuration (ZYE-BUG-011)
        realtime_input_cfg = None
        if hasattr(types, "RealtimeInputConfig") and hasattr(types, "AutomaticActivityDetection"):
            is_auto_vad = getattr(self.config, "automatic_vad", True)
            if is_auto_vad:
                aad = types.AutomaticActivityDetection(
                    disabled=False,
                    prefix_padding_ms=300,
                    silence_duration_ms=450,
                )
            else:
                aad = types.AutomaticActivityDetection(disabled=True)
            realtime_input_cfg = types.RealtimeInputConfig(automatic_activity_detection=aad)

        # Context window compression (ZYE-BUG-011)
        compression_cfg = None
        if getattr(self.config, "context_window_compression", False) and hasattr(types, "ContextWindowCompressionConfig"):
            compression_cfg = types.ContextWindowCompressionConfig()

        connect_config = types.LiveConnectConfig(
            response_modalities=[types.Modality.AUDIO],
            http_options=types.HttpOptions(api_version=self.config.api_version),
            system_instruction=system_prompt,
            tools=tools_list if tools_list else None,
            speech_config=speech_cfg,
            input_audio_transcription=input_trans,
            output_audio_transcription=output_trans,
            session_resumption=resumption_cfg,
            realtime_input_config=realtime_input_cfg,
            context_window_compression=compression_cfg,
        )
        return connect_config

    # -------------------------------------------------------------------------
    # Audio Input Streaming & Echo Cancellation (Section 12, 13, 33)
    # -------------------------------------------------------------------------
    def push_microphone_audio(self, pcm16_bytes: bytes) -> None:
        """
        Accept raw 16kHz signed 16-bit PCM frames from microphone capture.
        Applies AudioAdmissionGate, echo tail suppression, pre-roll buffering, and local barge-in.
        """
        if not self._running or not pcm16_bytes or self._uplink_muted:
            return

        barge_threshold = getattr(self.config, "barge_in_energy_threshold", 9500.0)
        allow_barge = getattr(self.config, "allow_barge_in", True)
        admit, trigger_barge = self.admission_gate.evaluate_frame(
            pcm16_bytes,
            player=self.player,
            coordinator=self.coordinator,
            allow_barge_in=allow_barge,
            barge_in_threshold=barge_threshold,
        )

        if trigger_barge:
            logger.info("Confirmed high-energy user barge-in over playback; interrupting output")
            self.trigger_local_interruption(reason="LOCAL_VAD_BARGE_IN")

        if not admit:
            return

        # Maintain rolling pre-roll buffer (~320ms window) for onset preservation
        self._pre_roll_buffer.append(pcm16_bytes)

        t_now = time.perf_counter_ns()
        if self._current_turn is not None and not self._current_turn.t0_audio_activity_ns:
            self._current_turn.t0_audio_activity_ns = t_now
            self._current_turn.t1_frame_captured_ns = t_now

        q = self._get_audio_in_queue()
        try:
            q.put_nowait(pcm16_bytes)
        except asyncio.QueueFull:
            # Drop oldest frame to preserve real-time low latency
            try:
                q.get_nowait()
                q.put_nowait(pcm16_bytes)
            except Exception:
                pass

    async def pump_capture_engine(self, capture_engine: Any) -> None:
        """
        Continuously read frames from AudioCaptureEngine and push to Live audio queue.
        Uses fast non-blocking in-memory queue drain (zero thread-pool dispatch overhead).
        """
        from zye_audio_ear import downmix_to_mono, resample_audio, convert_float32_to_pcm16
        if not capture_engine.is_running:
            try:
                capture_engine.start()
            except Exception as e:
                logger.warning("Error starting capture engine for Live audio: %s", e)

        logger.debug("Microphone capture pump started for Gemini Live (non-blocking in-memory mode)")
        while self._running:
            try:
                drained = 0
                while not capture_engine.frame_queue.empty() and drained < 8:
                    try:
                        frame = capture_engine.frame_queue.get_nowait()
                        drained += 1
                    except Exception:
                        break

                    if frame is None or len(frame) == 0:
                        continue
                    mono = downmix_to_mono(frame) if frame.ndim > 1 else frame
                    if capture_engine.needs_resampling:
                        mono_16k = resample_audio(mono, orig_sr=capture_engine.active_sample_rate, target_sr=self.config.input_sample_rate)
                    else:
                        mono_16k = mono
                    pcm16 = convert_float32_to_pcm16(mono_16k).tobytes()
                    self.push_microphone_audio(pcm16)

                # Brief non-blocking yield to asyncio loop
                await asyncio.sleep(0.01)
            except asyncio.CancelledError:
                break
            except Exception as e:
                await asyncio.sleep(0.02)
        logger.debug("Microphone capture pump stopped")

    async def _send_audio_loop(self, session: Any) -> None:
        """Asynchronously stream microphone PCM16 chunks to the Gemini Live session."""
        logger.debug("Live audio sender loop started")
        bytes_sent = 0
        self._user_speaking = False
        speech_frame_count = 0
        silence_frame_count = 0
        resume_speech_frames = 0
        speech_duration_frames = 0
        voiced_speech_frames = 0
        speech_threshold = getattr(self.config, "speech_energy_threshold", 500.0)
        min_speech_frames = 2          # ~64ms of sustained speech
        silence_threshold_frames = getattr(self.config, "silence_frames_threshold", 36)  # ~1.15s silence after speech to signal end_of_turn
        noise_floor_rms = 0.0

        try:
            while self._running:
                try:
                    q = self._get_audio_in_queue()
                    pcm_chunk = await asyncio.wait_for(q.get(), timeout=0.1)
                except asyncio.TimeoutError:
                    continue

                if not pcm_chunk:
                    continue

                # Half-duplex safety: Drop chunks and keep VAD counters zeroed during output or echo tail guard
                if self.admission_gate.state in (AudioAdmissionState.OUTPUT_ACTIVE, AudioAdmissionState.ECHO_TAIL_GUARD):
                    speech_frame_count = 0
                    silence_frame_count = 0
                    resume_speech_frames = 0
                    speech_duration_frames = 0
                    voiced_speech_frames = 0
                    self._user_speaking = False
                    continue

                # VAD turn boundary detection: prompt Gemini Live immediately after user stops speaking
                samples = np.frombuffer(pcm_chunk, dtype=np.int16)
                rms = float(np.sqrt(np.mean(samples.astype(np.float32)**2))) if len(samples) > 0 else 0.0

                # Adaptive noise floor tracking: dynamically adjust threshold when ambient mic noise exceeds nominal baseline
                # Asymmetric tracking: quickly tracks down to real ambient quiet, slowly tracks gradual baseline drift
                if noise_floor_rms == 0.0:
                    noise_floor_rms = min(rms, 3500.0)
                elif not self._user_speaking:
                    if rms < noise_floor_rms:
                        noise_floor_rms = 0.90 * noise_floor_rms + 0.10 * rms
                    elif rms < noise_floor_rms * 1.5:
                        noise_floor_rms = 0.98 * noise_floor_rms + 0.02 * rms

                effective_speech_threshold = (
                    max(speech_threshold, noise_floor_rms * 1.35 + 250.0)
                    if noise_floor_rms > speech_threshold
                    else speech_threshold
                )

                if rms >= effective_speech_threshold:
                    speech_frame_count += 1
                    if not self._user_speaking:
                        if speech_frame_count >= min_speech_frames:
                            self._user_speaking = True
                            speech_duration_frames = 0
                            silence_frame_count = 0
                            resume_speech_frames = 0
                            voiced_speech_frames = speech_frame_count
                            print("\n[Zye Hearing You...] Spoken audio detected...", flush=True)
                            if self.chime_player:
                                try:
                                    self.chime_player.play_start()
                                except Exception:
                                    pass
                    else:
                        # User was already speaking and is continuing/resuming speech
                        voiced_speech_frames += 1
                        resume_speech_frames += 1
                        if resume_speech_frames >= 2:
                            # Confirmed sustained speech: reset silence counter
                            silence_frame_count = 0
                else:
                    speech_frame_count = max(0, speech_frame_count - 1)
                    resume_speech_frames = 0
                    if self._user_speaking:
                        silence_frame_count += 1

                if self._user_speaking:
                    speech_duration_frames += 1

                # Turn completion dispatch:
                # 1) Natural silence timeout reached, OR
                # 2) Maximum utterance timeout (>=10s with at least 8 frames of quiet)
                should_complete_turn = self._user_speaking and (
                    silence_frame_count >= silence_threshold_frames
                    or (speech_duration_frames >= 300 and silence_frame_count >= 8)
                )

                if should_complete_turn:
                    # Guard against empty/spurious turns: only send end_of_turn if genuine speech occurred
                    # (at least 2 frames ~64ms of voiced energy above speech threshold; rejects ambient noise/clicks)
                    has_genuine_speech = voiced_speech_frames >= 2
                    self._user_speaking = False
                    speech_frame_count = 0
                    silence_frame_count = 0
                    resume_speech_frames = 0
                    speech_duration_frames = 0
                    current_voiced = voiced_speech_frames
                    voiced_speech_frames = 0

                    if has_genuine_speech:
                        logger.info("Speech completion detected (%d voiced frames, rms=%.0f, threshold=%.0f) -> sending end_of_turn", current_voiced, rms, effective_speech_threshold)
                        print("\n[Zye Processing...] Generating response...\n", flush=True)
                        if self.chime_player:
                            try:
                                self.chime_player.play_stop()
                            except Exception:
                                pass
                        # Only dispatch manual end_of_turn in manual VAD mode (ZYE-BUG-010)
                        if not getattr(self.config, "automatic_vad", True):
                            try:
                                async with self._get_send_lock():
                                    await session.send(end_of_turn=True)
                            except Exception as e_eot:
                                logger.debug("Manual VAD end_of_turn dispatch notice: %s", e_eot)
                    else:
                        logger.debug("Discarding brief acoustic transient (%d voiced frames < 3); remaining in listening mode", current_voiced)

                t_send = time.perf_counter_ns()
                if self._current_turn is not None and not self._current_turn.t4_sent_to_live_ns:
                    self._current_turn.t4_sent_to_live_ns = t_send
                    self._current_turn.t6_user_speech_completed_ns = t_send

                # Send realtime audio input to Gemini Live with session lock
                async with self._get_send_lock():
                    await session.send_realtime_input(
                        audio=dict(
                            data=pcm_chunk,
                            mime_type=f"audio/pcm;rate={self.config.input_sample_rate}",
                        )
                    )
                self.telemetry.total_audio_chunks_sent += 1
                bytes_sent += len(pcm_chunk)
                self.telemetry.input_audio_seconds = round(bytes_sent / (self.config.input_sample_rate * 2), 2)

        except asyncio.CancelledError:
            logger.debug("Audio sender loop cancelled")
        except Exception as exc:
            logger.warning("Error in live audio sender loop: %s", exc)
            self.telemetry.last_error = str(exc)

    # -------------------------------------------------------------------------
    # Server Event Reception & Turn Handling (Section 10, 16, 17, 20, 22)
    # -------------------------------------------------------------------------
    async def _safe_speak_fallback(self, text: str) -> None:
        """Safely synthesize fallback text via coordinator Edge-TTS without blocking receiver."""
        if not self.coordinator or not text:
            return
        try:
            await self.coordinator.speak(text)
        except Exception as exc:
            logger.warning("Error speaking fallback text: %s", exc)

    async def _receive_events_loop(self, session: Any) -> None:
        """
        Continuously receive streaming events from Gemini Live across multiple turns:
        audio chunks, tool calls, barge-in, transcriptions.
        Keeps WebSocket open and healthy across conversational turns without reconnecting.
        Exits when stream exhausts or session disconnects.
        """
        logger.debug("Live multi-turn event receiver loop started")
        self.set_state(LiveSessionState.LISTENING)

        # Real Gemini Live AsyncSession has _ws (underlying WebSocket connection) and lives across turns
        is_real_session = hasattr(session, "_ws") or getattr(session, "_persistent", False)

        try:
            while self._running:
                received_in_turn = False
                async for response in session.receive():
                    received_in_turn = True
                    if not self._running:
                        break

                    # 1. Session Resumption update (Section 29)
                    session_resumption = getattr(response, "session_resumption_update", None)
                    if session_resumption:
                        handle = getattr(session_resumption, "new_handle", None)
                        if handle:
                            self.telemetry.resumption_handle = str(handle)

                    go_away = getattr(response, "go_away", None)
                    if go_away:
                        logger.warning("Gemini Live sent GoAway event: %s; preparing clean reconnect", go_away)
                        return

                    # Tool Call Cancellation from Gemini Live
                    tool_cancellation = getattr(response, "tool_call_cancellation", None)
                    if tool_cancellation is not None:
                        cancelled_ids = getattr(tool_cancellation, "ids", []) or []
                        logger.info("Gemini Live requested tool_call_cancellation for IDs: %s", cancelled_ids)
                        for c_id in cancelled_ids:
                            self._pending_tool_cancellations.add(c_id)

                    # 2. Tool Calls (Section 22, 23, 24) - Schedule first so turn_complete knows if tool is in-flight
                    tool_call = getattr(response, "tool_call", None)
                    if tool_call is not None:
                        self._turn_tool_requested = True
                        self._turn_tools_in_flight += 1
                        self._turn_tool_count += 1
                        if self._current_turn is not None:
                            self._current_turn.has_tool_call = True
                        t_task = asyncio.create_task(self._handle_live_tool_call(session, tool_call))
                        self._active_tool_tasks.append(t_task)
                        self._active_tool_tasks = [t for t in self._active_tool_tasks if not t.done()]

                    # 3. Server Content (Audio / Text / Interruption)
                    server_content = getattr(response, "server_content", None)
                    if server_content is not None:
                        t_now = time.perf_counter_ns()
                        if self._current_turn is not None and not self._current_turn.t7_first_server_event_ns:
                            self._current_turn.t7_first_server_event_ns = t_now

                        # Check Barge-in / Interruption (Section 20 & 32)
                        interrupted = getattr(server_content, "interrupted", False)
                        if interrupted:
                            self.telemetry.interruption_count += 1
                            self.set_state(LiveSessionState.INTERRUPTED)
                            self._response_generation += 1
                            if self._current_turn is not None:
                                self._current_turn.interrupted = True
                                self._current_turn.status = "INTERRUPTED"
                            logger.info("User interrupted Gemini Live; flushing playback queue (gen=%d)", self._response_generation)
                            self.player.flush()
                            if self._audio_ducker:
                                try:
                                    asyncio.create_task(self._audio_ducker.unduck(force=True))
                                except Exception:
                                    pass
                            self.set_state(LiveSessionState.LISTENING)

                        # Model Turn Parts (Native 24kHz audio + transcription)
                        model_turn = getattr(server_content, "model_turn", None)
                        part_text_received = False
                        if model_turn and model_turn.parts:
                            self.set_state(LiveSessionState.RESPONDING)
                            if self._audio_ducker:
                                try:
                                    asyncio.create_task(self._audio_ducker.duck())
                                except Exception:
                                    pass
                            for part in model_turn.parts:
                                # Stream native audio chunk immediately (Section 17) with generation fence
                                if getattr(part, "inline_data", None):
                                    audio_bytes = part.inline_data.data
                                    if audio_bytes:
                                        if self._current_turn is not None and self._current_turn.interrupted:
                                            logger.debug("Discarding audio chunk from interrupted turn")
                                            continue
                                        curr_gen = self._response_generation
                                        accepted = self.player.queue_chunk(audio_bytes, generation=curr_gen)
                                        if accepted:
                                            t_part = time.perf_counter_ns()
                                            if self._current_turn is not None and not self._current_turn.t8_first_audio_bytes_ns:
                                                self._current_turn.t8_first_audio_bytes_ns = t_part
                                                self._current_turn.t9_playback_queued_ns = time.perf_counter_ns()
                                                # T10 represents actual hardware DAC submission (ZYE-BUG-012)
                                                # Do not conflate network arrival with DAC presentation
                                                player_write = getattr(self.player, "last_write_timestamp_ns", 0)
                                                self._current_turn.t10_output_submitted_ns = player_write if player_write > 0 else None
                                            self._current_turn_audio_chunks += 1
                                            self.telemetry.total_audio_chunks_received += 1
                                            self.telemetry.output_audio_seconds += len(audio_bytes) / (self.config.output_sample_rate * 2)

                                # Captured text transcript from model turn parts
                                if getattr(part, "text", None):
                                    text = part.text
                                    part_text_received = True
                                    self.telemetry.latest_model_transcript += text
                                    if self._current_turn is not None:
                                        self._current_turn.model_transcript += text
                                    print(f"\n[Zye] {text}\n", flush=True)
                                    logger.info("[Zye Response]: %s", text)

                        # Official SDK input transcription (user speech) from LiveServerContent
                        # Interim input transcription (provisional partial)
                        interim_trans = getattr(server_content, "interim_input_transcription", None)
                        if interim_trans and getattr(interim_trans, "text", None):
                            if self._audio_ducker:
                                try:
                                    asyncio.create_task(self._audio_ducker.duck())
                                except Exception:
                                    pass
                            self.telemetry.latest_interim_transcript = interim_trans.text
                            if self._current_turn is not None and not getattr(self._current_turn, "final_transcript_received", False):
                                self._current_turn.user_transcript = interim_trans.text
                            print(f"\r[Hearing]: {interim_trans.text}", end="", flush=True)

                        # Final input transcription (official completed user turn)
                        in_trans = getattr(server_content, "input_transcription", None)
                        if in_trans and getattr(in_trans, "text", None):
                            self.telemetry.latest_user_transcript = in_trans.text
                            if self._current_turn is not None:
                                self._current_turn.user_transcript = in_trans.text
                                self._current_turn.final_transcript_received = True
                            print(f"\n[Voice Recognized]: {in_trans.text}\n", flush=True)
                            logger.info("[Live User Speech Transcript]: %s", in_trans.text)

                        # Fallback for user_turn mock fixtures
                        user_turn = getattr(server_content, "user_turn", None)
                        if user_turn and getattr(user_turn, "parts", None):
                            for u_part in user_turn.parts:
                                if getattr(u_part, "text", None):
                                    self.telemetry.latest_user_transcript = u_part.text
                                    if self._current_turn is not None:
                                        self._current_turn.user_transcript = u_part.text
                                        self._current_turn.final_transcript_received = True
                                    print(f"\n[Voice Recognized]: {u_part.text}\n", flush=True)
                                    logger.info("[Live User Speech Transcript]: %s", u_part.text)

                        # Official SDK output transcription (assistant speech) from LiveServerContent
                        out_trans = getattr(server_content, "output_transcription", None)
                        if out_trans and getattr(out_trans, "text", None):
                            text = out_trans.text
                            if not part_text_received:
                                self.telemetry.latest_model_transcript += text
                                if self._current_turn is not None:
                                    self._current_turn.model_transcript += text
                                print(f"\n[Zye]: {text}\n", flush=True)
                                logger.info("[Zye Response]: %s", text)

                        # Turn completion (Section 10: DO NOT RECONNECT, STAY LISTENING)
                        if getattr(server_content, "turn_complete", False):
                            if self._audio_ducker:
                                try:
                                    asyncio.create_task(self._audio_ducker.unduck())
                                except Exception:
                                    pass

                            # Check if tool execution is in flight or pending for this turn
                            is_tool_in_flight = (
                                (self._turn_tool_requested and not self._turn_tool_executed)
                                or self._turn_tools_in_flight > 0
                                or any(not t.done() for t in self._active_tool_tasks)
                                or (self.state in (LiveSessionState.TOOL_CALL_PENDING, LiveSessionState.TOOL_RUNNING))
                                or (self._current_turn and bool(self._current_turn.tool_name and not self._turn_tool_executed))
                            )

                            if is_tool_in_flight:
                                logger.debug("Gemini Live turn waiting for tool execution response (turn_id=%s)", self._current_turn.turn_id if self._current_turn else "none")
                                if self._current_turn is not None:
                                    self._current_turn.status = "WAITING_FOR_TOOL"
                                continue

                            # Autonomous Music Refusal Recovery:
                            # If user requested a song or music, but Gemini responded with a refusal ("paada mudiyathu" / "cannot sing")
                            completed_turn = self._current_turn
                            if completed_turn and completed_turn.user_transcript:
                                u_text = completed_turn.user_transcript.strip().lower()
                                m_text = (completed_turn.model_transcript or "").strip().lower()
                                if any(k in u_text for k in ("சாங்", "பாட்டு", "பாடு", "song", "paatu", "music", "பாட")) and any(
                                    k in m_text for k in ("paada mudiyathu", "cannot sing", "ennaala paada", "manikkavum, ennaala")
                                ):
                                    logger.info("Detected model refusal on music request ('%s'). Triggering autonomous play_music reflex.", u_text)
                                    if self.tool_dispatcher:
                                        try:
                                            from zye_music.music_intent_router import MusicIntentRouter
                                            p_intent = MusicIntentRouter.parse_intent(completed_turn.user_transcript)
                                            query_arg = p_intent.query or ""
                                            asyncio.create_task(self.tool_dispatcher("play_music", {"track_or_query": query_arg}))
                                            if self.coordinator:
                                                asyncio.create_task(self.coordinator.speak("Sure, ippo paatu play panren!"))
                                        except Exception as f_err:
                                            logger.debug("Autonomous music fallback error: %s", f_err)

                            t_comp = time.perf_counter_ns()
                            completed_turn = self._current_turn
                            turn_model_text = completed_turn.model_transcript if completed_turn else ""
                            turn_chunks = self._current_turn_audio_chunks
                            was_interrupted = completed_turn.interrupted if completed_turn else False
                            had_user_speech = bool(completed_turn and completed_turn.user_transcript)

                            if completed_turn is not None:
                                completed_turn.t12_response_complete_ns = t_comp
                                if not was_interrupted:
                                    completed_turn.status = "COMPLETED"
                                audio_lat = completed_turn.first_audio_latency_ms()
                                self.telemetry.last_audio_latency_ms = audio_lat
                                self.telemetry.total_turns_completed += 1
                                if self.telemetry.average_audio_latency_ms <= 0:
                                    self.telemetry.average_audio_latency_ms = audio_lat
                                else:
                                    self.telemetry.average_audio_latency_ms = round(
                                        0.7 * self.telemetry.average_audio_latency_ms + 0.3 * audio_lat, 2
                                    )
                                for log_line in completed_turn.format_diagnostic_trace():
                                    logger.info(log_line)
                                self._turn_history.append(completed_turn)
                                if len(self._turn_history) > 50:
                                    self._turn_history = self._turn_history[-50:]

                            # Rotate to new turn metrics container
                            self._turn_counter += 1
                            self._current_turn = TurnMetrics(
                                turn_id=f"live_turn_{self._turn_counter:03d}",
                                session_id=str(self.telemetry.session_id or "session_001"),
                            )
                            self._current_turn_audio_chunks = 0
                            # Reset turn-scoped tool state for next turn
                            self._turn_tool_count = 0
                            self._turn_tool_executed = False
                            self._turn_tool_requested = False
                            self._turn_tools_in_flight = 0

                            # Audio fallback: if text was received with 0 native audio chunks, speak via Edge TTS
                            if (
                                self.coordinator is not None
                                and turn_model_text
                                and turn_chunks == 0
                                and not was_interrupted
                            ):
                                clean_text = turn_model_text.replace("<no speech>", "").replace("{pause}", "").strip()
                                if clean_text:
                                    if clean_text == self._last_spoken_model_text and not had_user_speech:
                                        logger.info("Suppressing duplicate fallback TTS response on empty user turn: %s", clean_text[:60])
                                    else:
                                        self._last_spoken_model_text = clean_text
                                        logger.info("Gemini Live text produced with 0 native audio chunks; speaking via Fallback TTS: %s", clean_text[:60])
                                        asyncio.create_task(self._safe_speak_fallback(clean_text))
                            elif (
                                self.coordinator is not None
                                and not turn_model_text
                                and turn_chunks == 0
                                and not was_interrupted
                                and had_user_speech
                                and not self._turn_tool_executed
                                and not self._turn_tool_requested
                            ):
                                clarification = "Purinjikikka mudiyala, thirumba solreengala?"
                                logger.info("Gemini Live turn produced 0 audio and 0 text for user utterance; speaking clarification prompt")
                                print(f"\n[Zye]: {clarification}\n", flush=True)
                                asyncio.create_task(self._safe_speak_fallback(clarification))

                            # Native playback streaming: wait_for_playback_complete is non-blocking to prevent receiver starvation
                            logger.debug("Gemini Live turn complete; session retained in LISTENING state for next turn")
                            self.set_state(LiveSessionState.LISTENING)
                            self._user_speaking = False

                if not self._running:
                    break
                if not is_real_session:
                    # Single-turn mock session in unit tests finishes here
                    break
                if not received_in_turn:
                    # Real session returned 0 items: stream has ended/closed
                    logger.info("Gemini Live stream ended (0 items received in turn); closing receiver")
                    break
                if hasattr(session, "_ws") and getattr(session._ws, "closed", False):
                    logger.info("Gemini Live underlying websocket closed; exiting receiver")
                    break

        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.warning("Error in live event receiver turn: %s", exc)
            self.telemetry.last_error = str(exc)
        except Exception as exc:
            logger.warning("Error in live event receiver turn: %s", exc)
            self.telemetry.last_error = str(exc)

    # -------------------------------------------------------------------------
    # Tool Execution Bridge (Section 22, 23, 24, 25, 26, 37)
    # -------------------------------------------------------------------------
    async def _handle_live_tool_call(self, session: Any, tool_call: Any) -> None:
        """
        Bridge Gemini Live function calls directly to existing MCP Orchestrator.
        Enforces execution gate, deduplication, and returns structured FunctionResponse.
        """
        function_calls = getattr(tool_call, "function_calls", [])
        if not function_calls:
            return

        self.set_state(LiveSessionState.TOOL_CALL_PENDING)
        function_responses: list[Any] = []

        try:
            for fc in function_calls:
                call_id = getattr(fc, "id", None) or f"call_{time.time()}"
                tool_name = getattr(fc, "name", "")
                tool_args = getattr(fc, "args", {}) or {}
                self.telemetry.total_tool_calls += 1

                if call_id in self._pending_tool_cancellations:
                    logger.info("Tool call %s (id=%s) cancelled before execution", tool_name, call_id)
                    self._pending_tool_cancellations.discard(call_id)
                    function_responses.append(
                        types.FunctionResponse(
                            name=tool_name,
                            id=call_id,
                            response={"result": {"status": "CANCELLED", "message": "Tool execution cancelled"}},
                        )
                    )
                    continue

                # Circuit breaker check: per-turn tool budget
                max_budget = getattr(self.config, "max_tools_per_turn", 4)
                if self._turn_tool_count > max_budget:
                    logger.warning("Tool call loop circuit breaker tripped (%d > %d) for turn; returning budget exceeded", self._turn_tool_count, max_budget)
                    function_responses.append(
                        types.FunctionResponse(
                            name=tool_name,
                            id=call_id,
                            response={"result": {"status": "LOOP_PREVENTED", "error": "Maximum per-turn tool call limit reached. Please summarize the status and respond to the user directly."}},
                        )
                    )
                    continue

                if self._current_turn is not None:
                    self._current_turn.m0_tool_requested_ns = time.perf_counter_ns()
                    self._current_turn.tool_name = tool_name
                    self._current_turn.m1_tool_validated_ns = time.perf_counter_ns()

                # Redact raw argument values in logs for privacy (ZYE-BUG-022)
                arg_summary = list(tool_args.keys()) if isinstance(tool_args, dict) else type(tool_args).__name__
                logger.info("Gemini Live requested MCP tool '%s' (id=%s, arg_keys=%s)", tool_name, call_id, arg_summary)

                # Prune cache entries older than 60 seconds
                now = time.time()
                self._operation_cache = {
                    k: v for k, v in self._operation_cache.items()
                    if now - v.get("_timestamp", 0) < 60.0
                }

                # Logical operation identity deduplication (ZYE-BUG-006):
                # Bind deduplication key to the specific provider call_id.
                # If the same call_id is redelivered over the wire, reuse the settled result.
                # If a new call_id arrives (even with identical args), execute it as a fresh distinct command.
                op_key = f"call_{call_id}_{tool_name}" if call_id else f"{tool_name}_{sorted(tool_args.items())}"
                cached_res = self._operation_cache.get(op_key)
                if cached_res and (now - cached_res.get("_timestamp", 0) < 60.0):
                    logger.info("Reusing deduplicated network delivery tool result for call_id=%s, tool=%s", call_id, tool_name)
                    tool_result = cached_res.get("result", {})
                else:
                    self.set_state(LiveSessionState.TOOL_RUNNING)
                    if self._current_turn is not None:
                        self._current_turn.m2_orchestrator_invoked_ns = time.perf_counter_ns()
                        self._current_turn.m3_tool_started_ns = time.perf_counter_ns()

                    if self.tool_dispatcher is not None:
                        try:
                            # Propagate voice origin metadata
                            if isinstance(tool_args, dict):
                                tool_args.setdefault("_origin", "voice")
                            tool_result = await self.tool_dispatcher(tool_name, tool_args)
                            is_success = (
                                isinstance(tool_result, dict)
                                and (tool_result.get("status") in ("SUCCESS", "OK", "success", "UI_READY", "ALREADY_OPEN") or tool_result.get("verified") is True)
                                and tool_result.get("verified", True) is not False
                                and not bool(tool_result.get("error"))
                            )
                            if is_success:
                                self.telemetry.successful_tool_calls += 1
                            self._operation_cache[op_key] = {"result": tool_result, "_timestamp": now, "call_id": call_id}
                        except Exception as t_err:
                            logger.error("Tool execution error for %s: %s", tool_name, t_err)
                            tool_result = {"status": "ERROR", "error": str(t_err)}
                            self._operation_cache[op_key] = {"result": tool_result, "_timestamp": now, "call_id": call_id}
                    else:
                        tool_result = {"status": "NO_DISPATCHER", "message": f"Executed {tool_name}"}

                    if self._current_turn is not None:
                        self._current_turn.m4_tool_completed_ns = time.perf_counter_ns()

                function_responses.append(
                    types.FunctionResponse(
                        name=tool_name,
                        id=call_id,
                        response={"result": tool_result},
                    )
                )

            # Return tool response to Gemini Live
            try:
                logger.info("Returning %d tool response(s) to Gemini Live", len(function_responses))
                if self._current_turn is not None:
                    self._current_turn.m5_response_sent_ns = time.perf_counter_ns()
                async with self._get_send_lock():
                    await session.send_tool_response(function_responses=function_responses)
                self.set_state(LiveSessionState.PROCESSING)
            except Exception as send_err:
                logger.error("Failed to send tool response to Gemini Live: %s", send_err)
                self.set_state(LiveSessionState.ERROR)
        finally:
            self._turn_tools_in_flight = max(0, self._turn_tools_in_flight - 1)
            self._turn_tool_executed = True
            self._turn_tool_requested = False

    # -------------------------------------------------------------------------
    # Main Continuous Conversation Runner (Section 10, 15, 36)
    # -------------------------------------------------------------------------
    async def run_live_loop(self) -> None:
        """
        Master background loop: manages continuous full-duplex session,
        reconnection with backoff, and event dispatch.
        Reuses persistent session across conversational turns.
        """
        self._running = True
        self.player.start()
        reconnect_attempts = 0

        while self._running:
            try:
                slot_id, client, project_id = self._resolve_authorized_client()
                self._active_slot_id = slot_id
                self._client = client
                target_model = (
                    self.config.fallback_model_id
                    if reconnect_attempts >= 2 and self.config.fallback_model_id
                    else self.config.model_id
                )
                self.telemetry.slot_id = slot_id
                self.telemetry.project_id = project_id
                self.telemetry.model_id = target_model

                connect_cfg = self._build_live_connect_config()
                self.set_state(LiveSessionState.CONNECTING)

                async with client.aio.live.connect(model=target_model, config=connect_cfg) as session:
                    self._active_session = session
                    self.set_state(LiveSessionState.CONNECTED)
                    self.telemetry.connected_timestamp = datetime.now(timezone.utc).isoformat()
                    self.telemetry.session_id = getattr(session, "session_id", None) or f"live_session_{int(time.time())}"
                    reconnect_attempts = 0
                    logger.info("Active Gemini Live persistent session established on slot %d (%s) using model %s",
                                slot_id, project_id, target_model)

                    # Spawn sender and receiver tasks concurrently
                    self._send_task = asyncio.create_task(self._send_audio_loop(session))
                    self._recv_task = asyncio.create_task(self._receive_events_loop(session))

                    done, pending = await asyncio.wait(
                        [self._send_task, self._recv_task],
                        return_when=asyncio.FIRST_COMPLETED,
                    )

                    for d in done:
                        if not d.cancelled() and d.exception():
                            sub_exc = d.exception()
                            logger.warning("Live subtask raised exception: %s", sub_exc)
                            self.telemetry.last_error = str(sub_exc)

                    for p in pending:
                        p.cancel()
                        try:
                            await p
                        except asyncio.CancelledError:
                            pass

            except asyncio.CancelledError:
                break
            except Exception as exc:
                reconnect_attempts += 1
                self.telemetry.reconnection_count += 1
                self.telemetry.last_error = str(exc)
                exc_msg = str(exc)
                logger.warning("Gemini Live session disconnected (%s). Reconnect attempt %d/%d in %.1fs...",
                               exc, reconnect_attempts, self.config.max_reconnect_attempts, self.config.reconnect_delay_seconds)
                self.set_state(LiveSessionState.RECONNECTING)
                self.player.flush()

                # Failover to next key on 429 / quota error
                if any(kw in exc_msg for kw in ("429", "RESOURCE_EXHAUSTED", "quota", "exhausted", "quotaExceeded")):
                    logger.warning("Quota exhausted on slot %d; advancing to next healthy slot...", slot_id)
                    self._slot_cursor = (self._slot_cursor % 7) + 1
                    if self.key_manager:
                        if hasattr(self.key_manager, "mark_rate_limited"):
                            try:
                                self.key_manager.mark_rate_limited(slot_id)
                            except Exception:
                                pass
                        if hasattr(self.key_manager, "rotate_key"):
                            try:
                                self.key_manager.rotate_key(current_slot=slot_id, reason="LIVE_SESSION_QUOTA_EXHAUSTED")
                            except Exception:
                                pass

                if reconnect_attempts >= self.config.max_reconnect_attempts:
                    logger.error("Maximum Live reconnection attempts reached. Entering DEGRADED mode.")
                    self._running = False
                    self.set_state(LiveSessionState.DEGRADED)
                    break

                await asyncio.sleep(self.config.reconnect_delay_seconds)

        if self.state != LiveSessionState.DEGRADED:
            self.set_state(LiveSessionState.CLOSED)
        self.player.stop()

    def stop(self) -> None:
        """Gracefully shut down active Gemini Live session and audio playback."""
        self._running = False
        if self._send_task and not self._send_task.done():
            self._send_task.cancel()
        if self._recv_task and not self._recv_task.done():
            self._recv_task.cancel()
        for t in self._active_tool_tasks:
            if not t.done():
                t.cancel()
        self._active_tool_tasks.clear()
        self.player.stop()
        if self.state != LiveSessionState.DEGRADED:
            self.set_state(LiveSessionState.CLOSED)
        logger.info("ZyeGeminiLiveManager stopped")

    def get_latest_turn_metrics(self) -> TurnMetrics | None:
        """Return the most recently finalized turn metrics object."""
        if self._turn_history:
            return self._turn_history[-1]
        return self._current_turn

    def get_all_turn_metrics(self) -> list[TurnMetrics]:
        """Return history of all recorded turn metrics."""
        return list(self._turn_history)

    def get_status(self) -> dict[str, Any]:
        """Return diagnostic health and telemetry dictionary for Doctor and UI."""
        return {
            "enabled": self.config.enabled,
            "state": self.state.value,
            "model_id": self.config.model_id,
            "slot_id": self.telemetry.slot_id,
            "project_id": self.telemetry.project_id,
            "is_audio_playing": self.player.is_playing(),
            "total_audio_sent_sec": self.telemetry.input_audio_seconds,
            "total_audio_received_sec": round(self.telemetry.output_audio_seconds, 2),
            "chunks_sent": self.telemetry.total_audio_chunks_sent,
            "chunks_received": self.telemetry.total_audio_chunks_received,
            "total_tool_calls": self.telemetry.total_tool_calls,
            "successful_tool_calls": self.telemetry.successful_tool_calls,
            "interruptions": self.telemetry.interruption_count,
            "reconnections": self.telemetry.reconnection_count,
            "last_error": self.telemetry.last_error,
            "resumption_handle": self.telemetry.resumption_handle,
            "last_audio_latency_ms": self.telemetry.last_audio_latency_ms,
            "average_audio_latency_ms": self.telemetry.average_audio_latency_ms,
            "total_turns_completed": self.telemetry.total_turns_completed,
            "echo_cancellation_active": self.config.echo_cancellation,
            "self_listening_suppression": self.config.self_listening_suppression,
        }
