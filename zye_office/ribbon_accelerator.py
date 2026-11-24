"""
Zye Office Ribbon Accelerator
Executes verified Ribbon and menu accelerator keystrokes with active foreground window verification.
Prevents sending keystrokes to non-Office windows.
"""

from typing import Dict, Any, List, Optional
import time
import sys
import psutil

try:
    import win32gui
    import win32process
    import win32con
except ImportError:
    win32gui = None
    win32process = None
    win32con = None

try:
    import pyautogui
    pyautogui.FAILSAFE = True
except ImportError:
    pyautogui = None

from zye_office.models import OfficeAppType
from zye_office.errors import OfficeSecurityError, OfficeValidationError


class OfficeRibbonAccelerator:
    """
    Safely executes Ribbon hotkeys and keytip sequences against verified
    Office foreground windows.
    """

    APP_PROCESS_MAP = {
        OfficeAppType.WORD: "WINWORD.EXE",
        OfficeAppType.EXCEL: "EXCEL.EXE",
        OfficeAppType.POWERPOINT: "POWERPNT.EXE",
        OfficeAppType.OUTLOOK: "OUTLOOK.EXE",
    }

    APP_WINDOW_CLASSES = {
        OfficeAppType.WORD: ["OpusApp"],
        OfficeAppType.EXCEL: ["XLMAIN"],
        OfficeAppType.POWERPOINT: ["PPTFrameClass", "screenClass"],
        OfficeAppType.OUTLOOK: ["rctrl_renwnd32"],
    }

    ACTION_HOTKEYS = {
        "save": ["ctrl", "s"],
        "bold": ["ctrl", "b"],
        "italic": ["ctrl", "i"],
        "underline": ["ctrl", "u"],
        "undo": ["ctrl", "z"],
        "redo": ["ctrl", "y"],
        "find": ["ctrl", "f"],
        "print": ["ctrl", "p"],
        "new_item": ["ctrl", "n"],
        "new_slide": ["ctrl", "m"],
        "home_tab": ["alt", "h"],
        "insert_tab": ["alt", "n"],
        "layout_tab": ["alt", "p"],
        "formulas_tab": ["alt", "m"],
        "data_tab": ["alt", "a"],
        "review_tab": ["alt", "r"],
        "view_tab": ["alt", "w"],
    }

    DANGEROUS_KEYS = {"alt+f4", "ctrl+alt+del", "win", "windows", "delete", "backspace"}

    def __init__(self):
        pass

    def get_foreground_process(self) -> tuple[Optional[int], Optional[str], Optional[str]]:
        """
        Returns (hwnd, process_name, window_title) of current foreground window.
        """
        if not win32gui or not win32process:
            return None, None, None

        try:
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return None, None, None
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            title = win32gui.GetWindowText(hwnd)
            proc = psutil.Process(pid)
            return hwnd, proc.name().upper(), title
        except Exception as e:
            sys.stderr.write(f"[RibbonAccelerator] Error getting foreground process: {e}\n")
            return None, None, None

    def verify_foreground_app(self, app_type: OfficeAppType) -> bool:
        """
        Verifies that the target application is currently in the foreground.
        """
        expected_binary = self.APP_PROCESS_MAP.get(app_type)
        if not expected_binary:
            return False

        _, current_proc, _ = self.get_foreground_process()
        if not current_proc:
            return False

        return current_proc.upper() == expected_binary.upper()

    def focus_app_window(self, app_type: OfficeAppType) -> bool:
        """
        Attempts to find and activate a window belonging to the target Office application.
        """
        if not win32gui or not win32process:
            return False

        expected_binary = self.APP_PROCESS_MAP.get(app_type)
        if not expected_binary:
            return False

        target_hwnd = None

        def enum_cb(hwnd, _):
            nonlocal target_hwnd
            if not win32gui.IsWindowVisible(hwnd):
                return True
            try:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                proc = psutil.Process(pid)
                if proc.name().upper() == expected_binary.upper():
                    target_hwnd = hwnd
                    return False
            except Exception:
                pass
            return True

        try:
            win32gui.EnumWindows(enum_cb, None)
        except Exception:
            pass

        if target_hwnd:
            try:
                # SW_RESTORE = 9
                win32gui.ShowWindow(target_hwnd, 9)
                win32gui.SetForegroundWindow(target_hwnd)
                time.sleep(0.15)
                return self.verify_foreground_app(app_type)
            except Exception as e:
                sys.stderr.write(f"[RibbonAccelerator] Error focusing window {target_hwnd}: {e}\n")
                return False

        return False

    def execute_accelerator(
        self,
        app_type: OfficeAppType,
        action_or_keys: str,
        auto_focus: bool = True,
    ) -> Dict[str, Any]:
        """
        Executes a ribbon shortcut or key sequence after verifying foreground focus.
        """
        if not pyautogui:
            raise OfficeValidationError("pyautogui is required for Ribbon accelerator execution")

        key_clean = action_or_keys.strip().lower()

        # Check dangerous keys
        if key_clean in self.DANGEROUS_KEYS or any(dk in key_clean for dk in ("f4", "del", "win")):
            raise OfficeSecurityError(f"Shortcut '{action_or_keys}' is blocked by security policy")

        # Resolve sequence
        if key_clean in self.ACTION_HOTKEYS:
            keys = self.ACTION_HOTKEYS[key_clean]
        else:
            # Parse custom sequence e.g. "ctrl+s" or "alt+h"
            keys = [k.strip() for k in key_clean.split("+") if k.strip()]

        if not keys:
            raise OfficeValidationError("Empty key sequence provided")

        # Foreground check
        is_focused = self.verify_foreground_app(app_type)
        if not is_focused:
            if auto_focus:
                focused = self.focus_app_window(app_type)
                if not focused:
                    raise OfficeSecurityError(
                        f"Cannot execute accelerator '{action_or_keys}': "
                        f"{app_type.value} is not the foreground window and could not be focused."
                    )
            else:
                raise OfficeSecurityError(
                    f"Cannot execute accelerator '{action_or_keys}': "
                    f"{app_type.value} is not the foreground active window."
                )

        # Dispatch keystrokes
        try:
            if len(keys) == 1:
                pyautogui.press(keys[0])
            else:
                pyautogui.hotkey(*keys)
            
            return {
                "success": True,
                "app": app_type.value,
                "action": action_or_keys,
                "keys": keys,
                "timestamp": time.time(),
            }
        except Exception as e:
            raise OfficeSecurityError(f"Failed to send keystrokes: {e}") from e
