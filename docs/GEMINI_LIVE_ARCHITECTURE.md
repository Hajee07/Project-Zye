# ZYE AI — GEMINI LIVE NATIVE AUDIO MASTER BRAIN ARCHITECTURE

## 1. System Overview
Zye AI integrates Google Gemini Live as the native conversational and speech reasoning authority for Windows Desktop.
Rather than employing a decoupled speech-to-text pipeline (e.g. Whisper or external STT) that converts user speech to text before calling a separate reasoning LLM, Gemini Live receives raw microphone audio directly via a bidirectional streaming WebSocket session.

```
USER SPEAKS (Tamil / English / Tanglish)
       |
       v
WINDOWS MICROPHONE (Hardware Input)
       |
       v
ZYE AUDIO EAR / CAPTURE ENGINE
       |
       v
PCM 16kHz MONO LITTLE-ENDIAN CONVERSION
       |
       v
GEMINI LIVE WEBSOCKET SESSION (v1alpha GenerativeService.BidiGenerateContent)
       |
       +------------------------------------+
       |                                    |
       v                                    v
NATIVE AUDIO UNDERSTANDING          SERVER-SIDE AUTOMATIC VAD
       |                                    |
       +------------------+-----------------+
                          |
                          v
                 GEMINI MASTER BRAIN
               (Supreme Reasoning Arbiter)
                          |
                          v
                MCP FUNCTION CALL
                          |
                          v
             ZYE EXECUTION GATE / PRE-MORTEM
                          |
                          v
              ZYE MCP ORCHESTRATOR
                          |
                          v
            REAL REGISTERED MCP TOOLS (351 Tools)
                          |
                          v
                STRUCTURED TOOL RESULT
                          |
                          v
             GEMINI LIVE FUNCTION RESPONSE
                          |
                          v
             GEMINI NATIVE AUDIO (24kHz PCM)
                          |
                          v
              LIVE AUDIO PLAYER QUEUE
       (Full-Duplex Barge-In Interruption Guard)
                          |
                          v
              WINDOWS AUDIO PLAYBACK
```

## 2. Core Architectural Invariants
1. **Single Master Brain:** Gemini Live is not a second brain or a disconnected chatbot; it operates as the live multimodal execution mode of the unified Gemini Master Brain.
2. **7-Slot Key Manager Integration:** WebSocket authentication is managed through `GeminiKeyManager` across Slots 1 through 7, reusing existing quota and project allocations without exposing plaintext secrets.
3. **No Duplicate Tool Authority:** All tool executions flow exclusively through the existing `ZyeMCPExecutionRouter` and `SafetyExecutionGateway` / `ZyeExecutionGate`.
4. **Native Audio In / Native Audio Out:** Audio input is 16,000 Hz signed 16-bit PCM little-endian. Audio output is 24,000 Hz signed 16-bit PCM little-endian.
5. **Full Duplex Barge-In:** When the user interrupts Gemini while it is speaking, Gemini Live detects user speech and emits `server_content.interrupted = True`. `LiveAudioPlayer.flush()` instantaneously discards remaining queued audio and stops playback.
