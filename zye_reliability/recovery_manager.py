"""
Zye AI — Application Crash Detection & Recovery Engine (Day 17).
Monitors external application health, detects hung/crashed processes, coordinates graceful
or forced recovery workflows, and tracks crash loops with circuit breaking.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

try:
    import psutil
    _PSUTIL_AVAILABLE = True
except ImportError:
    _PSUTIL_AVAILABLE = False

from zye_reliability.error_handler import redact_error_details

logger = logging.getLogger("zye.reliability.recovery_manager")


class ApplicationRecoveryManager:
    """Manages crash detection, hanging process recovery, and crash-loop circuit breaking."""

    def __init__(self) -> None:
        self._crash_history: list[dict[str, Any]] = []

    def detect_crash(self, pid: int, app_name: str = "") -> bool:
        """
        Check if a process has terminated unexpectedly or turned into a zombie.
        Returns True if the process is detected as crashed or missing.
        """
        if not _PSUTIL_AVAILABLE:
            return False

        try:
            p = psutil.Process(pid)
            if app_name and app_name.lower() not in p.name().lower():
                # Process ID has been recycled or does not match target app
                return True
            status = p.status()
            if status in (psutil.STATUS_ZOMBIE, psutil.STATUS_DEAD):
                return True
            return False
        except (psutil.NoSuchProcess, psutil.ZombieProcess):
            return True
        except psutil.AccessDenied:
            # Process exists but we lack query rights; assume running
            return False
        except Exception as exc:
            logger.debug("Error checking process crash state: %s", exc)
            return False

    def recover_hung_application(
        self,
        pid: int,
        timeout: float = 5.0,
        force: bool = False,
    ) -> dict[str, Any]:
        """
        Attempt to recover a frozen or unresponsive application process.
        First sends SIGTERM / graceful termination request. If still active after
        timeout and force=True, forces process kill.
        """
        if not _PSUTIL_AVAILABLE:
            return {
                "status": "ERROR",
                "message": "psutil package is unavailable on host.",
                "recovered": False,
            }

        try:
            p = psutil.Process(pid)
            app_name = p.name()
        except psutil.NoSuchProcess:
            return {
                "status": "PROCESS_NOT_FOUND",
                "message": f"Process {pid} is no longer running.",
                "recovered": True,
            }
        except psutil.AccessDenied:
            return {
                "status": "ACCESS_DENIED",
                "message": f"Access denied to process {pid}.",
                "recovered": False,
            }

        try:
            # Attempt 1: Graceful termination
            p.terminate()
            gone, alive = psutil.wait_procs([p], timeout=timeout)
            if not alive:
                self.record_crash(app_name, pid, "Recovered via graceful termination")
                return {
                    "status": "RECOVERED_GRACEFUL",
                    "app_name": app_name,
                    "pid": pid,
                    "recovered": True,
                    "message": f"Application '{app_name}' (PID {pid}) terminated gracefully.",
                }

            # Attempt 2: Forced termination if confirmed
            if force:
                p.kill()
                gone, alive = psutil.wait_procs([p], timeout=timeout)
                if not alive:
                    self.record_crash(app_name, pid, "Recovered via forced kill")
                    return {
                        "status": "RECOVERED_FORCED",
                        "app_name": app_name,
                        "pid": pid,
                        "recovered": True,
                        "message": f"Application '{app_name}' (PID {pid}) killed forcefully.",
                    }

            return {
                "status": "STILL_RUNNING",
                "app_name": app_name,
                "pid": pid,
                "recovered": False,
                "message": f"Application '{app_name}' (PID {pid}) did not exit within timeout.",
            }

        except psutil.AccessDenied:
            return {
                "status": "ACCESS_DENIED",
                "app_name": app_name,
                "pid": pid,
                "recovered": False,
                "message": f"Insufficient permissions to terminate PID {pid}.",
            }
        except Exception as exc:
            return {
                "status": "ERROR",
                "app_name": app_name,
                "pid": pid,
                "recovered": False,
                "message": redact_error_details(str(exc)),
            }

    def record_crash(self, app_name: str, pid: int, reason: str = "") -> None:
        """Record crash event for loop detection."""
        entry = {
            "app_name": app_name.lower(),
            "pid": pid,
            "reason": redact_error_details(reason),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._crash_history.append(entry)
        if len(self._crash_history) > 100:
            self._crash_history = self._crash_history[-100:]

    def get_crash_history(self, app_name: str = "") -> list[dict[str, Any]]:
        """Retrieve recent crash events, optionally filtered by application."""
        if not app_name:
            return list(self._crash_history)
        norm = app_name.lower().strip()
        return [c for c in self._crash_history if norm in c.get("app_name", "")]

    def should_circuit_break(
        self,
        app_name: str,
        threshold: int = 3,
        window_minutes: int = 10,
    ) -> bool:
        """
        Check if an application has crashed too frequently in a short duration.
        Prevents endless rapid launch-crash restart loops.
        """
        if not app_name:
            return False
        norm = app_name.lower().strip()
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)

        recent_crashes = 0
        for entry in self._crash_history:
            if norm in entry.get("app_name", ""):
                try:
                    ts = datetime.fromisoformat(entry["timestamp"])
                    if ts >= cutoff:
                        recent_crashes += 1
                except Exception:
                    pass

        return recent_crashes >= threshold
