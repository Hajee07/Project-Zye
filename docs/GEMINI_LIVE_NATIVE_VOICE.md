# GEMINI LIVE NATIVE VOICE OUTPUT & PLAYBACK

## 1. Native Audio Generation
Gemini Live synthesizes spoken responses natively in the selected voice persona (`Aoede` by default):
- **Output Format:** Signed 16-bit PCM, little-endian, mono.
- **Output Sample Rate:** 24,000 Hz (`audio/pcm;rate=24000`).
- **Streaming Chunks:** Each chunk arrives as `part.inline_data.data` within `session.receive()` model turns.

## 2. Low-Latency Playback via LiveAudioPlayer
`LiveAudioPlayer` manages hardware playback through `sounddevice.RawOutputStream`:
- Direct signed 16-bit PCM playback at 24 kHz.
- Bounded thread-safe queue prevents memory exhaustion.
- Continuous streaming ensures zero gaps between successive audio chunks.

## 3. Instantaneous Barge-In Cancellation
When the user speaks while Gemini is outputting speech:
1. Gemini Live detects incoming user voice.
2. The server emits `server_content.interrupted = True`.
3. `ZyeGeminiLiveManager` invokes `player.flush()`.
4. `player.flush()` calls `_stream.abort()`, purges all unplayed chunks in the queue, and resets the playback flag.
5. Audio output ceases immediately (< 20 ms perceived stop latency).
