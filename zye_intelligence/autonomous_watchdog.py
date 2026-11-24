"""
Autonomous Problem Identification & Zero-Prompt Proactive Watchdog — Zye Day 13.
Continuously scans system health, audits RAM, Disk, Battery, and error logs,
deduplicates alerts, triggers approved reflexes, and notifies user without polling loops.
"""

from __future__ import annotations

import asyncio
import logging
import os
import pathlib
import time
from datetime import datetime, timezone
from typing import Any

from zye_intelligence.schemas import WatchdogProblem

try:
    import psutil
    _PSUTIL_AVAILABLE = True
except ImportError:
    _PSUTIL_AVAILABLE = False

logger = logging.getLogger("zye.intelligence.watchdog")

class WatchdogScanResult(dict):
    """
    Dict result of watchdog scan.
    len(result) returns count of unsuppressed problems for backward compatibility with Day 11,
    while retaining all dict keys ('unsuppressed_problems', 'detected_problems', etc.) for Day 13.
    """
    def __len__(self) -> int:
        return len(self.get("unsuppressed_problems", []))


DEFAULT_CONFIG: dict[str, Any] = {
    "ram_high_threshold": 95.0,
    "ram_clear_threshold": 90.0,
    "disk_high_threshold": 92.0,
    "disk_clear_threshold": 87.0,
    "battery_warning_threshold": 15.0,
    "battery_critical_threshold": 8.0,
    "error_log_tail_lines": 15,
    "alert_cooldown_seconds": 300.0,
    "interval_seconds": 25.0,
    "deduplicate_alerts": True,
}

WATCHDOG_INTERVAL_SECONDS = 25.0


