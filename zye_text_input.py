#!/usr/bin/env python3
"""
ZYE AI — Alt+Z Text Fallback & Keyboard Input Handler v1.0
===========================================================

Provides a silent text-input mode activated by the Alt+Z hotkey when
voice input is unavailable or disabled. Features:
- Global Alt+Z hotkey registration (Windows, via `keyboard` library)
- Non-blocking hotkey listener thread
- Thread-safe trigger queue
- Multi-line text input from stdin with timeout
- Graceful disable/enable of hotkey listener
- Integration with the voice loop in main.py

Operating System: Windows 10/11 x64
Hotkey: Alt + Z (configurable)
"""

from __future__ import annotations

import logging
import queue
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable

try:
    import keyboard as kb
    _KEYBOARD_AVAILABLE = True
except ImportError:
    kb = None  # type: ignore
    _KEYBOARD_AVAILABLE = False

logger = logging.getLogger("zye_text_input")


# ============================================================================
# 1. Custom Exceptions
# ============================================================================

class TextInputError(Exception):
    """Base exception for hotkey/text-input subsystem failures."""
    pass


class TextInputUnavailableError(TextInputError):
    """Raised when the keyboard library is not installed."""
    pass


class TextInputTimeoutError(TextInputError):
    """Raised when waiting for user text input exceeds the timeout."""
    pass


# ============================================================================
# 2. Configuration
# ============================================================================

@dataclass
class TextInputConfig:
    """Configuration for Alt+Z text fallback mode."""
    hotkey: str = "alt+z"
    input_timeout_seconds: float = 60.0
    prompt_message: str = "[Zye Text Mode] Type your message and press Enter:"
    max_input_length: int = 2000
    enabled: bool = True


# ============================================================================
# 3. Trigger Event
# ============================================================================

@dataclass
class TextTriggerEvent:
    """Represents a single Alt+Z activation event."""
    timestamp: float = field(default_factory=time.time)
    source: str = "hotkey"


# ============================================================================
# 4. Text Input Result
# ============================================================================

@dataclass
class TextInputResult:
    """Result of a text input session."""
    text: str
    source: str          # "hotkey" | "direct" | "timeout" | "cancelled"
    duration_seconds: float
    truncated: bool = False


# ============================================================================
# 5. AltZ Text Input Handler
# ============================================================================

