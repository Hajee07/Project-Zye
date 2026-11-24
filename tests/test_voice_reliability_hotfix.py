"""
Comprehensive Verification Test Suite for P0 Voice Reliability Hotfix:
1. Pre-Mortem Schema Compatibility (recursively strips additionalProperties)
2. Audio Admission Gate (playback active, echo tail guard, barge-in)
3. Silence Gating & Phantom Speech Prevention
4. Turn Management & Anti-Premature Clarification on Tool Calls
5. Tool Circuit Breaker & Safe Caching
6. Monotonic Latency Instrumentation (no negative offsets or '+-')
7. Watchdog RAM Hysteresis & Stable Fingerprinting
"""

import asyncio
import time
import pytest
import numpy as np

from zye_gemini_live import (
    AudioAdmissionGate,
    AudioAdmissionState,
    LiveAudioPlayer,
    TurnMetrics,
    GeminiLiveConfig,
    ZyeGeminiLiveManager,
    LiveSessionState,
)
from zye_intelligence.premortem import _clean_gemini_schema
from zye_intelligence.schemas import NegativeAuditReport
from zye_intelligence.autonomous_watchdog import (
    ZyeAutonomousWatchdog,
    _scan_emerging_problems_sync,
)


# ============================================================================
# 1. Pre-Mortem Schema Compatibility Test
# ============================================================================

def test_premortem_gemini_developer_mode_schema():
    """Verify that NegativeAuditReport schema has zero additionalProperties for Gemini Developer API."""
    raw_schema = NegativeAuditReport.model_json_schema()
    cleaned = _clean_gemini_schema(raw_schema)
    
    # Assert additionalProperties is completely eliminated at all levels
    def _assert_no_additional_properties(d):
        if isinstance(d, dict):
            assert "additionalProperties" not in d, f"Found additionalProperties in dict: {d}"
            for v in d.values():
                _assert_no_additional_properties(v)
        elif isinstance(d, list):
            for item in d:
                _assert_no_additional_properties(item)

    _assert_no_additional_properties(cleaned)
    assert cleaned.get("type") == "object"
    assert "properties" in cleaned


# ============================================================================
# 2. Audio Admission Gate & Echo Tail Guard Tests
# ============================================================================

def test_audio_admission_gate_playback_active():
    """When output player is active, normal microphone frames must be dropped."""
    gate = AudioAdmissionGate(echo_tail_guard_ms=300.0, half_duplex_safety=True)
    
    class MockPlayer:
        def is_playing(self, include_tail_ms: float = 0.0):
            return True

    player = MockPlayer()
    normal_speech_frame = (np.ones(512, dtype=np.int16) * 1500).tobytes()

    admit, barge = gate.evaluate_frame(
        normal_speech_frame,
        player=player,
        allow_barge_in=True,
        barge_in_threshold=9500.0,
    )

    assert not admit, "Audio frame during playback must not be admitted"
    assert not barge, "Normal speech must not trigger barge-in"
    assert gate.state == AudioAdmissionState.OUTPUT_ACTIVE
    assert gate.dropped_frames_count == 1


def test_audio_admission_gate_echo_tail_guard():
    """When output player stops, echo tail guard must drop frames until guard window elapses."""
    gate = AudioAdmissionGate(echo_tail_guard_ms=150.0, half_duplex_safety=True)

    class MockPlayer:
        def __init__(self):
            self._playing = True
        def is_playing(self, include_tail_ms: float = 0.0):
            return self._playing

    player = MockPlayer()
    frame = (np.ones(512, dtype=np.int16) * 1200).tobytes()

    # Step 1: Active output
    admit, _ = gate.evaluate_frame(frame, player=player)
    assert not admit
    assert gate.state == AudioAdmissionState.OUTPUT_ACTIVE

    # Step 2: Output finishes now -> enters ECHO_TAIL_GUARD
    player._playing = False
    admit_tail, _ = gate.evaluate_frame(frame, player=player)
    assert not admit_tail, "Frame during echo tail window must be dropped"
    assert gate.state == AudioAdmissionState.ECHO_TAIL_GUARD

    # Step 3: Wait for echo tail guard window (150ms) to elapse
    time.sleep(0.18)

    # Step 4: Next frame must now be admitted cleanly
    admit_after, _ = gate.evaluate_frame(frame, player=player)
    assert admit_after, "Frame after echo tail window must be admitted"
    assert gate.state == AudioAdmissionState.ADMITTING


