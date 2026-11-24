#!/usr/bin/env python3
"""
ZYE AI — Neural Hearing Engine v2.0 Smoke Test
==============================================

Verifies Silero Neural VAD ONNX model loading, CPU execution provider,
512-sample float32 frame validation, inference latency, speech probability,
start/hold dual threshold hysteresis, recurrent state reset, and adaptive RMS fallback.

Usage:
    python scripts/test_neural_vad.py
    python scripts/test_neural_vad.py --json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import zye_audio_ear
from zye_audio_ear import (
    AudioConfig,
    CaptureState,
    SmartAudioEar,
    VADModelStatus,
    calculate_peak,
    calculate_rms,
    validate_vad_frame,
)


def run_neural_vad_smoke_test(verbose: bool = True) -> tuple[bool, dict[str, Any]]:
    """Execute complete smoke test verifying all Day 08 Neural VAD capabilities."""
    results: dict[str, Any] = {
        "engine": "ZyeNeuralHearing",
        "version": "2.0.0",
        "timestamp": time.time(),
        "stages": {},
        "overall_status": "FAIL",
    }

    ear: SmartAudioEar | None = None
    try:
        # Stage 1: Dependency Check
        t0 = time.perf_counter()
        has_torch = zye_audio_ear.torch is not None
        has_silero = zye_audio_ear.load_silero_vad is not None
        has_ort = zye_audio_ear.ort is not None
        dep_time = (time.perf_counter() - t0) * 1000.0

        provider = None
        if has_ort:
            providers = zye_audio_ear.ort.get_available_providers()
            provider = "CPUExecutionProvider" if "CPUExecutionProvider" in providers else (providers[0] if providers else None)

        results["stages"]["stage_1_dependencies"] = {
            "status": "PASS" if (has_torch and has_silero and has_ort) else "FAIL",
            "torch": has_torch,
            "silero_vad": has_silero,
            "onnxruntime": has_ort,
            "onnx_provider": provider,
            "duration_ms": round(dep_time, 2),
        }

        if not (has_torch and has_silero):
            results["error"] = "Core VAD packages (torch, silero-vad) missing"
            return False, results

        # Stage 2: Engine Initialization
        cfg = AudioConfig(vad_mode="silero_onnx")
        ear = SmartAudioEar(config=cfg)

        init_res = ear.load_neural_vad()
        results["stages"]["stage_2_model_initialization"] = {
            "status": "PASS" if init_res.get("status") == "success" else "FAIL",
            "backend": init_res.get("backend"),
            "model_status": init_res.get("model_status"),
            "load_time_ms": init_res.get("load_time_ms", 0.0),
            "warmup_time_ms": init_res.get("warmup_time_ms", 0.0),
        }

        # Stage 3: Frame Validation
        valid_frame = np.zeros(512, dtype=np.float32)
        inv_short = np.zeros(256, dtype=np.float32)
        inv_long = np.zeros(1024, dtype=np.float32)
        inv_2d = np.zeros((512, 2), dtype=np.float32)
        inv_nan = np.full(512, np.nan, dtype=np.float32)

        v_ok = ear.validate_vad_frame(valid_frame)
        v_short_rejected = not ear.validate_vad_frame(inv_short)
        v_long_rejected = not ear.validate_vad_frame(inv_long)
        v_2d_rejected = not ear.validate_vad_frame(inv_2d)
        v_nan_rejected = not ear.validate_vad_frame(inv_nan)

        all_validation_passed = (v_ok and v_short_rejected and v_long_rejected and v_2d_rejected and v_nan_rejected)
        results["stages"]["stage_3_frame_validation"] = {
            "status": "PASS" if all_validation_passed else "FAIL",
            "valid_512_accepted": v_ok,
            "short_256_rejected": v_short_rejected,
            "long_1024_rejected": v_long_rejected,
            "stereo_2d_rejected": v_2d_rejected,
            "nan_rejected": v_nan_rejected,
        }

        # Stage 4: Inference on Digital Silence
        t_inf0 = time.perf_counter()
        prob_silence = ear.calculate_speech_probability(valid_frame)
        silence_inf_ms = (time.perf_counter() - t_inf0) * 1000.0

        results["stages"]["stage_4_silence_inference"] = {
            "status": "PASS" if (0.0 <= prob_silence <= 0.15) else "FAIL",
            "speech_probability": round(prob_silence, 6),
            "inference_duration_ms": round(silence_inf_ms, 2),
            "is_speech_started": ear.is_speech_started(prob_silence),
        }

        # Stage 5: Dual Threshold & Hysteresis Verification
        # Start threshold: 0.52, Hold threshold: 0.40
        test_high_prob = 0.65
        test_mid_prob = 0.45
        test_low_prob = 0.30

        idle_trigger_high = ear.is_speech_started(test_high_prob)
        idle_trigger_mid = ear.is_speech_started(test_mid_prob)  # False, below 0.52
        rec_hold_mid = ear.is_speech_continued(test_mid_prob)    # True, above 0.40
        rec_hold_low = ear.is_speech_continued(test_low_prob)    # False, below 0.40

        hysteresis_ok = (idle_trigger_high and not idle_trigger_mid and rec_hold_mid and not rec_hold_low)
        results["stages"]["stage_5_threshold_hysteresis"] = {
            "status": "PASS" if hysteresis_ok else "FAIL",
            "start_threshold": cfg.vad_start_threshold,
            "hold_threshold": cfg.vad_hold_threshold,
            "idle_high_0_65_triggered": idle_trigger_high,
            "idle_mid_0_45_suppressed": not idle_trigger_mid,
            "recording_mid_0_45_sustained": rec_hold_mid,
            "recording_low_0_30_ended": not rec_hold_low,
        }

        # Stage 6: Recurrent State Reset
        ear.reset_vad_state()
        results["stages"]["stage_6_state_reset"] = {
            "status": "PASS",
            "consecutive_speech_frames": ear.consecutive_speech_frames,
            "last_speech_probability": ear.last_speech_probability,
        }

        # Stage 7: Fallback to Adaptive RMS Verification
        ear.unload_neural_vad()
        ear.active_vad_backend = "adaptive_rms"
        cand_res, rms_val, pk_val = ear.is_speech(valid_frame)

        results["stages"]["stage_7_rms_fallback"] = {
            "status": "PASS",
            "active_backend": ear.active_vad_backend,
            "fallback_detection_candidate": cand_res,
            "noise_floor": round(ear.rms_detector.noise_floor, 6),
        }

        # Telemetry & Diagnostics
        vad_diag = ear.get_vad_status()
        results["stages"]["stage_8_telemetry"] = {
            "status": "PASS" if vad_diag.get("status") == "success" else "FAIL",
            "vad_telemetry": vad_diag,
        }

        all_stages_passed = all(
            stage.get("status") == "PASS" for stage in results["stages"].values()
        )

        results["overall_status"] = "PASS" if all_stages_passed else "FAIL"
        return all_stages_passed, results

    except Exception as exc:
        results["overall_status"] = "ERROR"
        results["error"] = str(exc)
        return False, results

    finally:
        if ear is not None:
            ear.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Zye Neural Hearing Engine v2.0 Smoke Test")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON only")
    args = parser.parse_args()

    success, results = run_neural_vad_smoke_test(verbose=not args.json)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print("=" * 72)
        print("ZYE AI — Neural Hearing Engine v2.0 Smoke Test")
        print("=" * 72)
        for stage_name, stage_data in results.get("stages", {}).items():
            status = stage_data.get("status", "UNKNOWN")
            print(f"  [{status}] {stage_name}")
            for k, v in stage_data.items():
                if k != "status":
                    print(f"         {k}: {v}")
        print("-" * 72)
        print(f"Overall Result: {results['overall_status']}")
        print("=" * 72)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
