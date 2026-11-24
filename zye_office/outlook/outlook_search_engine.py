"""
Email Search Engine for Microsoft Outlook — Zye Day 23.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from zye_office.models.day23_models import OutlookMessageMetadata
from zye_office.outlook.outlook_adapter import OutlookAdapter
from zye_office.outlook.outlook_constants import OutlookConstants

logger = logging.getLogger("zye.office.outlook.search")


class OutlookSearchEngine:
    """Searches Outlook messages by sender, subject, and unread state."""

    def __init__(self, adapter: Optional[OutlookAdapter] = None) -> None:
        self.adapter = adapter or OutlookAdapter()
        self.worker = self.adapter.worker

    def search_messages(
        self,
        sender: Optional[str] = None,
        subject: Optional[str] = None,
        unread_only: bool = False,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Search Inbox items matching criteria."""
        def _sta_search() -> List[Dict[str, Any]]:
            inbox = self.adapter.get_default_folder_raw(OutlookConstants.olFolderInbox)
            if inbox is None:
                return []

            items = inbox.Items
            items.Sort("[ReceivedTime]", True)

            results = []
            for item in items:
                if len(results) >= limit:
                    break
                try:
                    if getattr(item, "Class", 0) != 43:
                        continue

                    # Filter unread
                    if unread_only and not getattr(item, "UnRead", False):
                        continue

                    # Filter sender
                    if sender:
                        s_name = getattr(item, "SenderName", "").lower()
                        if sender.lower() not in s_name:
                            continue

                    # Filter subject
                    if subject:
                        subj = getattr(item, "Subject", "").lower()
                        if subject.lower() not in subj:
                            continue

                    results.append(OutlookMessageMetadata(
                        status="SUCCESS",
                        entry_id=getattr(item, "EntryID", None),
                        subject=getattr(item, "Subject", "(No Subject)"),
                        sender_name=getattr(item, "SenderName", "Unknown"),
                        received_time=str(getattr(item, "ReceivedTime", "")),
                        is_unread=bool(getattr(item, "UnRead", False)),
                        body_preview=(getattr(item, "Body", "") or "").strip()[:150],
                    ).model_dump())
                except Exception:
                    pass

            return results

        return self.worker.run(_sta_search)
