"""
Async Session Manager for Zye Master MCP Orchestrator (Day 15).
Manages individual MCP server runtimes, stdio subprocess lifecycles,
asynchronous ClientSession contexts, and health tracking across the ecosystem.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from contextlib import AsyncExitStack
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from zye_orchestrator.server_runtime import MCPConnectionManager, MCPServerRuntime, ServerStatus

logger = logging.getLogger("zye.orchestrator.session_manager")


class MCPSessionState(str, Enum):
    """Lifecycle states for managed MCP sessions."""
    STOPPED = "STOPPED"
    STARTING = "STARTING"
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    RESTARTING = "RESTARTING"
    FAILED = "FAILED"
    SHUTTING_DOWN = "SHUTTING_DOWN"


class MCPSessionManager:
    """
    Centralized manager for MCP subprocess sessions, health monitoring,
    reconnections, and leak-free resource release.
    """

    def __init__(self, connection_manager: Optional[MCPConnectionManager] = None) -> None:
        self._conn_mgr = connection_manager or MCPConnectionManager()
        self._session_locks: dict[str, asyncio.Lock] = {}
        self._shutting_down = False

    @property
    def connection_manager(self) -> MCPConnectionManager:
        return self._conn_mgr

    @property
    def runtimes(self) -> dict[str, MCPServerRuntime]:
        return self._conn_mgr.runtimes

    def _get_lock(self, server_name: str) -> asyncio.Lock:
        if server_name not in self._session_locks:
            self._session_locks[server_name] = asyncio.Lock()
        return self._session_locks[server_name]

    def get_session_state(self, server_name: str) -> MCPSessionState:
        """Query current state of a server runtime."""
        rt = self._conn_mgr.get_runtime(server_name)
        if not rt:
            return MCPSessionState.STOPPED
        status_val = rt.status.value if hasattr(rt.status, "value") else str(rt.status)
        if status_val == "HEALTHY":
            return MCPSessionState.HEALTHY
        if status_val == "STARTING":
            return MCPSessionState.STARTING
        if status_val == "DEGRADED":
            return MCPSessionState.DEGRADED
        if status_val in ("RELOADING", "RESTARTING"):
            return MCPSessionState.RESTARTING
        if status_val in ("STOPPING", "SHUTTING_DOWN"):
            return MCPSessionState.SHUTTING_DOWN
        if status_val == "FAILED":
            return MCPSessionState.FAILED
        return MCPSessionState.STOPPED

    async def initialize_session(
        self,
        server_name: str,
        command: str,
        args: list[str],
        env: dict[str, str] | None = None,
        timeout: float = 25.0,
    ) -> MCPServerRuntime:
        """
        Start stdio subprocess and initialize MCP session with concurrency protection.
        Prevents duplicate session initialization.
        """
        if self._shutting_down:
            rt = self._conn_mgr.ensure_runtime(server_name)
            rt.mark_failed("Session manager is shutting down")
            return rt

        async with self._get_lock(server_name):
            existing = self._conn_mgr.get_runtime(server_name)
            if existing and existing.is_available() and existing.session is not None:
                logger.debug("Session for '%s' already healthy and active.", server_name)
                return existing

            logger.info("Initializing MCP session for '%s'...", server_name)
            runtime = await self._conn_mgr.start_server(
                server_name=server_name,
                command=command,
                args=args,
                env=env,
                timeout=timeout,
            )
            return runtime

    async def close_session(self, server_name: str) -> bool:
        """Safely drain in-flight calls and terminate server session context."""
        async with self._get_lock(server_name):
            logger.info("Closing session for '%s'...", server_name)
            return await self._conn_mgr.stop_server(server_name)

    async def reconnect_session(
        self,
        server_name: str,
        command: str,
        args: list[str],
        env: dict[str, str] | None = None,
        timeout: float = 25.0,
    ) -> MCPServerRuntime:
        """Perform controlled restart of a crashed or degraded server."""
        async with self._get_lock(server_name):
            logger.warning("Reconnecting session for '%s'...", server_name)
            rt = self._conn_mgr.ensure_runtime(server_name)
            rt.status = ServerStatus.STARTING
            await self._conn_mgr.stop_server(server_name)
            new_rt = await self._conn_mgr.start_server(
                server_name=server_name,
                command=command,
                args=args,
                env=env,
                timeout=timeout,
            )
            return new_rt

    async def shutdown_all(self) -> dict[str, bool]:
        """Gracefully terminate all running MCP server sessions."""
        self._shutting_down = True
        results = {}
        for name in list(self._conn_mgr.runtimes.keys()):
            try:
                ok = await self.close_session(name)
                results[name] = ok
            except Exception as e:
                logger.error("Error stopping session '%s': %s", name, e)
                results[name] = False
        return results

    def get_all_session_diagnostics(self) -> list[dict[str, Any]]:
        """Return diagnostic health records across all registered runtimes."""
        records = []
        for name, rt in self._conn_mgr.runtimes.items():
            records.append({
                "server_name": name,
                "status": self.get_session_state(name).value,
                "session_active": rt.session is not None,
                "generation": rt.generation,
                "in_flight_calls": rt.in_flight_calls,
                "restart_count": rt.restart_count,
                "last_error": rt.last_error,
                "last_health_check": rt.last_health_check,
            })
        return records
