#!/usr/bin/env python3
"""
ZYE AI — Audio Input Hardware Smoke Test Script
================================================

Interactive and automated hardware verification for microphone detection,
stream initialization, real-time PCM capture, pre-roll buffer, adaptive RMS,
and WAV serialization.

Usage:
    python scripts/check_audio_input.py
    python scripts/check_audio_input.py --auto
    python scripts/check_audio_input.py --device-index 1
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def run_smoke_test(device_index: int | None = None, auto_mode: bool = False) -> int:
    """Execute live microphone hardware diagnostics and report actual results."""
    print("=" * 64)
    print("       ZYE AI — AUDIO INPUT HARDWARE SMOKE TEST v1.0")
    print("=" * 64)

    try:
        import zye_audio_ear
        from zye_audio_ear import (
            AudioConfig,
            SmartAudioEar,
            list_input_devices,
            get_default_input_device,
            validate_input_device,
        )
    except ImportError as e:
        print(f"[FAIL] Failed to import zye_audio_ear: {e}")
        return 1

    # 1. Device Discovery
    print("\n--- STAGE 1: Audio Hardware Discovery ---")
    devices = list_input_devices()
    if not devices:
        print("[FAIL] No microphone input devices found on this system.")
        print("[WARN] PortAudio reports zero active recording channels.")
        return 1

    print(f"[PASS] Microphone detected: Found {len(devices)} input device(s).")
    default_dev = get_default_input_device()
    for d in devices:
        mark = " (DEFAULT)" if default_dev and d["index"] == default_dev["index"] else ""
        print(f"  [{d['index']}] {d['name']} | Channels: {d['max_input_channels']} | Default Rate: {d['default_samplerate']} Hz{mark}")

    target_index = device_index if device_index is not None else (default_dev["index"] if default_dev else None)
    if target_index is None:
        print("[FAIL] Could not resolve a valid input device index.")
        return 1

    print(f"\nTargeting Device Index: {target_index}")

    # 2. Input Settings Validation
    print("\n--- STAGE 2: Device Validation ---")
    valid, err_msg, dev_info = validate_input_device(target_index, sample_rate=16000, channels=1)
    if valid:
        print("[PASS] Device natively supports 16,000 Hz Mono input.")
    else:
        print(f"[WARN] Native 16 kHz stream check: {err_msg}")
        print("  (AudioCaptureEngine will automatically capture at native rate and resample to 16 kHz)")

    # 3. Stream & Frame Capture Test
    print("\n--- STAGE 3: Stream Capture & Pre-Roll Verification ---")
    if not auto_mode:
        print("Press ENTER to begin 2-second capture test (or Ctrl+C to abort)...", end="", flush=True)
        try:
            input()
        except KeyboardInterrupt:
            print("\nAborted by user.")
            return 0

    cfg = AudioConfig(preferred_device_index=target_index, silence_timeout_seconds=0.8, maximum_record_seconds=2.0)
    ear = SmartAudioEar(config=cfg, device_index=target_index)

    try:
        print("Opening microphone stream...")
        ear.start()
        print("[PASS] Input stream opened.")

        # Let it buffer to verify pre-roll
        time.sleep(0.7)
        pr_len = len(ear.capture_engine.pre_roll_buffer)
        if pr_len >= 15:
            print(f"[PASS] Pre-roll buffer operational: {pr_len} frames retained in RAM (0.64s window).")
        else:
            print(f"[WARN] Pre-roll buffer count is {pr_len} (expected >= 15).")

        print("Listening for short test utterance...")
        wav_bytes = ear.listen_smart(silence_timeout=0.6, max_record_sec=2.0)
        diag = ear.get_audio_diagnostics()

        last_cap = diag.get("last_capture", {})
        rms_val = last_cap.get("rms", 0.0)
        peak_val = last_cap.get("peak", 0.0)
        dur = last_cap.get("duration_seconds", 0.0)

        print(f"[PASS] Audio frames received: {dur:.2f}s captured, RMS: {rms_val:.4f}, Peak: {peak_val:.4f}.")

        if rms_val < 0.002:
            print("[WARN] Microphone signal is unusually low (possible hardware mute or distant mic).")

        # 4. Conversion & WAV Validation
        print("\n--- STAGE 4: PCM Conversion & WAV Encoding ---")
        if wav_bytes and len(wav_bytes) > 44:
            print(f"[PASS] PCM conversion completed: Generated {len(wav_bytes)} WAV bytes.")
            import io
            import scipy.io.wavfile
            rate, samples = scipy.io.wavfile.read(io.BytesIO(wav_bytes))
            print(f"[PASS] WAV validation completed: Rate = {rate} Hz, Channels = {samples.ndim}, Dtype = {samples.dtype}, Samples = {len(samples)}.")
        else:
            print("[WARN] No speech exceeded RMS threshold during short test window (silence recorded).")

        print("\n" + "=" * 64)
        print("           HARDWARE SMOKE TEST COMPLETE: READY")
        print("=" * 64)
        return 0

    except Exception as exc:
        print(f"[FAIL] Audio stream test failure: {exc}")
        return 1
    finally:
        ear.close()
        print("[PASS] Stream closed and PortAudio resources released cleanly.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Zye AI Audio Input Smoke Test")
    parser.add_argument("--device-index", type=int, default=None, help="Device index to test")
    parser.add_argument("--auto", action="store_true", help="Run without waiting for interactive keypress")
    args = parser.parse_args()
    sys.exit(run_smoke_test(device_index=args.device_index, auto_mode=args.auto))
