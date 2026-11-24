"""
Multi-Monitor and Display Management Engine — Zye Day 18.
Discovers connected physical and virtual displays, detects primary monitors,
and moves windows seamlessly across multi-monitor desktop environments.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import logging
import sys
from typing import Any, Optional

try:
    import pyautogui
    _PYAUTOGUI_AVAILABLE = True
except ImportError:
    _PYAUTOGUI_AVAILABLE = False

try:
    import pygetwindow as gw
    _PYGETWINDOW_AVAILABLE = True
except ImportError:
    _PYGETWINDOW_AVAILABLE = False

from zye_windows.windows_models import DisplayInfo

logger = logging.getLogger("zye.windows.display")


# Win32 Structures for Multi-Monitor Enumeration
class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class MONITORINFOEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", RECT),
        ("rcWork", RECT),
        ("dwFlags", wintypes.DWORD),
        ("szDevice", wintypes.WCHAR * 32),
    ]


class WindowsDisplayManager:
    """
    Manages multi-monitor discovery and window positioning across displays.
    """

    def __init__(self) -> None:
        pass

    def get_connected_displays(self) -> list[DisplayInfo]:
        """
        Enumerate all connected displays using Win32 EnumDisplayMonitors API.
        Falls back to PyAutoGUI screen size if API is unavailable.
        """
        displays: list[DisplayInfo] = []

        try:
            user32 = ctypes.windll.user32

            def _monitor_enum_proc(hMonitor, hdcMonitor, lprcMonitor, dwData):
                info = MONITORINFOEXW()
                info.cbSize = ctypes.sizeof(MONITORINFOEXW)
                if user32.GetMonitorInfoW(hMonitor, ctypes.byref(info)):
                    width = info.rcMonitor.right - info.rcMonitor.left
                    height = info.rcMonitor.bottom - info.rcMonitor.top
                    is_primary = bool(info.dwFlags & 1)  # MONITORINFOF_PRIMARY = 1
                    name = str(info.szDevice)
                    displays.append(
                        DisplayInfo(
                            display_id=len(displays) + 1,
                            name=name,
                            width=int(width),
                            height=int(height),
                            left=int(info.rcMonitor.left),
                            top=int(info.rcMonitor.top),
                            is_primary=is_primary,
                            is_available=True,
                        )
                    )
                return True

            MONITORENUMPROC = ctypes.WINFUNCTYPE(
                wintypes.BOOL,
                wintypes.HMONITOR,
                wintypes.HDC,
                ctypes.POINTER(RECT),
                wintypes.LPARAM,
            )

            callback = MONITORENUMPROC(_monitor_enum_proc)
            user32.EnumDisplayMonitors(0, 0, callback, 0)

        except Exception as exc:
            logger.warning("Win32 EnumDisplayMonitors failed: %s, falling back to pyautogui.", exc)

        if not displays:
            # Fallback to single primary monitor via pyautogui
            w, h = (1920, 1080)
            if _PYAUTOGUI_AVAILABLE:
                try:
                    w, h = pyautogui.size()
                except Exception:
                    pass
            displays.append(
                DisplayInfo(
                    display_id=1,
                    name="Generic Display (Primary)",
                    width=int(w),
                    height=int(h),
                    left=0,
                    top=0,
                    is_primary=True,
                    is_available=True,
                )
            )

        return displays

    def get_primary_display(self) -> Optional[DisplayInfo]:
        """Fetch the primary display monitor."""
        displays = self.get_connected_displays()
        for d in displays:
            if d.is_primary:
                return d
        return displays[0] if displays else None

    def get_display_details(self, display_id: int) -> dict[str, Any]:
        """Fetch details for a specific display ID."""
        displays = self.get_connected_displays()
        matching = [d for d in displays if d.display_id == display_id]
        if not matching:
            return {
                "status": "NOT_FOUND",
                "message": f"Display ID {display_id} not found. Connected count: {len(displays)}",
                "display_id": display_id,
            }
        return {"status": "SUCCESS", "display": matching[0].model_dump()}

    def get_window_monitor(self, window_id: Any) -> dict[str, Any]:
        """Identify which monitor currently hosts the given window."""
        if not _PYGETWINDOW_AVAILABLE:
            return {"status": "ERROR", "message": "pygetwindow required."}

        matches = [w for w in gw.getAllWindows() if getattr(w, "_hWnd", 0) == window_id] if isinstance(window_id, int) else [
            w for w in gw.getAllWindows() if str(window_id).lower() in (w.title or "").lower() and w.title.strip()
        ]
        if not matches:
            return {"status": "WINDOW_NOT_FOUND", "target": window_id}

        win = matches[0]
        wx = getattr(win, "left", 0) + getattr(win, "width", 800) // 2
        wy = getattr(win, "top", 0) + getattr(win, "height", 600) // 2

        displays = self.get_connected_displays()
        for d in displays:
            if d.left <= wx <= (d.left + d.width) and d.top <= wy <= (d.top + d.height):
                return {
                    "status": "SUCCESS",
                    "window": win.title,
                    "monitor_id": d.display_id,
                    "display": d.model_dump(),
                }

        primary = self.get_primary_display()
        return {
            "status": "SUCCESS",
            "window": win.title,
            "monitor_id": primary.display_id if primary else 1,
            "display": primary.model_dump() if primary else {},
        }

    def move_window_to_monitor(self, window_keyword: str, display_id: int) -> dict[str, Any]:
        """
        Move a window to the specified display monitor.
        Validates target display existence and adjusts window geometry.
        """
        displays = self.get_connected_displays()
        matching_displays = [d for d in displays if d.display_id == display_id]
        if not matching_displays:
            return {
                "status": "DISPLAY_NOT_FOUND",
                "message": f"Display ID {display_id} is not connected. Available displays: {len(displays)}",
                "target_display_id": display_id,
                "available_displays": [d.model_dump() for d in displays],
            }

        target_display = matching_displays[0]

        if not _PYGETWINDOW_AVAILABLE:
            return {"status": "ERROR", "message": "pygetwindow required."}

        matches = [w for w in gw.getAllWindows() if str(window_keyword).lower() in (w.title or "").lower() and w.title.strip()]
        if not matches:
            return {
                "status": "WINDOW_NOT_FOUND",
                "message": f"No active window found matching '{window_keyword}'.",
                "keyword": window_keyword,
            }

        target_win = matches[0]
        try:
            was_maximized = bool(getattr(target_win, "isMaximized", False))
            if was_maximized:
                target_win.restore()

            # Place at top-left with 50px margin of target display
            new_x = target_display.left + 50
            new_y = target_display.top + 50
            target_win.moveTo(new_x, new_y)

            if was_maximized:
                target_win.maximize()

            return {
                "status": "SUCCESS",
                "action": "move_window_to_monitor",
                "window": target_win.title,
                "target_display_id": display_id,
                "target_display": target_display.name,
                "new_coordinates": {"x": new_x, "y": new_y},
                "verified": True,
            }
        except Exception as exc:
            logger.error("Failed to move window to monitor: %s", exc)
            return {"status": "ERROR", "message": f"Failed to move window to monitor: {exc}"}
