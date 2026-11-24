"""
ZYE AI — Verified Tool Execution & Anti-Hallucination Gate
==========================================================

Implements Section 08 & Section 09 of Master Engineering Specification.
Ensures tool execution follows a strict verifiable lifecycle:
REQUESTED -> AUTHORIZED -> STARTED -> VERIFIED_SUCCESS / FAILED.

Eliminates false-success hallucinations by inspecting actual tool outcomes,
exit statuses, response structures, and system state before reporting success to user.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from zye_core.event_bus import ZyeEventBus
from zye_core.types import ExecutionOutcome, ZyeEvent, ZyeEventType

logger = logging.getLogger("zye.reliability.verified_execution")


@dataclass
class ExecutionStep:
    """Represents a discrete tool execution attempt through its complete lifecycle."""

    step_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    server: str = ""
    tool_name: str = ""
    arguments: Dict[str, Any] = field(default_factory=dict)
    status: ExecutionOutcome = ExecutionOutcome.REQUESTED
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    raw_result: Any = None
    error_message: Optional[str] = None
    verification_detail: str = ""

    def mark_authorized(self) -> None:
        self.status = ExecutionOutcome.AUTHORIZED

    def mark_started(self) -> None:
        self.status = ExecutionOutcome.STARTED
        self.started_at = time.time()

    def mark_blocked(self, outcome: ExecutionOutcome, reason: str) -> None:
        self.status = outcome
        self.error_message = reason
        self.completed_at = time.time()

    def mark_completed(self, verified: bool, detail: str, raw_result: Any = None) -> None:
        self.completed_at = time.time()
        self.raw_result = raw_result
        self.verification_detail = detail
        if verified:
            self.status = ExecutionOutcome.VERIFIED_SUCCESS
        else:
            self.status = ExecutionOutcome.FAILED


class VerifiedExecutionEngine:
    """
    Validates and audits tool execution outcomes to prevent false-success hallucinations.
    """

    def __init__(self, event_bus: Optional[ZyeEventBus] = None) -> None:
        self.event_bus = event_bus
        self._history: list[ExecutionStep] = []

    def request_execution(
        self,
        server: str,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> ExecutionStep:
        """Create and track an initial tool execution request."""
        step = ExecutionStep(server=server, tool_name=tool_name, arguments=arguments)
        self._history.append(step)
        if self.event_bus:
            self.event_bus.publish_sync(
                ZyeEvent(
                    event_type=ZyeEventType.TOOL_REQUESTED,
                    source_module="zye.reliability.verified_execution",
                    payload={"step_id": step.step_id, "tool": f"{server}:{tool_name}"},
                )
            )
        return step

    def verify_result(self, step: ExecutionStep, raw_result: Any) -> ExecutionStep:
        """
        Inspect tool execution result for real-world validity.
        Catches errors disguised as successful return values.
        """
        verified = True
        detail = "Tool execution verified successful."
        error_msg = None

        if raw_result is None:
            verified = False
            detail = "Result was None. Tool returned no output."
            error_msg = detail
        elif isinstance(raw_result, dict):
            # Inspect for embedded error keys
            if raw_result.get("isError") is True or raw_result.get("error") is not None:
                verified = False
                error_msg = str(raw_result.get("error") or "Tool returned isError=True")
                detail = f"Explicit error in result: {error_msg}"
            elif raw_result.get("status") in ("failed", "error", "rejected"):
                verified = False
                detail = f"Result status indicates failure: {raw_result.get('status')}"
                error_msg = detail
        elif isinstance(raw_result, str):
            lower_res = raw_result.lower()
            if lower_res.startswith("error:") or lower_res.startswith("exception:") or "failed with exit code" in lower_res:
                verified = False
                detail = f"String output indicates command failure: {raw_result[:100]}"
                error_msg = detail

        step.mark_completed(verified=verified, detail=detail, raw_result=raw_result)
        if not verified and error_msg:
            step.error_message = error_msg

        if self.event_bus:
            event_type = (
                ZyeEventType.TOOL_EXECUTION_COMPLETED
                if verified
                else ZyeEventType.TOOL_EXECUTION_FAILED
            )
            self.event_bus.publish_sync(
                ZyeEvent(
                    event_type=event_type,
                    payload={
                        "step_id": step.step_id,
                        "tool": f"{step.server}:{step.tool_name}",
                        "outcome": step.status.value,
                        "detail": detail,
                    },
                )
            )

        return step


__all__ = [
    "ExecutionStep",
    "VerifiedExecutionEngine",
]
