# GEMINI LIVE AUDIO STREAMING PIPELINE

## 1. Microphone Acquisition & Real-Time Framing
The hardware microphone stream is acquired using `sounddevice.InputStream` via `AudioCaptureEngine`:
- **Native Hardware Format:** Negotiated default rate (e.g. 44,100 Hz or 48,000 Hz), stereo or mono, float32 samples in `[-1.0, 1.0]`.
- **Downmixing:** `downmix_to_mono` calculates the mean across channels for multi-channel input.
- **Polyphase Resampling:** `resample_audio` uses `scipy.signal.resample_poly` to convert native rate to exactly 16,000 Hz.
- **PCM16 Conversion:** `convert_float32_to_pcm16` scales float32 samples by 32,767.0, clips safely to `[-32768, 32767]`, and converts to `np.int16` little-endian byte array.

## 2. Real-Time Streaming via WebSocket
The raw PCM16 chunk (typically 512 samples = 32 ms) is streamed directly into the active `AsyncSession` using `send_realtime_input`:
```python
await session.send_realtime_input(
    audio=dict(
        data=pcm_bytes,
        mime_type="audio/pcm;rate=16000",
    )
)
```
- No WAV headers are transmitted.
- No temporary audio files are written to disk.
- Pure memory streaming achieves sub-10ms upload framing latency.

## 3. Server-Side Turn Detection (VAD)
Gemini Live's server-side VAD automatically detects:
- Speech initiation (transitioning turn state to `USER_SPEAKING`).
- Speech termination / pause completion (transitioning turn state to `PROCESSING`).
- Natural pauses in Tamil / Tanglish sentences without prematurely terminating the turn.