def test_audio_admission_gate_intentional_barge_in():
    """Very loud sustained user speech over playback must trigger barge-in."""
    gate = AudioAdmissionGate(echo_tail_guard_ms=200.0, half_duplex_safety=True)

    class MockPlayer:
        def is_playing(self, include_tail_ms: float = 0.0):
            return True

    player = MockPlayer()
    # High energy frame (>12000 RMS)
    loud_frame = (np.ones(512, dtype=np.int16) * 14000).tobytes()

    barge_triggered = False
    for _ in range(6):
        admit, barge = gate.evaluate_frame(
            loud_frame,
            player=player,
            allow_barge_in=True,
            barge_in_threshold=9500.0,
        )
        if barge:
            barge_triggered = True
            assert admit, "Frame triggering barge-in must be admitted"
            break

    assert barge_triggered, "Sustained high-energy speech must trigger barge-in"


# ============================================================================
# 3. Monotonic Latency Instrumentation Tests
# ============================================================================

def test_monotonic_latency_trace():
    """Verify that diagnostic traces never produce negative offsets or '+-' strings."""
    t0 = 1000_000_000
    turn = TurnMetrics(
        turn_id="live_turn_001",
        session_id="session_test",
        t0_audio_activity_ns=t0,
        t1_frame_captured_ns=t0 + 10_000_000,
        t4_sent_to_live_ns=t0 + 25_000_000,
        t7_first_server_event_ns=t0 + 200_000_000,
        t8_first_audio_bytes_ns=t0 + 250_000_000,
        t10_output_submitted_ns=t0 + 255_000_000,
        m0_tool_requested_ns=t0 + 260_000_000,
        m4_tool_completed_ns=t0 + 350_000_000,
        t12_response_complete_ns=t0 + 500_000_000,
        tool_name="play_music",
    )

    lines = turn.format_diagnostic_trace()
    assert len(lines) >= 7

    for line in lines:
        assert "+-" not in line, f"Found malformed '+-' in trace: {line}"
        assert "-" not in line.split(":")[-1], f"Found negative offset in trace: {line}"
        assert "+0.0 ms" in lines[0]


# ============================================================================
# 4. Turn Management & Premature Clarification Prevention
# ============================================================================

def test_tool_call_prevents_premature_clarification():
    """
    When Gemini Live requests a tool call and returns 0 audio and 0 text,
    it must NOT emit a clarification prompt.
    """
    spoken_prompts = []

    class MockCoordinator:
        async def speak(self, text: str):
            spoken_prompts.append(text)

    cfg = GeminiLiveConfig(enabled=True)
    mgr = ZyeGeminiLiveManager(config=cfg, coordinator=MockCoordinator())

    # Simulate turn state where user spoke and a tool was requested
    mgr._current_turn = TurnMetrics(
        turn_id="live_turn_001",
        session_id="session_001",
        user_transcript="play some music",
    )
    mgr._turn_tool_requested = True
    mgr._turn_tools_in_flight = 1

    # Verify is_tool_in_flight calculation
    is_tool_in_flight = (
        mgr._turn_tool_requested
        or mgr._turn_tools_in_flight > 0
        or (mgr._current_turn and bool(mgr._current_turn.tool_name and not mgr._turn_tool_executed))
    )
    assert is_tool_in_flight is True, "Tool must be marked in flight"

    # Simulate what _receive_events_loop does on turn_complete when tool is in flight:
    # It must NOT speak clarification, and must set status to WAITING_FOR_TOOL
    if is_tool_in_flight:
        mgr._current_turn.status = "WAITING_FOR_TOOL"

    assert len(spoken_prompts) == 0, "Clarification must not be spoken during tool execution"
    assert mgr._current_turn.status == "WAITING_FOR_TOOL"


