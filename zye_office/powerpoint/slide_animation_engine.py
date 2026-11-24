"""
Slide Animation Engine for Microsoft PowerPoint — Zye Day 23.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from zye_office.powerpoint.powerpoint_adapter import PowerPointAdapter
from zye_office.powerpoint.powerpoint_constants import PowerPointConstants
from zye_office.powerpoint.powerpoint_errors import (
    PowerPointNoActivePresentationError,
    PowerPointShapeNotFoundError,
)
from zye_office.powerpoint.powerpoint_validator import PowerPointValidator

logger = logging.getLogger("zye.office.powerpoint.animations")

ANIMATION_MAP = {
    "appear": PowerPointConstants.msoAnimEffectAppear,
    "fly_in": PowerPointConstants.msoAnimEffectFly,
    "fade": PowerPointConstants.msoAnimEffectFade,
    "zoom": PowerPointConstants.msoAnimEffectZoom,
    "wipe": PowerPointConstants.msoAnimEffectWipe,
    "float_in": PowerPointConstants.msoAnimEffectFloat,
    "pulse": PowerPointConstants.msoAnimEffectPulse,
    "spin": PowerPointConstants.msoAnimEffectSpin,
    "grow_shrink": PowerPointConstants.msoAnimEffectGrowShrink,
    "teeter": PowerPointConstants.msoAnimEffectTeeter,
    "fly_out": PowerPointConstants.msoAnimEffectFly,
    "disappear": PowerPointConstants.msoAnimEffectAppear,
}

TRIGGER_MAP = {
    "on_click": PowerPointConstants.msoAnimTriggerOnPageClick,
    "with_previous": PowerPointConstants.msoAnimTriggerWithPrevious,
    "after_previous": PowerPointConstants.msoAnimTriggerAfterPrevious,
}


class PowerPointAnimationEngine:
    """Manages PowerPoint MainSequence effects on slide shapes."""

    def __init__(
        self,
        adapter: Optional[PowerPointAdapter] = None,
        validator: Optional[PowerPointValidator] = None,
    ) -> None:
        self.adapter = adapter or PowerPointAdapter()
        self.worker = self.adapter.worker
        self.validator = validator or PowerPointValidator()

    def add_animation(
        self,
        slide_index: int,
        shape_identifier: Any = "Title",
        effect_name: str = "fly_in",
        start_mode: str = "on_click",
        duration: float = 0.75,
        delay: float = 0.0,
    ) -> Dict[str, Any]:
        """Attach a native animation effect to a shape via Slide.TimeLine.MainSequence."""
        norm_effect = self.validator.validate_animation_name(effect_name)
        eff_enum = ANIMATION_MAP.get(norm_effect, PowerPointConstants.msoAnimEffectFly)
        trig_enum = TRIGGER_MAP.get(start_mode.lower(), PowerPointConstants.msoAnimTriggerOnPageClick)

        def _sta_anim() -> Dict[str, Any]:
            pres = self.adapter.get_active_presentation_raw()
            if pres is None:
                raise PowerPointNoActivePresentationError()

            self.validator.validate_slide_index(slide_index, pres.Slides.Count)
            s = pres.Slides(slide_index)

            shape = None
            if str(shape_identifier).lower() == "title" and s.Shapes.HasTitle:
                shape = s.Shapes.Title
            else:
                try:
                    shape = s.Shapes(shape_identifier)
                except Exception:
                    # Fallback to first shape with text if title requested
                    if s.Shapes.Count > 0:
                        shape = s.Shapes(1)

            if shape is None:
                raise PowerPointShapeNotFoundError(str(shape_identifier))

            seq = s.TimeLine.MainSequence
            # AddEffect(Shape, effectId, Level=0, trigger=trig_enum)
            effect = seq.AddEffect(shape, eff_enum, 0, trig_enum)

            try:
                effect.Timing.Duration = duration
                effect.Timing.TriggerDelayTime = delay
            except Exception:
                pass

            return {
                "status": "SUCCESS",
                "slide_index": slide_index,
                "shape": shape.Name,
                "effect": norm_effect,
                "start_mode": start_mode,
                "duration": duration,
                "total_effects": seq.Count,
            }

        return self.worker.run(_sta_anim)

    def get_slide_animations(self, slide_index: int) -> Dict[str, Any]:
        """Inspect all animation effects on a slide."""
        def _sta_get_anim() -> Dict[str, Any]:
            pres = self.adapter.get_active_presentation_raw()
            if pres is None:
                raise PowerPointNoActivePresentationError()

            self.validator.validate_slide_index(slide_index, pres.Slides.Count)
            s = pres.Slides(slide_index)
            seq = s.TimeLine.MainSequence

            effects_list = []
            for i in range(1, seq.Count + 1):
                try:
                    eff = seq(i)
                    effects_list.append({
                        "index": i,
                        "shape": eff.Shape.Name if eff.Shape else None,
                        "effect_type": eff.EffectType,
                        "duration": eff.Timing.Duration,
                    })
                except Exception:
                    pass

            return {
                "status": "SUCCESS",
                "slide_index": slide_index,
                "total_effects": len(effects_list),
                "effects": effects_list,
            }

        return self.worker.run(_sta_get_anim)

    def remove_animation(self, slide_index: int, effect_index: int = 1) -> Dict[str, Any]:
        """Remove a specific animation effect from slide timeline."""
        def _sta_rem() -> Dict[str, Any]:
            pres = self.adapter.get_active_presentation_raw()
            if pres is None:
                raise PowerPointNoActivePresentationError()

            self.validator.validate_slide_index(slide_index, pres.Slides.Count)
            s = pres.Slides(slide_index)
            seq = s.TimeLine.MainSequence
            if seq.Count >= effect_index:
                seq(effect_index).Delete()

            return {
                "status": "SUCCESS",
                "slide_index": slide_index,
                "removed_effect_index": effect_index,
                "remaining_effects": seq.Count,
            }

        return self.worker.run(_sta_rem)
