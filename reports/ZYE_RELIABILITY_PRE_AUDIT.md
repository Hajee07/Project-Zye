# ZYE AI — PRE-IMPLEMENTATION RELIABILITY AUDIT REPORT
**System Diagnostics & Root Cause Analysis for Voice Reliability and Verified Application Execution**

**Audit Date:** 2026-11-22  
**Platform:** Windows 11 Desktop  
**Python Virtual Environment:** `d:\Zye\.venv\Scripts\python.exe`  
**Primary Modules:** `main.py`, `zye_gemini_live.py`, `zye_audio_ear.py`, `windows_control_mcp.py`, `zye_windows/`, `system_os_mcp.py`  
**Certification Status:** AUDIT COMPLETE — ROOT CAUSES CONFIRMED  

---

### 1. Verified Architecture & Module Mapping

| Pipeline Function | Actual Module / File | Actual Class / Function | Verification Status |
|---|---|---|---|
| **Microphone Audio Capture** | `zye_audio_ear.py` | `AudioCaptureEngine` (sounddevice `RawInputStream`, 16kHz PCM) | Active & Verified |
| **Audio Preprocessing & VAD** | `zye_audio_ear.py` | `ZyeVoiceEar` (`SileroVAD` / `AdaptiveRMSDetector`) | Active & Verified |
| **Gemini Live Connection** | `zye_gemini_live.py` | `ZyeGeminiLiveManager.run_live_loop()` (`client.aio.live.connect`) | Active & Verified |
| **Live Audio Stream Pump** | `zye_gemini_live.py` | `ZyeGeminiLiveManager.pump_capture_engine()` & `_send_audio_loop()` | Active & Verified |
| **Live Event & Transcript Reception**| `zye_gemini_live.py` | `ZyeGeminiLiveManager._receive_events_loop()` | Active & Verified |
| **Gemini Master Brain Gateway** | `gemini_gateway.py` | `GeminiGateway` (7 API key slot management) | Active & Verified |
| **MCP Orchestrator / Host** | `main.py` | `ZyeMasterAgent` (dispatches 436 FastMCP tools across 9 servers) | Active & Verified |
| **TTS Generation** | `zye_voice/edge_tts_engine.py` | `ZyeEdgeTTSEngine` (Edge-TTS `en-IN-NeerjaNeural`) | Active & Verified |
| **Audio Playback** | `zye_voice/playback.py` & `zye_gemini_live.py` | `ZyeAudioPlayback` (Pygame) & `LiveAudioPlayer` (`sounddevice`) | Concurrency Conflict Detected |
| **Application Launching** | `zye_windows/app_launcher.py` & `system_os_mcp.py` | `WindowsAppLauncher.open_any_app()` / `start_application_process()` | Vulnerability Confirmed |
| **Window Verification** | `zye_windows/window_manager.py` | `WindowsWindowManager.find_windows()` (`pygetwindow`) | Inadequate for Store/UWP Apps |

---

### 2. Problem A: Voice Reliability & Session Interruption — Root Causes

