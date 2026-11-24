"""
Slide Transition Engine for Microsoft PowerPoint — Zye Day 23.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from zye_office.powerpoint.powerpoint_adapter import PowerPointAdapter
from zye_office.powerpoint.powerpoint_constants import PowerPointConstants
from zye_office.powerpoint.powerpoint_errors import (
    PowerPointNoActivePresentationError,
)
from zye_office.powerpoint.powerpoint_validator import PowerPointValidator

logger = logging.getLogger("zye.office.powerpoint.transitions")

TRANSITION_MAP = {
    "none": PowerPointConstants.ppEffectNone,
    "cut": PowerPointConstants.ppEffectCut,
    "fade": PowerPointConstants.ppEffectFade,
    "fade_smoothly": PowerPointConstants.ppEffectFadeSmoothly,
    "push": PowerPointConstants.ppEffectPushLeft,
    "wipe": PowerPointConstants.ppEffectWipeRight,
    "cover": PowerPointConstants.ppEffectCoverLeft,
    "uncover": PowerPointConstants.ppEffectUncoverRight,
}


class PowerPointTransitionEngine:
    """Manages entry transitions across presentation slides."""

    def __init__(
        self,
        adapter: Optional[PowerPointAdapter] = None,
        validator: Optional[PowerPointValidator] = None,
    ) -> None:
        self.adapter = adapter or PowerPointAdapter()
        self.worker = self.adapter.worker
        self.validator = validator or PowerPointValidator()

    def set_slide_transition(
        self,
        slide_index: int,
        transition_name: str = "fade",
        duration: float = 1.0,
    ) -> Dict[str, Any]:
        """Apply a transition to a single slide."""
        norm_trans = self.validator.validate_transition_name(transition_name)
        eff_enum = TRANSITION_MAP.get(norm_trans, PowerPointConstants.ppEffectFadeSmoothly)

        def _sta_set() -> Dict[str, Any]:
            pres = self.adapter.get_active_presentation_raw()
            if pres is None:
                raise PowerPointNoActivePresentationError()

            self.validator.validate_slide_index(slide_index, pres.Slides.Count)
            s = pres.Slides(slide_index)
            t = s.SlideShowTransition
            t.EntryEffect = eff_enum
            try:
                t.Duration = duration
            except Exception:
                pass

            return {
                "status": "SUCCESS",
                "slide_index": slide_index,
                "transition": norm_trans,
                "duration": duration,
            }

        return self.worker.run(_sta_set)

    def set_all_slide_transitions(
        self,
        transition_name: str = "fade",
        duration: float = 1.0,
    ) -> Dict[str, Any]:
        """Apply a transition uniformly across all slides in active presentation."""
        norm_trans = self.validator.validate_transition_name(transition_name)
        eff_enum = TRANSITION_MAP.get(norm_trans, PowerPointConstants.ppEffectFadeSmoothly)

        def _sta_set_all() -> Dict[str, Any]:
            pres = self.adapter.get_active_presentation_raw()
            if pres is None:
                raise PowerPointNoActivePresentationError()

            count = pres.Slides.Count
            for i in range(1, count + 1):
                s = pres.Slides(i)
                t = s.SlideShowTransition
                t.EntryEffect = eff_enum
                try:
                    t.Duration = duration
                except Exception:
                    pass

            return {
                "status": "SUCCESS",
                "transition": norm_trans,
                "duration": duration,
                "slides_updated": count,
            }

        return self.worker.run(_sta_set_all)

    def get_slide_transitions(self) -> Dict[str, Any]:
        """Inspect transitions on all slides."""
        def _sta_get() -> Dict[str, Any]:
            pres = self.adapter.get_active_presentation_raw()
            if pres is None:
                raise PowerPointNoActivePresentationError()

            transitions = []
            for i in range(1, pres.Slides.Count + 1):
                s = pres.Slides(i)
                t = s.SlideShowTransition
                eff = getattr(t, "EntryEffect", 0)
                dur = getattr(t, "Duration", 1.0)
                transitions.append({
                    "slide_index": i,
                    "entry_effect": eff,
                    "duration": dur,
                })

            return {
                "status": "SUCCESS",
                "total_slides": len(transitions),
                "transitions": transitions,
            }

        return self.worker.run(_sta_get)
