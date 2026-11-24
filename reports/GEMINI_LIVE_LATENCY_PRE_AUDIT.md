# ZYE AI — GEMINI LIVE LATENCY PRE-AUDIT REPORT
**Target System:** ZYE AI Hybrid Personal Assistant  
**Milestone:** Gemini Live Native Bidirectional Audio Master Brain Optimization  
**Platform:** Windows Desktop (x64), Python 3.12, `google-genai` SDK v3.6.1  
**Timestamp:** 2026-11-21 17:42:00 IST  
**Audit Status:** COMPLETE — ROOT CAUSE IDENTIFIED & EMPIRICALLY CONFIRMED

---

## 1. Executive Summary & Problem Definition

During interactive voice testing on Windows desktop, the user observed that greeting ZYE with natural speech (e.g. *"Hi"*, *"Hello Zye"*, or Tanglish *"Enna panra Zye?"*) occasionally experienced massive latency (120–180 seconds, 2–3 minutes) before a response was heard, or the response was prematurely aborted.

This pre-audit report traces the entire voice processing pipeline from physical microphone capture through audio queuing, WebSocket transmission, Gemini Live model processing, tool evaluation, server event handling, and audio playback to pinpoint the exact mechanisms producing this unacceptable delay.

---

## 2. End-to-End Execution Path Audit: User Says "Hi" to Audible Output

```
[User Utterance: "Hi"]
       │
       ▼
[1. AudioCaptureEngine (PortAudio sd.InputStream)]
  - Callback buffers 32ms float32 frames into bounded queue
       │
       ▼
[2. pump_capture_engine in zye_gemini_live.py]
  - Drains frames from capture queue, downmixes to mono, converts to PCM16 (16kHz)
  - Pushes PCM16 bytes into self._audio_in_queue
       │
       ▼
[3. _send_audio_loop (Asyncio WebSocket Sender)]
  - Reads pcm_chunk from self._audio_in_queue
  - Calls session.send_realtime_input(audio=dict(data=pcm_chunk, mime_type="audio/pcm;rate=16000"))
       │
       ▼
[4. Gemini Live WebSocket (wss://generativelanguage.googleapis.com/.../BidiGenerateContent)]
  - Model: gemini-3.8-live (v1alpha)
  - Evaluates audio against 351 declared MCP tool schemas
  - Computes native response & streams 24kHz PCM16 audio chunks
       │
       ▼
[5. _receive_events_loop (Asyncio WebSocket Receiver)]
  - Consumes session.receive() generator
  - Detects server_content.model_turn audio parts (inline_data)
  - Calls self.player.queue_chunk(audio_bytes)
       │
       ▼
[6. LiveAudioPlayer (sd.RawOutputStream Background Thread)]
  - Dedicated background thread consumes audio chunks
  - Submits 24kHz PCM16 frames to sound card
       │
       ▼
[7. First Audible Sound from Speakers]
```

---

## 3. Empirically Confirmed Latency Root Causes

Through isolated benchmarking (`scratch/benchmark_tools_overhead.py`, `scratch/test_session_lifecycle.py`, `scratch/test_continuous_recv.py`), the following exact root causes were identified:

### Root Cause 1: Single-Turn WebSocket Teardown (Cause A & Cause N)
- **Mechanism:** In `google-genai` v3.6.1, `session.receive()` is an async generator that **exits** when the server signals `turn_complete=True`.
- **Existing Code Flaw:** In `zye_gemini_live.py`, `_receive_events_loop` ran `async for response in session.receive():` only **once**. When the first turn completed, `_receive_events_loop` terminated.
- In `run_live_loop`, `asyncio.wait([self._send_task, self._recv_task], return_when=asyncio.FIRST_COMPLETED)` detected that `_recv_task` finished, cancelled `_send_task`, exited the `async with client.aio.live.connect` context, and **closed the WebSocket**.
- **Impact:** Every single conversational utterance destroyed the WebSocket connection. The system entered `reconnect_attempts` with a 1.5-second backoff delay, reopened the WebSocket (1.4–1.6s handshake), re-sent all 351 tool schemas, and restarted. If the user spoke during this teardown/reconnect window, the speech frames were lost or truncated, leading to multiple retry cascades accumulating to 120–180 seconds!

