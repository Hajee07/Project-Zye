"""
Category & Flag Management for Microsoft Outlook — Zye Day 23.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from zye_office.outlook.outlook_adapter import OutlookAdapter
from zye_office.outlook.outlook_errors import (
    OutlookMessageNotFoundError,
)

logger = logging.getLogger("zye.office.outlook.categories")


class OutlookCategoryManager:
    """Manages email color categories, follow-up flags, and read status."""

    def __init__(self, adapter: Optional[OutlookAdapter] = None) -> None:
        self.adapter = adapter or OutlookAdapter()
        self.worker = self.adapter.worker

    def get_categories(self) -> List[str]:
        """List master categories defined in Outlook profile."""
        def _sta_cats() -> List[str]:
            ns = self.adapter.get_namespace_raw()
            if ns is None:
                return []
            cats = []
            try:
                for c in ns.Categories:
                    cats.append(c.Name)
            except Exception:
                pass
            return cats

        return self.worker.run(_sta_cats)

    def assign_category(self, entry_id: str, category_name: str) -> Dict[str, Any]:
        """Assign category tag to a message."""
        def _sta_assign() -> Dict[str, Any]:
            ns = self.adapter.get_namespace_raw()
            if ns is None:
                raise OutlookMessageNotFoundError(entry_id)

            mail = ns.GetItemFromID(entry_id)
            mail.Categories = category_name
            mail.Save()
            return {
                "status": "SUCCESS",
                "entry_id": entry_id,
                "categories": category_name,
            }

        return self.worker.run(_sta_assign)

    def mark_read_status(self, entry_id: str, is_read: bool = True) -> Dict[str, Any]:
        """Mark message as read or unread."""
        def _sta_mark() -> Dict[str, Any]:
            ns = self.adapter.get_namespace_raw()
            if ns is None:
                raise OutlookMessageNotFoundError(entry_id)

            mail = ns.GetItemFromID(entry_id)
            mail.UnRead = not is_read
            mail.Save()
            return {
                "status": "SUCCESS",
                "entry_id": entry_id,
                "is_unread": not is_read,
            }

        return self.worker.run(_sta_mark)