def _scan_emerging_problems_sync(
    config: dict[str, Any] | None = None,
    mission_controller: Any = None,
) -> dict[str, Any]:
    """
    Synchronous system problem identification scan.
    Audits RAM, Disk, Battery, Process telemetry, and recent error logs.
    """
    cfg = {**DEFAULT_CONFIG, **(config or {})}
    problems: list[dict[str, Any]] = []
    telemetry: dict[str, Any] = {}

    ram_thresh = float(cfg.get("ram_high_threshold", cfg.get("ram_warning_pct", 88.0)))
    ram_clear = float(cfg.get("ram_clear_threshold", ram_thresh - 5.0))
    disk_thresh = float(cfg.get("disk_high_threshold", cfg.get("disk_warning_pct", 92.0)))
    disk_clear = float(cfg.get("disk_clear_threshold", disk_thresh - 5.0))
    batt_warn = float(cfg.get("battery_warning_threshold", cfg.get("battery_warning_pct", 15.0)))
    batt_crit = float(cfg.get("battery_critical_threshold", cfg.get("battery_critical_pct", 8.0)))
    tail_lines = int(cfg.get("error_log_tail_lines", 15))
    active_cats = set(cfg.get("active_categories") or ())

    # 1. RAM Audit
    top_procs: list[dict[str, Any]] = []
    if _PSUTIL_AVAILABLE:
        try:
            vm = psutil.virtual_memory()
            telemetry["ram_used_pct"] = float(vm.percent)
            telemetry["free_ram_gb"] = round(vm.available / (1024**3), 2)

            effective_ram_thresh = ram_clear if "RAM" in active_cats else ram_thresh
            if vm.percent >= effective_ram_thresh:
                # Inspect top 3 memory processes only when RAM actually exceeds threshold
                for p in psutil.process_iter(["pid", "name", "memory_info"]):
                    try:
                        mem = p.info.get("memory_info")
                        rss = mem.rss if mem else 0
                        top_procs.append({
                            "process_name": p.info.get("name") or "unknown",
                            "memory_mb": round(rss / (1024**2), 1),
                        })
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        continue
                top_procs.sort(key=lambda x: x["memory_mb"], reverse=True)
                top_procs = top_procs[:3]
                for proc in top_procs:
                    proc["severity"] = "HIGH"
                    proc["recommended_fix"] = "Review process memory consumption or close unneeded background apps"
                telemetry["top_memory_processes"] = top_procs

                problems.append(
                    WatchdogProblem(
                        category="RAM",
                        severity="HIGH",
                        description=f"High RAM utilization: {vm.percent:.1f}% used (>= {ram_thresh:.0f}%)",
                        recommendation="Trigger ram_overload_relief reflex and prompt user to close unused applications",
                        details={"used_pct": vm.percent, "top_processes": top_procs},
                    ).model_dump()
                )
        except Exception as exc:
            logger.warning("RAM audit error: %s", exc)

        # 2. Disk Audit
        try:
            drive = pathlib.Path.cwd().anchor or "C:\\"
            du = psutil.disk_usage(drive)
            telemetry["disk_used_pct"] = float(du.percent)
            telemetry["free_disk_gb"] = round(du.free / (1024**3), 2)
            effective_disk_thresh = disk_clear if "DISK" in active_cats else disk_thresh
            if du.percent >= effective_disk_thresh:
                problems.append(
                    WatchdogProblem(
                        category="DISK",
                        severity="MEDIUM",
                        description=f"High disk utilization on {drive}: {du.percent:.1f}% used (>= {disk_thresh:.0f}%)",
                        recommendation="Offer safe cleanup plan for temp files and purge old backups",
                        details={"drive": drive, "used_pct": du.percent, "free_gb": telemetry["free_disk_gb"]},
                    ).model_dump()
                )
        except Exception as exc:
            logger.warning("Disk audit error: %s", exc)

        # 3. Battery Audit
        try:
            batt = psutil.sensors_battery()
            if batt:
                telemetry["battery_percent"] = float(batt.percent)
                telemetry["power_plugged"] = bool(batt.power_plugged)
                if not batt.power_plugged:
                    if batt.percent <= batt_crit:
                        problems.append(
                            WatchdogProblem(
                                category="BATTERY",
                                severity="CRITICAL",
                                description=f"Critical battery level: {batt.percent:.1f}% remaining and unplugged (<= {batt_crit:.0f}%)",
                                recommendation="Switch to STEALTH_BATTERY_SAVER and reduce display brightness",
                                details={"percent": batt.percent, "power_plugged": False},
                            ).model_dump()
                        )
                    elif batt.percent <= batt_warn:
                        problems.append(
                            WatchdogProblem(
                                category="BATTERY",
                                severity="HIGH",
                                description=f"Low battery level: {batt.percent:.1f}% remaining and unplugged (<= {batt_warn:.0f}%)",
                                recommendation="Recommend connecting charger or activating STEALTH_BATTERY_SAVER",
                                details={"percent": batt.percent, "power_plugged": False},
                            ).model_dump()
                        )
            else:
                telemetry["battery_percent"] = None
                telemetry["power_plugged"] = None
        except Exception as exc:
            logger.warning("Battery audit error: %s", exc)

    # 4. Error Log Audit
    err_log = pathlib.Path("logs/zye_errors.log")
    if err_log.exists():
        try:
            lines = err_log.read_text(encoding="utf-8", errors="replace").splitlines()
            tail = lines[-tail_lines:] if len(lines) > tail_lines else lines
            bug_reports = [line for line in tail if "BUG REPORT" in line or "guard_traceback" in line]
            if bug_reports:
                problems.append(
                    WatchdogProblem(
                        category="ERROR_LOG",
                        severity="MEDIUM",
                        description=f"Detected {len(bug_reports)} recent BUG REPORT entries in {err_log.name}",
                        recommendation="Review error logs and consider invoking self-repair workflow",
                        details={"bug_reports_count": len(bug_reports), "samples": bug_reports[:3]},
                    ).model_dump()
                )
        except Exception as exc:
            logger.warning("Error log audit error: %s", exc)

    active_mission = "NORMAL_ASSISTANT"
    if mission_controller:
        try:
            m_state = mission_controller.get_current_mission()
            active_mission = m_state.get("mission", "NORMAL_ASSISTANT")
        except Exception:
            pass

    status = "PROBLEMS_DETECTED" if problems else "ALL_SYSTEMS_NOMINAL"
    return {
        "status": status,
        "detected_problems": problems,
        "telemetry": telemetry,
        "scan_timestamp": datetime.now(timezone.utc).isoformat(),
        "active_mission": active_mission,
    }


