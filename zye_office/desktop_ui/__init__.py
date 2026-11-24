"""
Universal Desktop UI Automation & Ribbon Accelerator Package — Zye Day 23.
"""

from zye_office.desktop_ui.foreground_window_guard import ForegroundWindowGuard
from zye_office.desktop_ui.keyboard_sequence_engine import KeyboardSequenceEngine
from zye_office.desktop_ui.ribbon_accelerator import DesktopRibbonAccelerator
from zye_office.desktop_ui.ui_errors import (
    DesktopUIError,
    UIControlNotFoundError,
    UIFocusLostError,
    UIForegroundMismatchError,
    UIWindowNotFoundError,
)
from zye_office.desktop_ui.ui_inspector import DesktopUIInspector

__all__ = [
    "ForegroundWindowGuard",
    "DesktopUIInspector",
    "KeyboardSequenceEngine",
    "DesktopRibbonAccelerator",
    "DesktopUIError",
    "UIWindowNotFoundError",
    "UIForegroundMismatchError",
    "UIControlNotFoundError",
    "UIFocusLostError",
]
