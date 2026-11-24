# ZYE AI — Desktop HUD & WebSocket Telemetry Report

**Subsystem:** `zye_desktop` (`ws_bridge.py`), `desktop` (`overlay.html`)  
**Specification:** Master Specification Section 30  
**Status:** VERIFIED & PASSING  

---

## 1. Overview

Provides a lightweight, floating Windows desktop Heads-Up Display (HUD) overlay that connects via a secure local loopback WebSocket server (`ws://127.0.0.1:8765`) to stream real-time assistant state, audio waveforms, host resource metrics, and tool execution traces.

---

## 2. Architecture & Components

### 2.1 Desktop WebSocket Bridge (`ws_bridge.py`)
- Strictly bound to loopback `127.0.0.1:8765` to prevent external network exposure.
- Subscribes to `ZyeEventBus.subscribe_all` to automatically format and broadcast state changes to connected HUD clients.
- State mapping:
  - `USER_SPEECH_STARTED` $\rightarrow$ `LISTENING`
  - `MODEL_REQUEST_STARTED` $\rightarrow$ `THINKING`
  - `AUDIO_PLAYBACK_STARTED` $\rightarrow$ `SPEAKING`
  - `TOOL_EXECUTION_STARTED` $\rightarrow$ `EXECUTING_TOOL`
  - `AUDIO_PLAYBACK_DRAINED` / `USER_SPEECH_COMPLETED` $\rightarrow$ `IDLE`
- Bidirectional protocol: Supports `ping`/`pong` heartbeat and `get_status` telemetry requests.

### 2.2 Glassmorphism Desktop Overlay (`desktop/overlay.html`)
- Floating overlay with semi-transparent frosted glass aesthetic (`backdrop-filter: blur(24px)`).
- HTML5 Canvas real-time sine visualizer simulating voice input/output amplitude.
- Real-time Memory & CPU utilization gauges with color-coded status badges.
- Live scrolling event log showing tool invocations and system milestones.
- Auto-reconnect WebSocket loop.

---

## 3. Test Evidence

```
tests/test_desktop_hud.py::test_overlay_html_file_structure PASSED                     [ 33%]
tests/test_desktop_hud.py::test_desktop_bridge_state_transitions_on_bus_events PASSED [ 66%]
tests/test_desktop_hud.py::test_desktop_bridge_handshake_and_commands PASSED          [100%]
```
- **CLI Verification:** `python doctor.py --hud-health` returned exit code 0.