#### Root Cause A1: Premature End-of-Turn & Crude RMS Threshold in `zye_gemini_live.py`
- **Location:** [zye_gemini_live.py](file:///d:/Zye/zye_gemini_live.py#L663-L697)
- **Defect:** In `_send_audio_loop`, `speech_threshold = 9500.0` and `silence_threshold_frames = 25` (~800ms) are hardcoded:
  1. An RMS threshold of 9500 is excessively high for normal speech (typical desktop microphone speech is 1,000–3,500 RMS). When speaking at normal or soft volume, `user_speaking` remains `False`, causing turn boundary signaling to fail.
  2. If speech triggers `user_speaking = True`, any brief pause longer than 800ms (standard natural conversational pauses, especially in Tamil/Tanglish) immediately sends `await session.send(end_of_turn=True)`.
  3. This cuts off the user mid-sentence. When the user resumes speaking, Gemini treats the continuation as an interruption.

#### Root Cause A2: Self-Interruption Due to Unsynchronized Playback State & Speaker Bleed
- **Location:** [zye_gemini_live.py](file:///d:/Zye/zye_gemini_live.py#L759-L768) and [zye_gemini_live.py](file:///d:/Zye/zye_gemini_live.py#L807-L836)
- **Defect:** 
  1. When Gemini Live sends `turn_complete = True`, line 835 immediately executes `self.set_state(LiveSessionState.LISTENING)`.
  2. However, `LiveAudioPlayer` or Edge-TTS is still actively playing audio through the speakers because audio chunks were buffered.
  3. Because the state is now `LISTENING`, microphone frames are no longer suppressed or gated. The microphone captures Zye's own speech from the speakers and sends it back to Gemini Live.
  4. Gemini Live detects speech, triggers `server_content.interrupted = True`, and line 766 executes `self.player.flush()`, **abruptly terminating Zye's spoken response mid-sentence**.

#### Root Cause A3: Dual-Player Architecture Mismatch
- **Location:** [main.py](file:///d:/Zye/main.py#L1292-L1311) vs [zye_gemini_live.py](file:///d:/Zye/zye_gemini_live.py#L775-L786)
- **Defect:** `main.py` routes audio through `ZyeAudioPlayback` (Pygame mixer) for Edge-TTS (`en-IN-NeerjaNeural`), while `zye_gemini_live.py` routes audio through `LiveAudioPlayer` (`sounddevice.RawOutputStream`) for native Google voice. Neither player coordinates with the other's mute state, causing lock contention, sounddevice collision, and playback truncation.

#### Root Cause A4: Brittle Task Cancellation in `run_live_loop`
- **Location:** [zye_gemini_live.py](file:///d:/Zye/zye_gemini_live.py#L962-L973)
- **Defect:** `asyncio.wait([self._send_task, self._recv_task], return_when=asyncio.FIRST_COMPLETED)` immediately cancels the entire session if either sender or receiver finishes or encounters a transient WebSocket keepalive glitch, prematurely terminating active multi-turn conversations.

---

### 3. Problem B: Application False Success — Root Causes

#### Root Cause B1: Process Start Equated with UI Readiness in `process_manager.py`
- **Location:** [zye_windows/process_manager.py](file:///d:/Zye/zye_windows/process_manager.py#L548-L555)
- **Defect:** `start_application_process()` executes `subprocess.Popen(cmd, shell=False)`, sleeps for 0.3 seconds, and unconditionally returns:
  ```json
  {"status": "SUCCESS", "pid": 1234, "message": "Launched 'chrome' with PID 1234."}
  ```
  Zero window verification is performed. If the application crashes on startup, starts headless, or hangs, Gemini sees `status: SUCCESS` and falsely reports to the user that the application opened successfully.

#### Root Cause B2: Store / UWP Applications Invisibility in `pygetwindow`
- **Location:** [zye_windows/window_manager.py](file:///d:/Zye/zye_windows/window_manager.py#L125-L136)
- **Defect:** `find_windows()` relies exclusively on `pygetwindow.getAllWindows()`. In Windows 10/11, packaged Store applications (e.g., WhatsApp Desktop, Windows Calculator) run inside `ApplicationFrameHost.exe`. Their window titles are frequently empty during launch enumeration, causing `find_windows()` to return an empty list even when the window is actually visible on screen.

#### Root Cause B3: Unchecked Asynchronous Shell Activation
- **Location:** [zye_windows/app_launcher.py](file:///d:/Zye/zye_windows/app_launcher.py#L177-L179)
- **Defect:** Store apps are launched via `explorer.exe shell:AppsFolder\<AppID>`. `explorer.exe` exits immediately with status 0, but the target application's window creation is handled asynchronously by Windows Application Activation Manager. When the window appears after a 1.5s delay, polling using only substring title matching frequently times out or misidentifies existing background processes.

#### Root Cause B4: Lack of Strict Negative System Instruction in Gemini Brain
- **Location:** [main.py](file:///d:/Zye/main.py#L419) and [zye_gemini_live.py](file:///d:/Zye/zye_gemini_live.py#L518-L530)
- **Defect:** Gemini's system instructions lacked explicit zero-false-success grounding. When an MCP tool returns `PROCESS_STARTED` or `LAUNCH_PENDING_OR_BACKGROUND`, Gemini's default conversational bias assumed the application opened and hallucinated "Successfully opened WhatsApp".

---

### 4. Reproduction Protocols

1. **Reproduction Step 1 (Voice Cutoff)**:
   Speak into Zye: *"Zye, check my schedule..."* (pause for 900ms) *"...and read the unread emails."*
   - Observed Result: Zye cuts off after "schedule", sends `end_of_turn`, and begins talking over the user. When the user finishes the sentence, Gemini detects barge-in and aborts speech completely.
2. **Reproduction Step 2 (Application False Success)**:
   Ask Zye: *"Zye, open WhatsApp"* (when WhatsApp process is hung or AppID differs).
   - Observed Result: Tool executes `explorer.exe` or `subprocess.Popen`, returns success/started, and Gemini announces "WhatsApp successfully opened" while desktop remains completely unchanged.

---

### 5. Architectural Repair Strategy (Minimal Change, High Reliability)

1. **Voice Reliability Engine**:
   - Replace crude 9500 RMS threshold with adaptive, calibrated VAD hysteresis matching `zye_audio_ear.py` (start threshold: 0.52, hold: 0.40, silence timeout: 1.5s).
   - Implement true half-duplex playback gating: while Edge-TTS / Pygame or `LiveAudioPlayer` is active, suppress microphone input frames to prevent acoustic self-interruption.
   - Wait for verified playback completion before transitioning state back to `LISTENING`.
   - Prevent task cancellation storms in `run_live_loop` and `main.py`.

2. **Verified Application Execution Engine**:
   - Implement `application_execution_schema.py` defining strict states: `UI_READY`, `WINDOW_VISIBLE`, `ALREADY_OPEN`, `PROCESS_STARTED`, `WINDOW_TIMEOUT`, `APP_NOT_FOUND`, `AMBIGUOUS_APP_MATCH`, `LAUNCH_FAILED`.
   - Implement real window verification combining `pywinauto.Desktop(backend="uia")` and Win32 `GetWindowThreadProcessId` to verify both Win32 and UWP/Store application windows.
   - Update `process_manager.py` and `app_launcher.py` to require verified window emergence before reporting success.
   - Update Gemini system instructions with the **Mandatory Zero-False-Success Rule**.