### Root Cause 2: Acoustic Echo & Self-Listening Interruption (Cause V & Section 33)
- **Mechanism:** When Gemini Live starts speaking through laptop speakers, the physical microphone immediately captures ZYE's own voice output.
- **Existing Code Flaw:** `pump_capture_engine` continuously streamed all microphone audio to Gemini Live without muting or energy-gating while `self.player.is_playing()` was active.
- **Impact:** Gemini Live heard its own speech echoed back through the microphone, interpreted it as a user barge-in, and emitted `server_content.interrupted = True`!
- As logged in `task-13076.log`:
  ```
  2026-11-21 17:09:37,756 [INFO] zye.gemini.live: User interrupted Gemini Live; flushing playback queue
  2026-11-21 17:21:44,557 [INFO] zye.gemini.live: User interrupted Gemini Live; flushing playback queue
  ```
- The audio player immediately flushed its queue and aborted the hardware stream. The user heard only a fraction of a syllable or silence. The user was left waiting, spoke again, and triggered another abort cycle!

### Root Cause 3: Thread Dispatch Contention in Audio Capture Pump (Cause M & Section 27)
- **Mechanism:** `pump_capture_engine` called `await asyncio.to_thread(capture_engine.read_frame, 0.05)` for each 32ms audio frame.
- **Existing Code Flaw:** Spawning a Python thread pool worker ~31 times per second on Windows created thread scheduling jitter and CPU overhead.
- When background tasks (Autonomous Watchdog, SQLite Calendar reconciliation) performed checks, the frame queue accumulated backlog. Draining only 1 frame every 32ms caused speech frames to lag seconds behind wall-clock time.

---

## 4. Evaluated & Rejected Hypotheses

| Hypothesis | Test Result | Conclusion |
| :--- | :--- | :--- |
| **Gemini Live Service Latency** | Baseline test with text "Hi" returned first audio in **434.8ms**; connection in **1415ms**. | **REJECTED**: Gemini Live itself is extremely fast (< 500ms P50). |
| **7-Key Manager Rotation Delay** | Key lookup for Slot 1 took **0.4ms**. | **REJECTED**: No key-polling delay on conversational turns. |
| **Negative Pre-Mortem on Greetings** | Pre-mortem only executes when MCP tools are dispatched; greetings do not trigger tools. | **REJECTED**: Pre-mortem does not run on ordinary greetings. |
| **Edge-TTS Double Synthesis** | Path B streams native Gemini 24kHz audio; Edge-TTS is only called in Path C fallback. | **REJECTED**: No duplicate TTS synthesis occurring in Live mode. |
| **351 MCP Tool Schema Ingestion** | Measured connection with 351 tools: **1594ms** vs **1415ms** without tools. First audio: **551ms** vs **435ms**. | **MINOR FACTOR**: Contributes ~116ms overhead, not 2–3 minutes, but optimization is beneficial. |

---

## 5. Architectural Corrective Actions

1. **Persistent Session Multi-Turn Loop:**
   - Modify `_receive_events_loop` to run in a continuous `while self._running:` loop that restarts `async for response in session.receive():` upon `turn_complete=True` without closing the session.
   - Maintain the stateful WebSocket connection persistently across all conversational turns.
2. **Software Echo Cancellation & Self-Listening Suppression:**
   - In `push_microphone_audio`, suppress or gate audio transmission when `self.player.is_playing()` is True unless input RMS energy exceeds a high barge-in threshold (+12dB above ambient/speaker feedback).
3. **Non-Blocking In-Memory Capture Queue Drain:**
   - In `pump_capture_engine`, replace `asyncio.to_thread` with non-blocking `capture_engine.frame_queue.get_nowait()` in a fast drain loop, reducing thread dispatches to 0.
4. **End-to-End Latency Instrumentation:**
   - Integrate monotonic nanosecond timers (`time.perf_counter_ns()`) for T0–T13 and tool events M0–M5 with correlation turn IDs.
5. **Direct Conversational Greeting Policy:**
   - Explicit system prompt rule instructing Gemini Live to answer greetings immediately in spoken Tanglish/English without tool invocation.
