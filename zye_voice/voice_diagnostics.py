#!/usr/bin/env python3
"""
ZYE AI — Voice Diagnostics & Real-Time Pipeline Telemetry
=========================================================

Provides development-only structured diagnostic logging for the voice pipeline:
1. Microphone detected: YES/NO
2. Incoming audio level (RMS & dB)
3. VAD speech start timestamp
4. VAD speech end timestamp
5. Partial transcript (if streamed)
6. Final transcript
7. Gemini interpreted user intent
8. Selected MCP tool
9. Tool execution result
10. Total processing latency

Privacy & Security:
- Strict zero-retention policy by default.
- Does NOT record raw microphone audio or retain private transcripts to disk
  unless explicitly authorized via allow_audio_save=True / ZYE_VOICE_SAVE_AUDIO=1.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import logging
import math
import os
import time
from typing import Any

logger = logging.getLogger("zye_voice_diagnostics")


@dataclass
class VoiceDiagnosticEvent:
    """Telemetry record for a single voice interaction cycle."""
    session_id: str
    timestamp_iso: str
    mic_detected: bool
    audio_level_rms: float
    audio_level_db: float
    vad_speech_start_ts: float | None = None
    vad_speech_end_ts: float | None = None
    vad_duration_seconds: float | None = None
    partial_transcript: str | None = None
    final_transcript: str = ""
    interpreted_intent: str = ""
    selected_mcp_tool: str | None = None
    tool_execution_result: Any | None = None
    total_latency_ms: float = 0.0
    status: str = "PASS"  # "PASS" | "FAIL"
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "timestamp": self.timestamp_iso,
            "mic_detected": "YES" if self.mic_detected else "NO",
            "audio_level_rms": round(self.audio_level_rms, 6),
            "audio_level_db": round(self.audio_level_db, 2),
            "vad_speech_start": self.vad_speech_start_ts,
            "vad_speech_end": self.vad_speech_end_ts,
            "vad_duration_sec": round(self.vad_duration_seconds, 3) if self.vad_duration_seconds else None,
            "partial_transcript": self.partial_transcript,
            "final_transcript": self.final_transcript,
            "interpreted_intent": self.interpreted_intent,
            "selected_mcp_tool": self.selected_mcp_tool or "NONE",
            "tool_execution_result": self.tool_execution_result,
            "total_latency_ms": round(self.total_latency_ms, 2),
            "status": self.status,
            "error_message": self.error_message,
        }

    def format_terminal(self) -> str:
        """Format event as human-readable diagnostic banner for terminal."""
        lines = [
            "----------------- [ZYE VOICE DIAGNOSTICS] -----------------",
            f"Timestamp               : {self.timestamp_iso}",
            f"1. Microphone Detected  : {'YES' if self.mic_detected else 'NO'}",
            f"2. Audio Level          : RMS {self.audio_level_rms:.4f} ({self.audio_level_db:.1f} dBFS)",
            f"3. VAD Speech Start     : {f'{self.vad_speech_start_ts:.3f}s' if self.vad_speech_start_ts else 'N/A'}",
            f"4. VAD Speech End       : {f'{self.vad_speech_end_ts:.3f}s' if self.vad_speech_end_ts else 'N/A'}",
            f"5. Partial Transcript   : {self.partial_transcript or 'N/A'}",
            f"6. Final Transcript     : {self.final_transcript or '<EMPTY>'}",
            f"7. Interpreted Intent   : {self.interpreted_intent or 'N/A'}",
            f"8. Selected MCP Tool    : {self.selected_mcp_tool or 'NONE'}",
            f"9. Tool Result          : {str(self.tool_execution_result)[:80] if self.tool_execution_result else 'NONE'}",
            f"10. Total Latency       : {self.total_latency_ms:.1f} ms",
            f"Status                  : {self.status}",
            "-----------------------------------------------------------",
        ]
        return "\n".join(lines)


class VoiceDiagnosticsTracker:
    """
    Session tracker capturing and formatting the 10 diagnostic parameters
    with sub-millisecond precision.
    """

    def __init__(self, allow_audio_save: bool = False) -> None:
        self.allow_audio_save = (
            allow_audio_save or os.environ.get("ZYE_VOICE_SAVE_AUDIO", "0").strip() == "1"
        )
        self.enabled = os.environ.get("ZYE_VOICE_DIAGNOSTICS", "1").strip() != "0"
        self._current_event: VoiceDiagnosticEvent | None = None
        self._start_time: float = 0.0

    def start_interaction(
        self,
        mic_detected: bool = True,
        audio_level_rms: float = 0.0,
    ) -> VoiceDiagnosticEvent:
        """Initialize a new diagnostic tracking cycle."""
        self._start_time = time.perf_counter()
        now_iso = datetime.now(timezone.utc).isoformat()
        session_id = f"vdiag_{int(self._start_time * 1000)}"

        # Compute dBFS safely
        db = 20.0 * math.log10(max(audio_level_rms, 1e-6))

        self._current_event = VoiceDiagnosticEvent(
            session_id=session_id,
            timestamp_iso=now_iso,
            mic_detected=mic_detected,
            audio_level_rms=audio_level_rms,
            audio_level_db=db,
        )
        return self._current_event

    def record_vad_timing(
        self,
        start_ts: float | None = None,
        end_ts: float | None = None,
    ) -> None:
        """Record VAD speech onset and offset timestamps."""
        if not self._current_event:
            return
        if start_ts is not None:
            self._current_event.vad_speech_start_ts = start_ts
        if end_ts is not None:
            self._current_event.vad_speech_end_ts = end_ts
        if self._current_event.vad_speech_start_ts and self._current_event.vad_speech_end_ts:
            self._current_event.vad_duration_seconds = max(
                0.0,
                self._current_event.vad_speech_end_ts - self._current_event.vad_speech_start_ts,
            )

    def record_transcript(
        self,
        final_transcript: str,
        partial_transcript: str | None = None,
    ) -> None:
        """Record partial and final recognized speech transcripts."""
        if not self._current_event:
            return
        self._current_event.final_transcript = final_transcript
        if partial_transcript is not None:
            self._current_event.partial_transcript = partial_transcript

    def record_gemini_intent(self, intent: str) -> None:
        """Record Gemini's interpreted user intent."""
        if not self._current_event:
            return
        self._current_event.interpreted_intent = intent

    def record_tool_dispatch(
        self,
        tool_name: str | None,
        tool_result: Any | None = None,
        status: str = "PASS",
        error_message: str | None = None,
    ) -> None:
        """Record the selected MCP tool and execution outcome."""
        if not self._current_event:
            return
        self._current_event.selected_mcp_tool = tool_name
        self._current_event.tool_execution_result = tool_result
        self._current_event.status = status
        if error_message:
            self._current_event.error_message = error_message

    def finalize(
        self,
        status: str | None = None,
        error_message: str | None = None,
    ) -> VoiceDiagnosticEvent:
        """Finalize timing and return diagnostic event."""
        if not self._current_event:
            self.start_interaction(mic_detected=False)

        elapsed_ms = (time.perf_counter() - self._start_time) * 1000.0
        self._current_event.total_latency_ms = elapsed_ms

        if status:
            self._current_event.status = status
        if error_message:
            self._current_event.error_message = error_message

        # Output diagnostic banner if enabled
        if self.enabled:
            print(self._current_event.format_terminal())

        return self._current_event


# Singleton diagnostic instance
_tracker: VoiceDiagnosticsTracker | None = None


def get_voice_diagnostics() -> VoiceDiagnosticsTracker:
    """Retrieve global diagnostic tracker."""
    global _tracker
    if _tracker is None:
        _tracker = VoiceDiagnosticsTracker()
    return _tracker
