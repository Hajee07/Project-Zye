"""
Foreground Window Guard for Universal Desktop UI Automation — Zye Day 23.
Ensures UI commands and keyboard sequences execute only on the validated foreground window.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import logging
from typing import Any, Dict, Optional
import psutil
from zye_office.desktop_ui.ui_errors import (
    UIForegroundMismatchError,
    UIWindowNotFoundError,
)

logger = logging.getLogger("zye.office.ui.foreground_guard")

user32 = ctypes.windll.user32


class ForegroundWindowGuard:
    """Verifies and tracks the active foreground Windows window."""

    @staticmethod
    def get_foreground_window_info() -> Dict[str, Any]:
        """Query HWND, window title, and owning process of current foreground window."""
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            raise UIWindowNotFoundError("No active foreground window found.")

        # Window Title
        length = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value

        # Process ID
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

        proc_name = "unknown.exe"
        try:
            proc = psutil.Process(pid.value)
            proc_name = proc.name()
        except Exception:
            pass

        return {
            "hwnd": hwnd,
            "title": title,
            "pid": pid.value,
            "process_name": proc_name,
        }

    @classmethod
    def verify_foreground_process(cls, expected_process_substring: str) -> bool:
        """Verify that foreground window belongs to expected process (e.g. 'excel', 'powerpnt')."""
        info = cls.get_foreground_window_info()
        proc = info["process_name"].lower()
        title = info["title"].lower()
        expected = expected_process_substring.lower().strip()

        if expected not in proc and expected not in title:
            raise UIForegroundMismatchError(expected=expected_process_substring, actual=f"{info['process_name']} ({info['title']})")
        return True
