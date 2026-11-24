"""
Live system preflight diagnostics for Zye Day 13 Autonomous Intelligence System.
Performs non-invasive, lightweight inspection of hardware telemetry, resource constraints,
and target file/directory states without modifying target resources or blocking the voice loop.
"""

from __future__ import annotations

import asyncio
import logging
import os
import pathlib
import sys
from datetime import datetime, timezone
from typing import Any

try:
    import psutil
    _PSUTIL_AVAILABLE = True
except ImportError:
    _PSUTIL_AVAILABLE = False

logger = logging.getLogger("zye.intelligence.preflight")


def _is_windows_file_locked(path: pathlib.Path) -> str:
    """
    Non-invasively inspect whether an existing file is currently locked on Windows.
    Strictly avoids append mode and avoids creating new files or modifying existing files.
    Returns 'LOCKED', 'NOT_LOCKED', 'UNKNOWN', or 'NOT_APPLICABLE'.
    """
    if not path.exists():
        return "NOT_APPLICABLE"
    if path.is_dir():
        return "NOT_APPLICABLE"

    if sys.platform != "win32":
        return "UNKNOWN"

    try:
        # Non-invasive attempt: Try opening in exclusive read mode via os.open
        # On Windows, os.O_RDONLY | os.O_BINARY does not modify or create the file
        fd = os.open(str(path), os.O_RDONLY | getattr(os, "O_BINARY", 0))
        os.close(fd)
        # Successfully opened for reading, but other processes might hold an exclusive write lock
        # As mandated by Section 06.1, report UNKNOWN when lock status cannot be definitively established
        return "UNKNOWN"
    except PermissionError as perm_err:
        # WinError 32: ERROR_SHARING_VIOLATION (file is locked by another process)
        # WinError 33: ERROR_LOCK_VIOLATION
        winerror = getattr(perm_err, "winerror", None)
        if winerror in (32, 33):
            return "LOCKED"
        return "UNKNOWN"
    except Exception:
        return "UNKNOWN"