class AltZTextInputHandler:
    """
    Non-blocking Alt+Z hotkey listener and text input collector.

    Registers a global Alt+Z hotkey (via `keyboard` library).
    When triggered, adds a TextTriggerEvent to an internal queue.
    The voice loop polls is_triggered() or awaits get_trigger_event().
    """

    def __init__(self, config: TextInputConfig | None = None) -> None:
        self.config = config or TextInputConfig()
        self._trigger_queue: queue.Queue[TextTriggerEvent] = queue.Queue(maxsize=4)
        self._running = False
        self._hotkey_registered = False
        self._lock = threading.Lock()

        # Diagnostics
        self.total_triggers: int = 0
        self.total_sessions: int = 0
        self.total_timeouts: int = 0
        self.last_trigger_time: float | None = None

    # ------------------------------------------------------------------------
    # Hotkey Lifecycle
    # ------------------------------------------------------------------------

    def start(self) -> dict[str, Any]:
        """Register the Alt+Z global hotkey and start listening."""
        with self._lock:
            if self._running:
                return {"status": "already_running", "hotkey": self.config.hotkey}

            if not _KEYBOARD_AVAILABLE:
                logger.warning("keyboard library not available — Alt+Z hotkey cannot be registered")
                return {
                    "status": "unavailable",
                    "error": "keyboard library not installed",
                    "hotkey": self.config.hotkey,
                }

            if not self.config.enabled:
                return {"status": "disabled", "hotkey": self.config.hotkey}

            try:
                kb.add_hotkey(self.config.hotkey, self._on_hotkey_pressed, suppress=False)
                self._hotkey_registered = True
                self._running = True
                logger.info("Alt+Z text fallback hotkey registered: %s", self.config.hotkey)
                return {"status": "running", "hotkey": self.config.hotkey}
            except Exception as exc:
                logger.warning("Failed to register hotkey %s: %s", self.config.hotkey, exc)
                return {
                    "status": "error",
                    "hotkey": self.config.hotkey,
                    "error": str(exc),
                }

    def stop(self) -> None:
        """Unregister the hotkey and stop listening."""
        with self._lock:
            if not self._running:
                return
            if _KEYBOARD_AVAILABLE and self._hotkey_registered:
                try:
                    kb.remove_hotkey(self.config.hotkey)
                except Exception:
                    pass
                self._hotkey_registered = False
            self._running = False
            logger.info("Alt+Z text fallback hotkey unregistered")

    def __enter__(self) -> AltZTextInputHandler:
        self.start()
        return self

    def __exit__(self, *args: Any) -> None:
        self.stop()

    # ------------------------------------------------------------------------
    # Trigger API
    # ------------------------------------------------------------------------

    def _on_hotkey_pressed(self) -> None:
        """Internal callback fired when Alt+Z is pressed."""
        self.total_triggers += 1
        self.last_trigger_time = time.time()
        event = TextTriggerEvent(source="hotkey")
        try:
            self._trigger_queue.put_nowait(event)
        except queue.Full:
            logger.debug("Alt+Z trigger queue full; discarding extra press")

    def is_triggered(self) -> bool:
        """Return True if at least one pending Alt+Z trigger is in the queue."""
        return not self._trigger_queue.empty()

    def get_trigger_event(self, block: bool = False, timeout: float = 0.05) -> TextTriggerEvent | None:
        """
        Retrieve the next pending Alt+Z trigger event.
        Returns None if no event is available within timeout.
        """
        try:
            return self._trigger_queue.get(block=block, timeout=timeout)
        except queue.Empty:
            return None

    def clear_pending_triggers(self) -> None:
        """Drain all pending events from the trigger queue."""
        while not self._trigger_queue.empty():
            try:
                self._trigger_queue.get_nowait()
            except queue.Empty:
                break

    # ------------------------------------------------------------------------
    # Text Collection
    # ------------------------------------------------------------------------

    def collect_text_input(
        self,
        prompt: str | None = None,
        timeout: float | None = None,
        on_prompt_shown: Callable[[], None] | None = None,
    ) -> TextInputResult:
        """
        Display prompt and collect a line of text from stdin with timeout.

        Parameters:
            prompt: Custom prompt string (uses config default if None).
            timeout: Seconds before auto-cancellation (uses config default if None).
            on_prompt_shown: Optional callback triggered immediately after prompt is displayed.

        Returns:
            TextInputResult with the collected text.
        """
        effective_prompt = prompt or self.config.prompt_message
        effective_timeout = timeout or self.config.input_timeout_seconds
        self.total_sessions += 1
        t0 = time.time()

        result_holder: list[str | None] = [None]
        exception_holder: list[Exception | None] = [None]

        def _read_stdin() -> None:
            try:
                print(f"\n{effective_prompt} ", flush=True, end="")
                line = input()
                result_holder[0] = line
            except (EOFError, KeyboardInterrupt) as exc:
                exception_holder[0] = exc

        reader = threading.Thread(target=_read_stdin, daemon=True)
        reader.start()

        if on_prompt_shown:
            try:
                on_prompt_shown()
            except Exception:
                pass

        reader.join(timeout=effective_timeout)
        elapsed = time.time() - t0

        if result_holder[0] is not None:
            raw = result_holder[0]
            truncated = len(raw) > self.config.max_input_length
            text = raw[: self.config.max_input_length].strip()
            return TextInputResult(
                text=text,
                source="hotkey",
                duration_seconds=round(elapsed, 3),
                truncated=truncated,
            )

        if exception_holder[0] is not None:
            return TextInputResult(
                text="",
                source="cancelled",
                duration_seconds=round(elapsed, 3),
            )

        # Timeout
        self.total_timeouts += 1
        return TextInputResult(
            text="",
            source="timeout",
            duration_seconds=round(elapsed, 3),
        )

    # ------------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------------

    def get_diagnostics(self) -> dict[str, Any]:
        """Return structured telemetry for doctor.py."""
        return {
            "status": "running" if self._running else "stopped",
            "keyboard_available": _KEYBOARD_AVAILABLE,
            "hotkey": self.config.hotkey,
            "enabled": self.config.enabled,
            "hotkey_registered": self._hotkey_registered,
            "pending_triggers": self._trigger_queue.qsize(),
            "total_triggers": self.total_triggers,
            "total_sessions": self.total_sessions,
            "total_timeouts": self.total_timeouts,
            "last_trigger_time": self.last_trigger_time,
        }


if __name__ == "__main__":
    print("Alt+Z Text Input Handler")
    handler = AltZTextInputHandler()
    result = handler.start()
    print("Start result:", result)
    print("Press Alt+Z then type a message, or wait 5 seconds to exit...")
    for _ in range(50):
        time.sleep(0.1)
        if handler.is_triggered():
            handler.get_trigger_event()
            text_result = handler.collect_text_input(timeout=30.0)
            print(f"Collected: {text_result!r}")
            break
    handler.stop()
    print("Diagnostics:", handler.get_diagnostics())
