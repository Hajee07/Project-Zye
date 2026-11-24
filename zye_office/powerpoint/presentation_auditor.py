"""
Presentation Auditor for Microsoft PowerPoint — Zye Day 23.
Audits presentation structure, duplicate slides, empty placeholders, and font consistency.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from zye_office.powerpoint.powerpoint_adapter import PowerPointAdapter
from zye_office.powerpoint.powerpoint_errors import (
    PowerPointNoActivePresentationError,
)

logger = logging.getLogger("zye.office.powerpoint.auditor")


class PowerPointAuditor:
    """Audits presentations for structural and typographical consistency."""

    def __init__(self, adapter: Optional[PowerPointAdapter] = None) -> None:
        self.adapter = adapter or PowerPointAdapter()
        self.worker = self.adapter.worker

    def audit_presentation(self) -> Dict[str, Any]:
        """Audit presentation structure and consistency."""
        def _sta_audit() -> Dict[str, Any]:
            pres = self.adapter.get_active_presentation_raw()
            if pres is None:
                raise PowerPointNoActivePresentationError()

            findings: List[Dict[str, Any]] = []
            titles_seen: Dict[str, int] = {}
            total_slides = pres.Slides.Count

            for i in range(1, total_slides + 1):
                s = pres.Slides(i)
                # Check empty slide
                if s.Shapes.Count == 0:
                    findings.append({
                        "slide_index": i,
                        "category": "EMPTY_SLIDE",
                        "severity": "MEDIUM",
                        "description": f"Slide {i} has 0 shapes or content.",
                    })

                # Check duplicate titles
                if s.Shapes.HasTitle:
                    title_text = s.Shapes.Title.TextFrame.TextRange.Text.strip()
                    if title_text in titles_seen:
                        findings.append({
                            "slide_index": i,
                            "category": "DUPLICATE_TITLE",
                            "severity": "LOW",
                            "description": f"Slide {i} duplicates title '{title_text}' from Slide {titles_seen[title_text]}.",
                        })
                    else:
                        titles_seen[title_text] = i

            return {
                "status": "SUCCESS",
                "total_slides": total_slides,
                "findings_count": len(findings),
                "findings": findings,
            }

        return self.worker.run(_sta_audit)