class ZyeSystemPreflight:
    """
    Collects real-time hardware telemetry and target resource diagnostics.
    Designed for non-blocking execution via asyncio.to_thread.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}

    def inspect_memory(self) -> dict[str, Any]:
        """Inspect RAM metrics via psutil.virtual_memory()."""
        if not _PSUTIL_AVAILABLE:
            return {
                "available": False,
                "error": "psutil not installed",
                "total_gb": 0.0,
                "available_gb": 0.0,
                "used_gb": 0.0,
                "percent": 0.0,
                "free_gb": 0.0,
            }
        try:
            vm = psutil.virtual_memory()
            return {
                "available": True,
                "total_gb": round(vm.total / (1024**3), 2),
                "available_gb": round(vm.available / (1024**3), 2),
                "used_gb": round(vm.used / (1024**3), 2),
                "percent": float(vm.percent),
                "free_gb": round(getattr(vm, "free", vm.available) / (1024**3), 2),
            }
        except Exception as exc:
            logger.warning("Memory inspection error: %s", exc)
            return {"available": False, "error": str(exc), "percent": 0.0, "available_gb": 0.0}

    def inspect_storage(self, path: str | None = None) -> dict[str, Any]:
        """Inspect storage metrics for the drive containing path or working drive."""
        if not _PSUTIL_AVAILABLE:
            return {"available": False, "error": "psutil not installed", "free_gb": 0.0, "percent": 0.0}
        try:
            if path:
                p = pathlib.Path(path).resolve()
                drive = p.anchor or str(p)
            else:
                drive = pathlib.Path.cwd().anchor or "C:\\"

            if not os.path.exists(drive):
                drive = pathlib.Path.cwd().anchor or "C:\\"

            usage = psutil.disk_usage(drive)
            return {
                "available": True,
                "drive": drive,
                "total_gb": round(usage.total / (1024**3), 2),
                "used_gb": round(usage.used / (1024**3), 2),
                "free_gb": round(usage.free / (1024**3), 2),
                "percent": float(usage.percent),
            }
        except Exception as exc:
            logger.warning("Storage inspection error for '%s': %s", path, exc)
            return {"available": False, "drive": str(path), "error": str(exc), "free_gb": 0.0, "percent": 0.0}

    def inspect_cpu(self, interval: float = 0.05) -> dict[str, Any]:
        """Inspect CPU usage percentage without excessive blocking."""
        if not _PSUTIL_AVAILABLE:
            return {"available": False, "error": "psutil not installed", "percent": 0.0}
        try:
            percent = float(psutil.cpu_percent(interval=interval))
            core_count = psutil.cpu_count(logical=True) or 1
            physical_cores = psutil.cpu_count(logical=False) or 1
            return {
                "available": True,
                "percent": percent,
                "logical_cores": core_count,
                "physical_cores": physical_cores,
            }
        except Exception as exc:
            logger.warning("CPU inspection error: %s", exc)
            return {"available": False, "error": str(exc), "percent": 0.0}

    def inspect_battery(self) -> dict[str, Any]:
        """Inspect battery state safely handling desktop/virtual environments."""
        if not _PSUTIL_AVAILABLE:
            return {
                "available": False,
                "percent": None,
                "power_plugged": None,
                "battery_powered": None,
                "error": "psutil not installed",
            }
        try:
            batt = psutil.sensors_battery()
            if batt is None:
                return {
                    "available": False,
                    "percent": None,
                    "power_plugged": None,
                    "battery_powered": None,
                    "note": "No battery sensor detected (desktop or virtual environment)",
                }
            plugged = bool(batt.power_plugged) if batt.power_plugged is not None else None
            return {
                "available": True,
                "percent": float(batt.percent),
                "power_plugged": plugged,
                "battery_powered": (not plugged) if plugged is not None else None,
                "secsleft": batt.secsleft if getattr(batt, "secsleft", -1) != -1 else None,
            }
        except Exception as exc:
            logger.warning("Battery inspection error: %s", exc)
            return {
                "available": False,
                "error": str(exc),
                "percent": None,
                "power_plugged": None,
                "battery_powered": None,
            }

    def inspect_processes(self, top_n: int = 5) -> list[dict[str, Any]]:
        """Bounded process inspection for top memory-consuming applications."""
        if not _PSUTIL_AVAILABLE:
            return []
        procs: list[dict[str, Any]] = []
        try:
            for p in psutil.process_iter(["pid", "name", "memory_info", "cpu_percent"]):
                try:
                    info = p.info
                    mem = info.get("memory_info")
                    rss = mem.rss if mem else 0
                    procs.append({
                        "pid": info.get("pid"),
                        "name": info.get("name") or "unknown",
                        "memory_mb": round(rss / (1024**2), 1),
                        "cpu_percent": info.get("cpu_percent") or 0.0,
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            procs.sort(key=lambda x: x["memory_mb"], reverse=True)
            return procs[:top_n]
        except Exception as exc:
            logger.warning("Process list inspection error: %s", exc)
            return []

    def inspect_target_paths(self, targets: list[str]) -> list[dict[str, Any]]:
        """
        Non-invasively inspect target files and directories.
        Never modifies, overwrites, or creates files.
        """
        results: list[dict[str, Any]] = []
        for target in targets:
            info: dict[str, Any] = {
                "target": str(target),
                "original_target": str(target),
            }
            if not str(target).strip():
                info["exists"] = False
                info["target_type"] = "invalid"
                info["readable"] = False
                info["writable"] = False
                info["file_size_mb"] = None
                info["size_bytes"] = None
                info["possible_lock_status"] = "NOT_APPLICABLE"
                info["lock_status"] = "UNKNOWN"
                info["diagnostic_status"] = "INVALID"
                info["error"] = "Target path cannot be empty"
                results.append(info)
                continue

            try:
                p = pathlib.Path(str(target)).resolve()
                info["resolved_path"] = str(p)

                if not p.exists():
                    info["exists"] = False
                    info["target_type"] = "missing"
                    info["is_file"] = False
                    info["is_dir"] = False
                    info["readable"] = False
                    info["writable"] = False
                    info["file_size_mb"] = None
                    info["size_bytes"] = None
                    info["possible_lock_status"] = "NOT_APPLICABLE"
                    info["lock_status"] = "UNKNOWN"
                    info["diagnostic_status"] = "MISSING"
                    info["error"] = "Target does not exist"
                    parent = p.parent
                    info["parent_exists"] = parent.exists()
                    info["parent_writable"] = os.access(parent, os.W_OK) if parent.exists() else False
                    results.append(info)
                    continue

                info["exists"] = True
                info["is_file"] = p.is_file()
                info["is_dir"] = p.is_dir()
                info["target_type"] = "file" if p.is_file() else ("directory" if p.is_dir() else "special")
                info["readable"] = os.access(p, os.R_OK)
                info["writable"] = os.access(p, os.W_OK)

                if p.is_file():
                    stat_info = p.stat()
                    info["size_bytes"] = stat_info.st_size
                    info["file_size_mb"] = round(stat_info.st_size / (1024**2), 3)
                    info["modified_at"] = datetime.fromtimestamp(stat_info.st_mtime, tz=timezone.utc).isoformat()
                    lock_res = _is_windows_file_locked(p)
                    info["possible_lock_status"] = lock_res
                    info["lock_status"] = lock_res
                    info["diagnostic_status"] = "LOCKED" if lock_res == "LOCKED" else "OK"
                else:
                    info["size_bytes"] = None
                    info["file_size_mb"] = None
                    info["possible_lock_status"] = "NOT_APPLICABLE"
                    info["lock_status"] = "UNKNOWN"
                    info["diagnostic_status"] = "OK"

                # Check free storage on containing drive
                try:
                    drive = p.anchor or str(p)
                    disk_res = self.inspect_storage(drive)
                    info["drive_free_gb"] = disk_res.get("free_gb")
                except Exception:
                    info["drive_free_gb"] = None

            except PermissionError as p_err:
                info["exists"] = "unknown"
                info["target_type"] = "unknown"
                info["possible_lock_status"] = "UNKNOWN"
                info["lock_status"] = "UNKNOWN"
                info["diagnostic_status"] = "ERROR"
                info["readable"] = False
                info["writable"] = False
                info["error"] = f"Permission denied: {p_err}"
            except Exception as exc:
                info["exists"] = False
                info["target_type"] = "unknown"
                info["possible_lock_status"] = "UNKNOWN"
                info["lock_status"] = "UNKNOWN"
                info["diagnostic_status"] = "ERROR"
                info["error"] = str(exc)

            results.append(info)
        return results

    def collect_system_metrics(self) -> dict[str, Any]:
        """Collect current system metrics (memory, storage, cpu, battery). Backward compatible with Day 11."""
        report = self.generate_preflight_report([])
        return {
            "ram": self.inspect_memory(),
            "storage": self.inspect_storage(),
            "cpu": self.inspect_cpu(),
            "battery": self.inspect_battery(),
            "preflight_summary": report,
        }

    def generate_preflight_report(
        self, targets: list[str] | None = None
    ) -> dict[str, Any]:
        """
        Generate full synchronous preflight report.
        Matches Section 06 schemas:
        free_ram_gb, ram_used_pct, free_disk_gb, disk_used_pct, cpu_load_pct,
        battery_percent, battery_powered, top_memory_processes, target_diagnostics.
        """
        mem = self.inspect_memory()
        disk = self.inspect_storage()
        cpu = self.inspect_cpu(interval=0.05)
        batt = self.inspect_battery()
        top_procs = self.inspect_processes(top_n=3)

        warnings: list[str] = []
        unknowns: list[str] = []

        ram_used_pct = mem.get("percent", 0.0)
        free_ram_gb = mem.get("available_gb", 0.0)
        disk_used_pct = disk.get("percent", 0.0)
        free_disk_gb = disk.get("free_gb", 0.0)
        cpu_load_pct = cpu.get("percent", 0.0)

        # Threshold validations (configurable via self._config)
        ram_high = float(self._config.get("ram_high_threshold", 88.0))
        disk_high = float(self._config.get("disk_high_threshold", 92.0))
        batt_warn = float(self._config.get("battery_warning_threshold", 15.0))
        batt_crit = float(self._config.get("battery_critical_threshold", 8.0))

        if ram_used_pct >= ram_high:
            warnings.append(f"High RAM usage: {ram_used_pct:.1f}% used (>= {ram_high:.0f}%)")
        if disk_used_pct >= disk_high:
            warnings.append(f"High disk utilization: {disk_used_pct:.1f}% used (>= {disk_high:.0f}%)")
        if cpu_load_pct >= 85.0:
            warnings.append(f"Elevated CPU load: {cpu_load_pct:.1f}%")

        batt_pct = batt.get("percent")
        power_plugged = batt.get("power_plugged")
        battery_powered = batt.get("battery_powered")

        if batt.get("available"):
            if power_plugged is False and batt_pct is not None:
                if batt_pct <= batt_crit:
                    warnings.append(f"CRITICAL BATTERY: {batt_pct:.1f}% remaining, unplugged")
                elif batt_pct <= batt_warn:
                    warnings.append(f"Low battery: {batt_pct:.1f}% remaining, unplugged")
        else:
            unknowns.append("Battery sensor telemetry unavailable on this hardware")

        # Target diagnostics
        target_results = self.inspect_target_paths(targets or [])
        for t_diag in target_results:
            if t_diag.get("exists") is False and not t_diag.get("parent_exists", True):
                warnings.append(f"Target path parent directory missing: {t_diag.get('target')}")
            if t_diag.get("possible_lock_status") == "LOCKED":
                warnings.append(f"File locked by another process: {t_diag.get('target')}")
            elif t_diag.get("lock_status") == "UNKNOWN":
                unknowns.append(f"Lock status unknown for target: {t_diag.get('target')}")
            if "Permission denied" in str(t_diag.get("error", "")):
                warnings.append(f"Permission denied on target: {t_diag.get('target')}")

        has_critical = any("CRITICAL" in w for w in warnings)
        if has_critical:
            system_status = "BLOCKED"
        elif len(warnings) > 0:
            system_status = "DEGRADED"
        else:
            system_status = "READY"

        return {
            "system_status": system_status,
            "free_ram_gb": free_ram_gb,
            "ram_used_pct": ram_used_pct,
            "free_disk_gb": free_disk_gb,
            "disk_used_pct": disk_used_pct,
            "cpu_load_pct": cpu_load_pct,
            "battery_percent": batt_pct,
            "battery_powered": battery_powered,
            "power_plugged": power_plugged,
            "top_memory_processes": top_procs,
            "target_diagnostics": target_results,
            "warnings": warnings,
            "unknowns": unknowns,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def preflight_system_check_async(
        self, targets: list[str] | None = None
    ) -> dict[str, Any]:
        """Asynchronous wrapper running preflight in a worker thread to avoid blocking voice loop."""
        return await asyncio.to_thread(self.generate_preflight_report, targets)


def _preflight_system_check(targets: list[str]) -> dict[str, Any]:
    """Top-level functional interface for Section 06 preflight check."""
    pf = ZyeSystemPreflight()
    return pf.generate_preflight_report(targets)
