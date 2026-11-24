"""
ZYE AI — Tool Loop Guard & Degenerate Cycle Prevention
======================================================

Implements Section 08 & Section 09 of Master Engineering Specification.
Adapted from OpenJarvis agent loop guard patterns to safeguard ZYE's MCP Orchestrator.
Provides:
1. Canonical tool fingerprinting (SHA-256 of sorted server:tool:arguments)
2. A-A-A repeated call detection (blocks after max_identical_calls)
3. A-B-A-B / A-B-C-A-B-C ping-pong oscillation detection
4. Turn-scoped tool call budget enforcement (max 4 per user turn)
5. Warn-before-block graceful recovery
6. Event bus publishing of loop warnings and blocks
"""

from __future__ import annotations

import hashlib
import json
import logging
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Set

from zye_core.event_bus import ZyeEventBus
from zye_core.types import ExecutionOutcome, ZyeEvent, ZyeEventType

logger = logging.getLogger("zye.reliability.tool_loop_guard")


def tool_fingerprint(server: str, tool_name: str, arguments: Any) -> str:
    """
    Generate canonical deterministic SHA-256 fingerprint for a tool invocation.
    Ensures key order in arguments does not produce duplicate false misses.
    """
    if isinstance(arguments, dict):
        try:
            norm_args = json.dumps(arguments, sort_keys=True, separators=(",", ":"))
        except Exception:
            norm_args = str(sorted(arguments.items()))
    elif isinstance(arguments, (list, tuple)):
        try:
            norm_args = json.dumps(arguments, sort_keys=True, separators=(",", ":"))
        except Exception:
            norm_args = str(arguments)
    else:
        norm_args = str(arguments)

    raw_key = f"{server.strip().lower()}:{tool_name.strip().lower()}:{norm_args}"
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:16]


@dataclass(slots=True)
class ToolLoopGuardConfig:
    """Configuration for Tool Loop Guard."""

    enabled: bool = True
    max_identical_calls: int = 3       # Max consecutive identical calls before block
    ping_pong_window: int = 6          # Window length to inspect for periodic cycling
    max_turn_budget: int = 4           # Maximum tool calls permitted within a single user turn
    poll_tool_budget: int = 8          # Relaxed budget for polling/status inspection tools
    warn_before_block: bool = True     # Emit warning on first trip before enforcing block


@dataclass(slots=True)
class ToolLoopVerdict:
    """Result of loop evaluation."""

    blocked: bool = False
    warned: bool = False
    reason: str = ""
    fingerprint: str = ""
    outcome: ExecutionOutcome = ExecutionOutcome.AUTHORIZED
    _warn_key: str = field(default="", repr=False, compare=False)


