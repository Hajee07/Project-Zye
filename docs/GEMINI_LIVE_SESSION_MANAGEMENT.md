# GEMINI LIVE SESSION MANAGEMENT & RESUMPTION

## 1. Lifecycle States
A Gemini Live connection traverses strict explicit states defined in `LiveSessionState`:
- `IDLE` -> `CONNECTING` -> `CONNECTED` -> `LISTENING`
- `LISTENING` -> `USER_SPEAKING` -> `PROCESSING` -> `RESPONDING`
- Interruption: `RESPONDING` -> `INTERRUPTED` -> `LISTENING`
- Tool Calling: `PROCESSING` -> `TOOL_CALL_PENDING` -> `TOOL_RUNNING` -> `PROCESSING`
- Disconnection: `CONNECTED` -> `RECONNECTING` -> `CONNECTED` (or `DEGRADED`)

## 2. Session Resumption
When connecting with `session_resumption = true`:
1. The server supplies a session resumption token or handle in the `setup_complete` message.
2. `ZyeGeminiLiveManager` caches this handle in `telemetry.resumption_handle`.
3. If a transient network glitch or GoAway message occurs, subsequent connection requests supply `SessionResumptionConfig(handle=...)`.
4. If the server validates the handle, previous conversational context is preserved.
5. If the handle has expired or is rejected, a clean fresh session is established automatically.

## 3. GoAway Event Handling & Reconnection Backoff
Google Cloud servers periodically send `GoAway` messages when server maintenance or maximum connection duration is approached:
- `ZyeGeminiLiveManager` detects `response.go_away`.
- It flushes current buffers and gracefully closes the WebSocket.
- An exponential/bounded backoff (1.5s delay) initiates a clean reconnect.
- Up to `max_reconnect_attempts = 5` attempts are performed before entering `DEGRADED` fallback mode.
