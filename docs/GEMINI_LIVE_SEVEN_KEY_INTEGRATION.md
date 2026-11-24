# GEMINI LIVE SEVEN-KEY ROTATION & QUOTA INTEGRATION

## 1. Zero Duplicate Key Infrastructure
Zye AI manages seven Google Cloud project API keys via `GeminiKeyManager` (`ACCOUNT_01` to `ACCOUNT_07`).
The Gemini Live system reuses this existing key infrastructure directly:
- No independent secret stores or redundant `.env` parsers.
- No plaintext API keys are printed in console logs, error messages, or telemetry.
- All display formats use `mask_credential` (e.g. `************ghyg`).

## 2. Session-Based Key Stability
Unlike single-turn stateless REST HTTP calls, Gemini Live operates over stateful WebSocket connections:
- A Live session selects an authorized healthy slot upon connection (default Slot 1 or designated voice slot).
- The key remains associated with the session throughout its connection lifespan to avoid session disruption.
- Telemetry records session start timestamp, duration, input/output audio seconds, and tool execution counts under the respective slot.

## 3. Quota Failover & Health Status
If a slot encounters quota exhaustion (`RESOURCE_EXHAUSTED` / HTTP 429) during connection establishment or GoAway reconnection:
1. `GeminiKeyManager` marks the slot as `RATE_LIMITED`.
2. `ZyeGeminiLiveManager._resolve_authorized_client()` rotates to the next available healthy configured slot (e.g. Slot 2, Slot 3).
3. The new session connects seamlessly without disrupting the desktop assistant lifecycle.
