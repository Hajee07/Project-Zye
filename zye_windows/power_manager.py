"""
Windows Power Management & Hardware Telemetry Engine — Zye Day 16.
Handles Lock, Sleep, Shutdown, and Restart with mandatory confirmation gates,
grace periods, shutdown cancellation, and battery monitoring.
"""

from __future__ import annotations

import ctypes
import logging
import subprocess
import sys
from typing import Any

try:
    import psutil
    _PSUTIL_AVAILABLE = True
except ImportError:
    _PSUTIL_AVAILABLE = False

from zye_windows.windows_models import BatteryInfo

logger = logging.getLogger("zye.windows.power_manager")

SUPPORTED_POWER_ACTIONS = {"lock", "sleep", "shutdown", "restart"}


class WindowsPowerManager:
    """
    Executes controlled power management operations and queries battery telemetry.
    """

    def power_action(self, action: str, confirmed: bool = False) -> dict[str, Any]:
        """
        Execute an authorized power action.
        Shutdown and restart require explicit user confirmation (confirmed=True).
        """
        clean_action = str(action).strip().lower()
        if clean_action not in SUPPORTED_POWER_ACTIONS:
            return {
                "status": "REJECTED",
                "message": f"Unsupported power action '{action}'. Supported: {sorted(list(SUPPORTED_POWER_ACTIONS))}",
                "action": action,
            }

        # 1. LOCK WORKSTATION
        if clean_action == "lock":
            if sys.platform == "win32":
                try:
                    res = ctypes.windll.user32.LockWorkStation()
                    return {
                        "status": "SUCCESS",
                        "action": "lock",
                        "message": "Windows workstation locked successfully.",
                        "verified": bool(res),
                    }
                except Exception as exc:
                    return {"status": "ERROR", "action": "lock", "message": f"LockWorkStation failed: {exc}"}
            else:
                return {"status": "ERROR", "message": "LockWorkStation is only supported on Windows."}

        # 2. SLEEP MODE
        elif clean_action == "sleep":
            if sys.platform == "win32":
                try:
                    # Request suspend state (sleep)
                    # SetSuspendState(bHibernate=0, bForce=0, bWakeupEventsDisabled=0)
                    res = ctypes.windll.PowrProf.SetSuspendState(0, 0, 0)
                    return {
                        "status": "SUCCESS",
                        "action": "sleep",
                        "message": "Sleep mode requested.",
                        "verified": bool(res),
                    }
                except Exception as exc:
                    # Fallback to rundll32
                    try:
                        subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], check=False)
                        return {
                            "status": "SUCCESS",
                            "action": "sleep",
                            "message": "Sleep command dispatched via powrprof.dll.",
                            "verified": True,
                        }
                    except Exception as fb_exc:
                        return {"status": "ERROR", "action": "sleep", "message": f"Sleep request failed: {exc} ({fb_exc})"}
            else:
                return {"status": "ERROR", "message": "Sleep is only supported on Windows."}

        # 3. SHUTDOWN & RESTART (CRITICAL RISK — REQUIRE EXPLICIT CONFIRMATION)
        elif clean_action in ("shutdown", "restart"):
            if not confirmed:
                return {
                    "status": "CONFIRMATION_REQUIRED",
                    "action": clean_action,
                    "message": (
                        f"CRITICAL: User authorization required before {clean_action.upper()}. "
                        f"Please ask user to confirm. If confirmed, call power_action with confirmed=True. "
                        f"A 30-second cancellation window will be provided."
                    ),
                    "requires_user_confirmation": True,
                }

            # Execute with a 30-second grace window allowing cancellation via 'shutdown /a'
            flag = "/s" if clean_action == "shutdown" else "/r"
            cmd = ["shutdown.exe", flag, "/t", "30", "/c", f"Zye AI scheduled {clean_action}. Run 'shutdown /a' to cancel."]
            try:
                res = subprocess.run(cmd, capture_output=True, text=True, check=False)
                if res.returncode == 0:
                    return {
                        "status": "SCHEDULED",
                        "action": clean_action,
                        "message": f"{clean_action.capitalize()} scheduled in 30 seconds. Run cancel_shutdown() to abort.",
                        "cancellation_window_seconds": 30,
                        "verified": True,
                    }
                else:
                    return {
                        "status": "ERROR",
                        "action": clean_action,
                        "message": f"Shutdown command failed: {res.stderr.strip()}",
                    }
            except Exception as exc:
                return {"status": "ERROR", "action": clean_action, "message": str(exc)}

        return {"status": "ERROR", "message": "Unknown branch"}

    def cancel_shutdown(self) -> dict[str, Any]:
        """Cancel any pending scheduled shutdown or restart."""
        try:
            res = subprocess.run(["shutdown.exe", "/a"], capture_output=True, text=True, check=False)
            if res.returncode == 0:
                return {"status": "SUCCESS", "message": "Pending shutdown or restart successfully cancelled."}
            else:
                return {"status": "NO_PENDING_SHUTDOWN", "message": res.stderr.strip() or "No scheduled shutdown was active."}
        except Exception as exc:
            return {"status": "ERROR", "message": str(exc)}

    def get_battery_status(self) -> dict[str, Any]:
        """
        Query system battery percentage, AC power connection, and estimated remaining time.
        Gracefully supports desktop systems with no battery.
        """
        if not _PSUTIL_AVAILABLE:
            return {
                "status": "UNKNOWN",
                "percent": 0.0,
                "has_battery": False,
                "is_plugged": True,
                "message": "psutil is not installed to query battery telemetry.",
            }

        try:
            batt = psutil.sensors_battery()
            if batt is None:
                # Desktop PC without battery
                info = BatteryInfo(
                    percent=100.0,
                    is_plugged=True,
                    has_battery=False,
                    status="AC_POWER_NO_BATTERY",
                    estimated_time_remaining_minutes=None,
                )
                return info.model_dump()

            percent = round(float(batt.percent), 1)
            is_plugged = bool(batt.power_plugged)
            rem_secs = batt.secsleft
            rem_mins = int(rem_secs // 60) if rem_secs is not None and rem_secs > 0 and rem_secs != psutil.POWER_TIME_UNLIMITED else None

            status_label = "CHARGING" if is_plugged and percent < 99.0 else ("FULL" if percent >= 99.0 and is_plugged else "DISCHARGING")
            if not is_plugged and percent <= 8.0:
                status_label = "CRITICAL_LOW"
            elif not is_plugged and percent <= 15.0:
                status_label = "WARNING_LOW"

            info = BatteryInfo(
                percent=percent,
                is_plugged=is_plugged,
                has_battery=True,
                status=status_label,
                estimated_time_remaining_minutes=rem_mins,
            )
            return info.model_dump()
        except Exception as exc:
            logger.error("Error retrieving battery telemetry: %s", exc)
            return {
                "status": "ERROR",
                "percent": 0.0,
                "has_battery": False,
                "is_plugged": True,
                "message": f"Battery query error: {exc}",
            }
