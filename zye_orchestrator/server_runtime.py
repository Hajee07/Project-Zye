"""
ZYE AI — MCP Server Runtime Manager (Day 12)
=============================================
Per-server lifecycle state machine, independent AsyncExitStack ownership,
in-flight call tracking, and resource cleanup.
"""

from __future__ import annotations

import asyncio
import logging
import time
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger("zye_orchestrator.runtime")


class ServerStatus(str, Enum):
    """MCP server lifecycle states."""
    STOPPED = "STOPPED"
    STARTING = "STARTING"
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    RELOADING = "RELOADING"
    STOPPING = "STOPPING"
    FAILED = "FAILED"


@dataclass
class MCPServerRuntime:
    """Runtime state for a single MCP server."""

    server_name: str
    session: Any = None                # ClientSession instance
    context_stack: AsyncExitStack | None = None
    status: ServerStatus = ServerStatus.STOPPED
    generation: int = 0
    started_at: str = ""
    last_health_check: str = ""
    last_error: str = ""
    restart_count: int = 0
    in_flight_calls: int = 0
    tool_names: list[str] = field(default_factory=list)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)
    _reload_lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)
    _admission_open: bool = True

    def is_available(self) -> bool:
        """Return True if server is accepting new requests."""
        return (
            self.status in (ServerStatus.HEALTHY, ServerStatus.DEGRADED)
            and self._admission_open
            and self.session is not None
        )

    def increment_in_flight(self) -> None:
        self.in_flight_calls += 1

    def decrement_in_flight(self) -> None:
        self.in_flight_calls = max(0, self.in_flight_calls - 1)

    def close_admission(self) -> None:
        """Stop accepting new requests (before reload/shutdown)."""
        self._admission_open = False

    def open_admission(self) -> None:
        """Resume accepting new requests."""
        self._admission_open = True

    def mark_healthy(self) -> None:
        self.status = ServerStatus.HEALTHY
        self.last_error = ""
        self.last_health_check = datetime.now(timezone.utc).isoformat()
        self.open_admission()

    def mark_failed(self, error: str) -> None:
        self.status = ServerStatus.FAILED
        self.last_error = error
        self.close_admission()

    def mark_degraded(self, reason: str) -> None:
        self.status = ServerStatus.DEGRADED
        self.last_error = reason

    def to_dict(self) -> dict[str, Any]:
        """Return serializable runtime state."""
        return {
            "server_name": self.server_name,
            "status": self.status.value,
            "session_active": self.session is not None,
            "generation": self.generation,
            "started_at": self.started_at,
            "last_health_check": self.last_health_check,
            "last_error": self.last_error,
            "restart_count": self.restart_count,
            "in_flight_calls": self.in_flight_calls,
            "tool_count": len(self.tool_names),
            "admission_open": self._admission_open,
        }


class MCPConnectionManager:
    """
    Manages real stdio MCP client connections.
    Each server gets its own AsyncExitStack, ClientSession, and subprocess.
    """

    def __init__(self) -> None:
        self._runtimes: dict[str, MCPServerRuntime] = {}

    @property
    def runtimes(self) -> dict[str, MCPServerRuntime]:
        return self._runtimes

    def get_runtime(self, server_name: str) -> MCPServerRuntime | None:
        return self._runtimes.get(server_name)

    def ensure_runtime(self, server_name: str) -> MCPServerRuntime:
        """Get or create runtime entry for a server."""
        if server_name not in self._runtimes:
            self._runtimes[server_name] = MCPServerRuntime(server_name=server_name)
        return self._runtimes[server_name]

    async def start_server(
        self,
        server_name: str,
        command: str,
        args: list[str],
        env: dict[str, str] | None = None,
        timeout: float = 20.0,
    ) -> MCPServerRuntime:
        """Start and initialize a stdio MCP server connection."""
        runtime = self.ensure_runtime(server_name)
        runtime.status = ServerStatus.STARTING

        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
        except ImportError:
            runtime.mark_failed("MCP SDK not available")
            return runtime

        stack = AsyncExitStack()
        try:
            # Build env: merge allowlisted vars with PYTHONUNBUFFERED
            merged_env = dict(env or {})
            merged_env.setdefault("PYTHONUNBUFFERED", "1")

            params = StdioServerParameters(
                command=command,
                args=args,
                env=merged_env if merged_env else None,
            )

            # Enter stdio client context
            read_stream, write_stream = await asyncio.wait_for(
                stack.enter_async_context(stdio_client(params)),
                timeout=timeout,
            )

            # Enter session context
            session = await asyncio.wait_for(
                stack.enter_async_context(ClientSession(read_stream, write_stream)),
                timeout=timeout,
            )

            # Initialize MCP protocol
            await asyncio.wait_for(session.initialize(), timeout=timeout)

            # Success: update runtime
            runtime.session = session
            runtime.context_stack = stack
            runtime.generation += 1
            runtime.started_at = datetime.now(timezone.utc).isoformat()
            runtime.mark_healthy()
            logger.info("MCP server '%s' started (gen %d)", server_name, runtime.generation)
            return runtime

        except Exception as exc:
            # Clean up failed connection
            try:
                await stack.aclose()
            except Exception:
                pass
            runtime.mark_failed(str(exc))
            logger.error("Failed to start MCP server '%s': %s", server_name, exc)
            return runtime

    async def stop_server(self, server_name: str) -> bool:
        """Stop a running MCP server and release its resources."""
        runtime = self._runtimes.get(server_name)
        if not runtime:
            return False

        runtime.status = ServerStatus.STOPPING
        runtime.close_admission()

        # Wait briefly for in-flight calls to drain (max 5s)
        drain_start = time.monotonic()
        while runtime.in_flight_calls > 0 and (time.monotonic() - drain_start < 5.0):
            await asyncio.sleep(0.05)

        # Close the context stack (session + subprocess)
        if runtime.context_stack is not None:
            try:
                await runtime.context_stack.aclose()
            except Exception as exc:
                logger.debug("Error closing server '%s': %s", server_name, exc)
            runtime.context_stack = None

        runtime.session = None
        runtime.status = ServerStatus.STOPPED
        logger.info("MCP server '%s' stopped", server_name)
        return True

    async def close_all(self) -> None:
        """Stop all servers gracefully."""
        for name in list(self._runtimes.keys()):
            await self.stop_server(name)

    def register_mock_runtime(
        self,
        server_name: str,
        tool_names: list[str],
    ) -> MCPServerRuntime:
        """Register a mock runtime for testing or offline operation."""
        runtime = self.ensure_runtime(server_name)
        runtime.session = type("MockSession", (), {"is_active": True})()
        runtime.tool_names = list(tool_names)
        runtime.generation = 1
        runtime.started_at = datetime.now(timezone.utc).isoformat()
        runtime.mark_healthy()
        return runtime
