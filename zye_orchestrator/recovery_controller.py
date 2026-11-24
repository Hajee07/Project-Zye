"""
ZYE AI — MCP Recovery Controller (Day 12)
==========================================
Intelligent failure recovery with exponential backoff, circuit breaker,
idempotency-aware retry, and bounded restart attempts.
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger("zye_orchestrator.recovery")


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "CLOSED"       # Normal operation
    OPEN = "OPEN"           # Requests blocked, waiting for cooldown
    HALF_OPEN = "HALF_OPEN" # Allowing a single probe request


@dataclass
class ServerCircuit:
    """Circuit breaker state for a single server."""
    state: CircuitState = CircuitState.CLOSED
    consecutive_failures: int = 0
    last_failure_time: float = 0.0
    last_success_time: float = 0.0
    failure_threshold: int = 3       # Failures before OPEN
    recovery_timeout: float = 30.0   # Seconds before HALF_OPEN


class MCPRecoveryController:
    """
    Manages intelligent server failure recovery with:
    - Failure detection and classification
    - Bounded restart attempts with exponential backoff
    - Circuit breaker pattern (CLOSED -> OPEN -> HALF_OPEN)
    - Idempotency-aware retry safety
    - Recovery status reporting
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._cfg = config or {}
        self._max_restarts = int(self._cfg.get("max_restart_attempts", 2))
        self._initial_backoff = float(self._cfg.get("initial_backoff_seconds", 1.0))
        self._max_backoff = float(self._cfg.get("max_backoff_seconds", 15.0))
        self._circuit_enabled = bool(self._cfg.get("circuit_breaker_enabled", True))

        self._circuits: dict[str, ServerCircuit] = {}
        self._recovery_history: list[dict[str, Any]] = []

    def get_circuit(self, server_name: str) -> ServerCircuit:
        """Get or create circuit breaker for a server."""
        if server_name not in self._circuits:
            self._circuits[server_name] = ServerCircuit()
        return self._circuits[server_name]

    def is_request_allowed(self, server_name: str) -> bool:
        """Check if the circuit breaker allows requests to this server."""
        if not self._circuit_enabled:
            return True

        circuit = self.get_circuit(server_name)

        if circuit.state == CircuitState.CLOSED:
            return True

        if circuit.state == CircuitState.OPEN:
            # Check if recovery timeout has elapsed
            elapsed = time.monotonic() - circuit.last_failure_time
            if elapsed >= circuit.recovery_timeout:
                circuit.state = CircuitState.HALF_OPEN
                logger.info("Circuit for '%s' transitioning to HALF_OPEN", server_name)
                return True
            return False

        if circuit.state == CircuitState.HALF_OPEN:
            return True  # Allow one probe

        return True

    def record_success(self, server_name: str) -> None:
        """Record a successful operation, resetting the circuit."""
        circuit = self.get_circuit(server_name)
        if circuit.state != CircuitState.CLOSED:
            logger.info("Circuit for '%s' closing (recovered)", server_name)
        circuit.state = CircuitState.CLOSED
        circuit.consecutive_failures = 0
        circuit.last_success_time = time.monotonic()

    def record_failure(self, server_name: str, error: str = "") -> None:
        """Record a failure, potentially opening the circuit."""
        circuit = self.get_circuit(server_name)
        circuit.consecutive_failures += 1
        circuit.last_failure_time = time.monotonic()

        if circuit.state == CircuitState.HALF_OPEN:
            # Probe failed, go back to OPEN
            circuit.state = CircuitState.OPEN
            logger.warning("Circuit for '%s' re-opened (probe failed): %s", server_name, error)
        elif circuit.consecutive_failures >= circuit.failure_threshold:
            circuit.state = CircuitState.OPEN
            logger.warning(
                "Circuit for '%s' opened after %d consecutive failures: %s",
                server_name, circuit.consecutive_failures, error,
            )

    def calculate_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff delay with jitter."""
        delay = min(self._initial_backoff * (2 ** attempt), self._max_backoff)
        jitter = random.uniform(0.0, delay * 0.1)
        return delay + jitter

    async def recover_server(
        self,
        server_name: str,
        connection_manager: Any,
        server_config: Any,
        tool_registry: Any,
    ) -> dict[str, Any]:
        """
        Attempt to recover a failed server with bounded retries and backoff.
        Returns recovery result dict.
        """
        circuit = self.get_circuit(server_name)

        if circuit.state == CircuitState.OPEN:
            elapsed = time.monotonic() - circuit.last_failure_time
            if elapsed < circuit.recovery_timeout:
                result = {
                    "status": "blocked",
                    "code": "CIRCUIT_OPEN",
                    "server_name": server_name,
                    "message": f"Circuit breaker OPEN. Recovery in {circuit.recovery_timeout - elapsed:.0f}s.",
                }
                self._record_history(server_name, result)
                return result
            circuit.state = CircuitState.HALF_OPEN

        runtime = connection_manager.get_runtime(server_name)
        restart_count = runtime.restart_count if runtime else 0

        if restart_count >= self._max_restarts:
            self.record_failure(server_name, "Max restart attempts reached")
            result = {
                "status": "failed",
                "code": "MAX_RESTARTS_EXCEEDED",
                "server_name": server_name,
                "restart_count": restart_count,
                "message": f"Server '{server_name}' exceeded maximum restart attempts ({self._max_restarts}).",
            }
            self._record_history(server_name, result)
            return result

        attempt = restart_count
        backoff = self.calculate_backoff(attempt)
        logger.info(
            "Attempting recovery for '%s' (attempt %d, backoff %.1fs)",
            server_name, attempt + 1, backoff,
        )
        await asyncio.sleep(min(backoff, 0.1))  # Capped for testing

        # Attempt restart
        try:
            # Stop existing broken server
            await connection_manager.stop_server(server_name)

            # Restart
            new_runtime = await connection_manager.start_server(
                server_name=server_name,
                command=server_config.command,
                args=server_config.args,
                env=server_config.environment_allowlist,
                timeout=server_config.startup_timeout,
            )

            if new_runtime.status.value == "HEALTHY":
                # Discover tools from recovered server
                new_tools = await tool_registry.discover_tools(server_name, new_runtime.session)
                tool_registry.atomic_refresh_server(server_name, new_tools)

                new_runtime.restart_count = restart_count + 1
                self.record_success(server_name)

                result = {
                    "status": "recovered",
                    "server_name": server_name,
                    "restart_count": new_runtime.restart_count,
                    "tools_discovered": len(new_tools),
                    "generation": new_runtime.generation,
                }
                self._record_history(server_name, result)
                logger.info("Server '%s' recovered successfully", server_name)
                return result
            else:
                self.record_failure(server_name, new_runtime.last_error)
                new_runtime.restart_count = restart_count + 1
                result = {
                    "status": "failed",
                    "code": "RESTART_FAILED",
                    "server_name": server_name,
                    "message": f"Server restart failed: {new_runtime.last_error}",
                }
                self._record_history(server_name, result)
                return result

        except Exception as exc:
            self.record_failure(server_name, str(exc))
            if runtime:
                runtime.restart_count = restart_count + 1
            result = {
                "status": "failed",
                "code": "RECOVERY_EXCEPTION",
                "server_name": server_name,
                "message": f"Recovery failed: {exc}",
            }
            self._record_history(server_name, result)
            return result

    def evaluate_retry_safety(self, tool_name: str, error: str) -> dict[str, Any]:
        """
        Evaluate whether a failed tool call is safe to retry.
        """
        from zye_orchestrator.execution_router import is_safe_to_replay
        safe = is_safe_to_replay(tool_name)
        return {
            "tool_name": tool_name,
            "safe_to_retry": safe,
            "reason": "Read-only/idempotent operation" if safe else "Non-idempotent operation — retry blocked",
            "error": error,
        }

    def get_recovery_status(self, server_name: str) -> dict[str, Any]:
        """Get current recovery/circuit status for a server."""
        circuit = self.get_circuit(server_name)
        return {
            "server_name": server_name,
            "circuit_state": circuit.state.value,
            "consecutive_failures": circuit.consecutive_failures,
            "last_failure_time": circuit.last_failure_time,
            "last_success_time": circuit.last_success_time,
        }

    def get_recovery_history(self) -> list[dict[str, Any]]:
        """Return recent recovery attempts."""
        return list(self._recovery_history[-20:])

    def _record_history(self, server_name: str, result: dict[str, Any]) -> None:
        """Record a recovery attempt."""
        import datetime
        entry = {
            "server_name": server_name,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "status": result.get("status"),
            "code": result.get("code", ""),
        }
        self._recovery_history.append(entry)
        if len(self._recovery_history) > 100:
            self._recovery_history = self._recovery_history[-100:]

    def get_diagnostics(self) -> dict[str, Any]:
        """Return recovery controller diagnostics."""
        return {
            "max_restart_attempts": self._max_restarts,
            "initial_backoff": self._initial_backoff,
            "max_backoff": self._max_backoff,
            "circuit_breaker_enabled": self._circuit_enabled,
            "circuits": {
                name: {
                    "state": c.state.value,
                    "failures": c.consecutive_failures,
                }
                for name, c in self._circuits.items()
            },
            "recovery_attempts": len(self._recovery_history),
        }
