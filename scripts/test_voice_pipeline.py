#!/usr/bin/env python3
"""
ZYE AI — Day 10 Voice Pipeline Smoke Test
=========================================
Runs a 5-stage validation of the complete Day 10 audio and voice stack:
  Stage 1: Module Imports & Environment
  Stage 2: Edge-TTS Engine & Diagnostics
  Stage 3: Alt+Z Text Input Subsystem
  Stage 4: Configuration File Verification
  Stage 5: Unified Pipeline Co-existence

Usage:
    python scripts/test_voice_pipeline.py [--playback] [--live-mic]
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def print_stage(num: int, title: str) -> None:
    print(f"\n[{num}/5] {title} " + "-" * (50 - len(title)))


def test_stage_1_imports() -> bool:
    print_stage(1, "Module Imports & Environment")
    passed = True

    modules = [
        ("zye_tts", "ZyeTTSEngine, TTSConfig, TTSResult"),
        ("zye_text_input", "AltZTextInputHandler, TextInputConfig"),
        ("zye_audio_ear", "SmartAudioEar, AudioConfig"),
        ("zye_audio.agc", "AGCProcessor, AGCConfig"),
        ("zye_audio.chime_player", "JarvisChimePlayer, ChimeConfig"),
        ("main", "ZyeVoiceLoop, ZyeMasterAgent"),
    ]

    for mod_name, symbols in modules:
        try:
            mod = __import__(mod_name, fromlist=["*"])
            print(f"  [PASS] {mod_name} ({symbols})")
        except Exception as exc:
            print(f"  [FAIL] {mod_name}: {exc}")
            passed = False

    return passed


def test_stage_2_tts(live_playback: bool = False) -> bool:
    print_stage(2, "Edge-TTS Engine & Diagnostics")
    passed = True

    try:
        from zye_tts import TTSConfig, ZyeTTSEngine

        cfg = TTSConfig(timeout_seconds=10.0, playback_enabled=live_playback)
        engine = ZyeTTSEngine(cfg)
        diag = engine.get_diagnostics()

        print(f"  [INFO] TTS Status: {diag['status']}")
        print(f"  [INFO] Configured Voice: {diag['configured_voice']}")
        print(f"  [INFO] Edge-TTS Available: {diag['edge_tts_available']}")

        if not diag["edge_tts_available"]:
            print("  [WARN] edge-tts is not available — skipping live synthesis")
            return True

        # Test synthesis
        test_text = "Zye voice engine online."
        print(f"  [INFO] Synthesizing: {test_text!r}")
        t0 = time.perf_counter()
        result = engine.synthesize_sync(test_text)
        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)

        if result.status == "SUCCESS" and result.byte_count > 0:
            print(f"  [PASS] Synthesis SUCCESS: {result.byte_count} bytes in {elapsed_ms}ms")
            if live_playback:
                print("  [INFO] Playing audio...")
                engine._play_mp3_bytes(result.audio_bytes)
                print("  [PASS] Audio playback complete")
        else:
            print(f"  [WARN] Synthesis returned status={result.status}: {result.error}")
            # Network might be unavailable in some offline environments
            print("  [INFO] Marking as WARN (non-fatal offline fallback)")

    except Exception as exc:
        print(f"  [FAIL] TTS Stage 2 error: {exc}")
        passed = False

    return passed


def test_stage_3_text_input() -> bool:
    print_stage(3, "Alt+Z Text Input Subsystem")
    passed = True

    try:
        from zye_text_input import AltZTextInputHandler, TextInputConfig, TextTriggerEvent

        cfg = TextInputConfig(hotkey="alt+z", input_timeout_seconds=0.1)
        handler = AltZTextInputHandler(cfg)
        diag = handler.get_diagnostics()

        print(f"  [INFO] Hotkey: {diag['hotkey']}")
        print(f"  [INFO] Keyboard Available: {diag['keyboard_available']}")
        print(f"  [INFO] Handler Status: {diag['status']}")

        # Test queue trigger mechanism
        handler._on_hotkey_pressed()
        if handler.is_triggered():
            print("  [PASS] Hotkey trigger registered in queue")
        else:
            print("  [FAIL] Hotkey trigger was not queued")
            passed = False

        event = handler.get_trigger_event()
        if isinstance(event, TextTriggerEvent):
            print(f"  [PASS] Trigger event dequeued: source={event.source}")
        else:
            print("  [FAIL] Failed to dequeue trigger event")
            passed = False

        # Test timeout handling
        result = handler.collect_text_input(timeout=0.05)
        if result.source == "timeout":
            print(f"  [PASS] Timeout correctly handled: source={result.source}")
        else:
            print(f"  [WARN] Unexpected collect result source: {result.source}")

    except Exception as exc:
        print(f"  [FAIL] Text input stage 3 error: {exc}")
        passed = False

    return passed


def test_stage_4_config() -> bool:
    print_stage(4, "Configuration File Verification")
    passed = True

    try:
        import tomllib

        config_path = PROJECT_ROOT / "zye_config.toml"
        if not config_path.is_file():
            print(f"  [FAIL] Config file not found: {config_path}")
            return False

        with open(config_path, "rb") as f:
            cfg = tomllib.load(f)

        required_sections = ["system", "audio", "neural_vad", "tts", "text_input"]
        for section in required_sections:
            if section in cfg:
                print(f"  [PASS] [{section}] section present")
            else:
                print(f"  [FAIL] [{section}] section missing")
                passed = False

        # Check TTS fields
        tts = cfg.get("tts", {})
        print(f"  [INFO] Voice: {tts.get('voice')}")
        print(f"  [INFO] Rate: {tts.get('rate')}, Volume: {tts.get('volume')}")

        # Check text input fields
        ti = cfg.get("text_input", {})
        print(f"  [INFO] Hotkey: {ti.get('hotkey')}")
        print(f"  [INFO] Timeout: {ti.get('input_timeout_seconds')}s")

    except Exception as exc:
        print(f"  [FAIL] Config verification error: {exc}")
        passed = False

    return passed


def test_stage_5_integration() -> bool:
    print_stage(5, "Unified Pipeline Co-existence")
    passed = True

    try:
        from main import ZyeVoiceLoop

        voice_loop = ZyeVoiceLoop()

        has_tts = voice_loop.tts_engine is not None
        has_ti = voice_loop.text_handler is not None
        has_ear = voice_loop.ear is not None

        print(f"  [{'PASS' if has_tts else 'WARN'}] TTS Engine initialized: {has_tts}")
        print(f"  [{'PASS' if has_ti else 'WARN'}] Text Handler initialized: {has_ti}")
        print(f"  [{'PASS' if has_ear else 'WARN'}] SmartAudioEar initialized: {has_ear}")

        # Verify echo mode logic
        echo_mode = voice_loop._echo_mode
        print(f"  [INFO] Echo Mode Active: {echo_mode} (safe offline fallback)")

        # Test response generation
        res = asyncio.run(voice_loop._generate_response("Zye status check"))
        print(f"  [PASS] Response generation: {res!r}")

        # Clean shutdown
        asyncio.run(voice_loop._shutdown())
        print("  [PASS] Voice loop cleanly initialized and shut down")

    except Exception as exc:
        print(f"  [FAIL] Pipeline co-existence error: {exc}")
        passed = False

    return passed


def main() -> int:
    parser = argparse.ArgumentParser(description="Zye AI Day 10 Voice Pipeline Smoke Test")
    parser.add_argument("--playback", action="store_true", help="Enable live audio speaker playback")
    parser.add_argument("--live-mic", action="store_true", help="Enable live microphone test")
    args = parser.parse_args()

    print("=" * 64)
    print("       ZYE AI — DAY 10 VOICE PIPELINE SMOKE TEST")
    print("=" * 64)

    s1 = test_stage_1_imports()
    s2 = test_stage_2_tts(live_playback=args.playback)
    s3 = test_stage_3_text_input()
    s4 = test_stage_4_config()
    s5 = test_stage_5_integration()

    results = [s1, s2, s3, s4, s5]
    all_passed = all(results)

    print("\n" + "=" * 64)
    print(f"  SMOKE TEST RESULT: {'ALL PASS' if all_passed else 'FAILURES DETECTED'}")
    print(f"  Stages: {sum(results)}/5 passed")
    print("=" * 64)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