class ToolLoopGuard:
    """
    Protects Zye MCP Orchestrator and Gemini Live Tool Caller against runaway loops,
    repetitive identical calls, turn budget exhaustion, and oscillation traps.
    """

    def __init__(
        self,
        config: Optional[ToolLoopGuardConfig] = None,
        event_bus: Optional[ZyeEventBus] = None,
    ) -> None:
        self.config = config or ToolLoopGuardConfig()
        self.event_bus = event_bus

        # Tracking state
        self.turn_tool_count: int = 0
        self._call_counts: Dict[str, int] = {}
        self._tool_sequence: deque[str] = deque(maxlen=self.config.ping_pong_window * 2)
        self._per_tool_counts: Dict[str, int] = {}
        self._warned_keys: Set[str] = set()

    def reset_turn(self) -> None:
        """Reset turn-scoped tool budgets. Called at the start of each user turn."""
        self.turn_tool_count = 0
        logger.debug("ToolLoopGuard turn counter reset to 0.")

    def reset_all(self) -> None:
        """Full reset of loop detection history and counts."""
        self.turn_tool_count = 0
        self._call_counts.clear()
        self._tool_sequence.clear()
        self._per_tool_counts.clear()
        self._warned_keys.clear()
        logger.debug("ToolLoopGuard state completely cleared.")

    def check_call(
        self,
        server: str,
        tool_name: str,
        arguments: Any,
        is_polling: bool = False,
    ) -> ToolLoopVerdict:
        """
        Evaluate an outbound tool call before dispatching to MCP.
        Returns ToolLoopVerdict indicating whether the call is authorized, warned, or blocked.
        """
        if not self.config.enabled:
            return ToolLoopVerdict(blocked=False, outcome=ExecutionOutcome.AUTHORIZED)

        fp = tool_fingerprint(server, tool_name, arguments)
        qual_tool_name = f"{server}:{tool_name}"

        # 1. Turn-Scoped Tool Call Budget Enforcement
        if self.turn_tool_count >= self.config.max_turn_budget and not is_polling:
            reason = (
                f"Turn tool call budget exhausted ({self.turn_tool_count}/{self.config.max_turn_budget}). "
                f"Halting tool loop for this turn."
            )
            logger.warning(reason)
            verdict = ToolLoopVerdict(
                blocked=True,
                reason=reason,
                fingerprint=fp,
                outcome=ExecutionOutcome.LOOP_BLOCKED,
                _warn_key="turn_budget_exhausted",
            )
            return self._handle_verdict(verdict, qual_tool_name)

        # 2. Identical Tool Call Hash Tracking (A-A-A pattern)
        prior_calls = self._call_counts.get(fp, 0)
        if prior_calls >= self.config.max_identical_calls:
            reason = (
                f"Identical tool call '{qual_tool_name}' repeated {prior_calls + 1} times "
                f"(max permitted: {self.config.max_identical_calls})."
            )
            logger.warning(reason)
            verdict = ToolLoopVerdict(
                blocked=True,
                reason=reason,
                fingerprint=fp,
                outcome=ExecutionOutcome.LOOP_BLOCKED,
                _warn_key=f"identical:{fp}",
            )
            return self._handle_verdict(verdict, qual_tool_name)

        # 3. Polling Tool Budget Check
        if is_polling:
            tool_count = self._per_tool_counts.get(qual_tool_name, 0)
            if tool_count >= self.config.poll_tool_budget:
                reason = (
                    f"Polling tool '{qual_tool_name}' exceeded poll limit "
                    f"({tool_count + 1}/{self.config.poll_tool_budget})."
                )
                logger.warning(reason)
                verdict = ToolLoopVerdict(
                    blocked=True,
                    reason=reason,
                    fingerprint=fp,
                    outcome=ExecutionOutcome.LOOP_BLOCKED,
                    _warn_key=f"poll:{qual_tool_name}",
                )
                return self._handle_verdict(verdict, qual_tool_name)

        # 4. Oscillation / Ping-Pong Sequence Detection (A-B-A-B)
        temp_seq = list(self._tool_sequence) + [qual_tool_name]
        if len(temp_seq) >= self.config.ping_pong_window:
            if self._detect_oscillation(temp_seq):
                reason = (
                    f"Ping-pong oscillation detected in tool sequence: {list(temp_seq)[-6:]}. "
                    f"Breaking tool cycling."
                )
                logger.warning(reason)
                verdict = ToolLoopVerdict(
                    blocked=True,
                    reason=reason,
                    fingerprint=fp,
                    outcome=ExecutionOutcome.LOOP_BLOCKED,
                    _warn_key="ping_pong_detected",
                )
                return self._handle_verdict(verdict, qual_tool_name)

        # If not blocked, increment counts and proceed
        self.turn_tool_count += 1
        self._call_counts[fp] = prior_calls + 1
        self._per_tool_counts[qual_tool_name] = self._per_tool_counts.get(qual_tool_name, 0) + 1
        self._tool_sequence.append(qual_tool_name)

        return ToolLoopVerdict(
            blocked=False,
            outcome=ExecutionOutcome.AUTHORIZED,
            fingerprint=fp,
        )

    def _handle_verdict(self, verdict: ToolLoopVerdict, tool_name: str) -> ToolLoopVerdict:
        """Handle warn-before-block hysteresis and emit event bus notifications."""
        warn_key = verdict._warn_key or verdict.reason

        if verdict.blocked and self.config.warn_before_block:
            if warn_key not in self._warned_keys:
                self._warned_keys.add(warn_key)
                logger.info("Tool loop guard issued FIRST-CHANCE WARNING: %s", verdict.reason)
                if self.event_bus:
                    self.event_bus.publish_sync(
                        ZyeEvent(
                            event_type=ZyeEventType.TOOL_EXECUTION_BLOCKED,
                            source_module="zye.reliability.tool_loop_guard",
                            payload={
                                "tool": tool_name,
                                "warning": True,
                                "reason": verdict.reason,
                            },
                        )
                    )
                return ToolLoopVerdict(
                    blocked=False,
                    warned=True,
                    reason=f"[WARNING] {verdict.reason}",
                    fingerprint=verdict.fingerprint,
                    outcome=ExecutionOutcome.AUTHORIZED,
                )

        # Hard block confirmed
        if self.event_bus:
            self.event_bus.publish_sync(
                ZyeEvent(
                    event_type=ZyeEventType.TOOL_EXECUTION_BLOCKED,
                    source_module="zye.reliability.tool_loop_guard",
                    payload={
                        "tool": tool_name,
                        "blocked": True,
                        "reason": verdict.reason,
                    },
                )
            )

        return verdict

    def _detect_oscillation(self, seq: list[str]) -> bool:
        """Detect period 2 (A-B-A-B) or period 3 (A-B-C-A-B-C) repeating sequence."""
        n = len(seq)
        for period in (2, 3):
            window = period * 2
            if n >= window:
                tail = seq[-window:]
                pattern = tail[:period]
                if all(tail[i] == pattern[i % period] for i in range(window)):
                    return True
        return False


__all__ = [
    "tool_fingerprint",
    "ToolLoopGuardConfig",
    "ToolLoopVerdict",
    "ToolLoopGuard",
]
