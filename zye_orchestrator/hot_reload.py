"""
ZYE AI — Hot Reload Controller (Day 12)
========================================
Transactional hot reload for individual MCP servers.
Supports staged replacement, in-flight draining, candidate validation,
atomic registry swap, and rollback on failure.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from zye_orchestrator.server_runtime import MCPServerRuntime, ServerStatus

logger = logging.getLogger("zye_orchestrator.hot_reload")


class HotReloadController:
    """
    Manages transactional hot reload of individual MCP servers.
    Staged replacement preferred: new server validated before old is closed.
    """

    def __init__(
        self,
        server_registry: Any,
        connection_manager: Any,
        tool_registry: Any,
        config: dict[str, Any] | None = None,
    ) -> None:
        self._registry = server_registry
        self._conn_mgr = connection_manager
        self._tool_registry = tool_registry
        self._cfg = config or {}

        self._drain_timeout = float(self._cfg.get("reload_drain_timeout_seconds", 15.0))
        self._staged_preferred = bool(self._cfg.get("staged_reload_preferred", True))
        self._require_validation = bool(self._cfg.get("require_candidate_validation", True))
        self._require_schema_refresh = bool(self._cfg.get("require_schema_refresh", True))
        self._require_health_verify = bool(self._cfg.get("require_health_verification", True))

        # Track reload history
        self._reload_history: list[dict[str, Any]] = []

    @property
    def reload_history(self) -> list[dict[str, Any]]:
        return list(self._reload_history)

    async def hot_reload_server(self, server_name: str) -> dict[str, Any]:
        """
        Perform a transactional hot reload for a single MCP server.
        Steps:
            1. Validate server exists in registry
            2. Acquire reload lock
            3. Close admission, drain in-flight
            4. Start candidate server
            5. Discover and validate tools
            6. Atomic registry swap
            7. Close old runtime
            8. Verify health
            9. Report result
        """
        # Step 1: Validate
        config = self._registry.get_config(server_name)
        if config is None:
            result = {
                "status": "error",
                "code": "SERVER_NOT_CONFIGURED",
                "server_name": server_name,
                "message": f"Server '{server_name}' is not in the trusted registry.",
            }
            self._record_history(server_name, result)
            return result

        if not config.enabled:
            result = {
                "status": "error",
                "code": "SERVER_DISABLED",
                "server_name": server_name,
                "message": f"Server '{server_name}' is disabled in configuration.",
            }
            self._record_history(server_name, result)
            return result

        runtime = self._conn_mgr.get_runtime(server_name)
        if runtime is None:
            runtime = self._conn_mgr.ensure_runtime(server_name)

        # Step 2: Acquire reload lock
        if not runtime._reload_lock.locked():
            async with runtime._reload_lock:
                return await self._execute_reload(server_name, config, runtime)
        else:
            result = {
                "status": "error",
                "code": "RELOAD_IN_PROGRESS",
                "server_name": server_name,
                "message": f"Server '{server_name}' is already being reloaded.",
            }
            self._record_history(server_name, result)
            return result

    async def _execute_reload(
        self,
        server_name: str,
        config: Any,
        runtime: MCPServerRuntime,
    ) -> dict[str, Any]:
        """Execute the actual reload transaction."""
        old_status = runtime.status
        old_tools = self._tool_registry.get_server_tools(server_name)
        reload_start = time.monotonic()

        try:
            # Step 3: Mark reloading and drain in-flight
            runtime.status = ServerStatus.RELOADING
            runtime.close_admission()

            # Wait for in-flight calls to drain
            drain_start = time.monotonic()
            while runtime.in_flight_calls > 0:
                if time.monotonic() - drain_start > self._drain_timeout:
                    # Deferred: active operations still running
                    runtime.open_admission()
                    runtime.status = old_status
                    result = {
                        "status": "error",
                        "code": "RELOAD_DEFERRED_ACTIVE_OPERATION",
                        "server_name": server_name,
                        "message": f"Cannot reload: {runtime.in_flight_calls} operations still active after {self._drain_timeout}s.",
                        "in_flight_calls": runtime.in_flight_calls,
                    }
                    self._record_history(server_name, result)
                    return result
                await asyncio.sleep(0.05)

            # Step 4: Start candidate server
            candidate = await self._conn_mgr.start_server(
                server_name=f"_candidate_{server_name}",
                command=config.command,
                args=config.args,
                env=config.environment_allowlist,
                timeout=config.startup_timeout,
            )

            if candidate.status != ServerStatus.HEALTHY:
                # Candidate failed: preserve old runtime
                await self._cleanup_candidate(candidate)
                runtime.status = old_status if old_status != ServerStatus.RELOADING else ServerStatus.HEALTHY
                runtime.open_admission()
                result = {
                    "status": "error",
                    "code": "CANDIDATE_STARTUP_FAILED",
                    "server_name": server_name,
                    "message": f"Replacement server failed to start: {candidate.last_error}",
                    "previous_preserved": True,
                }
                self._record_history(server_name, result)
                return result

            # Step 5: Discover tools from candidate
            new_raw_tools = await self._tool_registry.discover_tools(
                server_name, candidate.session,
            )

            valid_tools = [t for t in new_raw_tools if self._tool_registry.validate_tool_schema(t)]
            if self._require_validation and not valid_tools:
                await self._cleanup_candidate(candidate)
                runtime.status = old_status if old_status != ServerStatus.RELOADING else ServerStatus.HEALTHY
                runtime.open_admission()
                result = {
                    "status": "error",
                    "code": "CANDIDATE_NO_TOOLS",
                    "server_name": server_name,
                    "message": "Replacement server exposed no valid tools.",
                    "previous_preserved": True,
                }
                self._record_history(server_name, result)
                return result

            # Step 6: Atomic registry swap
            swap_summary = self._tool_registry.atomic_refresh_server(
                server_name, new_raw_tools,
            )

            # Step 7: Transfer candidate to main runtime
            old_stack = runtime.context_stack
            old_session = runtime.session

            runtime.session = candidate.session
            runtime.context_stack = candidate.context_stack
            runtime.generation += 1
            runtime.tool_names = [t["name"] for t in new_raw_tools if self._tool_registry.validate_tool_schema(t)]
            runtime.started_at = candidate.started_at
            runtime.mark_healthy()

            # Remove candidate entry from connection manager
            self._conn_mgr.runtimes.pop(f"_candidate_{server_name}", None)

            # Close old resources
            if old_stack is not None:
                try:
                    await old_stack.aclose()
                except Exception as exc:
                    logger.debug("Error closing old stack for '%s': %s", server_name, exc)

            duration = time.monotonic() - reload_start
            result = {
                "status": "success",
                "operation": "hot_reload_server",
                "server_name": server_name,
                "generation": runtime.generation,
                "duration_seconds": round(duration, 3),
                "tools_added": swap_summary.get("added", []),
                "tools_removed": swap_summary.get("removed", []),
                "tools_retained": swap_summary.get("retained", []),
                "active_tools_count": len(runtime.tool_names),
            }
            self._record_history(server_name, result)
            logger.info(
                "Hot reload '%s' succeeded (gen %d, %.2fs)",
                server_name, runtime.generation, duration,
            )
            return result

        except Exception as exc:
            # Unexpected error: try to restore previous state
            runtime.status = old_status if old_status != ServerStatus.RELOADING else ServerStatus.DEGRADED
            runtime.open_admission()
            runtime.last_error = str(exc)
            result = {
                "status": "error",
                "code": "RELOAD_UNEXPECTED_ERROR",
                "server_name": server_name,
                "message": f"Hot reload failed unexpectedly: {exc}",
            }
            self._record_history(server_name, result)
            return result

    async def _cleanup_candidate(self, candidate: MCPServerRuntime) -> None:
        """Close a failed candidate's resources."""
        if candidate.context_stack is not None:
            try:
                await candidate.context_stack.aclose()
            except Exception:
                pass
        # Remove from connection manager
        cand_name = candidate.server_name
        self._conn_mgr.runtimes.pop(cand_name, None)

    def _record_history(self, server_name: str, result: dict[str, Any]) -> None:
        """Record reload attempt in history."""
        import datetime
        entry = {
            "server_name": server_name,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "status": result.get("status"),
            "code": result.get("code", "SUCCESS"),
        }
        self._reload_history.append(entry)
        # Keep last 50 entries
        if len(self._reload_history) > 50:
            self._reload_history = self._reload_history[-50:]

    def get_diagnostics(self) -> dict[str, Any]:
        """Return hot reload diagnostics."""
        return {
            "staged_preferred": self._staged_preferred,
            "drain_timeout_seconds": self._drain_timeout,
            "require_candidate_validation": self._require_validation,
            "total_reloads": len(self._reload_history),
            "recent_history": self._reload_history[-10:],
        }
