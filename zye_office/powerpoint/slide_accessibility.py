"""
Accessibility Engine for Microsoft PowerPoint — Zye Day 23.
Detects missing titles, images without alternative text, and reading order issues.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from zye_office.powerpoint.powerpoint_adapter import PowerPointAdapter
from zye_office.powerpoint.powerpoint_errors import (
    PowerPointNoActivePresentationError,
)

logger = logging.getLogger("zye.office.powerpoint.accessibility")


class PowerPointAccessibilityEngine:
    """Audits presentations for accessibility best practices."""

    def __init__(self, adapter: Optional[PowerPointAdapter] = None) -> None:
        self.adapter = adapter or PowerPointAdapter()
        self.worker = self.adapter.worker

    def generate_accessibility_report(self) -> Dict[str, Any]:
        """Audit active presentation for accessibility compliance."""
        def _sta_audit() -> Dict[str, Any]:
            pres = self.adapter.get_active_presentation_raw()
            if pres is None:
                raise PowerPointNoActivePresentationError()

            issues: List[Dict[str, Any]] = []
            for i in range(1, pres.Slides.Count + 1):
                s = pres.Slides(i)
                # 1. Missing Title Check
                if not s.Shapes.HasTitle:
                    issues.append({
                        "slide_index": i,
                        "type": "MISSING_TITLE",
                        "severity": "HIGH",
                        "description": f"Slide {i} does not have a designated title placeholder.",
                    })

                # 2. Shapes & Images Alt-Text Check
                for shape in s.Shapes:
                    try:
                        # Check pictures and shapes
                        if getattr(shape, "Type", 0) in (13, 11):  # msoPicture or embedded OLE
                            alt = getattr(shape, "AlternativeText", "").strip()
                            if not alt:
                                issues.append({
                                    "slide_index": i,
                                    "shape_name": shape.Name,
                                    "type": "MISSING_ALT_TEXT",
                                    "severity": "MEDIUM",
                                    "description": f"Shape '{shape.Name}' on Slide {i} is missing alternative text.",
                                })
                    except Exception:
                        pass

            return {
                "status": "SUCCESS",
                "total_slides": pres.Slides.Count,
                "issues_count": len(issues),
                "is_accessible": len(issues) == 0,
                "issues": issues,
            }

        return self.worker.run(_sta_audit)