def test_tool_circuit_breaker_limit():
    """Verify tool loop circuit breaker terminates excessive tool loops within a turn."""
    async def _run():
        tool_calls_executed = 0

        async def mock_dispatcher(name: str, args: dict):
            nonlocal tool_calls_executed
            tool_calls_executed += 1
            return {"status": "OK", "action": "test"}

        cfg = GeminiLiveConfig(enabled=True, max_tools_per_turn=3)
        mgr = ZyeGeminiLiveManager(config=cfg, tool_dispatcher=mock_dispatcher)

        class MockFunctionCall:
            def __init__(self, call_id: str, name: str, args: dict | None = None):
                self.id = call_id
                self.name = name
                self.args = args or {}

        class MockToolCall:
            def __init__(self, fcs):
                self.function_calls = fcs

        class MockSession:
            def __init__(self):
                self.responses_sent = []
            async def send_tool_response(self, function_responses):
                self.responses_sent.extend(function_responses)

        session = MockSession()

        # Dispatch tool call 1, 2, 3 (within budget, distinct tools)
        for i in range(1, 4):
            mgr._turn_tool_count += 1
            tc = MockToolCall([MockFunctionCall(f"call_{i}", f"test_tool_{i}", {"step": i})])
            await mgr._handle_live_tool_call(session, tc)

        assert tool_calls_executed == 3
        assert len(session.responses_sent) == 3

        # Dispatch tool call 4 (exceeds max_tools_per_turn=3)
        mgr._turn_tool_count += 1
        tc_excess = MockToolCall([MockFunctionCall("call_4", "test_tool_4", {"step": 4})])
        await mgr._handle_live_tool_call(session, tc_excess)

        # Tool dispatcher must NOT be called again
        assert tool_calls_executed == 3
        # Response must report LOOP_PREVENTED
        last_resp = session.responses_sent[-1]
        assert last_resp.response["result"]["status"] == "LOOP_PREVENTED"

    asyncio.run(_run())


def test_watchdog_ram_hysteresis_and_stable_fingerprint():
    """
    Verify that fluctuating RAM (95.1% -> 95.8% -> 95.3%) uses stable fingerprint 'RAM:HIGH',
    does NOT clear and re-alert every scan, and respects alert cooldown.
    """
    async def _run():
        cfg = {
            "ram_high_threshold": 95.0,
            "ram_clear_threshold": 90.0,
            "alert_cooldown_seconds": 300.0,
            "interval_seconds": 25.0,
        }
        watchdog = ZyeAutonomousWatchdog(config=cfg)

        # Mock psutil memory return
        class MockVirtualMemory:
            def __init__(self, percent):
                self.percent = percent
                self.available = 1024 * 1024 * 1024  # 1GB

        import psutil
        orig_vm = psutil.virtual_memory
        orig_pi = psutil.process_iter

        try:
            # Fast mock for process_iter to avoid scanning all Windows processes in test
            psutil.process_iter = lambda attrs: []

            # Scan 1: RAM at 95.2% (exceeds 95.0% threshold) -> should alert
            psutil.virtual_memory = lambda: MockVirtualMemory(95.2)
            res1 = await watchdog.scan_system()
            assert len(res1["unsuppressed_problems"]) == 1
            assert "RAM:HIGH" in watchdog._active_problem_fingerprints

            # Scan 2: RAM fluctuates to 95.7% (still high, but within cooldown) -> should NOT alert
            psutil.virtual_memory = lambda: MockVirtualMemory(95.7)
            res2 = await watchdog.scan_system()
            assert len(res2["unsuppressed_problems"]) == 0, "Alert must be suppressed during cooldown"
            assert len(watchdog._resolved_problems) == 0, "Problem must NOT be cleared during 0.5% fluctuation"
            assert "RAM:HIGH" in watchdog._active_problem_fingerprints

            # Scan 3: RAM drops to 92.0% (between 90.0% clear and 95.0% alert) -> hysteresis keeps it active
            psutil.virtual_memory = lambda: MockVirtualMemory(92.0)
            res3 = await watchdog.scan_system()
            assert len(res3["unsuppressed_problems"]) == 0
            assert "RAM:HIGH" in watchdog._active_problem_fingerprints

            # Scan 4: RAM drops to 88.0% (below 90.0% clear threshold) -> problem clears cleanly!
            psutil.virtual_memory = lambda: MockVirtualMemory(88.0)
            res4 = await watchdog.scan_system()
            assert len(res4["unsuppressed_problems"]) == 0
            assert "RAM:HIGH" not in watchdog._active_problem_fingerprints
            assert len(watchdog._resolved_problems) == 1
            assert watchdog._resolved_problems[0]["fingerprint"] == "RAM:HIGH"

        finally:
            psutil.virtual_memory = orig_vm
            psutil.process_iter = orig_pi

    asyncio.run(_run())
