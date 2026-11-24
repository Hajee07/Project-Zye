import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from zye_gemini_live import LiveAudioPlayer

player = LiveAudioPlayer()
print("Starting LiveAudioPlayer...")
player.start()
print("LiveAudioPlayer started! _running:", player._running)
time.sleep(0.5)
player.stop()
print("LiveAudioPlayer stopped cleanly!")
