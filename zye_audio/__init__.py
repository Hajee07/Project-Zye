#!/usr/bin/env python3
"""
ZYE AI — Audio Enhancement & Acoustic Feedback Package v3.0
===========================================================

Provides Automatic Gain Control (AGC), adaptive volume normalization,
peak limiting, dynamic Jarvis acoustic chimes, and acoustic feedback guard windows.
"""

from __future__ import annotations

from zye_audio.agc import (
    AGCConfig,
    AGCConfigError,
    AGCError,
    AGCProcessor,
    AGCResult,
)
from zye_audio.chime_player import (
    ChimeConfig,
    ChimeConfigError,
    ChimeDeviceError,
    ChimeError,
    ChimeQueueFullError,
    JarvisChimePlayer,
    generate_start_chime,
    generate_stop_chime,
    generate_tone,
)

__all__ = [
    "AGCConfig",
    "AGCConfigError",
    "AGCError",
    "AGCProcessor",
    "AGCResult",
    "ChimeConfig",
    "ChimeConfigError",
    "ChimeDeviceError",
    "ChimeError",
    "ChimeQueueFullError",
    "JarvisChimePlayer",
    "generate_start_chime",
    "generate_stop_chime",
    "generate_tone",
]
