"""
Safe Keyboard Sequence Engine for Universal Desktop UI — Zye Day 23.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional
import pyautogui
from zye_office.desktop_ui.foreground_window_guard import ForegroundWindowGuard
from zye_office.desktop_ui.ui_errors import (
    UIFocusLostError,
)

logger = logging.getLogger("zye.office.ui.keyboard")

SAFE_KEY_NAMES = {
    "alt", "ctrl", "shift", "enter", "esc", "tab", "space", "backspace",
    "up", "down", "left", "right", "home", "end", "pageup", "pagedown",
    "f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10", "f11", "f12",
}


class KeyboardSequenceEngine:
    """Executes validated and bounded keystrokes with active window focus verification."""

    def __init__(self, max_sequence_length: int = 20) -> None:
        self.max_length = max_sequence_length
        self.guard = ForegroundWindowGuard()

    def execute_sequence(
        self,
        keys: List[str],
        expected_process: Optional[str] = None,
        interval: float = 0.05,
    ) -> Dict[str, Any]:
        """Send keystrokes safely to the active window."""
        if not keys or len(keys) > self.max_length:
            raise ValueError(f"Sequence length ({len(keys)}) exceeds maximum of {self.max_length}.")

        # 1. Verify target window
        initial_win = self.guard.get_foreground_window_info()
        if expected_process:
            self.guard.verify_foreground_process(expected_process)

        # 2. Execute keystrokes
        executed: List[str] = []
        for k in keys:
            norm_k = k.lower().strip()
            # Verify focus has not changed before pressing
            curr_hwnd = self.guard.get_foreground_window_info()["hwnd"]
            if curr_hwnd != initial_win["hwnd"]:
                raise UIFocusLostError(f"Focus changed from HWND {initial_win['hwnd']} to {curr_hwnd}.")

            if len(norm_k) == 1 and (norm_k.isalnum() or norm_k in "-=_+[]{}|;:',.<>/?"):
                pyautogui.press(norm_k)
            elif norm_k in SAFE_KEY_NAMES:
                pyautogui.press(norm_k)
            else:
                logger.warning("Skipping untrusted key: %s", norm_k)
                continue

            executed.append(norm_k)
            time.sleep(interval)

        return {
            "status": "SUCCESS",
            "executed_keys": executed,
            "target_window": initial_win["title"],
            "process_name": initial_win["process_name"],
        }
