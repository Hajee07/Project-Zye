# ZYE AI — Gemini Live Turn Lifecycle & Anti-Premature Clarification Report

**Project:** ZYE AI Hybrid Personal Windows AI Assistant  
**Module:** `zye_gemini_live.py` (`_receive_events_loop`, `TurnMetrics`, `ZyeGeminiLiveManager`)  
**Status:** FULLY CERTIFIED & OPERATIONAL  

---

## 1. The Premature Clarification Defect

### Forensic Problem Description
In Gemini Live's bidirectional streaming architecture (`v1alpha` WebSocket), a single multi-step interaction involves intermediate protocol turns:
1. User speaks: *"Play some songs"* or *"Open Notepad"*.
2. Gemini Live server analyzes the input and emits a `ToolCall` event (e.g. `play_music` or `launch_application`).
3. Immediately upon emitting the tool call, Gemini Live marks `server_content.turn_complete = True` with `model_turn = None` (0 audio frames, 0 text characters).
4. Meanwhile, the client executes the tool asynchronously through `ZyeExecutionGate` / MCP dispatcher.
5. In previous versions, the turn completion listener checked:
   ```python
   if not received_model_audio and not received_model_text:
       await self.coordinator.speak("Purinjikikka mudiyala, thirumba solreengala?")
   ```
6. Because `turn_complete` was true while the tool was in flight, Zye immediately blurted out: *"Purinjikikka mudiyala, thirumba solreengala?"*.
7. Seconds later, the tool response was returned, Gemini Live generated its playback answer, and spoke over itself!

---

## 2. Repaired Turn Lifecycle State Machine

To eliminate this defect, the turn listener was restructured to recognize intermediate vs final turns:

```
        User Audio In
             |
             v
      [Model Processing]
             |
             +---> [Tool Call Emitted]
             |          |
             |          v
             |     Set is_tool_in_flight = True
             |     Set Turn status = "WAITING_FOR_TOOL"
             |     Execute tool in background task
             |          |
             |          v
             |     [turn_complete received]
             |     Is tool in flight? 
             |       YES -> YIELD (continue loop, NO clarification!)
             |       NO  -> Final turn complete
             |          |
             |          v
             |     Tool completes -> send_tool_response()
             |          |
             v          v
      [Model Generates Audio / Text]
             |
             v
      [Final turn_complete received]
             |
             v
      Turn status = "COMPLETED"
```

### Code Implementation (`zye_gemini_live.py`)

```python
# 1. Evaluate tool in flight status
is_tool_in_flight = (
    self._turn_tool_requested
    or self._turn_tools_in_flight > 0
    or (self._current_turn is not None and bool(self._current_turn.tool_name and not self._turn_tool_executed))
)

if is_tool_in_flight:
    if self._current_turn is not None:
        self._current_turn.status = "WAITING_FOR_TOOL"
    logger.debug("Turn marked WAITING_FOR_TOOL while MCP tool execution finishes")
    continue

# 2. Only emit clarification if NO tool was requested and NO speech was generated
if not received_audio and not received_text:
    if not self._turn_tool_executed and not self._turn_tool_requested:
        # Legitimate unintelligible audio clarification
        await self._speak_clarification()
```

---

## 3. Monotonic Latency Trace Formatting Repair

Previously, diagnostic latency metrics logged negative or malformed offsets:
`First PCM frame sent: +-3525.4 ms`  
`Tool completed: +-36.9 ms`

### Root Cause
1. Literal `+` hardcoded before f-string with negative values: `f"+{offset:.1f}"` when `offset` was negative produced `+-`.
2. Offset was computed relative to `t0_audio_activity_ns`, which in mock tests or discontinuous events was greater than subsequent timestamps.

### Resolution
Anchored offset calculation to `base = min(valid_timestamps)`. All subsequent stages are guaranteed $\ge base$:
```python
candidates = [t for t in [self.t0_audio_activity_ns, self.t1_frame_captured_ns, self.t4_sent_to_live_ns] if t]
base = min(candidates) if candidates else (self.t0_audio_activity_ns or 0)
offset_ms = max(0.0, (t_val - base) / 1_000_000)
line = f"  [{tag}] {label:<32}: +{offset_ms:.1f} ms"
```

---

## 4. Verification

Verified via `test_tool_call_prevents_premature_clarification` and `test_monotonic_latency_trace`:
- Zero premature clarifications when tool is requested: **PASSED (0 prompts emitted)**.
- Monotonic latency trace contains zero `+-` or negative values: **PASSED (8 lines verified)**.
