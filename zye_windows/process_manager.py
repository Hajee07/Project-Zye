"""
Process Telemetry & Safe Windows Process Management — Zye Day 16 & Day 17.
Inspects running processes, monitors system resources, validates process trees,
protects core operating system tasks, and provides safe, two-stage process termination
and Recycle Bin management.
"""

from __future__ import annotations

import ctypes
import logging
import sys
import time
from typing import Any, Optional

try:
    import psutil
    _PSUTIL_AVAILABLE = True
except ImportError:
    _PSUTIL_AVAILABLE = False

logger = logging.getLogger("zye.windows.process_manager")


class WindowsProcessManager:
    """
    Non-invasive process telemetry, lifecycle inspection, protected task filtering,
    and Recycle Bin management.
    """

    # Protected core Windows OS tasks that must never be terminated
    PROTECTED_PROCESSES: frozenset[str] = frozenset({
        "system",
        "system idle process",
        "registry",
        "smss.exe",
        "csrss.exe",
        "wininit.exe",
        "services.exe",
        "lsass.exe",
        "svchost.exe",
        "winlogon.exe",
        "dwm.exe",
        "explorer.exe",
        "runtimebroker.exe",
        "fontdrvhost.exe",
        "sihost.exe",
        "securityhealthservice.exe",
        "msmpeng.exe",
        "taskhostw.exe",
        "spoolsv.exe",
    })

    def __init__(self) -> None:
        self._pid_create_times: dict[int, float] = {}

    # =========================================================================
    # Day 16 Baseline Methods (PRESERVED)
    # =========================================================================

    def list_running_applications(self, limit: int = 20) -> list[dict[str, Any]]:
        """List currently running user applications with non-zero memory and visible titles."""
        if not _PSUTIL_AVAILABLE:
            return []

        apps: list[dict[str, Any]] = []
        try:
            for p in psutil.process_iter(["pid", "name", "memory_info"]):
                try:
                    name = p.info.get("name") or ""
                    mem = p.info.get("memory_info")
                    mem_mb = round(mem.rss / (1024 * 1024), 1) if mem else 0.0

                    # Filter to user apps (.exe, >= 15MB)
                    if name.lower().endswith(".exe") and mem_mb >= 15.0:
                        apps.append({
                            "name": name,
                            "pid": p.info.get("pid"),
                            "memory_mb": mem_mb,
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as exc:
            logger.error("Error inspecting processes: %s", exc)

        apps.sort(key=lambda x: x.get("memory_mb", 0.0), reverse=True)
        return apps[:limit]

    def is_app_running(self, app_keyword: str) -> bool:
        """Check if any process matching keyword is running."""
        if not _PSUTIL_AVAILABLE or not app_keyword:
            return False
        kw = str(app_keyword).strip().lower()
        try:
            for p in psutil.process_iter(["name"]):
                try:
                    if kw in (p.info.get("name") or "").lower():
                        return True
                except Exception:
                    continue
        except Exception:
            pass
        return False

    def preview_recycle_bin(self) -> dict[str, Any]:
        """
        Stage 1 of Recycle Bin management: inspect items and size without deleting anything.
        """
        if sys.platform != "win32":
            return {"status": "ERROR", "message": "Only supported on Windows."}

        class SHQUERYRBINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", ctypes.c_ulong),
                ("i64Size", ctypes.c_int64),
                ("i64NumItems", ctypes.c_int64),
            ]

        try:
            rb_info = SHQUERYRBINFO()
            rb_info.cbSize = ctypes.sizeof(SHQUERYRBINFO)
            res = ctypes.windll.shell32.SHQueryRecycleBinW(None, ctypes.byref(rb_info))
            if res == 0:
                size_mb = round(rb_info.i64Size / (1024 * 1024), 2)
                return {
                    "status": "SUCCESS",
                    "num_items": rb_info.i64NumItems,
                    "total_size_mb": size_mb,
                    "message": f"Recycle Bin contains {rb_info.i64NumItems} items ({size_mb} MB). Deletion is irreversible.",
                }
            else:
                return {
                    "status": "ERROR",
                    "message": f"SHQueryRecycleBin failed with return code {res}.",
                }
        except Exception as exc:
            return {"status": "ERROR", "message": f"Could not inspect Recycle Bin: {exc}"}

    def empty_recycle_bin(self, confirmed: bool = False) -> dict[str, Any]:
        """
        Stage 2 of Recycle Bin management: empty items with mandatory confirmation.
        """
        if not confirmed:
            return {
                "status": "CONFIRMATION_REQUIRED",
                "message": "CRITICAL: Emptying Recycle Bin permanently deletes all recycled files. Call with confirmed=True to proceed.",
                "requires_user_confirmation": True,
            }

        if sys.platform != "win32":
            return {"status": "ERROR", "message": "Only supported on Windows."}

        flags = 0x00000001 | 0x00000002 | 0x00000004
        try:
            res = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, flags)
            if res == 0:
                return {
                    "status": "SUCCESS",
                    "message": "Recycle Bin has been permanently emptied.",
                    "verified": True,
                }
            else:
                return {
                    "status": "ERROR",
                    "message": f"SHEmptyRecycleBin failed with return code {res}.",
                }
        except Exception as exc:
            return {"status": "ERROR", "message": f"Empty Recycle Bin failed: {exc}"}

    # =========================================================================
    # Day 17 Enhancements: Full Process Lifecycle & Security
    # =========================================================================

    def is_protected_process(self, name: str) -> bool:
        """Check if an executable name is in the protected OS process blacklist."""
        clean = (name or "").strip().lower()
        if clean in self.PROTECTED_PROCESSES:
            return True
        for p in self.PROTECTED_PROCESSES:
            if clean == p or clean.endswith("\\" + p) or clean.endswith("/" + p):
                return True
        return False

    def list_running_processes(
        self,
        query: str = "",
        limit: int = 50,
        include_details: bool = False,
    ) -> list[dict[str, Any]]:
        """List running processes matching an optional query string."""
        if not _PSUTIL_AVAILABLE:
            return []

        q = (query or "").strip().lower()
        results: list[dict[str, Any]] = []

        attrs = ["pid", "name", "memory_info"]
        if include_details:
            attrs.extend(["cpu_percent", "ppid", "status"])

        try:
            for p in psutil.process_iter(attrs):
                try:
                    name = p.info.get("name") or ""
                    if q and q not in name.lower():
                        continue

                    mem = p.info.get("memory_info")
                    mem_mb = round(mem.rss / (1024 * 1024), 1) if mem else 0.0

                    item: dict[str, Any] = {
                        "pid": p.info.get("pid"),
                        "name": name,
                        "memory_mb": mem_mb,
                        "is_protected": self.is_protected_process(name),
                    }
                    if include_details:
                        item["cpu_percent"] = p.info.get("cpu_percent", 0.0)
                        item["ppid"] = p.info.get("ppid", 0)
                        item["status"] = str(p.info.get("status", "unknown"))

                    results.append(item)
                    if len(results) >= limit:
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as exc:
            logger.error("Error listing processes: %s", exc)

        results.sort(key=lambda x: x.get("memory_mb", 0.0), reverse=True)
        return results

    def find_process_by_name(self, name: str) -> list[dict[str, Any]]:
        """Find all running processes matching the exact or partial name."""
        return self.list_running_processes(query=name, limit=20, include_details=True)

    def get_process_details(self, pid: int) -> dict[str, Any]:
        """Fetch exhaustive telemetry and runtime status for a single PID."""
        if not _PSUTIL_AVAILABLE:
            return {"status": "ERROR", "message": "psutil unavailable"}

        try:
            p = psutil.Process(pid)
            with p.oneshot():
                name = p.name()
                create_time = p.create_time()
                self._pid_create_times[pid] = create_time
                mem = p.memory_info()
                mem_mb = round(mem.rss / (1024 * 1024), 2)
                try:
                    cmdline = p.cmdline()
                except (psutil.AccessDenied, psutil.ZombieProcess):
                    cmdline = []

                return {
                    "status": "SUCCESS",
                    "pid": pid,
                    "name": name,
                    "ppid": p.ppid(),
                    "create_time": create_time,
                    "status_str": p.status(),
                    "num_threads": p.num_threads(),
                    "memory_mb": mem_mb,
                    "cpu_percent": p.cpu_percent(interval=None),
                    "cmdline": cmdline,
                    "is_protected": self.is_protected_process(name),
                }
        except psutil.NoSuchProcess:
            return {"status": "NOT_FOUND", "message": f"Process {pid} does not exist."}
        except psutil.AccessDenied:
            return {"status": "ACCESS_DENIED", "message": f"Access denied to process {pid}."}
        except Exception as exc:
            return {"status": "ERROR", "message": str(exc)}

    def get_process_resource_usage(self, pid: int) -> dict[str, Any]:
        """Fetch real-time CPU, RAM and thread metrics for a PID."""
        if not _PSUTIL_AVAILABLE:
            return {"status": "ERROR", "message": "psutil unavailable"}

        try:
            p = psutil.Process(pid)
            mem = p.memory_info()
            return {
                "status": "SUCCESS",
                "pid": pid,
                "name": p.name(),
                "memory_mb": round(mem.rss / (1024 * 1024), 2),
                "memory_percent": round(p.memory_percent(), 2),
                "cpu_percent": p.cpu_percent(interval=None),
                "num_threads": p.num_threads(),
            }
        except psutil.NoSuchProcess:
            return {"status": "NOT_FOUND", "message": f"Process {pid} does not exist."}
        except psutil.AccessDenied:
            return {"status": "ACCESS_DENIED", "message": f"Access denied to process {pid}."}
        except Exception as exc:
            return {"status": "ERROR", "message": str(exc)}

    def get_top_processes(self, sort_by: str = "memory", limit: int = 10) -> list[dict[str, Any]]:
        """Retrieve top N processes ranked by memory or CPU usage."""
        if not _PSUTIL_AVAILABLE:
            return []

        procs: list[dict[str, Any]] = []
        try:
            for p in psutil.process_iter(["pid", "name", "memory_info", "cpu_percent"]):
                try:
                    name = p.info.get("name") or ""
                    mem = p.info.get("memory_info")
                    mem_mb = round(mem.rss / (1024 * 1024), 1) if mem else 0.0
                    cpu = p.info.get("cpu_percent") or 0.0

                    procs.append({
                        "pid": p.info.get("pid"),
                        "name": name,
                        "memory_mb": mem_mb,
                        "cpu_percent": cpu,
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as exc:
            logger.error("Error retrieving top processes: %s", exc)

        sort_key = "cpu_percent" if sort_by.lower() == "cpu" else "memory_mb"
        procs.sort(key=lambda x: x.get(sort_key, 0.0), reverse=True)
        return procs[:limit]

    def check_process_responsiveness(self, pid: int) -> dict[str, Any]:
        """Check if process is active and responding without freezing."""
        if not _PSUTIL_AVAILABLE:
            return {"status": "ERROR", "message": "psutil unavailable"}

        try:
            p = psutil.Process(pid)
            status_str = p.status()
            is_responsive = status_str not in (
                psutil.STATUS_ZOMBIE,
                psutil.STATUS_DEAD,
                psutil.STATUS_STOPPED,
            )
            return {
                "status": "SUCCESS",
                "pid": pid,
                "name": p.name(),
                "process_status": status_str,
                "is_responsive": is_responsive,
            }
        except psutil.NoSuchProcess:
            return {"status": "NOT_FOUND", "message": f"Process {pid} does not exist.", "is_responsive": False}
        except psutil.AccessDenied:
            return {"status": "ACCESS_DENIED", "message": f"Access denied to process {pid}.", "is_responsive": True}
        except Exception as exc:
            return {"status": "ERROR", "message": str(exc), "is_responsive": False}

    def get_process_tree(self, pid: int) -> dict[str, Any]:
        """Inspect the process hierarchy (parent, process, and children)."""
        if not _PSUTIL_AVAILABLE:
            return {"status": "ERROR", "message": "psutil unavailable"}

        try:
            p = psutil.Process(pid)
            name = p.name()
            parent = p.parent()
            parent_info = {"pid": parent.pid, "name": parent.name()} if parent else None

            children = []
            for c in p.children(recursive=True):
                try:
                    children.append({"pid": c.pid, "name": c.name()})
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            return {
                "status": "SUCCESS",
                "pid": pid,
                "name": name,
                "parent": parent_info,
                "children": children,
                "children_count": len(children),
            }
        except psutil.NoSuchProcess:
            return {"status": "NOT_FOUND", "message": f"Process {pid} does not exist."}
        except psutil.AccessDenied:
            return {"status": "ACCESS_DENIED", "message": f"Access denied to process {pid}."}
        except Exception as exc:
            return {"status": "ERROR", "message": str(exc)}

    def request_process_termination(
        self,
        pid: int,
        confirmed: bool = False,
        expected_name: str = "",
    ) -> dict[str, Any]:
        """
        Stage 1 of Process Termination: Validates target against OS protected blacklist,
        checks for PID reuse, and demands confirmation for non-destructive inspection.
        """
        if not _PSUTIL_AVAILABLE:
            return {"status": "ERROR", "message": "psutil unavailable"}

        try:
            p = psutil.Process(pid)
            name = p.name()
        except psutil.NoSuchProcess:
            return {"status": "NOT_FOUND", "message": f"Process {pid} does not exist."}
        except psutil.AccessDenied:
            return {"status": "ACCESS_DENIED", "message": f"Access denied to inspect PID {pid}."}

        # Check protected OS tasks
        if self.is_protected_process(name):
            return {
                "status": "PROTECTED_PROCESS",
                "pid": pid,
                "name": name,
                "message": f"SECURITY: '{name}' is a protected Windows system process and cannot be terminated.",
                "allowed": False,
            }

        # Check PID reuse if expected_name was provided
        if expected_name and expected_name.lower() not in name.lower():
            return {
                "status": "PID_REUSE_DETECTED",
                "pid": pid,
                "actual_name": name,
                "expected_name": expected_name,
                "message": f"PID {pid} now belongs to '{name}', not expected '{expected_name}'. Aborted.",
                "allowed": False,
            }

        if not confirmed:
            return {
                "status": "CONFIRMATION_REQUIRED",
                "pid": pid,
                "name": name,
                "message": f"Terminating process '{name}' (PID {pid}) will lose unsaved work. Call terminate_process with confirmed=True.",
                "requires_confirmation": True,
            }

        return {
            "status": "READY_FOR_TERMINATION",
            "pid": pid,
            "name": name,
            "allowed": True,
        }

    def get_process_children(self, pid: int, recursive: bool = False) -> list[dict[str, Any]]:
        """Get immediate or recursive child processes for a given PID."""
        if not _PSUTIL_AVAILABLE:
            return []
        try:
            p = psutil.Process(pid)
            children = []
            for c in p.children(recursive=recursive):
                try:
                    children.append({
                        "pid": c.pid,
                        "name": c.name(),
                        "status": str(c.status()),
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return children
        except Exception as exc:
            logger.warning("Error getting children for PID %d: %s", pid, exc)
            return []

    def get_system_resource_summary(self) -> dict[str, Any]:
        """
        Produce on-demand snapshot of system CPU, RAM, active processes,
        and top resource consumers without continuous polling.
        """
        if not _PSUTIL_AVAILABLE:
            return {"status": "ERROR", "message": "psutil unavailable"}

        try:
            cpu_total = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory()
            total_ram_mb = round(mem.total / (1024 * 1024), 1)
            avail_ram_mb = round(mem.available / (1024 * 1024), 1)
            used_ram_mb = round(mem.used / (1024 * 1024), 1)
            ram_percent = mem.percent

            top_mem = self.get_top_processes(sort_by="memory", limit=5)
            top_cpu = self.get_top_processes(sort_by="cpu", limit=5)
            active_pids = len(psutil.pids())

            return {
                "status": "SUCCESS",
                "cpu_percent": cpu_total,
                "ram_total_mb": total_ram_mb,
                "ram_available_mb": avail_ram_mb,
                "ram_used_mb": used_ram_mb,
                "ram_percent": ram_percent,
                "active_processes_count": active_pids,
                "top_memory_processes": top_mem,
                "top_cpu_processes": top_cpu,
            }
        except Exception as exc:
            return {"status": "ERROR", "message": f"Failed to gather resource summary: {exc}"}

    def list_processes(
        self,
        query: str = "",
        limit: int = 50,
        sort_by: str = "memory",
    ) -> list[dict[str, Any]]:
        """List running processes with pagination and configurable limit."""
        results = self.list_running_processes(query=query, limit=limit, include_details=True)
        sort_key = "cpu_percent" if sort_by.lower() == "cpu" else "memory_mb"
        results.sort(key=lambda x: x.get(sort_key, 0.0), reverse=True)
        return results[:limit]

    def start_application_process(
        self,
        application: str,
        args: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """
        Safely start an approved application process without shell=True to prevent command injection.
        """
        import subprocess

        if not application or not str(application).strip():
            return {"status": "ERROR", "message": "Application cannot be empty."}

        clean_app = str(application).strip()
        lower_app = clean_app.lower()
        if lower_app.startswith("cmd") or "powershell" in lower_app or "bash" in lower_app:
            return {
                "status": "REJECTED",
                "message": "Direct shell interpreters (cmd, powershell, bash) cannot be launched via Process Manager.",
            }

        # Security checks: prevent shell metacharacters
        for char in [";", "&", "|", "`", "$", "(", ")", "<", ">", "\n"]:
            if char in clean_app:
                return {
                    "status": "REJECTED",
                    "message": f"Illegal character '{char}' in application path or command.",
                }

        cmd = [clean_app]
        if args:
            for a in args:
                cmd.append(str(a))

        try:
            proc = subprocess.Popen(cmd, shell=False)
            time.sleep(0.5)
            # Check if process terminated immediately
            if proc.poll() is not None and proc.returncode != 0:
                return {
                    "status": "LAUNCH_FAILED",
                    "verified": False,
                    "pid": proc.pid,
                    "exit_code": proc.returncode,
                    "application": clean_app,
                    "message": f"Process '{clean_app}' exited immediately with code {proc.returncode}.",
                }

            # Empirical window verification (Zero False Success)
            try:
                from zye_windows.window_verifier import WindowVerifier
                win_check = WindowVerifier.verify_window(
                    app_name=clean_app,
                    executable_name=clean_app,
                    target_pid=proc.pid,
                )
            except Exception:
                win_check = {"found": False}

            if win_check.get("found"):
                return {
                    "status": "SUCCESS",
                    "verified": True,
                    "pid": proc.pid,
                    "hwnd": win_check.get("hwnd"),
                    "window_title": win_check.get("title"),
                    "application": clean_app,
                    "message": f"Launched '{clean_app}' (PID {proc.pid}) with verified visible window: '{win_check.get('title')}'.",
                }
            else:
                return {
                    "status": "PROCESS_STARTED",
                    "verified": False,
                    "pid": proc.pid,
                    "application": clean_app,
                    "message": f"Started process '{clean_app}' with PID {proc.pid}, but application window has not appeared or is running headlessly.",
                }
        except FileNotFoundError:
            return {
                "status": "APP_NOT_FOUND",
                "verified": False,
                "message": f"Application '{clean_app}' not found on system PATH.",
            }
        except Exception as exc:
            return {
                "status": "LAUNCH_FAILED",
                "verified": False,
                "message": f"Failed to launch '{clean_app}': {exc}",
            }

    def verify_process_status(self, pid: int) -> dict[str, Any]:
        """Verify whether a process with the specified PID is active and running."""
        if not _PSUTIL_AVAILABLE:
            return {"status": "ERROR", "message": "psutil unavailable"}

        try:
            p = psutil.Process(pid)
            status_str = p.status()
            name = p.name()
            is_running = p.is_running() and status_str != psutil.STATUS_ZOMBIE
            return {
                "status": "SUCCESS",
                "pid": pid,
                "name": name,
                "is_running": is_running,
                "process_status": status_str,
            }
        except psutil.NoSuchProcess:
            return {
                "status": "NOT_FOUND",
                "pid": pid,
                "is_running": False,
                "message": f"Process {pid} is not running or has already exited.",
            }
        except psutil.AccessDenied:
            return {
                "status": "ACCESS_DENIED",
                "pid": pid,
                "is_running": True,
                "message": f"Access denied to inspect PID {pid}.",
            }
        except Exception as exc:
            return {
                "status": "ERROR",
                "pid": pid,
                "is_running": False,
                "message": str(exc),
            }

    def terminate_process(
        self,
        pid: int,
        force: bool = False,
        confirmed: bool = False,
        expected_name: str = "",
    ) -> dict[str, Any]:
        """
        Terminate target process:
        - If confirmed=False: Returns confirmation requirement with target details.
        - If confirmed=True: Validates against protected OS tasks and terminates the process.
        Enforces protected system process policies and PID reuse validation.
        """
        if not confirmed:
            return self.request_process_termination(pid, confirmed=False, expected_name=expected_name)

        if not _PSUTIL_AVAILABLE:
            return {"status": "ERROR", "message": "psutil unavailable"}

        req = self.request_process_termination(pid, confirmed=True, expected_name=expected_name)
        if req.get("status") != "READY_FOR_TERMINATION":
            return req

        try:
            p = psutil.Process(pid)
            name = p.name()
            p.kill()
            return {
                "status": "SUCCESS",
                "pid": pid,
                "name": name,
                "mode": "FORCE" if force else "GRACEFUL",
                "message": f"Process '{name}' (PID {pid}) has been terminated.",
                "terminated": True,
            }
        except psutil.NoSuchProcess:
            return {"status": "SUCCESS", "pid": pid, "message": "Process already exited.", "terminated": True}
        except psutil.AccessDenied:
            return {"status": "ACCESS_DENIED", "pid": pid, "message": f"Access denied to terminate PID {pid}."}
        except Exception as exc:
            return {"status": "ERROR", "pid": pid, "message": str(exc)}
