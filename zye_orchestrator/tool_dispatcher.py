"""
Central Tool Dispatcher for Zye Master MCP Orchestrator (Day 15).
Acts as the single authoritative gateway for Gemini-requested MCP tool calls,
validating arguments against JSON schemas, enforcing Safety Gateway checks,
and bounding output size.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Callable, Coroutine, Optional

from zye_orchestrator.safety_pipeline import RiskLevel, SafetyExecutionGateway
from zye_orchestrator.tool_registry import ZyeToolRegistry

logger = logging.getLogger("zye.orchestrator.tool_dispatcher")

DEFAULT_MAX_OUTPUT_CHARS = 4000


class ZyeToolDispatcher:
    """
    Authoritative dispatcher mediating all tool invocations from Gemini.
    Rejects unregistered tools, validates schemas, routes through Safety Gateway.
    """

    def __init__(
        self,
        tool_registry: ZyeToolRegistry,
        safety_gateway: SafetyExecutionGateway,
        call_executor_fn: Callable[[str, dict[str, Any]], Coroutine[Any, Any, Any]],
        max_output_chars: int = DEFAULT_MAX_OUTPUT_CHARS,
    ) -> None:
        self._tool_registry = tool_registry
        self._safety = safety_gateway
        self._executor = call_executor_fn
        self._max_output = max_output_chars

    async def dispatch(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
        task_context: str = "",
        user_confirmed: bool = False,
        approval_token: str = "",
    ) -> dict[str, Any]:
        """
        Execute an MCP tool call through the complete 13-stage validation pipeline.
        """
        clean_args = dict(arguments or {})
        norm_name = tool_name.strip()

        # 1. Resolve server route
        route = self._tool_registry.get_tool_route(norm_name)
        if route is None:
            # Check if it exists under server-qualified or raw tool name
            all_tools = self._tool_registry.get_all_tools()
            matched = [k for k, v in all_tools.items() if v.original_name == norm_name or k == norm_name]
            if matched:
                route = self._tool_registry.get_tool_route(matched[0])
                norm_name = matched[0]

        if route is None:
            logger.warning("Rejected call to unregistered tool: '%s'", tool_name)
            return {
                "status": "ERROR",
                "code": "TOOL_NOT_FOUND",
                "tool_name": tool_name,
                "message": f"Tool '{tool_name}' is not in the trusted MCP tool registry.",
            }

        # 2. Argument validation & sanity check
        tool_entry = self._tool_registry.get_tool_entry(norm_name)
        if tool_entry and tool_entry.input_schema:
            schema = tool_entry.input_schema
            required_props = schema.get("required", [])
            for req in required_props:
                if req not in clean_args:
                    return {
                        "status": "ERROR",
                        "code": "MISSING_REQUIRED_ARGUMENT",
                        "tool_name": norm_name,
                        "message": f"Missing required parameter '{req}' for tool '{norm_name}'.",
                    }

        # 3. Identify action type and targets
        action_type = str(clean_args.get("action", norm_name))
        targets = []
        for key in ("file_path", "path", "directory_path", "target", "destination", "name"):
            if key in clean_args and clean_args[key]:
                targets.append(str(clean_args[key]))

        # 4. Route through Safety Gateway
        async def _run_tool(**kwargs: Any) -> Any:
            return await self._executor(norm_name, kwargs)

        pipeline_res = await self._safety.authorize_and_execute(
            task_description=task_context or f"Invoke {norm_name}",
            action_type=action_type,
            target_resources=targets,
            tool_name=norm_name,
            tool_args=clean_args,
            executor_fn=_run_tool,
            user_confirmed=user_confirmed,
            approval_token=approval_token,
        )

        # 5. Output bounding
        raw_output = json.dumps(pipeline_res)
        if len(raw_output) > self._max_output:
            logger.debug("Truncating tool output from %d chars to %d", len(raw_output), self._max_output)
            pipeline_res["truncated"] = True
            pipeline_res["full_length"] = len(raw_output)
            if "data" in pipeline_res and isinstance(pipeline_res["data"], str):
                pipeline_res["data"] = pipeline_res["data"][: self._max_output] + "... [TRUNCATED]"

        return pipeline_res
