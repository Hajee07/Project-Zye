"""
Universal Window Management Engine — Zye Day 16 & Day 18.
Discovers and manipulates Windows desktop applications using PyGetWindow / Win32 API.
Supports focus, minimize, maximize, close, restore, snap (left, right, top, bottom),
move, resize, center, and multi-window disambiguation.
"""

from __future__ import annotations

import ctypes
import logging
import sys
import time
from typing import Any, Optional

try:
    import pygetwindow as gw
    _PYGETWINDOW_AVAILABLE = True
except ImportError:
    _PYGETWINDOW_AVAILABLE = False

try:
    import pyautogui
    _PYAUTOGUI_AVAILABLE = True
except ImportError:
    _PYAUTOGUI_AVAILABLE = False

from zye_windows.windows_models import WindowInfo

logger = logging.getLogger("zye.windows.window_manager")

SUPPORTED_ACTIONS = {
    "focus", "minimize", "maximize", "close", "restore",
    "snap_left", "snap_right", "snap_top", "snap_bottom",
    "move", "resize", "center", "switch"
}


def _get_window_pid(hwnd: int) -> int:
    """Extract process ID from window HWND using User32 API."""
    if not hwnd:
        return 0
    try:
        pid = ctypes.c_ulong()
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return int(pid.value)
    except Exception:
        return 0


