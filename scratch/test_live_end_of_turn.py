import asyncio
import sys
import time
import numpy as np
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google.genai import types
from gemini_key_manager import GeminiKeyManager
from zye_audio_ear import AudioConfig, AudioCaptureEngine, downmix_to_mono, convert_float32_to_pcm16
from zye_gemini_live import LiveAudioPlayer

async def test():
    print("Initializing test...", flush=True)
    km = GeminiKeyManager()
    slot = km.get_slot(1)

    cfg = types.LiveConnectConfig(
        response_modalities=[types.Modality.AUDIO, types.Modality.TEXT],
        http_options=types.HttpOptions(api_version="v1alpha"),
        system_instruction="You are Zye, an elite personal AI assistant. Reply warmly and briefly in Tamil, English, or Tanglish.",
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

    print("Connecting to Gemini Live...", flush=True)
    async with slot.client.aio.live.connect(model="gemini-3.8-live", config=cfg) as session:
        print("\n>>> ZYE IS LISTENING! Speak now (e.g. 'Hello Zye', 'Enna panra?')...", flush=True)

        user_spoke = False
        silence_frames = 0
        speech_threshold = 7000.0
        silence_threshold_frames = 25 # ~800ms of silence
        turn_done = asyncio.Event()

        async def send_mic():
            nonlocal user_spoke, silence_frames
            while not turn_done.is_set():
                if not capture.frame_queue.empty():
                    frame = capture.frame_queue.get_nowait()
                    mono = downmix_to_mono(frame) if frame.ndim > 1 else frame
                    pcm16_arr = convert_float32_to_pcm16(mono)
                    pcm_bytes = pcm16_arr.tobytes()

                    # Mute during playback unless barge-in
                    if player.is_playing():
                        await asyncio.sleep(0.01)
                        continue

                    # Calculate RMS
                    rms = float(np.sqrt(np.mean(pcm16_arr.astype(np.float32)**2))) if len(pcm16_arr) > 0 else 0.0

                    if rms > speech_threshold:
                        if not user_spoke:
                            print(f"\n[Speech Detected] (RMS={rms:.0f}) Streaming...", flush=True)
                        user_spoke = True
                        silence_frames = 0
                    elif user_spoke:
                        silence_frames += 1
                        if silence_frames >= silence_threshold_frames:
                            print(f"\n[Speech Ended] Silence detected. Sending end_of_turn...", flush=True)
                            await session.send(end_of_turn=True)
                            user_spoke = False
                            silence_frames = 0

                    await session.send_realtime_input(
                        audio=dict(
                            data=pcm_bytes,
                            mime_type="audio/pcm;rate=16000",
                        )
                    )
                await asyncio.sleep(0.01)

        async def recv_events():
            async for response in session.receive():
                server_content = getattr(response, "server_content", None)
                if server_content:
                    model_turn = getattr(server_content, "model_turn", None)
                    if model_turn and model_turn.parts:
                        for part in model_turn.parts:
                            if getattr(part, "text", None):
                                print(part.text, end="", flush=True)
                            if getattr(part, "inline_data", None):
                                audio_data = part.inline_data.data
                                player.queue_chunk(audio_data)

                    if getattr(server_content, "turn_complete", False):
                        print("\n[Zye Finished Speaking]", flush=True)
                        turn_done.set()
                        break

        send_task = asyncio.create_task(send_mic())
        recv_task = asyncio.create_task(recv_events())

        # Wait up to 15s for conversation turn
        try:
            await asyncio.wait_for(turn_done.wait(), timeout=15.0)
        except asyncio.TimeoutError:
            print("\n[Timeout after 15s]", flush=True)
        finally:
            turn_done.set()
            send_task.cancel()
            recv_task.cancel()

    capture.stop()
    time.sleep(1.0)
    player.stop()
    print("Done!", flush=True)

if __name__ == "__main__":
    asyncio.run(test())
