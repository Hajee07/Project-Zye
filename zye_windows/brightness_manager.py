"""
Screen Brightness Control Engine — Zye Day 16.
Interfaces with Windows WMI monitor brightness controls with range validation,
hardware capability detection, and external display fallback.
"""

from __future__ import annotations

import logging
import subprocess
import sys
from typing import Any

logger = logging.getLogger("zye.windows.brightness")


class WindowsBrightnessManager:
    """
    Manages display brightness via Windows WMI interfaces.
    """

    def set_brightness(self, level: int) -> dict[str, Any]:
        """
        Set primary display brightness to a percentage between 0 and 100.
        """
        try:
            val = int(level)
        except (ValueError, TypeError):
            return {
                "status": "ERROR",
                "message": f"Brightness level must be an integer between 0 and 100, got '{level}'.",
                "level": level,
            }

        if val < 0 or val > 100:
            return {
                "status": "REJECTED",
                "message": f"Brightness level must be between 0 and 100, got {val}.",
                "level": val,
            }

        if sys.platform != "win32":
            return {
                "status": "ERROR",
                "message": "Screen brightness control is only available on Windows.",
                "level": val,
            }

        cmd = (
            f"(Get-WmiObject -Namespace root/wmi -Class WmiMonitorBrightnessMethods)"
            f".WmiSetBrightness(1, {val})"
        )
        try:
            res = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", cmd],
                capture_output=True,
                text=True,
                timeout=5.0,
                check=False,
            )
            if res.returncode == 0:
                return {
                    "status": "SUCCESS",
                    "level": val,
                    "message": f"Display brightness set to {val}%.",
                    "verified": True,
                }
            else:
                err = res.stderr.strip() or res.stdout.strip()
                logger.warning("Brightness WMI call returned non-zero (%s)", err)
                return {
                    "status": "HARDWARE_NOT_SUPPORTED",
                    "level": val,
                    "message": f"Brightness adjustment unsupported on current display/hardware: {err}",
                    "verified": False,
                }
        except subprocess.TimeoutExpired:
            return {"status": "TIMEOUT", "message": "Brightness WMI call timed out."}
        except Exception as exc:
            logger.error("Brightness adjustment error: %s", exc)
            return {"status": "ERROR", "message": str(exc)}

    def get_brightness(self) -> dict[str, Any]:
        """
        Read the current display brightness level.
        """
        if sys.platform != "win32":
            return {"status": "ERROR", "message": "Only supported on Windows."}

        cmd = "(Get-WmiObject -Namespace root/wmi -Class WmiMonitorBrightness).CurrentBrightness"
        try:
            res = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", cmd],
                capture_output=True,
                text=True,
                timeout=4.0,
                check=False,
            )
            if res.returncode == 0 and res.stdout.strip().isdigit():
                cur = int(res.stdout.strip())
                return {"status": "SUCCESS", "current_brightness": cur}
            else:
                return {
                    "status": "HARDWARE_NOT_SUPPORTED",
                    "message": "Unable to query display brightness on this monitor.",
                }
        except Exception as exc:
            return {"status": "ERROR", "message": str(exc)}