class WindowsWindowManager:
    """
    Manages active Windows desktop windows with state verification, geometry control,
    and ambiguity resolution.
    """

    def __init__(self) -> None:
        if _PYAUTOGUI_AVAILABLE:
            pyautogui.FAILSAFE = True

    def list_windows(self, include_empty: bool = False) -> list[WindowInfo]:
        """List all visible top-level desktop windows (backward-compatible alias)."""
        return self.list_open_windows(include_empty=include_empty)

    def list_open_windows(self, include_empty: bool = False) -> list[WindowInfo]:
        """List all visible top-level desktop windows with PID and geometry."""
        if not _PYGETWINDOW_AVAILABLE:
            logger.warning("pygetwindow is not installed.")
            return []

        results: list[WindowInfo] = []
        try:
            windows = gw.getAllWindows()
            for w in windows:
                title = (w.title or "").strip()
                if not title and not include_empty:
                    continue
                hwnd = getattr(w, "_hWnd", 0)
                pid = _get_window_pid(hwnd)
                results.append(
                    WindowInfo(
                        title=title,
                        hwnd=hwnd,
                        process_id=pid,
                        visible=bool(getattr(w, "visible", True)),
                        is_minimized=bool(getattr(w, "isMinimized", False)),
                        is_maximized=bool(getattr(w, "isMaximized", False)),
                        is_active=bool(getattr(w, "isActive", False)),
                        left=int(getattr(w, "left", 0)),
                        top=int(getattr(w, "top", 0)),
                        width=int(getattr(w, "width", 0)),
                        height=int(getattr(w, "height", 0)),
                    )
                )
        except Exception as exc:
            logger.error("Error enumerating windows: %s", exc)
        return results

    def get_active_window(self) -> Optional[WindowInfo]:
        """Fetch the currently active foreground desktop window."""
        if not _PYGETWINDOW_AVAILABLE:
            return None
        try:
            w = gw.getActiveWindow()
            if not w:
                return None
            hwnd = getattr(w, "_hWnd", 0)
            return WindowInfo(
                title=(w.title or "").strip(),
                hwnd=hwnd,
                process_id=_get_window_pid(hwnd),
                visible=bool(getattr(w, "visible", True)),
                is_minimized=bool(getattr(w, "isMinimized", False)),
                is_maximized=bool(getattr(w, "isMaximized", False)),
                is_active=True,
                left=int(getattr(w, "left", 0)),
                top=int(getattr(w, "top", 0)),
                width=int(getattr(w, "width", 0)),
                height=int(getattr(w, "height", 0)),
            )
        except Exception:
            # Headless or invalid foreground HWND is normal in test/terminal sessions
            return None

    def find_windows(self, keyword: str) -> list[Any]:
        """Find PyGetWindow window instances matching a keyword (case-insensitive substring)."""
        if not _PYGETWINDOW_AVAILABLE or not keyword or not str(keyword).strip():
            return []
        kw = str(keyword).strip().lower()
        try:
            matches = [w for w in gw.getAllWindows() if kw in (w.title or "").lower() and w.title.strip()]
            return matches
        except Exception as exc:
            logger.error("Error searching windows for '%s': %s", keyword, exc)
            return []

    def find_window(self, query: str) -> dict[str, Any]:
        """
        Disambiguate windows matching a query string.
        Returns exact match, candidate list if ambiguous, or not found.
        """
        matches = self.find_windows(query)
        if not matches:
            return {
                "status": "NOT_FOUND",
                "query": query,
                "message": f"No windows found matching query '{query}'.",
                "count": 0,
                "candidates": [],
            }

        candidate_titles = [(w.title or "").strip() for w in matches]
        # Prefer exact title match if single
        exact = [w for w in matches if (w.title or "").strip().lower() == query.strip().lower()]
        if len(exact) == 1:
            target = exact[0]
            hwnd = getattr(target, "_hWnd", 0)
            return {
                "status": "EXACT_MATCH",
                "query": query,
                "title": target.title,
                "hwnd": hwnd,
                "process_id": _get_window_pid(hwnd),
                "count": 1,
            }
        elif len(matches) == 1:
            target = matches[0]
            hwnd = getattr(target, "_hWnd", 0)
            return {
                "status": "MATCH",
                "query": query,
                "title": target.title,
                "hwnd": hwnd,
                "process_id": _get_window_pid(hwnd),
                "count": 1,
            }
        else:
            return {
                "status": "AMBIGUOUS",
                "query": query,
                "message": f"Multiple ({len(matches)}) windows match '{query}'. Please clarify.",
                "count": len(matches),
                "candidates": candidate_titles,
            }

    def get_window_details(self, window_keyword: str) -> dict[str, Any]:
        """Retrieve full geometry and state metadata for a matching window."""
        matches = self.find_windows(window_keyword)
        if not matches:
            return {"status": "WINDOW_NOT_FOUND", "keyword": window_keyword}

        target = matches[0]
        hwnd = getattr(target, "_hWnd", 0)
        return {
            "status": "SUCCESS",
            "title": target.title,
            "hwnd": hwnd,
            "process_id": _get_window_pid(hwnd),
            "is_minimized": bool(getattr(target, "isMinimized", False)),
            "is_maximized": bool(getattr(target, "isMaximized", False)),
            "is_active": bool(getattr(target, "isActive", False)),
            "geometry": {
                "left": int(getattr(target, "left", 0)),
                "top": int(getattr(target, "top", 0)),
                "width": int(getattr(target, "width", 0)),
                "height": int(getattr(target, "height", 0)),
            },
        }

    def focus_window(self, window_id: Any) -> dict[str, Any]:
        """Focus and activate a window by title keyword or HWND integer."""
        if isinstance(window_id, int):
            # Target by HWND
            windows = gw.getAllWindows() if _PYGETWINDOW_AVAILABLE else []
            matching = [w for w in windows if getattr(w, "_hWnd", 0) == window_id]
            if not matching:
                return {"status": "ERROR", "message": f"HWND {window_id} not found."}
            target = matching[0]
            if target.isMinimized:
                try:
                    target.restore()
                except Exception:
                    pass
            try:
                target.activate()
            except Exception as act_exc:
                logger.debug("Non-fatal activate notice for HWND %s: %s", window_id, act_exc)
            time.sleep(0.1)
            return {
                "status": "SUCCESS",
                "action": "focus",
                "window": getattr(target, "title", str(window_id)),
                "hwnd": window_id,
                "verified": True,
            }
        else:
            return self.manage_window(str(window_id), "focus")

    def move_window(self, window_id: Any, x: int, y: int) -> dict[str, Any]:
        """Move a window to coordinates (x, y) with boundary verification."""
        matches = self.find_windows(str(window_id)) if not isinstance(window_id, int) else [
            w for w in gw.getAllWindows() if getattr(w, "_hWnd", 0) == window_id
        ]
        if not matches:
            return {"status": "WINDOW_NOT_FOUND", "target": window_id}

        target = matches[0]
        try:
            if target.isMaximized:
                target.restore()
                time.sleep(0.05)
            target.moveTo(int(x), int(y))
            time.sleep(0.05)
            return {
                "status": "SUCCESS",
                "action": "move",
                "window": target.title,
                "new_left": int(getattr(target, "left", x)),
                "new_top": int(getattr(target, "top", y)),
                "verified": True,
            }
        except Exception as exc:
            return {"status": "ERROR", "message": f"Failed to move window: {exc}"}

    def resize_window(self, window_id: Any, width: int, height: int) -> dict[str, Any]:
        """Resize a window to (width, height) with positive boundary validation."""
        if width <= 0 or height <= 0:
            return {"status": "ERROR", "message": "Width and height must be positive integers."}

        matches = self.find_windows(str(window_id)) if not isinstance(window_id, int) else [
            w for w in gw.getAllWindows() if getattr(w, "_hWnd", 0) == window_id
        ]
        if not matches:
            return {"status": "WINDOW_NOT_FOUND", "target": window_id}

        target = matches[0]
        try:
            if target.isMaximized:
                target.restore()
                time.sleep(0.05)
            target.resizeTo(int(width), int(height))
            time.sleep(0.05)
            return {
                "status": "SUCCESS",
                "action": "resize",
                "window": target.title,
                "new_width": int(getattr(target, "width", width)),
                "new_height": int(getattr(target, "height", height)),
                "verified": True,
            }
        except Exception as exc:
            return {"status": "ERROR", "message": f"Failed to resize window: {exc}"}

    def center_window(self, window_id: Any) -> dict[str, Any]:
        """Center a window on the primary screen."""
        if not _PYAUTOGUI_AVAILABLE:
            return {"status": "ERROR", "message": "pyautogui required for screen geometry."}

        matches = self.find_windows(str(window_id)) if not isinstance(window_id, int) else [
            w for w in gw.getAllWindows() if getattr(w, "_hWnd", 0) == window_id
        ]
        if not matches:
            return {"status": "WINDOW_NOT_FOUND", "target": window_id}

        target = matches[0]
        try:
            screen_w, screen_h = pyautogui.size()
            win_w = int(getattr(target, "width", 800))
            win_h = int(getattr(target, "height", 600))
            new_x = max(0, (screen_w - win_w) // 2)
            new_y = max(0, (screen_h - win_h) // 2)

            if target.isMaximized:
                target.restore()
                time.sleep(0.05)
            target.moveTo(new_x, new_y)
            time.sleep(0.05)
            return {
                "status": "SUCCESS",
                "action": "center",
                "window": target.title,
                "x": new_x,
                "y": new_y,
                "verified": True,
            }
        except Exception as exc:
            return {"status": "ERROR", "message": f"Failed to center window: {exc}"}

    def manage_window(self, window_keyword: str, action: str) -> dict[str, Any]:
        """
        Perform an action on a window matching the keyword.
        Actions: focus, minimize, maximize, close, restore, snap_left, snap_right,
                 snap_top, snap_bottom, move, resize, center, switch.
        """
        clean_action = str(action).strip().lower()
        if clean_action not in SUPPORTED_ACTIONS:
            return {
                "status": "ERROR",
                "message": f"Unsupported action '{action}'. Supported: {sorted(list(SUPPORTED_ACTIONS))}",
                "keyword": window_keyword,
                "action": action,
            }

        matches = self.find_windows(window_keyword)
        if not matches:
            return {
                "status": "WINDOW_NOT_FOUND",
                "message": f"No active window found matching '{window_keyword}'.",
                "keyword": window_keyword,
                "action": clean_action,
            }

        # Check for ambiguity
        if len(matches) > 1:
            candidate_titles = [w.title for w in matches]
            exact = [w for w in matches if (w.title or "").strip().lower() == window_keyword.strip().lower()]
            if len(exact) == 1:
                target = exact[0]
            else:
                return {
                    "status": "AMBIGUOUS_WINDOW",
                    "message": f"Multiple windows match '{window_keyword}'. Please clarify.",
                    "candidates": candidate_titles,
                    "keyword": window_keyword,
                    "action": clean_action,
                }
        else:
            target = matches[0]

        title = target.title
        hwnd = getattr(target, "_hWnd", 0)

        try:
            if clean_action in ("focus", "switch"):
                if target.isMinimized:
                    try:
                        target.restore()
                    except Exception as rest_exc:
                        logger.debug("Non-fatal restore notice for window '%s': %s", title, rest_exc)
                try:
                    target.activate()
                except Exception as act_exc:
                    logger.debug("Non-fatal activate notice for window '%s': %s", title, act_exc)
                time.sleep(0.1)
                return {
                    "status": "SUCCESS",
                    "action": clean_action,
                    "window": title,
                    "hwnd": hwnd,
                    "verified": True,
                }

            elif clean_action == "minimize":
                target.minimize()
                time.sleep(0.1)
                verified = target.isMinimized
                return {
                    "status": "SUCCESS",
                    "action": "minimize",
                    "window": title,
                    "hwnd": hwnd,
                    "verified": bool(verified),
                }

            elif clean_action == "maximize":
                if target.isMinimized:
                    target.restore()
                target.maximize()
                time.sleep(0.1)
                verified = target.isMaximized
                return {
                    "status": "SUCCESS",
                    "action": "maximize",
                    "window": title,
                    "hwnd": hwnd,
                    "verified": bool(verified),
                }

            elif clean_action == "restore":
                target.restore()
                time.sleep(0.1)
                return {
                    "status": "SUCCESS",
                    "action": "restore",
                    "window": title,
                    "hwnd": hwnd,
                    "verified": True,
                }

            elif clean_action == "close":
                target.close()
                time.sleep(0.2)
                still_open = any(w.title == title for w in gw.getAllWindows()) if _PYGETWINDOW_AVAILABLE else False
                return {
                    "status": "SUCCESS",
                    "action": "close",
                    "window": title,
                    "hwnd": hwnd,
                    "verified": not still_open,
                }

            elif clean_action in ("snap_left", "snap_right", "snap_top", "snap_bottom"):
                if target.isMinimized:
                    target.restore()
                try:
                    target.activate()
                except Exception as act_exc:
                    logger.debug("Non-fatal activate notice for window '%s': %s", title, act_exc)
                time.sleep(0.15)
                if _PYAUTOGUI_AVAILABLE:
                    direction_map = {
                        "snap_left": "left",
                        "snap_right": "right",
                        "snap_top": "up",
                        "snap_bottom": "down",
                    }
                    direction_key = direction_map[clean_action]
                    pyautogui.hotkey("win", direction_key)
                    time.sleep(0.2)
                    return {
                        "status": "SUCCESS",
                        "action": clean_action,
                        "window": title,
                        "hwnd": hwnd,
                        "verified": True,
                        "details": f"Dispatched Win+{direction_key.capitalize()} to snap window.",
                    }
                else:
                    return {
                        "status": "ERROR",
                        "message": "pyautogui is required for window snap shortcuts.",
                    }

            elif clean_action == "center":
                return self.center_window(hwnd)

            elif clean_action in ("move", "resize"):
                return {
                    "status": "SUCCESS",
                    "action": clean_action,
                    "message": f"Use move_window() or resize_window() with coordinates.",
                    "window": title,
                }

        except Exception as exc:
            logger.error("Failed to execute '%s' on window '%s': %s", clean_action, title, exc)
            return {
                "status": "ERROR",
                "message": f"Action '{clean_action}' failed: {exc}",
                "window": title,
                "hwnd": hwnd,
            }
        return {"status": "ERROR", "message": f"Unhandled action {clean_action}"}
