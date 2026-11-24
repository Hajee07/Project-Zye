"""
Universal Text Input, Dictation & Hotkey Dispatcher — Zye Day 16 & Day 18.
Provides reliable Unicode/Tamil dictation via clipboard paste, safe hotkey dispatching,
named shortcut registry, intelligent wheel scrolling, and thread-safe input serialization.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Optional

try:
    import pyautogui
    _PYAUTOGUI_AVAILABLE = True
except ImportError:
    _PYAUTOGUI_AVAILABLE = False

try:
    import pyperclip
    _PYPERCLIP_AVAILABLE = True
except ImportError:
    _PYPERCLIP_AVAILABLE = False

from zye_windows.uia_interaction import WindowsUIAInteraction
from zye_windows.window_manager import WindowsWindowManager

logger = logging.getLogger("zye.windows.input_controller")

# Global re-entrant lock protecting keyboard and mouse automation from concurrent interference
INPUT_LOCK = threading.RLock()

# Allowed individual hotkey components for security hardening
ALLOWED_KEYS = {
    "ctrl", "alt", "shift", "win", "tab", "enter", "esc", "space", "backspace", "delete",
    "left", "right", "up", "down", "home", "end", "pageup", "pagedown",
    "f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10", "f11", "f12",
    "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m",
    "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z",
    "0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
}

# Day 18 Validated Named Shortcut Registry
NAMED_SHORTCUTS: dict[str, list[str]] = {
    "alt_tab": ["alt", "tab"],
    "win_tab": ["win", "tab"],
    "win_d": ["win", "d"],
    "win_e": ["win", "e"],
    "win_i": ["win", "i"],
    "win_left": ["win", "left"],
    "win_right": ["win", "right"],
    "win_up": ["win", "up"],
    "win_down": ["win", "down"],
    "ctrl_c": ["ctrl", "c"],
    "ctrl_v": ["ctrl", "v"],
    "ctrl_x": ["ctrl", "x"],
    "ctrl_a": ["ctrl", "a"],
    "ctrl_z": ["ctrl", "z"],
    "ctrl_y": ["ctrl", "y"],
    "ctrl_s": ["ctrl", "s"],
    "ctrl_f": ["ctrl", "f"],
    "ctrl_shift_esc": ["ctrl", "shift", "esc"],
    "alt_f4": ["alt", "f4"],
    "esc": ["esc"],
    "enter": ["enter"],
    "tab": ["tab"],
}

MAX_DICTATION_CHARS = 20000


def normalize_shortcut_name(name: str) -> str:
    """Normalize shortcut strings like 'Ctrl + C' or 'Alt Tab' to 'ctrl_c' or 'alt_tab'."""
    s = str(name).strip().lower()
    s = s.replace("+", "_").replace("-", "_").replace(" ", "_")
    while "__" in s:
        s = s.replace("__", "_")
    return s


class WindowsInputController:
    """
    Handles typing, universal dictation, named shortcuts, and intelligent scrolling.
    """

    def __init__(
        self,
        window_mgr: Optional[WindowsWindowManager] = None,
        uia_interaction: Optional[WindowsUIAInteraction] = None,
    ) -> None:
        self.window_mgr = window_mgr or WindowsWindowManager()
        self.uia = uia_interaction or WindowsUIAInteraction()
        if _PYAUTOGUI_AVAILABLE:
            pyautogui.FAILSAFE = False

    def type_into_app(
        self,
        window_keyword: str,
        element_name: str,
        text: str,
        press_enter: bool = False,
    ) -> dict[str, Any]:
        """
        Focus target control in named application and type text using clipboard paste.
        """
        if not text:
            return {
                "status": "ERROR",
                "message": "Text to type cannot be empty.",
                "window": window_keyword,
                "element": element_name,
            }

        with INPUT_LOCK:
            # 1. Focus application window
            focus_res = self.window_mgr.manage_window(window_keyword, "focus")
            if focus_res.get("status") in ("WINDOW_NOT_FOUND", "AMBIGUOUS_WINDOW"):
                return focus_res

            # 2. Click target control if element_name is specified
            if element_name:
                click_res = self.uia.click_ui_element(window_keyword, element_name, control_type="Edit")
                if click_res.get("status") != "SUCCESS":
                    click_res = self.uia.click_ui_element(window_keyword, element_name)
                    if click_res.get("status") not in ("SUCCESS", "ALREADY_ACTIVE"):
                        logger.warning("Could not explicitly focus control '%s': %s", element_name, click_res)

            time.sleep(0.1)

            # 3. Paste text safely
            paste_res = self._paste_text(text, press_enter=press_enter)
            return {
                "status": "SUCCESS" if paste_res else "ERROR",
                "action": "type_into_app",
                "window": window_keyword,
                "element": element_name,
                "char_count": len(text),
                "press_enter": press_enter,
                "verified": paste_res,
            }

    def dictate_text_anywhere(
        self,
        text: str,
        press_enter: bool = False,
    ) -> dict[str, Any]:
        """
        Paste text into whichever input control currently has Windows focus.
        Supports Tamil Unicode, Tanglish, emojis, code, and multiline text.
        """
        if not text:
            return {
                "status": "ERROR",
                "message": "Dictation text cannot be empty.",
            }

        if len(text) > MAX_DICTATION_CHARS:
            return {
                "status": "ERROR",
                "message": f"Text exceeds maximum dictation length of {MAX_DICTATION_CHARS} characters.",
                "char_count": len(text),
            }

        with INPUT_LOCK:
            ok = self._paste_text(text, press_enter=press_enter)
            active_win = self.window_mgr.get_active_window()
            return {
                "status": "SUCCESS" if ok else "ERROR",
                "action": "dictate_text_anywhere",
                "char_count": len(text),
                "press_enter": press_enter,
                "active_window": active_win.title if active_win else "Unknown",
                "verified": ok,
            }

    def type_text(self, text: str) -> dict[str, Any]:
        """Direct text insertion into current focus (alias for dictate_text_anywhere)."""
        return self.dictate_text_anywhere(text=text, press_enter=False)

    def press_key(self, key: str) -> dict[str, Any]:
        """Press a single validated keyboard key (e.g. 'enter', 'esc', 'tab')."""
        if not _PYAUTOGUI_AVAILABLE:
            return {"status": "ERROR", "message": "pyautogui is required."}

        clean_key = str(key).strip().lower()
        if clean_key not in ALLOWED_KEYS:
            return {"status": "REJECTED", "message": f"Key '{key}' is not allowed.", "key": key}

        with INPUT_LOCK:
            try:
                pyautogui.press(clean_key)
                return {"status": "SUCCESS", "action": "press_key", "key": clean_key, "verified": True}
            except Exception as exc:
                return {"status": "ERROR", "message": f"Failed to press key: {exc}"}

    def press_hotkey(self, keys: list[str]) -> dict[str, Any]:
        """
        Execute an authorized keyboard shortcut combination safely.
        """
        if not _PYAUTOGUI_AVAILABLE:
            return {
                "status": "ERROR",
                "message": "pyautogui is not available for hotkey dispatch.",
            }

        if not keys or not isinstance(keys, list):
            return {
                "status": "ERROR",
                "message": "keys must be a non-empty list of key strings (e.g. ['ctrl', 'v']).",
            }

        clean_keys = [str(k).strip().lower() for k in keys]

        # Enforce maximum combination length
        if len(clean_keys) > 4:
            return {
                "status": "REJECTED",
                "message": "Hotkey combinations with more than 4 keys are rejected for security.",
                "keys": keys,
            }

        # Validate all keys
        for k in clean_keys:
            if k not in ALLOWED_KEYS:
                return {
                    "status": "REJECTED",
                    "message": f"Rejected unrecognized or unauthorized key '{k}'.",
                    "keys": keys,
                }

        with INPUT_LOCK:
            try:
                pyautogui.hotkey(*clean_keys)
                time.sleep(0.1)
                return {
                    "status": "SUCCESS",
                    "action": "press_hotkey",
                    "keys": clean_keys,
                    "verified": True,
                }
            except Exception as exc:
                logger.error("Hotkey execution error for %s: %s", clean_keys, exc)
                return {
                    "status": "ERROR",
                    "message": f"Hotkey execution failed: {exc}",
                    "keys": clean_keys,
                }

    def execute_shortcut(self, shortcut_name: str) -> dict[str, Any]:
        """
        Execute a validated shortcut from the named shortcut registry.
        Examples: 'alt_tab', 'win_d', 'ctrl_c', 'ctrl_v', 'ctrl_s', 'Alt + Tab'.
        """
        norm = normalize_shortcut_name(shortcut_name)
        if norm not in NAMED_SHORTCUTS:
            return {
                "status": "REJECTED",
                "message": f"Shortcut '{shortcut_name}' not in validated registry. Available: {sorted(list(NAMED_SHORTCUTS.keys()))}",
                "shortcut": shortcut_name,
            }

        keys = NAMED_SHORTCUTS[norm]
        res = self.press_hotkey(keys)
        if res.get("status") == "SUCCESS":
            res["shortcut_name"] = norm
        return res

    def scroll_page(self, direction: str = "down", amount: int = 5, unit: str = "steps") -> dict[str, Any]:
        """
        Intelligent hands-free scrolling.
        Supported directions: 'up', 'down', 'left', 'right'.
        Amount: 1..50 wheel steps (bounded for safety).
        """
        if not _PYAUTOGUI_AVAILABLE:
            return {"status": "ERROR", "message": "pyautogui is required for scrolling."}

        clean_dir = str(direction).strip().lower()
        if clean_dir not in ("up", "down", "left", "right"):
            return {
                "status": "ERROR",
                "message": f"Invalid scroll direction '{direction}'. Supported: 'up', 'down', 'left', 'right'.",
            }

        # Clamp magnitude to 1..50
        try:
            amt = int(amount)
        except ValueError:
            return {"status": "ERROR", "message": "Scroll amount must be an integer."}

        amt = max(1, min(amt, 50))
        wheel_clicks = amt * 100

        with INPUT_LOCK:
            try:
                if clean_dir == "up":
                    pyautogui.scroll(wheel_clicks)
                elif clean_dir == "down":
                    pyautogui.scroll(-wheel_clicks)
                elif clean_dir in ("left", "right"):
                    # Horizontal scrolling via hscroll or Shift+scroll fallback
                    if hasattr(pyautogui, "hscroll"):
                        h_clicks = -wheel_clicks if clean_dir == "left" else wheel_clicks
                        pyautogui.hscroll(h_clicks)
                    else:
                        with pyautogui.hold("shift"):
                            pyautogui.scroll(-wheel_clicks if clean_dir == "right" else wheel_clicks)

                time.sleep(0.05)
                active_win = self.window_mgr.get_active_window()
                return {
                    "status": "SUCCESS",
                    "action": "scroll_page",
                    "direction": clean_dir,
                    "steps": amt,
                    "unit": unit,
                    "active_window": active_win.title if active_win else "Unknown",
                    "verified": True,
                }
            except Exception as exc:
                logger.error("Scroll error: %s", exc)
                return {"status": "ERROR", "message": f"Scroll failed: {exc}"}

    def _paste_text(self, text: str, press_enter: bool = False) -> bool:
        """
        Internal clipboard-based text insertion with previous clipboard preservation.
        Uses native Windows user32 keybd_event to avoid mouse-corner FailSafeException.
        """
        if not _PYPERCLIP_AVAILABLE:
            logger.error("pyperclip is not available.")
            return False

        old_clipboard = ""
        try:
            old_clipboard = pyperclip.paste()
        except Exception:
            pass

        try:
            pyperclip.copy(text)
            time.sleep(0.08)

            # Send Ctrl+V using native Win32 keybd_event with PyAutoGUI fallback
            import sys
            if sys.platform == "win32":
                import ctypes
                VK_CONTROL = 0x11
                VK_V = 0x56
                KEYEVENTF_KEYUP = 0x0002
                ctypes.windll.user32.keybd_event(VK_CONTROL, 0, 0, 0)
                ctypes.windll.user32.keybd_event(VK_V, 0, 0, 0)
                time.sleep(0.05)
                ctypes.windll.user32.keybd_event(VK_V, 0, KEYEVENTF_KEYUP, 0)
                ctypes.windll.user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
            elif _PYAUTOGUI_AVAILABLE:
                pyautogui.hotkey("ctrl", "v")
            time.sleep(0.2)

            if press_enter:
                if sys.platform == "win32":
                    import ctypes
                    VK_RETURN = 0x0D
                    ctypes.windll.user32.keybd_event(VK_RETURN, 0, 0, 0)
                    time.sleep(0.05)
                    ctypes.windll.user32.keybd_event(VK_RETURN, 0, 2, 0)
                elif _PYAUTOGUI_AVAILABLE:
                    pyautogui.press("enter")
                time.sleep(0.1)

            return True
        except Exception as exc:
            logger.error("Error during clipboard text paste: %s", exc)
            return False
        finally:
            if old_clipboard:
                time.sleep(0.1)
                try:
                    pyperclip.copy(old_clipboard)
                except Exception:
                    pass
