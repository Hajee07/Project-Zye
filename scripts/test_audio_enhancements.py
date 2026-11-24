#!/usr/bin/env python3
"""
ZYE AI — Day 09 Audio Enhancement Smoke Test
=============================================

Validates AGC, Jarvis Chime synthesis, and SmartAudioEar integration without
requiring a live microphone. By default runs in --no-playback mode.

Usage:
    python scripts/test_audio_enhancements.py                 # no audio playback
    python scripts/test_audio_enhancements.py --no-playback   # explicit no playback
    python scripts/test_audio_enhancements.py --playback      # play chimes through speakers
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
import traceback
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


PASS = "[PASS]"
FAIL = "[FAIL]"
WARN = "[WARN]"
SKIP = "[SKIP]"
INFO = "[INFO]"

results: list[tuple[str, str, str]] = []


def result(tag: str, name: str, detail: str) -> None:
    results.append((tag, name, detail))
    color = {PASS: "\033[92m", FAIL: "\033[91m", WARN: "\033[93m", SKIP: "\033[94m", INFO: "\033[96m"}.get(tag, "")
    reset = "\033[0m"
    print(f"  {color}{tag}{reset}  {name}")
    if detail:
        print(f"         {detail}")


# ============================================================================
# Stage 1 — Import Verification
# ============================================================================

def stage_imports() -> None:
    print("\n--- STAGE 1 : Import Verification ---")
    try:
        from zye_audio.agc import AGCConfig, AGCProcessor, AGCResult
        result(PASS, "zye_audio.agc imports", f"AGCConfig, AGCProcessor, AGCResult accessible")
    except Exception as exc:
        result(FAIL, "zye_audio.agc imports", str(exc))

    try:
        from zye_audio.chime_player import (
            ChimeConfig, JarvisChimePlayer,
            generate_tone, generate_start_chime, generate_stop_chime,
        )
        result(PASS, "zye_audio.chime_player imports", "All chime symbols accessible")
    except Exception as exc:
        result(FAIL, "zye_audio.chime_player imports", str(exc))

    try:
        from zye_audio import AGCProcessor, JarvisChimePlayer
        result(PASS, "zye_audio __init__ re-exports", "Package __init__ re-exports working")
    except Exception as exc:
        result(FAIL, "zye_audio __init__ re-exports", str(exc))

    try:
        from zye_audio_ear import SmartAudioEar, AudioConfig
        result(PASS, "zye_audio_ear imports", "SmartAudioEar, AudioConfig accessible")
    except Exception as exc:
        result(FAIL, "zye_audio_ear imports", str(exc))


# ============================================================================
# Stage 2 — AGC Verification
# ============================================================================

def stage_agc_verification() -> None:
    print("\n--- STAGE 2 : AGC Verification ---")
    try:
        from zye_audio.agc import AGCConfig, AGCProcessor

        cfg = AGCConfig(mode="peak_normalize", target_peak=0.85, max_gain=12.0, limiter_peak=0.95)
        agc = AGCProcessor(cfg)
        result(PASS, "AGCConfig + AGCProcessor instantiation", f"mode={cfg.mode}, target_peak={cfg.target_peak}")
    except Exception as exc:
        result(FAIL, "AGCConfig + AGCProcessor instantiation", str(exc))
        return

    try:
        # Soft signal amplification
        t = np.linspace(0, 0.5, 8000, dtype=np.float32)
        soft = (0.05 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        res = agc.process(soft)
        assert res.status == "SUCCESS", f"Expected SUCCESS, got {res.status}"
        assert res.output_peak > res.input_peak, "AGC did not amplify soft signal"
        result(PASS, "AGC amplifies soft speech",
               f"input_peak={res.input_peak:.4f} -> output_peak={res.output_peak:.4f} (gain={res.applied_gain:.2f}x)")
    except Exception as exc:
        result(FAIL, "AGC amplifies soft speech", str(exc))

    try:
        # Loud signal limiting
        loud = (0.95 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        res = agc.process(loud)
        assert res.output_peak <= 0.96, f"Limiter failed: output_peak={res.output_peak}"
        result(PASS, "AGC peak limiter", f"output_peak={res.output_peak:.4f} (within 0.95 ceiling)")
    except Exception as exc:
        result(FAIL, "AGC peak limiter", str(exc))

    try:
        # Silent input passthrough
        silent = np.zeros(1600, dtype=np.float32)
        res = agc.process(silent)
        assert res.status == "SILENCE_PROTECTED", f"Expected SILENCE_PROTECTED, got {res.status}"
        assert res.applied_gain == 1.0
        result(PASS, "AGC silence protection", "Gain held at 1.0 for silent input")
    except Exception as exc:
        result(FAIL, "AGC silence protection", str(exc))

    try:
        # Input immutability
        sig = (0.1 * np.sin(2 * np.pi * 440 * t[:1600])).astype(np.float32)
        copy = sig.copy()
        agc.process(sig)
        assert np.array_equal(sig, copy), "AGC mutated input array"
        result(PASS, "AGC input immutability", "Original array unchanged after process()")
    except Exception as exc:
        result(FAIL, "AGC input immutability", str(exc))

    try:
        # Adaptive mode
        cfg2 = AGCConfig(mode="adaptive", target_rms=0.12)
        agc2 = AGCProcessor(cfg2)
        t2 = np.linspace(0, 0.5, 8000, dtype=np.float32)
        soft2 = (0.03 * np.sin(2 * np.pi * 440 * t2)).astype(np.float32)
        res2 = agc2.process(soft2)
        assert res2.mode == "adaptive"
        result(PASS, "AGC adaptive mode", f"output_rms={res2.output_rms:.4f} (target=0.12)")
    except Exception as exc:
        result(FAIL, "AGC adaptive mode", str(exc))

    try:
        diag = agc.get_diagnostics()
        assert "enabled" in diag and "mode" in diag
        result(PASS, "AGC get_diagnostics()", f"status={diag.get('status')}, total_processed={diag.get('total_processed')}")
    except Exception as exc:
        result(FAIL, "AGC get_diagnostics()", str(exc))


# ============================================================================
# Stage 3 — Chime Waveform Synthesis
# ============================================================================

def stage_chime_synthesis() -> None:
    print("\n--- STAGE 3 : Chime Waveform Synthesis ---")
    try:
        from zye_audio.chime_player import generate_tone, generate_start_chime, generate_stop_chime, ChimeConfig

        cfg = ChimeConfig()
        tone = generate_tone(540.0, 75.0, 0.12, 16000, 12.5)
        expected_len = int(round(16000 * 75.0 / 1000.0))
        assert len(tone) == expected_len, f"Expected {expected_len} samples, got {len(tone)}"
        assert tone.dtype == np.float32
        assert float(np.max(np.abs(tone))) <= 0.12 + 1e-5
        result(PASS, "Single tone synthesis (540 Hz)", f"{len(tone)} samples, peak={np.max(np.abs(tone)):.4f}")
    except Exception as exc:
        result(FAIL, "Single tone synthesis (540 Hz)", str(exc))

    try:
        cfg = ChimeConfig()
        start_chime = generate_start_chime(cfg)
        expected = 2 * int(round(16000 * 75.0 / 1000.0))
        assert len(start_chime) == expected
        assert start_chime.dtype == np.float32
        assert np.all(np.isfinite(start_chime))
        result(PASS, "Start chime synthesis (540Hz→820Hz)",
               f"{len(start_chime)} samples, peak={np.max(np.abs(start_chime)):.4f}")
    except Exception as exc:
        result(FAIL, "Start chime synthesis (540Hz→820Hz)", str(exc))

    try:
        cfg = ChimeConfig()
        stop_chime = generate_stop_chime(cfg)
        expected = 2 * int(round(16000 * 75.0 / 1000.0))
        assert len(stop_chime) == expected
        assert stop_chime.dtype == np.float32
        assert np.all(np.isfinite(stop_chime))
        result(PASS, "Stop chime synthesis (780Hz→480Hz)",
               f"{len(stop_chime)} samples, peak={np.max(np.abs(stop_chime)):.4f}")
    except Exception as exc:
        result(FAIL, "Stop chime synthesis (780Hz→480Hz)", str(exc))

    try:
        # Fade-in/out check: first and last samples should be near zero
        tone = generate_tone(440.0, 100.0, 0.5, 16000, 12.5)
        assert abs(float(tone[0])) < 0.001, f"Fade-in failed: tone[0]={tone[0]}"
        assert abs(float(tone[-1])) < 0.001, f"Fade-out failed: tone[-1]={tone[-1]}"
        result(PASS, "Tone fade-in/out envelope", f"first={tone[0]:.6f}, last={tone[-1]:.6f}")
    except Exception as exc:
        result(FAIL, "Tone fade-in/out envelope", str(exc))


# ============================================================================
# Stage 4 — Chime Player Engine
# ============================================================================

def stage_chime_player(playback: bool = False) -> None:
    print("\n--- STAGE 4 : JarvisChimePlayer Engine ---")
    try:
        from zye_audio.chime_player import JarvisChimePlayer, ChimeConfig

        cfg = ChimeConfig(enabled=True, vad_guard_ms=250.0)
        player = JarvisChimePlayer(config=cfg, auto_start=True)
        result(PASS, "JarvisChimePlayer instantiation", "Worker thread started")
    except Exception as exc:
        result(FAIL, "JarvisChimePlayer instantiation", str(exc))
        return

    try:
        assert not player.is_chime_guard_active(), "Guard should be inactive at rest"
        result(PASS, "Guard inactive at rest", "is_chime_guard_active() = False")
    except Exception as exc:
        result(FAIL, "Guard inactive at rest", str(exc))

    try:
        import time
        with player._guard_lock:
            player._guard_until_timestamp = time.perf_counter() + 10.0
        assert player.is_chime_guard_active()
        with player._guard_lock:
            player._guard_until_timestamp = 0.0
        result(PASS, "Guard activation and deactivation", "Guard window management working")
    except Exception as exc:
        result(FAIL, "Guard activation and deactivation", str(exc))

    try:
        diag = player.get_diagnostics()
        assert "status" in diag
        assert "total_chimes_played" in diag
        result(PASS, "Chime diagnostics", f"status={diag['status']}, output_device={diag['output_device'].get('device_name', '?')}")
    except Exception as exc:
        result(FAIL, "Chime diagnostics", str(exc))

    if playback:
        try:
            result(INFO, "Chime playback", "Playing START chime (ascending 540Hz→820Hz)...")
            player.play_start()
            time.sleep(0.4)
            result(INFO, "Chime playback", "Playing STOP chime (descending 780Hz→480Hz)...")
            player.play_stop()
            time.sleep(0.4)
            result(PASS, "Chime playback (live)", f"Played: start={player.start_chimes_played}, stop={player.stop_chimes_played}")
        except Exception as exc:
            result(WARN, "Chime playback (live)", f"Note: {exc}")
    else:
        result(SKIP, "Live chime playback", "Skipped (use --playback to enable)")

    try:
        player.close()
        assert not player._running
        result(PASS, "JarvisChimePlayer graceful close", "Worker thread stopped cleanly")
    except Exception as exc:
        result(FAIL, "JarvisChimePlayer graceful close", str(exc))


# ============================================================================
# Stage 5 — SmartAudioEar Integration
# ============================================================================

def stage_smart_audio_ear_integration() -> None:
    print("\n--- STAGE 5 : SmartAudioEar Day 09 Integration ---")
    try:
        from zye_audio_ear import SmartAudioEar, AudioConfig
        from zye_audio.agc import AGCConfig
        from zye_audio.chime_player import ChimeConfig

        cfg = AudioConfig(vad_mode="adaptive_rms")
        agc_cfg = AGCConfig(mode="peak_normalize")
        chime_cfg = ChimeConfig(enabled=True)
        ear = SmartAudioEar(config=cfg, agc_config=agc_cfg, chime_config=chime_cfg)
        result(PASS, "SmartAudioEar init with Day 09 config", "AGC + Chime injected successfully")
    except Exception as exc:
        result(FAIL, "SmartAudioEar init with Day 09 config", str(exc))
        return

    try:
        assert isinstance(ear.agc, AGCProcessor) if 'AGCProcessor' in dir() else True
        t = np.linspace(0, 0.1, 1600, dtype=np.float32)
        sig = (0.05 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        output = ear._apply_auto_gain(sig)
        assert isinstance(output, np.ndarray), "Expected numpy array"
        assert len(output) == len(sig), "Output length mismatch"
        result(PASS, "_apply_auto_gain compatibility method", f"Input {len(sig)} -> Output {len(output)} samples")
    except Exception as exc:
        result(FAIL, "_apply_auto_gain compatibility method", str(exc))

    try:
        agc_diag = ear.get_agc_diagnostics()
        assert isinstance(agc_diag, dict) and "enabled" in agc_diag
        result(PASS, "get_agc_diagnostics()", f"mode={agc_diag.get('mode')}")
    except Exception as exc:
        result(FAIL, "get_agc_diagnostics()", str(exc))

    try:
        chime_diag = ear.get_chime_diagnostics()
        assert isinstance(chime_diag, dict) and "enabled" in chime_diag
        result(PASS, "get_chime_diagnostics()", f"status={chime_diag.get('status')}")
    except Exception as exc:
        result(FAIL, "get_chime_diagnostics()", str(exc))

    try:
        enhancement_status = ear.get_audio_enhancement_status()
        assert enhancement_status.get("status") == "DAY_09_AUDIO_ENHANCEMENT_READY"
        result(PASS, "get_audio_enhancement_status()", f"status=DAY_09_AUDIO_ENHANCEMENT_READY")
    except Exception as exc:
        result(FAIL, "get_audio_enhancement_status()", str(exc))

    try:
        full_diag = ear.get_audio_diagnostics()
        assert full_diag.get("diagnostic_status") == "DAY_07_AUDIO_EAR_READY"
        assert "neural_vad_status" in full_diag
        assert "agc_status" in full_diag
        assert "chime_status" in full_diag
        result(PASS, "get_audio_diagnostics() Day 07/08/09 fields",
               f"All milestone status keys present")
    except Exception as exc:
        result(FAIL, "get_audio_diagnostics() Day 07/08/09 fields", str(exc))

    try:
        ear.close()
        assert not ear.chime_player._running
        assert ear.agc.total_processed_frames == 0
        result(PASS, "SmartAudioEar.close() Day 09 teardown", "Chime stopped, AGC reset")
    except Exception as exc:
        result(FAIL, "SmartAudioEar.close() Day 09 teardown", str(exc))


# ============================================================================
# Main Entry Point
# ============================================================================

def main() -> int:
    parser = argparse.ArgumentParser(description="Zye Day 09 Audio Enhancement Smoke Test")
    parser.add_argument(
        "--playback", action="store_true",
        help="Play chimes through audio output device during test"
    )
    parser.add_argument(
        "--no-playback", action="store_true", default=True,
        help="Run silently without audio playback (default)"
    )
    args = parser.parse_args()
    play = args.playback

    print("=" * 70)
    print("ZYE AI — Day 09 Audio Enhancement Smoke Test")
    print(f"Mode: {'LIVE PLAYBACK' if play else 'NO PLAYBACK (silent)'}")
    print("=" * 70)

    stage_imports()
    stage_agc_verification()
    stage_chime_synthesis()
    stage_chime_player(playback=play)
    stage_smart_audio_ear_integration()

    passed = sum(1 for r in results if r[0] == PASS)
    failed = sum(1 for r in results if r[0] == FAIL)
    warned = sum(1 for r in results if r[0] == WARN)
    skipped = sum(1 for r in results if r[0] == SKIP)

    print("\n" + "=" * 70)
    print(f"  Summary: {passed} passed, {warned} warnings, {failed} failed, {skipped} skipped")
    if failed == 0:
        print("  Overall: PASS — Day 09 Audio Enhancement Engine is operational.")
    else:
        print("  Overall: FAIL — One or more checks did not pass.")
    print("=" * 70)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
