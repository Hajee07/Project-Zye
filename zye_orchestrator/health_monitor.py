"""
ZYE AI — MCP Server Health Monitor (Day 12)
=============================================
Periodic background scanning of registered MCP servers, session availability,
error state tracking, and recovery triggering.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from zye_orchestrator.server_runtime import MCPServerRuntime, ServerStatus

logger = logging.getLogger("zye_orchestrator.health_monitor")


class MCPServerHealthMonitor:
    """
    Monitors running MCP servers on a configurable interval.
    Tracks uptime, tool counts, error states, and triggers recovery when appropriate.
    """

    def __init__(
        self,
        server_registry: Any,
        connection_manager: Any,
        recovery_controller: Any | None = None,
        tool_registry: Any | None = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        self._registry = server_registry
        self._conn_mgr = connection_manager
        self._recovery = recovery_controller
        self._tools = tool_registry
        self._cfg = config or {}

        self._interval = float(self._cfg.get("health_check_interval_seconds", 30.0))
        self._running = False
        self._task: asyncio.Task | None = None
        self._health_reports: dict[str, dict[str, Any]] = {}
        self._last_scan_time: str = ""

    @property
    def is_running(self) -> bool:
        return self._running

    async def start(self) -> None:
        """Start the background health monitoring loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info("MCP Server Health Monitor started (interval=%.1fs)", self._interval)

    async def stop(self) -> None:
        """Stop the background health monitor."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        logger.info("MCP Server Health Monitor stopped")

    async def _monitor_loop(self) -> None:
        """Periodic scan loop."""
        while self._running:
            try:
                await self.scan_all_servers()
                await asyncio.sleep(self._interval)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Error in MCP health monitor loop: %s", exc)
                await asyncio.sleep(2.0)

    async def scan_all_servers(self) -> dict[str, dict[str, Any]]:
        """Perform a single health check across all registered servers."""
        reports: dict[str, dict[str, Any]] = {}
        for name, config in self._registry.configs.items():
            if not config.enabled:
                reports[name] = {
                    "server_name": name,
                    "status": "DISABLED",
                    "healthy": True,
                    "enabled": False,
                }
                continue

            report = await self.check_server(name)
            reports[name] = report

            # If unhealthy and recovery enabled, trigger recovery
            if not report.get("healthy", False) and self._recovery and config.enabled:
                if self._recovery.is_request_allowed(name):
                    logger.warning("Health monitor detected unhealthy server '%s' — triggering recovery", name)
                    try:
                        asyncio.create_task(
                            self._recovery.recover_server(
                                name, self._conn_mgr, config, self._tools
                            )
                        )
                    except Exception as r_err:
                        logger.error("Failed to schedule recovery for '%s': %s", name, r_err)

        self._health_reports = reports
        self._last_scan_time = datetime.now(timezone.utc).isoformat()
        return reports

    async def check_server(self, server_name: str) -> dict[str, Any]:
        """Perform a comprehensive health check on a single server."""
        runtime = self._conn_mgr.get_runtime(server_name)
        config = self._registry.get_config(server_name)

        if runtime is None:
            return {
                "server_name": server_name,
                "status": "STOPPED",
                "healthy": not (config.required if config else False),
                "session_active": False,
                "error": "Runtime not initialized",
                "last_check": datetime.now(timezone.utc).isoformat(),
            }

        session_active = runtime.session is not None
        status = runtime.status.value
        is_healthy = runtime.status in (ServerStatus.HEALTHY, ServerStatus.DEGRADED)

        # MCP ping if session active
        ping_ok = True
        if session_active and hasattr(runtime.session, "send_ping"):
            try:
                await asyncio.wait_for(runtime.session.send_ping(), timeout=3.0)
            except Exception:
                ping_ok = False
                is_healthy = False
                runtime.mark_degraded("MCP ping failed")

        tool_count = len(runtime.tool_names)
        if self._tools:
            tool_count = len(self._tools.get_server_tools(server_name))

        report = {
            "server_name": server_name,
            "status": status,
            "healthy": is_healthy and ping_ok,
            "session_active": session_active,
            "ping_ok": ping_ok,
            "generation": runtime.generation,
            "in_flight_calls": runtime.in_flight_calls,
            "tool_count": tool_count,
            "restart_count": runtime.restart_count,
            "last_error": runtime.last_error,
            "last_check": datetime.now(timezone.utc).isoformat(),
        }

        # Update runtime last_health_check
        runtime.last_health_check = report["last_check"]
        return report

    def report_health(self) -> dict[str, Any]:
        """Return the latest health report summary."""
        total = len(self._health_reports)
        healthy = sum(1 for r in self._health_reports.values() if r.get("healthy", False))
        return {
            "last_scan": self._last_scan_time,
            "total_servers": total,
            "healthy_servers": healthy,
            "degraded_or_failed": total - healthy,
            "reports": dict(self._health_reports),
        }