class ZyeAutonomousWatchdog:
    """
    Proactive background watchdog engine.
    Scans system periodically, deduplicates alerts, triggers approved reflexes,
    and supports graceful async task cancellation.
    """

    def __init__(
        self,
        config: dict[str, Any] | None = None,
        mission_controller: Any = None,
    ) -> None:
        self._config = {**DEFAULT_CONFIG, **(config or {})}
        self._mission = mission_controller
        self._running = False
        self._task: asyncio.Task | None = None
        self._last_alert_times: dict[str, float] = {}
        self._active_problem_fingerprints: set[str] = set()
        self._active_categories: set[str] = set()
        self._resolved_problems: list[dict[str, Any]] = []
        self._scan_count = 0
        self._last_problems: list[dict[str, Any]] = []

    async def detect_problems(self) -> list[dict[str, Any]]:
        """Run problem scan asynchronously in thread."""
        scan_res = await asyncio.to_thread(_scan_emerging_problems_sync, self._config, self._mission)
        return scan_res.get("detected_problems", [])

    async def scan_system(self) -> dict[str, Any]:
        """Run system scan, update problem tracking, deduplicate, and record recoveries."""
        self._scan_count += 1
        scan_cfg = {**self._config, "active_categories": self._active_categories}
        scan_res = await asyncio.to_thread(_scan_emerging_problems_sync, scan_cfg, self._mission)
        raw_problems = scan_res.get("detected_problems", [])

        current_fingerprints = set()
        current_categories = set()
        unsuppressed_problems: list[dict[str, Any]] = []
        now = time.monotonic()
        cooldown = float(self._config.get("alert_cooldown_seconds", 300.0))

        for prob in raw_problems:
            cat = prob.get("category", "UNKNOWN")
            sev = prob.get("severity", "MEDIUM")
            current_categories.add(cat)
            # Stable fingerprint: independent of fluctuating percentage in description
            fp = f"{cat}:{sev}"
            current_fingerprints.add(fp)

            last_time = self._last_alert_times.get(fp, 0.0)
            if now - last_time >= cooldown:
                unsuppressed_problems.append(prob)
                self._last_alert_times[fp] = now

        # Identify resolved problems
        recovered = self._active_problem_fingerprints - current_fingerprints
        for r_fp in recovered:
            logger.info("Watchdog problem cleared: %s", r_fp)
            self._resolved_problems.append({"fingerprint": r_fp, "cleared_at": datetime.now(timezone.utc).isoformat()})

        self._active_problem_fingerprints = current_fingerprints
        self._active_categories = current_categories
        self._last_problems = raw_problems

        return WatchdogScanResult({
            **scan_res,
            "unsuppressed_problems": unsuppressed_problems,
            "active_problem_count": len(current_fingerprints),
            "scan_count": self._scan_count,
        })

    def get_watchdog_status(self) -> dict[str, Any]:
        """Return current status of watchdog monitor. Backward compatible with Day 11."""
        return {
            "running": bool(self._running),
            "scan_count": self._scan_count,
            "active_problem_count": len(self._active_problem_fingerprints),
            "resolved_problem_count": len(self._resolved_problems),
            "interval_seconds": float(self._config.get("interval_seconds", WATCHDOG_INTERVAL_SECONDS)),
        }

    async def start(self) -> None:
        """Start the background watchdog loop. Prevents duplicate task creation."""
        if self._running:
            logger.warning("Watchdog is already running — ignoring duplicate start request")
            return
        self._running = True
        self._task = asyncio.create_task(self._monitoring_loop(), name="zye_autonomous_watchdog")
        logger.info("Zye Autonomous Watchdog started (interval=%ss)", self._config.get("interval_seconds", 25.0))

    async def stop(self) -> None:
        """Stop background watchdog cleanly."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        logger.info("Zye Autonomous Watchdog stopped cleanly")

    async def _monitoring_loop(self) -> None:
        """Periodic background scan loop with graceful backoff."""
        interval = float(self._config.get("interval_seconds", WATCHDOG_INTERVAL_SECONDS))
        while self._running:
            try:
                await asyncio.sleep(interval)
                if not self._running:
                    break
                await self.scan_system()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Watchdog monitoring loop error: %s", exc)
                await asyncio.sleep(2.0)


async def proactive_autonomous_loop(zye: Any) -> None:
    """
    Main background loop as specified in Section 14.
    Runs periodically, calls autonomous_identify_problems via orchestrator or internal fallback,
    evaluates severity, triggers approved reflexes, and delivers notifications.
    """
    cfg = getattr(zye, "_cfg", {}).get("autonomous_brain", {}).get("watchdog", {})
    interval = float(cfg.get("interval_seconds", WATCHDOG_INTERVAL_SECONDS))
    logger.info("Starting proactive_autonomous_loop (interval=%.1fs)", interval)

    watchdog = ZyeAutonomousWatchdog(config=cfg, mission_controller=getattr(zye, "mission_controller", None))

    while True:
        try:
            await asyncio.sleep(interval)

            # Check orchestrator health if available
            agent = getattr(zye, "agent", None)
            res = None
            if agent and hasattr(agent, "call_mcp_with_recovery"):
                try:
                    res = await agent.call_mcp_with_recovery("autonomous_identify_problems", {})
                except Exception as mcp_err:
                    logger.warning("Watchdog MCP call failed: %s; using internal scan", mcp_err)
                    res = None

            if res is None or not isinstance(res, dict) or res.get("status") == "error":
                res = await watchdog.scan_system()

            # Inspect problems
            problems = res.get("detected_problems", [])
            for prob in problems:
                cat = prob.get("category")
                sev = prob.get("severity")

                # Handle critical reflex triggers
                if cat == "BATTERY" and sev == "CRITICAL":
                    logger.warning("Critical battery detected by watchdog; executing battery_critical reflex")
                    if hasattr(zye, "emergency_reflex") and zye.emergency_reflex:
                        await zye.emergency_reflex.execute("battery_critical")
                elif cat == "RAM" and sev == "CRITICAL":
                    logger.warning("Critical RAM overload detected by watchdog")
                    if hasattr(zye, "emergency_reflex") and zye.emergency_reflex:
                        await zye.emergency_reflex.execute("ram_overload_relief")

        except asyncio.CancelledError:
            logger.info("proactive_autonomous_loop cancelled cleanly")
            break
        except Exception as loop_err:
            logger.error("Unexpected error in proactive_autonomous_loop: %s", loop_err)
            await asyncio.sleep(5.0)
