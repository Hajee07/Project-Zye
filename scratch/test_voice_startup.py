import asyncio
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

print("[STEP 0] Script started", flush=True)
t0 = time.time()

print("[STEP 1] Importing main...", flush=True)
from main import ZyeVoiceLoop
print(f"[STEP 1] Imported main in {time.time()-t0:.2f}s", flush=True)

async def main():
    t1 = time.time()
    print("[STEP 2] Creating ZyeVoiceLoop...", flush=True)
    loop = ZyeVoiceLoop()
    print(f"[STEP 2] ZyeVoiceLoop created in {time.time()-t1:.2f}s", flush=True)

    t2 = time.time()
    print("[STEP 3] Initializing tts_engine...", flush=True)
    if loop.tts_engine:
        await loop.tts_engine.initialize()
    print(f"[STEP 3] tts_engine initialized in {time.time()-t2:.2f}s", flush=True)

    t3 = time.time()
    print("[STEP 4] Initializing brain...", flush=True)
    if loop.brain:
        await loop.brain.initialize()
    print(f"[STEP 4] brain initialized in {time.time()-t3:.2f}s", flush=True)

    t4 = time.time()
    print("[STEP 5] Registering hotkey...", flush=True)
    if loop.hotkey_controller:
        loop.hotkey_controller.register()
    print(f"[STEP 5] hotkey registered in {time.time()-t4:.2f}s", flush=True)

    t5 = time.time()
    print("[STEP 6] Testing _speak...", flush=True)
    announcement = "Zye online. Diagnostic test."
    try:
        await asyncio.wait_for(loop._speak(announcement), timeout=5.0)
        print(f"[STEP 6] _speak completed in {time.time()-t5:.2f}s", flush=True)
    except asyncio.TimeoutError:
        print("[STEP 6] _speak TIMED OUT after 5.0s!", flush=True)
    except Exception as e:
        print(f"[STEP 6] _speak error: {e}", flush=True)

    print("[STEP 7] Testing audio ear device detection...", flush=True)
    if loop.ear:
        print(f"Ear present: {loop.ear}", flush=True)
        if hasattr(loop.ear, "capture_engine"):
            print(f"Capture engine: {loop.ear.capture_engine}", flush=True)

    print("[STEP 8] Testing live_manager...", flush=True)
    if loop.live_manager:
        print(f"Live manager: {loop.live_manager}", flush=True)
        print(f"Live manager model: {loop.live_manager.config.model_id}", flush=True)
        print(f"Live manager fallback: {loop.live_manager.config.fallback_model_id}", flush=True)

    print("[STEP 9] Shutting down cleanly...", flush=True)
    await loop._shutdown()
    print("[STEP 10] Complete!", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
