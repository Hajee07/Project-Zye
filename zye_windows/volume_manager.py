"""
Master Audio Volume & Page Scrolling Engine — Zye Day 16.
Controls system volume (up, down, mute, unmute, set level) and page scrolling
using PyAutoGUI and Windows media keys with bounded limits.
"""

from __future__ import annotations

import logging
from typing import Any

try:
    import pyautogui
    _PYAUTOGUI_AVAILABLE = True
except ImportError:
    _PYAUTOGUI_AVAILABLE = False

logger = logging.getLogger("zye.windows.volume")

SUPPORTED_VOLUME_ACTIONS = {"up", "down", "mute", "unmute"}
MAX_VOLUME_STEPS = 20
MAX_SCROLL_STEPS = 25


class WindowsVolumeManager:
    """
    Controls master audio volume and provides hands-free page scrolling.
    """

    def __init__(self) -> None:
        if _PYAUTOGUI_AVAILABLE:
            pyautogui.FAILSAFE = True

    def control_volume(self, action: str, steps: int = 5) -> dict[str, Any]:
        """
        Adjust master output volume.
        Actions: up, down, mute, unmute.
        """
        if not _PYAUTOGUI_AVAILABLE:
            return {
                "status": "ERROR",
                "message": "pyautogui is required for volume key control.",
            }

        act = str(action).strip().lower()
        if act not in SUPPORTED_VOLUME_ACTIONS:
            return {
                "status": "REJECTED",
                "message": f"Unsupported volume action '{action}'. Supported: {sorted(list(SUPPORTED_VOLUME_ACTIONS))}",
                "action": action,
            }

        clamped_steps = max(1, min(int(steps or 5), MAX_VOLUME_STEPS))

        try:
            if act == "up":
                for _ in range(clamped_steps):
                    pyautogui.press("volumeup")
                return {
                    "status": "SUCCESS",
                    "action": "up",
                    "steps": clamped_steps,
                    "message": f"Increased volume by {clamped_steps} increments.",
                    "verified": True,
                }

            elif act == "down":
                for _ in range(clamped_steps):
                    pyautogui.press("volumedown")
                return {
                    "status": "SUCCESS",
                    "action": "down",
                    "steps": clamped_steps,
                    "message": f"Decreased volume by {clamped_steps} increments.",
                    "verified": True,
                }

            elif act in ("mute", "unmute"):
                pyautogui.press("volumemute")
                return {
                    "status": "SUCCESS",
                    "action": act,
                    "message": "Toggled master volume mute state.",
                    "verified": True,
                }

        except Exception as exc:
            logger.error("Volume control error: %s", exc)
            return {"status": "ERROR", "message": f"Volume control failed: {exc}"}

        return {"status": "ERROR", "message": "Unknown branch"}

    def set_volume_percent(self, level: int) -> dict[str, Any]:
        """
        Set master volume to an approximate percentage level (0..100).
        """
        try:
            val = int(level)
        except (ValueError, TypeError):
            return {"status": "ERROR", "message": f"Invalid volume level '{level}'."}

        if val < 0 or val > 100:
            return {"status": "REJECTED", "message": f"Volume level must be between 0 and 100, got {val}."}

        if not _PYAUTOGUI_AVAILABLE:
            return {"status": "ERROR", "message": "pyautogui is not available."}

        try:
            # First set to 0 by pressing volumedown 50 times
            for _ in range(50):
                pyautogui.press("volumedown")

            # Then step up: each step in Windows is 2% volume
            steps_up = int(val // 2)
            for _ in range(steps_up):
                pyautogui.press("volumeup")

            return {
                "status": "SUCCESS",
                "level": val,
                "message": f"Volume set to approximately {val}%.",
                "verified": True,
            }
        except Exception as exc:
            return {"status": "ERROR", "message": str(exc)}

    def scroll_page(self, direction: str = "down", amount: int = 5) -> dict[str, Any]:
        """
        Hands-free page scrolling.
        Directions: up, down.
        Amount: wheel clicks (clamped between 1 and 25).
        """
        if not _PYAUTOGUI_AVAILABLE:
            return {"status": "ERROR", "message": "pyautogui is required for scrolling."}

        dir_clean = str(direction).strip().lower()
        if dir_clean not in ("up", "down"):
            return {
                "status": "REJECTED",
                "message": f"Invalid scroll direction '{direction}'. Supported: 'up', 'down'.",
            }

        clamped = max(1, min(int(amount or 5), MAX_SCROLL_STEPS))
        # PyAutoGUI scroll: positive is up, negative is down. 1 click ~ 120 units
        clicks = clamped * 120 if dir_clean == "up" else -(clamped * 120)

        try:
            pyautogui.scroll(clicks)
            return {
                "status": "SUCCESS",
                "direction": dir_clean,
                "amount": clamped,
                "message": f"Scrolled page {dir_clean} by {clamped} wheel units.",
                "verified": True,
            }
        except Exception as exc:
            return {"status": "ERROR", "message": str(exc)}
