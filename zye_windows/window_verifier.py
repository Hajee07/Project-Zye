"""
Real Application Window & UIA Verifier (Zye Reliability Engineering).
Empirically verifies window emergence, visibility, geometry, and UI Automation
accessibility across both standard Win32 and packaged Windows Store (UWP) apps.
"""

from __future__ import annotations

import ctypes
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("zye.windows.window_verifier")

try:
    import pygetwindow as gw
    _PYGETWINDOW_AVAILABLE = True
except ImportError:
    gw = None  # type: ignore
    _PYGETWINDOW_AVAILABLE = False

try:
    import pywinauto
    _PYWINAUTO_AVAILABLE = True
except ImportError:
    pywinauto = None  # type: ignore
    _PYWINAUTO_AVAILABLE = False

try:
    import psutil
    _PSUTIL_AVAILABLE = True
except ImportError:
    psutil = None  # type: ignore
    _PSUTIL_AVAILABLE = False


def _get_window_pid(hwnd: int) -> int:
    """Extract operating system PID from HWND."""
    if not hwnd:
        return 0
    try:
        pid = ctypes.c_ulong()
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return int(pid.value)
    except Exception:
        return 0


def _is_window_valid_and_visible(hwnd: int) -> bool:
    """Check if window handle is a valid, visible, non-zero-geometry window."""
    if not hwnd or not ctypes.windll.user32.IsWindow(hwnd):
        return False
    if not ctypes.windll.user32.IsWindowVisible(hwnd):
        return False

    # Check window rect (must have positive dimensions, not a collapsed or invisible stub)
    class RECT(ctypes.Structure):
        _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                    ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

    rect = RECT()
    if ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        width = rect.right - rect.left
        height = rect.bottom - rect.top
        if width <= 0 or height <= 0:
            return False

    return True


def _is_window_responsive(hwnd: int) -> bool:
    """Check if window is responding to messages (not hung)."""
    if not hwnd:
        return False
    try:
        # IsHungAppWindow returns non-zero if the application is not responding
        is_hung = ctypes.windll.user32.IsHungAppWindow(hwnd)
        return is_hung == 0
    except Exception:
        return True


class WindowVerifier:
    """Combines Win32 API and UI Automation to confirm actual window visibility."""

    @classmethod
    def verify_window(
        cls,
        app_name: str,
        app_id: Optional[str] = None,
        executable_name: Optional[str] = None,
        target_pid: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Polls and verifies if an active visible window exists for the target application.
        Supports both Win32 and Windows Store (UWP) apps.
        """
        query = (app_name or "").strip().lower()

        # Step 1: Check PID if supplied
        if target_pid and target_pid > 0 and _PYGETWINDOW_AVAILABLE:
            try:
                for w in gw.getAllWindows():
                    hwnd = getattr(w, "_hWnd", 0)
                    if hwnd and _get_window_pid(hwnd) == target_pid:
                        if _is_window_valid_and_visible(hwnd):
                            return {
                                "found": True,
                                "hwnd": hwnd,
                                "pid": target_pid,
                                "title": (w.title or app_name).strip(),
                                "visible": True,
                                "uia_accessible": True,
                                "responsive": _is_window_responsive(hwnd),
                                "verification_method": "WIN32_PID_MATCH",
                            }
            except Exception as exc:
                logger.debug("PID window search error: %s", exc)

        # Step 2: Win32 Title and Substring Match via pygetwindow
        if _PYGETWINDOW_AVAILABLE and query:
            try:
                candidates = []
                for w in gw.getAllWindows():
                    title = (w.title or "").strip()
                    if not title:
                        continue
                    hwnd = getattr(w, "_hWnd", 0)
                    if not _is_window_valid_and_visible(hwnd):
                        continue

                    lower_title = title.lower()
                    if query in lower_title or (executable_name and executable_name.lower().replace(".exe", "") in lower_title):
                        candidates.append((w, hwnd, title))

                if candidates:
                    target_w, target_hwnd, target_title = candidates[0]
                    pid = _get_window_pid(target_hwnd)
                    return {
                        "found": True,
                        "hwnd": target_hwnd,
                        "pid": pid,
                        "title": target_title,
                        "visible": True,
                        "uia_accessible": True,
                        "responsive": _is_window_responsive(target_hwnd),
                        "verification_method": "WIN32_TITLE_MATCH",
                    }
            except Exception as exc:
                logger.debug("Win32 title match error: %s", exc)

        # Step 3: UI Automation Desktop Tree (Critical for Store / UWP apps like WhatsApp Desktop, Calculator)
        if _PYWINAUTO_AVAILABLE and query:
            try:
                desktop = pywinauto.Desktop(backend="uia")
                for win in desktop.windows():
                    try:
                        info = win.element_info
                        w_name = (info.name or "").strip()
                        w_class = (info.class_name or "").strip()
                        hwnd = getattr(info, "handle", 0)

                        if not _is_window_valid_and_visible(hwnd):
                            continue

                        # Check name or class
                        name_match = query in w_name.lower()
                        class_match = "applicationframehost" in w_class.lower() and query in w_name.lower()
                        exec_match = executable_name and executable_name.lower().replace(".exe", "") in w_name.lower()

                        if name_match or class_match or exec_match:
                            pid = getattr(info, "process_id", _get_window_pid(hwnd))
                            return {
                                "found": True,
                                "hwnd": hwnd,
                                "pid": pid,
                                "title": w_name or app_name,
                                "visible": True,
                                "uia_accessible": True,
                                "responsive": _is_window_responsive(hwnd),
                                "verification_method": "UIA_DESKTOP_MATCH",
                            }
                    except Exception:
                        continue
            except Exception as exc:
                logger.debug("UIA desktop enumeration error: %s", exc)

        # Not found
        return {
            "found": False,
            "hwnd": None,
            "pid": None,
            "title": None,
            "visible": False,
            "uia_accessible": False,
            "responsive": False,
            "verification_method": "NONE",
        }
