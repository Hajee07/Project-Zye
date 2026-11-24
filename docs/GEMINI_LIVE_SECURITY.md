# GEMINI LIVE SECURITY & PRIVACY POLICY

## 1. Zero Credential Exposure
- No API keys are passed over raw command line arguments or standard input/output.
- WebSocket authorization uses standard SSL TLS 1.3 encryption with HTTP header / query token hashing.
- Telemetry logs redact all credential strings using `mask_credential()`.

## 2. Audio Privacy & Ephemeral Buffering
- Raw microphone audio chunks are buffered strictly in ephemeral RAM (`asyncio.Queue` / ring buffer).
- No uncompressed or recorded audio files are retained to disk unless developer diagnostic mode is explicitly enabled by the user with sanitized temporary storage.
- Audio input streaming stops immediately when the user commands "stop listening" or presses Alt+Z.

## 3. Tool Authorization & Non-Idempotent Boundaries
- Dangerous or destructive actions (file deletion, power management, payment, code overwrites) cannot be triggered blindly through ambiguous speech recognition.
- Every function call passes through `ZyeExecutionGate` and `ZyeNegativePreMortem` before reaching local MCP servers.
- Non-idempotent operations are tracked with unique operation identifiers to prevent duplicate execution during retries or reconnections.
