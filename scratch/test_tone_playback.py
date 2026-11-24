import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import numpy as np
import sounddevice as sd
from zye_gemini_live import LiveAudioPlayer

print("Default output device:", sd.default.device[1])
player = LiveAudioPlayer(sample_rate=24000, channels=1)
player.start()

# Generate 1.0 second 440Hz sine wave at 24000Hz
sample_rate = 24000
duration = 1.0
t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
sine = (np.sin(2 * np.pi * 440 * t) * 0.3 * 32767).astype(np.int16)
pcm_bytes = sine.tobytes()

print("Queueing tone chunk into LiveAudioPlayer...")
# Split into chunks of 1024 frames
chunk_size = 1024 * 2 # 2 bytes per int16
for i in range(0, len(pcm_bytes), chunk_size):
    chunk = pcm_bytes[i:i+chunk_size]
    player.queue_chunk(chunk)

print("Playing tone...")
time.sleep(1.2)
print("Finished playing. Total played:", player.total_chunks_played, "chunks,", player.total_bytes_played, "bytes")
player.stop()
