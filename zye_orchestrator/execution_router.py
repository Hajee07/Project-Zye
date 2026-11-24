"""
ZYE AI — MCP Tool Execution Router (Day 12)
=============================================
Routes tool calls to correct servers, enforces Negative Brain pre-mortem
audits, validates arguments, checks registry generation, and handles results.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

logger = logging.getLogger("zye_orchestrator.execution_router")

# Operations requiring Negative Pre-Mortem audit
FILE_SYSTEM_OPERATIONS = frozenset({
    "patch_own_code", "rollback_code_backup", "create_source_backup",
    "delete_file", "delete_directory", "move_file", "copy_file",
    "write_file", "create_file",
})

SYSTEM_OPERATIONS = frozenset({
    "execute_emergency_reflex", "set_mission_mode",
    "shutdown_windows", "restart_windows", "cyber_lockdown",
})

PREMORTEM_TOOLS = frozenset({
    "run_negative_premortem_brain", "compare_and_decide_solutions",
    "autonomous_identify_problems",
})

NON_IDEMPOTENT_OPERATIONS = frozenset({
    "send_whatsapp_message", "send_email", "delete_file", "delete_directory",
    "execute_payment", "make_purchase", "shutdown_windows", "restart_windows",
    "drop_database", "patch_own_code", "execute_emergency_reflex",
    "cyber_lockdown", "set_mission_mode",
})

READ_ONLY_PREFIXES = ("read_", "list_", "get_", "inspect_", "check_", "search_", "preview_")


def is_safe_to_replay(tool_name: str) -> bool:
    """Return True if tool is idempotent and safe to automatically replay."""
    norm = tool_name.lower().strip()
    for risky in NON_IDEMPOTENT_OPERATIONS:
        if risky in norm:
            return False
    return any(norm.startswith(p) for p in READ_ONLY_PREFIXES)


class ZyeMCPExecutionRouter:
    """
    Routes tool calls to the correct MCP server session.
    Enforces Negative Brain pre-mortem audits for file/system operations.
    Validates arguments, checks server health, and handles results.
    """

    def __init__(
        self,
        tool_registry: Any,
        connection_manager: Any,
        premortem_brain: Any | None = None,
        execution_gate: Any | None = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        self._tool_registry = tool_registry
        self._conn_mgr = connection_manager
        self._premortem = premortem_brain
        self._gate = execution_gate
        self._cfg = config or {}

        # Feature flags
        self._premortem_for_fs = self._cfg.get("negative_premortem_required_for_file_system", True)
        self._premortem_for_sys = self._cfg.get("negative_premortem_required_for_system_tools", True)
        self._block_if_premortem_unavailable = self._cfg.get("block_if_premortem_unavailable", True)
        self._revalidate = self._cfg.get("revalidate_before_execution", True)

    async def route_tool_call(
        self,
        public_tool_name: str,
        arguments: dict[str, Any],
        registry_generation: int | None = None,
    ) -> dict[str, Any]:
        """
        Route a tool call through the full execution pipeline:
        1. Resolve route
        2. Check registry generation
        3. Check server health
        4. Apply pre-mortem enforcement
        5. Execute via MCP session
        6. Return result
        """
        # Step 1: Resolve routing
        route = self._tool_registry.get_tool_route(public_tool_name)
        if route is None:
            return {
                "status": "error",
                "code": "TOOL_NOT_FOUND",
                "tool_name": public_tool_name,
                "message": f"No server registered for tool '{public_tool_name}'.",
            }

        server_name, original_tool_name = route

        # Step 2: Check registry generation (stale call detection)
        if registry_generation is not None and not self._tool_registry.is_generation_current(registry_generation):
            return {
                "status": "error",
                "code": "STALE_REGISTRY",
                "tool_name": public_tool_name,
                "message": "Tool registry has been updated. Please re-plan with the current tool list.",
                "current_generation": self._tool_registry.generation,
            }

        # Step 3: Check server health
        runtime = self._conn_mgr.get_runtime(server_name)
        if runtime is None or not runtime.is_available():
            return {
                "status": "error",
                "code": "SERVER_UNAVAILABLE",
                "tool_name": public_tool_name,
                "server_name": server_name,
                "message": f"Server '{server_name}' is not available.",
            }

        # Step 4: Negative Pre-Mortem enforcement
        premortem_result = await self._enforce_premortem(public_tool_name, arguments)
        if premortem_result is not None:
            return premortem_result

        # Step 5: Execute via MCP session
        return await self.execute_mcp_tool(
            server_name, original_tool_name, public_tool_name, arguments, runtime,
        )

    async def execute_mcp_tool(
        self,
        server_name: str,
        original_tool_name: str,
        public_tool_name: str,
        arguments: dict[str, Any],
        runtime: Any,
    ) -> dict[str, Any]:
        """Execute a tool call on the MCP server session."""
        runtime.increment_in_flight()
        try:
            session = runtime.session
            if session is None:
                return {
                    "status": "error",
                    "code": "SESSION_LOST",
                    "tool_name": public_tool_name,
                    "message": f"Session for '{server_name}' is no longer active.",
                }

            # Execute via MCP SDK call_tool
            try:
                result = await asyncio.wait_for(
                    session.call_tool(original_tool_name, arguments=arguments),
                    timeout=self._cfg.get("tool_timeout", 30.0),
                )
            except asyncio.TimeoutError:
                runtime.mark_degraded(f"Tool '{original_tool_name}' timed out")
                return {
                    "status": "error",
                    "code": "TOOL_TIMEOUT",
                    "tool_name": public_tool_name,
                    "server_name": server_name,
                    "message": f"Tool '{public_tool_name}' exceeded timeout.",
                    "idempotent": is_safe_to_replay(original_tool_name),
                }
            except (ConnectionError, BrokenPipeError, EOFError) as exc:
                runtime.mark_failed(str(exc))
                return {
                    "status": "error",
                    "code": "TRANSPORT_FAILURE",
                    "tool_name": public_tool_name,
                    "server_name": server_name,
                    "message": f"Transport failure on '{server_name}': {exc}",
                }
            except Exception as exc:
                return {
                    "status": "error",
                    "code": "TOOL_ERROR",
                    "tool_name": public_tool_name,
                    "message": str(exc),
                }

            # Parse MCP result
            return self._parse_mcp_result(result, public_tool_name)

        finally:
            runtime.decrement_in_flight()

    def _parse_mcp_result(self, result: Any, tool_name: str) -> dict[str, Any]:
        """Parse an MCP CallToolResult into a normalized result dict preserving error semantics."""
        try:
            # Check for error indicator across both MCP v2 (is_error) and v1 wire (isError)
            is_error = False
            if hasattr(result, "is_error"):
                is_error = bool(result.is_error)
            elif hasattr(result, "isError"):
                is_error = bool(result.isError)
            elif isinstance(result, dict):
                is_error = bool(result.get("is_error", result.get("isError", False)))

            content = getattr(result, "content", [])
            if isinstance(result, dict) and not content:
                content = result.get("content", [])

            # Extract text content and structured blocks
            text_parts = []
            for item in (content or []):
                if hasattr(item, "text"):
                    text_parts.append(item.text)
                elif isinstance(item, dict) and "text" in item:
                    text_parts.append(item["text"])

            combined = "\n".join(text_parts) if text_parts else ""

            if is_error:
                return {
                    "status": "error",
                    "code": "TOOL_RETURNED_ERROR",
                    "tool_name": tool_name,
                    "message": combined or "Tool returned an error",
                    "is_error": True,
                }

            # Try to parse as JSON for structured results
            if combined:
                try:
                    import json
                    parsed = json.loads(combined)
                    if isinstance(parsed, dict):
                        # Preserve existing error / failure / blocked statuses
                        if "status" not in parsed:
                            if parsed.get("is_error") or parsed.get("isError") or "error" in parsed:
                                parsed["status"] = "error"
                            else:
                                parsed["status"] = "success"
                        return parsed
                except (ValueError, TypeError):
                    pass

            return {
                "status": "success",
                "tool_name": tool_name,
                "data": combined,
            }

        except Exception as exc:
            return {
                "status": "error",
                "code": "RESULT_PARSE_ERROR",
                "tool_name": tool_name,
                "message": f"Failed to parse tool result: {exc}",
            }

    async def _enforce_premortem(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any] | None:
        """
        Enforce Negative Pre-Mortem audit for protected operations.
        Returns None if allowed, error dict if blocked.
        Pre-mortem tools are exempt from recursive auditing.
        """
        norm_name = tool_name.lower().strip()

        # Pre-mortem tools are exempt from recursive audit
        if norm_name in PREMORTEM_TOOLS or any(norm_name == t for t in PREMORTEM_TOOLS):
            return None

        needs_audit = False
        if self._premortem_for_fs and any(op in norm_name for op in FILE_SYSTEM_OPERATIONS):
            needs_audit = True
        if self._premortem_for_sys and any(op in norm_name for op in SYSTEM_OPERATIONS):
            needs_audit = True

        if not needs_audit:
            return None

        # Check if Execution Gate is available
        if self._gate is not None:
            try:
                gate_eval = await self._gate.evaluate(tool_name=tool_name, tool_args=arguments)
                if not gate_eval.get("allowed", False):
                    return {
                        "status": "BLOCKED_BY_EXECUTION_GATE",
                        "tool_name": tool_name,
                        "reason": gate_eval.get("reason", "Execution gate denied"),
                        "approval_token": gate_eval.get("approval_token"),
                        "risk_class": gate_eval.get("risk_class"),
                        "requires_confirmation": gate_eval.get("requires_confirmation", False),
                    }
            except Exception as exc:
                if self._block_if_premortem_unavailable:
                    return {
                        "status": "BLOCKED_PREMORTEM_UNAVAILABLE",
                        "tool_name": tool_name,
                        "message": f"Execution gate failed: {exc}. Protected operation blocked.",
                    }

        elif self._block_if_premortem_unavailable:
            return {
                "status": "BLOCKED_PREMORTEM_UNAVAILABLE",
                "tool_name": tool_name,
                "message": "Negative Brain / Execution Gate is not available. Protected operation blocked.",
            }

        return None

    def get_diagnostics(self) -> dict[str, Any]:
        """Return execution router diagnostics."""
        return {
            "premortem_for_filesystem": self._premortem_for_fs,
            "premortem_for_system": self._premortem_for_sys,
            "block_if_premortem_unavailable": self._block_if_premortem_unavailable,
            "revalidate_before_execution": self._revalidate,
            "file_system_operations_count": len(FILE_SYSTEM_OPERATIONS),
            "system_operations_count": len(SYSTEM_OPERATIONS),
            "non_idempotent_count": len(NON_IDEMPOTENT_OPERATIONS),
        }
