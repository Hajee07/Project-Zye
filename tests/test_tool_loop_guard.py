"""
Unit tests for ZYE Tool Loop Guard & Verified Execution Engine.
"""

from __future__ import annotations

import pytest
from zye_core.event_bus import ZyeEventBus
from zye_core.types import ExecutionOutcome, ZyeEventType
from zye_reliability.tool_loop_guard import (
    ToolLoopGuard,
    ToolLoopGuardConfig,
    tool_fingerprint,
)
from zye_reliability.verified_execution import VerifiedExecutionEngine, ExecutionStep


def test_tool_fingerprint_deterministic_and_canonical():
    args1 = {"path": "C:/file.txt", "mode": "w", "encoding": "utf-8"}
    args2 = {"encoding": "utf-8", "mode": "w", "path": "C:/file.txt"}  # Different key order

    fp1 = tool_fingerprint("filesystem", "write_file", args1)
    fp2 = tool_fingerprint("filesystem", "write_file", args2)
    assert fp1 == fp2
    assert len(fp1) == 16


def test_loop_guard_blocks_aaa_repeated_calls():
    bus = ZyeEventBus()
    config = ToolLoopGuardConfig(max_identical_calls=3, warn_before_block=True)
    guard = ToolLoopGuard(config=config, event_bus=bus)

    args = {"query": "SELECT 1"}
    # Call 1, 2, 3 permitted
    for i in range(3):
        v = guard.check_call("sqlite", "query", args)
        assert v.blocked is False

    # 4th identical call triggers first-chance WARNING (warn_before_block=True)
    v4 = guard.check_call("sqlite", "query", args)
    assert v4.blocked is False
    assert v4.warned is True

    # 5th identical call triggers HARD BLOCK
    v5 = guard.check_call("sqlite", "query", args)
    assert v5.blocked is True
    assert v5.outcome == ExecutionOutcome.LOOP_BLOCKED


def test_loop_guard_ping_pong_detection():
    config = ToolLoopGuardConfig(ping_pong_window=4, warn_before_block=False)
    guard = ToolLoopGuard(config=config)

    # Sequence A -> B -> A -> B
    v1 = guard.check_call("server", "toolA", {})
    assert v1.blocked is False
    v2 = guard.check_call("server", "toolB", {})
    assert v2.blocked is False
    v3 = guard.check_call("server", "toolA", {})
    assert v3.blocked is False
    v4 = guard.check_call("server", "toolB", {})
    # 4th item completes A-B-A-B cycle
    assert v4.blocked is True
    assert "Ping-pong oscillation" in v4.reason


def test_turn_tool_budget_enforcement():
    config = ToolLoopGuardConfig(max_turn_budget=3, warn_before_block=False)
    guard = ToolLoopGuard(config=config)

    # 3 distinct tool calls permitted in turn
    assert guard.check_call("s", "t1", {"i": 1}).blocked is False
    assert guard.check_call("s", "t2", {"i": 2}).blocked is False
    assert guard.check_call("s", "t3", {"i": 3}).blocked is False

    # 4th tool call in same turn is blocked by budget
    v4 = guard.check_call("s", "t4", {"i": 4})
    assert v4.blocked is True
    assert "budget exhausted" in v4.reason.lower()

    # Reset turn -> next call passes
    guard.reset_turn()
    assert guard.check_call("s", "t4", {"i": 4}).blocked is False


def test_verified_execution_anti_hallucination():
    bus = ZyeEventBus()
    engine = VerifiedExecutionEngine(event_bus=bus)

    step = engine.request_execution("powershell", "execute", {"cmd": "dir"})
    assert step.status == ExecutionOutcome.REQUESTED

    # False success: result contains explicit error
    bad_result = {"status": "error", "message": "Access Denied"}
    step_res = engine.verify_result(step, bad_result)
    assert step_res.status == ExecutionOutcome.FAILED

    # Valid success
    step2 = engine.request_execution("powershell", "execute", {"cmd": "echo ok"})
    good_result = {"status": "ok", "output": "ok"}
    step_res2 = engine.verify_result(step2, good_result)
    assert step_res2.status == ExecutionOutcome.VERIFIED_SUCCESS
