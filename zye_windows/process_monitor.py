"""
Windows Process & System Telemetry Monitor — Zye Day 17.
Captures real-time CPU and RAM snapshots across processes and system-wide resources.
"""

from __future__ import annotations

import logging
import time
from typing import Any

try:
    import psutil
    _PSUTIL_AVAILABLE = True
except ImportError:
    _PSUTIL_AVAILABLE = False

logger = logging.getLogger("zye.windows.process_monitor")


class WindowsProcessMonitor:
    """Provides non-invasive system resource and process-level metric snapshots."""

    def get_system_snapshot(self) -> dict[str, Any]:
        """Capture overall host CPU usage, virtual memory, and process count."""
        if not _PSUTIL_AVAILABLE:
            return {"status": "ERROR", "message": "psutil unavailable"}

        try:
            mem = psutil.virtual_memory()
            cpu_pct = psutil.cpu_percent(interval=None)
            procs_count = len(psutil.pids())

            return {
                "status": "SUCCESS",
                "cpu_percent": cpu_pct,
                "ram_total_mb": round(mem.total / (1024 * 1024), 1),
                "ram_used_mb": round(mem.used / (1024 * 1024), 1),
                "ram_percent": mem.percent,
                "process_count": procs_count,
            }
        except Exception as exc:
            return {"status": "ERROR", "message": str(exc)}

    def get_process_cpu_snapshot(self, pid: int, interval: float = 0.5) -> dict[str, Any]:
        """Sample CPU percentage for a target process over a short measurement window."""
        if not _PSUTIL_AVAILABLE:
            return {"status": "ERROR", "message": "psutil unavailable"}

        try:
            p = psutil.Process(pid)
            # Initialize counter
            p.cpu_percent(interval=None)
            time.sleep(interval)
            val = p.cpu_percent(interval=None)

            return {
                "status": "SUCCESS",
                "pid": pid,
                "name": p.name(),
                "cpu_percent": val,
                "sample_interval_seconds": interval,
            }
        except psutil.NoSuchProcess:
            return {"status": "NOT_FOUND", "message": f"Process {pid} does not exist."}
        except psutil.AccessDenied:
            return {"status": "ACCESS_DENIED", "message": f"Access denied to process {pid}."}
        except Exception as exc:
            return {"status": "ERROR", "message": str(exc)}

    def get_top_by_cpu(self, limit: int = 10) -> list[dict[str, Any]]:
        """Retrieve top N processes ordered by CPU utilization."""
        if not _PSUTIL_AVAILABLE:
            return []

        procs: list[dict[str, Any]] = []
        try:
            for p in psutil.process_iter(["pid", "name", "cpu_percent"]):
                try:
                    procs.append({
                        "pid": p.info.get("pid"),
                        "name": p.info.get("name"),
                        "cpu_percent": p.info.get("cpu_percent") or 0.0,
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception:
            pass

        procs.sort(key=lambda x: x.get("cpu_percent", 0.0), reverse=True)
        return procs[:limit]

    def get_top_by_memory(self, limit: int = 10) -> list[dict[str, Any]]:
        """Retrieve top N processes ordered by resident memory footprint."""
        if not _PSUTIL_AVAILABLE:
            return []

        procs: list[dict[str, Any]] = []
        try:
            for p in psutil.process_iter(["pid", "name", "memory_info"]):
                try:
                    mem = p.info.get("memory_info")
                    mem_mb = round(mem.rss / (1024 * 1024), 1) if mem else 0.0
                    procs.append({
                        "pid": p.info.get("pid"),
                        "name": p.info.get("name"),
                        "memory_mb": mem_mb,
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception:
            pass

        procs.sort(key=lambda x: x.get("memory_mb", 0.0), reverse=True)
        return procs[:limit]
