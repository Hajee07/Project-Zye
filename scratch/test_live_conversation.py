import asyncio
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google.genai import types
from gemini_key_manager import GeminiKeyManager
from zye_audio_ear import AudioConfig, AudioCaptureEngine, downmix_to_mono, convert_float32_to_pcm16
from zye_gemini_live import LiveAudioPlayer

async def test():
    print("1. Initializing components...", flush=True)
    km = GeminiKeyManager()
    slot = km.get_slot(1)

    cfg = types.LiveConnectConfig(
        response_modalities=[types.Modality.AUDIO],
        http_options=types.HttpOptions(api_version="v1alpha"),
        system_instruction="You are Zye, a voice assistant. When the user speaks, reply immediately and briefly in Tanglish or English.",
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Aoede")
            )
        ),
    )

    player = LiveAudioPlayer(sample_rate=24000, channels=1)
    player.start()

    audio_cfg = AudioConfig(sample_rate=16000, channels=1)
    capture = AudioCaptureEngine(audio_cfg)
    capture.start()

    print("2. Connecting to Gemini Live (gemini-3.8-live)...", flush=True)
    async with slot.client.aio.live.connect(model="gemini-3.8-live", config=cfg) as session:
        print("3. Connected! Please speak into your microphone NOW for 4 seconds...", flush=True)
        t_start = time.time()
        chunks_sent = 0

        # Stream audio for 4 seconds
        while time.time() - t_start < 4.0:
            if not capture.frame_queue.empty():
                frame = capture.frame_queue.get_nowait()
                mono = downmix_to_mono(frame) if frame.ndim > 1 else frame
                pcm = convert_float32_to_pcm16(mono).tobytes()
                await session.send_realtime_input(
                    audio=dict(
                        data=pcm,
                        mime_type="audio/pcm;rate=16000",
                    )
                )
                chunks_sent += 1
            await asyncio.sleep(0.01)

        print(f"4. Finished recording (sent {chunks_sent} chunks). Sending end_of_turn...", flush=True)
        await session.send(end_of_turn=True)
        print("Waiting for Gemini response...", flush=True)

        # Signal end of turn if needed or listen for response
        try:
            async with asyncio.timeout(10.0):
                async for response in session.receive():
                    server_content = getattr(response, "server_content", None)
                    if server_content:
                        model_turn = getattr(server_content, "model_turn", None)
                        if model_turn and model_turn.parts:
                            for part in model_turn.parts:
                                if getattr(part, "text", None):
                                    print(f"[Gemini Text] {part.text}", flush=True)
                                if getattr(part, "inline_data", None):
                                    audio_data = part.inline_data.data
                                    print(f"[Gemini Audio Chunk] {len(audio_data)} bytes", flush=True)
                                    player.queue_chunk(audio_data)

                        if getattr(server_content, "turn_complete", False):
                            print("5. Turn complete from Gemini!", flush=True)
                            break
        except asyncio.TimeoutError:
            print("5. Timed out waiting for response!", flush=True)

    print("6. Waiting for audio playback to finish...", flush=True)
    time.sleep(2.0)
    capture.stop()
    player.stop()
    print("7. Test completed successfully!", flush=True)

if __name__ == "__main__":
    asyncio.run(test())
