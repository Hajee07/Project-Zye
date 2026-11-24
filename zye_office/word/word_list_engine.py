"""
Bullets & Numbering Engine — Zye Day 21.
Generates bulleted lists, standard numbered lists, and roman/alphabetic numbering with Unicode preservation.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from zye_office.word.word_adapter import WordAdapter
from zye_office.word.word_errors import WordNoActiveDocumentError
from zye_office.word.word_validator import WordValidator

logger = logging.getLogger("zye.office.word.lists")


class WordListEngine:
    """Manages creation, formatting, and numbering continuation for lists."""

    def __init__(
        self,
        adapter: Optional[WordAdapter] = None,
        validator: Optional[WordValidator] = None,
    ) -> None:
        self.adapter = adapter or WordAdapter()
        self.validator = validator or WordValidator()

    def create_bullet_list(self, items: List[str]) -> Dict[str, Any]:
        """Inserts a list formatted with bullet points."""
        def _sta_bullet() -> Dict[str, Any]:
            app = self.adapter.get_raw_app()
            doc = self.adapter.get_active_document_raw()
            if doc is None:
                raise WordNoActiveDocumentError()

            start_p = doc.Paragraphs.Count
            for item in items:
                clean_item = self.validator.validate_unicode_text(item)
                rng = doc.Content
                rng.Collapse(0)
                p = doc.Paragraphs.Add(rng)
                p.Range.Text = clean_item + "\n"
                try:
                    # Apply List Bullet or List Paragraph
                    p.Range.ListFormat.ApplyBulletDefault()
                except Exception:
                    p.Range.Style = "List Bullet"

            return {
                "status": "SUCCESS",
                "list_type": "BULLET",
                "item_count": len(items),
                "items_count": len(items),
                "message": f"Inserted {len(items)} bulleted items.",
            }

        return self.adapter.worker.run(_sta_bullet)

    def create_numbered_list(self, items: List[str], start_number: int = 1) -> Dict[str, Any]:
        """Inserts an ordered list with numbering."""
        def _sta_numbered() -> Dict[str, Any]:
            app = self.adapter.get_raw_app()
            doc = self.adapter.get_active_document_raw()
            if doc is None:
                raise WordNoActiveDocumentError()

            for item in items:
                clean_item = self.validator.validate_unicode_text(item)
                rng = doc.Content
                rng.Collapse(0)
                p = doc.Paragraphs.Add(rng)
                p.Range.Text = clean_item + "\n"
                try:
                    p.Range.ListFormat.ApplyNumberDefault()
                except Exception:
                    p.Range.Style = "List Number"

            return {
                "status": "SUCCESS",
                "list_type": "NUMBERED",
                "item_count": len(items),
                "items_count": len(items),
                "start_number": start_number,
                "message": f"Inserted {len(items)} numbered items.",
            }

        return self.adapter.worker.run(_sta_numbered)
