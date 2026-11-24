# ZYE AI — GEMINI LIVE ROOT CAUSE ANALYSIS REPORT
## Diagnostic Findings for Voice Session Interruptions, Playback Drops & Connection Lifecycle

**Document ID:** GL-RCA-2026-11-22  
**Component:** `zye_gemini_live.py` (Gemini Live Native Audio Master Brain Engine)  
**Status:** ROOT CAUSES IDENTIFIED & DOCUMENTED  

---

### 1. Executive Summary

Voice interaction with ZYE exhibited three symptom categories:
1. Speech recognition terminating prematurely while the user was speaking with natural pauses.
2. ZYE's spoken answers abruptly cutting off mid-sentence.
3. Random session disconnects and unrecoverable listening states.

Investigation of `zye_gemini_live.py` and its interaction with `main.py` revealed four deterministic flaws in audio event synchronization, threshold calibration, and task lifecycle management.

---

### 2. Deep Technical Breakdown of Root Causes

#### 2.1 Hardcoded High RMS Energy Threshold & Premature End-of-Turn
- **Mechanism:** In `_send_audio_loop()` (lines 663–695), turn boundaries were controlled by:
  ```python
  speech_threshold = 9500.0
  min_speech_frames = 8          # ~250ms of sustained speech
  silence_threshold_frames = 25  # ~800ms silence after speech to signal end_of_turn
  ```
- **Consequence:**
  - 16-bit PCM integer range is $[-32768, 32767]$.
  - Normal human voice into a laptop or desktop array microphone produces RMS amplitudes between **800 and 3,500**.
  - A threshold of **9500** required the user to yell into the microphone. Soft speech, distant speech, or low-frequency Tamil vowels failed to exceed 9500, meaning `user_speaking` was never flagged as `True`.
  - Conversely, if an utterance did exceed 9500, any brief pause $> 800\text{ ms}$ immediately dispatched `await session.send(end_of_turn=True)`.
  - Natural pauses (especially when formulating multi-part thoughts or switching between Tamil and English) are typically **1.2 to 1.8 seconds**. The 800ms limit sliced user sentences in half.

#### 2.2 Acoustic Self-Listening & Self-Interruption Loop
- **Mechanism:**
  - In `_receive_events_loop()` (line 835), the arrival of `server_content.turn_complete` immediately executed:
    ```python
    self.set_state(LiveSessionState.LISTENING)
    ```
  - However, the server finishes sending audio chunks over the WebSocket **seconds before the local audio hardware finishes playing them**.
  - As soon as the state became `LISTENING`, `push_microphone_audio()` resumed streaming microphone frames to Gemini Live without gating.
  - The microphone picked up Zye's own voice coming out of the desktop speakers.
  - Server-side VAD at Google interpreted this as the user speaking and flagged `server_content.interrupted = True`.
  - The handler in line 766 responded by calling `self.player.flush()`, which **instantly aborted the audio stream and flushed the queue**.
  - Result: Zye's voice cut off abruptly midway through its answer.

#### 2.3 Uncoordinated Dual Playback Engines
- **Mechanism:**
  - `main.py` used `ZyeAudioPlayback` (Pygame) to speak system greetings and Edge-TTS responses.
  - `zye_gemini_live.py` used `LiveAudioPlayer` (`sounddevice.RawOutputStream`) to play 24kHz PCM chunks.
  - Neither playback engine notified the other. When Pygame was speaking, `LiveAudioPlayer.is_playing()` was `False`, meaning the microphone was un-gated, feeding speaker sound directly into the live Gemini session.

#### 2.4 Race Condition in `asyncio.wait(return_when=FIRST_COMPLETED)`
- **Mechanism:**
  - In `run_live_loop()` (lines 962–973), `_send_task` and `_recv_task` were managed with `FIRST_COMPLETED`.
  - If a transient network hiccup or empty response caused `_recv_task` to complete a turn loop, `asyncio.wait` cancelled `_send_task` and terminated the entire WebSocket connection.
  - This forced a full reconnect cycle instead of maintaining a persistent multi-turn session.

---

### 3. Required Engineering Fixes

1. **Adaptive VAD & Realistic Turn Boundaries**:
   - Calibrate speech threshold: dynamic noise-floor baseline $+ \text{margin}$ (trigger at ~1,500 RMS or Silero VAD probability $\ge 0.52$).
   - Increase silence hangover from 800ms (25 frames) to **1.5 seconds (48 frames)** to comfortably accommodate natural pauses in Tamil and Tanglish.
2. **Synchronized Playback Gating & Completion Verification**:
   - Link `LiveSessionState` to actual hardware audio playback completion: do not transition to `LISTENING` until both the audio queue is empty AND `player.is_playing()` returns `False`.
   - Gate microphone audio while either `LiveAudioPlayer` OR `ZyeAudioPlayback` (Pygame) is playing.
3. **Robust Reconnection & Session Keepalive**:
   - Prevent `FIRST_COMPLETED` from tearing down healthy sessions on transient turn completions.
   - Implement exponential backoff with slot rotation via `GeminiKeyManager`.
