"""
Validation & Constraint Enforcement for Microsoft PowerPoint Automation — Zye Day 23.
"""

from __future__ import annotations

from typing import Any, List, Optional
from zye_office.powerpoint.powerpoint_errors import (
    PowerPointAnimationError,
    PowerPointSlideNotFoundError,
    PowerPointTransitionError,
)

VALID_TRANSITIONS = {
    "none", "fade", "push", "wipe", "split", "cut", "reveal", "random", "cover", "uncover", "flash"
}

VALID_ANIMATIONS = {
    "appear", "fade", "fly_in", "float_in", "split", "wipe", "zoom",
    "pulse", "spin", "grow_shrink", "teeter", "disappear", "fly_out", "float_out"
}


class PowerPointValidator:
    """Validates slide indices, transition names, and animation effects."""

    @staticmethod
    def validate_slide_index(slide_index: int, total_slides: int) -> int:
        if slide_index < 1 or slide_index > total_slides:
            raise PowerPointSlideNotFoundError(slide_index)
        return slide_index

    @staticmethod
    def validate_transition_name(transition_name: str) -> str:
        clean = transition_name.lower().strip()
        if clean not in VALID_TRANSITIONS:
            raise PowerPointTransitionError(f"Unsupported transition '{transition_name}'. Supported: {', '.join(sorted(VALID_TRANSITIONS))}")
        return clean

    @staticmethod
    def validate_animation_name(animation_name: str) -> str:
        clean = animation_name.lower().strip()
        if clean not in VALID_ANIMATIONS:
            raise PowerPointAnimationError(f"Unsupported animation effect '{animation_name}'. Supported: {', '.join(sorted(VALID_ANIMATIONS))}")
        return clean
