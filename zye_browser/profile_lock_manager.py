"""
Lock and Concurrency Management for Browser Profiles — Day 24.
Detects active Chrome locks, prevents concurrent access collisions, and safely recovers stale locks.
"""

from __future__ import annotations

import os
import sys
import psutil
from pathlib import Path
from typing import Any, Dict, Optional

from zye_browser.browser_errors import BrowserProfileLockedError


class ProfileLockManager:
    """Detects and coordinates profile locks across Chrome instances and Zye sessions."""

    LOCK_FILES = ("lockfile", "SingletonLock", "SingletonCookie", "SingletonSocket")

    @classmethod
    def is_profile_locked(cls, profile_dir: Path) -> bool:
        """
        Check if a browser profile user data dir is currently locked by a live process.
        Returns True if locked, False otherwise.
        """
        if not profile_dir.exists():
            return False

        # 1. Check for SingletonLock or lockfile
        for lock_name in cls.LOCK_FILES:
            lock_path = profile_dir / lock_name
            if lock_path.exists():
                # On Windows, try opening in exclusive write mode to test lock
                try:
                    with open(lock_path, "r+b"):
                        pass
                except (IOError, PermissionError):
                    return True

        # 2. Check Zye internal session lockfile
        zye_lock = profile_dir / ".zye_lock"
        if zye_lock.exists():
            try:
                content = zye_lock.read_text(encoding="utf-8").strip()
                if content:
                    pid = int(content.split(":")[0])
                    if psutil.pid_exists(pid):
                        # Verify process is still alive and resembles python or chrome
                        try:
                            proc = psutil.Process(pid)
                            if proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE:
                                return True
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
            except Exception:
                pass

        return False

    @classmethod
    def acquire_lock(cls, profile_id: str, profile_dir: Path) -> None:
        """
        Acquire internal lock for the profile directory.
        Raises BrowserProfileLockedError if already locked by another live process.
        """
        profile_dir.mkdir(parents=True, exist_ok=True)
        zye_lock = profile_dir / ".zye_lock"

        if cls.is_profile_locked(profile_dir):
            locking_info = cls.get_locking_process_info(profile_dir)
            raise BrowserProfileLockedError(
                code="ERR_BROWSER_PROFILE_LOCKED",
                message=f"Browser profile '{profile_id}' is currently in use by another Chrome or Zye process.",
                profile_id=profile_id,
                details=locking_info or {"path": str(profile_dir)},
                remediation="Close any running Chrome windows using this profile, or wait for the process to exit.",
            )

        # Write current process ID and timestamp
        try:
            zye_lock.write_text(f"{os.getpid()}:{profile_id}", encoding="utf-8")
        except Exception:
            pass

    @classmethod
    def release_lock(cls, profile_id: str, profile_dir: Path) -> None:
        """Release the internal Zye lock for this profile."""
        zye_lock = profile_dir / ".zye_lock"
        if zye_lock.exists():
            try:
                zye_lock.unlink(missing_ok=True)
            except Exception:
                pass

    @classmethod
    def get_locking_process_info(cls, profile_dir: Path) -> Optional[Dict[str, Any]]:
        """Attempt to read PID and process name holding the lock."""
        zye_lock = profile_dir / ".zye_lock"
        if zye_lock.exists():
            try:
                content = zye_lock.read_text(encoding="utf-8").strip()
                pid_str = content.split(":")[0]
                pid = int(pid_str)
                if psutil.pid_exists(pid):
                    proc = psutil.Process(pid)
                    return {
                        "pid": pid,
                        "process_name": proc.name(),
                        "create_time": proc.create_time(),
                        "status": proc.status(),
                    }
            except Exception:
                pass

        return None

    @classmethod
    def clean_stale_locks(cls, profile_dir: Path) -> bool:
        """
        Remove stale lock files if the owning process is no longer alive.
        Returns True if a stale lock was cleared, False otherwise.
        """
        zye_lock = profile_dir / ".zye_lock"
        if zye_lock.exists():
            try:
                content = zye_lock.read_text(encoding="utf-8").strip()
                pid = int(content.split(":")[0])
                if not psutil.pid_exists(pid):
                    zye_lock.unlink(missing_ok=True)
                    return True
            except Exception:
                pass
        return False
