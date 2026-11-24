"""
Professional Word Style Engine & Presets — Zye Day 21.
Manages built-in styles, document style registries, custom style creation, and corporate style presets.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from zye_office.word.word_adapter import WordAdapter
from zye_office.word.word_errors import WordNoActiveDocumentError, WordStyleNotFoundError

logger = logging.getLogger("zye.office.word.styles")

# Built-in Canonical Style Presets
STYLE_PRESETS: Dict[str, Dict[str, Any]] = {
    "BUSINESS_REPORT": {
        "title_font": "Calibri",
        "title_size": 26,
        "title_bold": True,
        "h1_font": "Calibri",
        "h1_size": 18,
        "h1_bold": True,
        "h1_color": 16711680,  # Deep Blue
        "body_font": "Calibri",
        "body_size": 11,
        "line_spacing": 1.15,
        "space_after": 6,
    },
    "ACADEMIC_REPORT": {
        "title_font": "Times New Roman",
        "title_size": 24,
        "title_bold": True,
        "h1_font": "Times New Roman",
        "h1_size": 16,
        "h1_bold": True,
        "body_font": "Times New Roman",
        "body_size": 12,
        "line_spacing": 2.0,  # Double-spaced
        "space_after": 0,
    },
    "TECHNICAL_DOCUMENTATION": {
        "title_font": "Segoe UI",
        "title_size": 24,
        "title_bold": True,
        "h1_font": "Segoe UI Semibold",
        "h1_size": 16,
        "h1_bold": True,
        "h1_color": 8421504,
        "body_font": "Segoe UI",
        "body_size": 10.5,
        "line_spacing": 1.15,
        "space_after": 4,
    },
    "EXECUTIVE_SUMMARY": {
        "title_font": "Arial",
        "title_size": 22,
        "title_bold": True,
        "h1_font": "Arial",
        "h1_size": 15,
        "h1_bold": True,
        "body_font": "Arial",
        "body_size": 11,
        "line_spacing": 1.25,
        "space_after": 8,
    },
}


class WordStyleManager:
    """Applies, queries, and defines paragraph and character styles in Microsoft Word."""

    def __init__(self, adapter: Optional[WordAdapter] = None) -> None:
        self.adapter = adapter or WordAdapter()

    @classmethod
    def list_corporate_presets(cls) -> List[str]:
        return list(STYLE_PRESETS.keys())

    def get_available_word_styles(self) -> Dict[str, Any]:
        """List active styles defined in the document style catalog."""
        def _sta_get_styles() -> Dict[str, Any]:
            doc = self.adapter.get_active_document_raw()
            if doc is None:
                raise WordNoActiveDocumentError()

            styles_list = []
            for s in doc.Styles:
                try:
                    if getattr(s, "InUse", False):
                        styles_list.append({
                            "name": s.NameLocal,
                            "type": s.Type,
                            "built_in": s.BuiltIn,
                        })
                except Exception:
                    pass

            return {
                "status": "SUCCESS",
                "count": len(styles_list),
                "styles": styles_list[:100],  # Bounded to top 100
                "available_presets": list(STYLE_PRESETS.keys()),
            }

        return self.adapter.worker.run(_sta_get_styles)

    def apply_word_style(self, style_name: str, target_range: Optional[Any] = None) -> Dict[str, Any]:
        """Apply a named style (e.g. 'Heading 1', 'Title', 'Normal') to selection or range."""
        def _sta_apply() -> Dict[str, Any]:
            app = self.adapter.get_raw_app()
            doc = self.adapter.get_active_document_raw()
            if doc is None:
                raise WordNoActiveDocumentError()

            rng = target_range or app.Selection.Range
            try:
                rng.Style = style_name
            except Exception as exc:
                raise WordStyleNotFoundError(f"Style '{style_name}' could not be applied: {exc}")

            return {
                "status": "SUCCESS",
                "style_name": style_name,
                "applied_style": style_name,
                "message": f"Style '{style_name}' applied successfully.",
            }

        return self.adapter.worker.run(_sta_apply)

    def apply_style_preset(self, preset_name: str) -> Dict[str, Any]:
        """Apply corporate style preset to active document styles."""
        norm = preset_name.strip().upper()
        if norm not in STYLE_PRESETS:
            raise WordStyleNotFoundError(f"Unknown preset '{preset_name}'. Available: {list(STYLE_PRESETS.keys())}")

        cfg = STYLE_PRESETS[norm]

        def _sta_apply_preset() -> Dict[str, Any]:
            doc = self.adapter.get_active_document_raw()
            if doc is None:
                raise WordNoActiveDocumentError()

            # Normal style formatting
            try:
                normal_style = doc.Styles("Normal")
                normal_style.Font.Name = cfg["body_font"]
                normal_style.Font.Size = cfg["body_size"]
                normal_style.ParagraphFormat.LineSpacing = cfg["line_spacing"]
                normal_style.ParagraphFormat.SpaceAfter = cfg["space_after"]
            except Exception as exc:
                logger.warning("Could not update Normal style: %s", exc)

            # Heading 1 formatting
            try:
                h1_style = doc.Styles("Heading 1")
                h1_style.Font.Name = cfg["h1_font"]
                h1_style.Font.Size = cfg["h1_size"]
                h1_style.Font.Bold = cfg.get("h1_bold", True)
                if "h1_color" in cfg:
                    h1_style.Font.Color = cfg["h1_color"]
            except Exception as exc:
                logger.warning("Could not update Heading 1 style: %s", exc)

            return {
                "status": "SUCCESS",
                "preset_name": norm,
                "applied_preset": norm,
                "config": cfg,
                "message": f"Preset '{norm}' configured across document styles.",
            }

        return self.adapter.worker.run(_sta_apply_preset)
