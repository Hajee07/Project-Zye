"""
Negative Pre-Mortem Brain & FMEA Engine for Zye Autonomy (Day 15).
Re-exports the 100% Negative Pre-Mortem Brain and NegativeAuditEngine.
"""

from __future__ import annotations

from zye_intelligence.premortem import (
    ADVERSARIAL_SYSTEM_INSTRUCTION,
    ZyeNegativePreMortem,
    _generate_offline_fmea,
    _run_negative_brain_sync,
)
from zye_intelligence.negative_audit import NegativeAuditEngine

__all__ = [
    "ADVERSARIAL_SYSTEM_INSTRUCTION",
    "ZyeNegativePreMortem",
    "_generate_offline_fmea",
    "_run_negative_brain_sync",
    "NegativeAuditEngine",
]
