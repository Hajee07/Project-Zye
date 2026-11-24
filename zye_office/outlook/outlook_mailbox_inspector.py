"""
Mailbox Inspector for Microsoft Outlook — Zye Day 23.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from zye_office.models.day23_models import OutlookMessageMetadata
from zye_office.outlook.outlook_adapter import OutlookAdapter
from zye_office.outlook.outlook_constants import OutlookConstants
from zye_office.outlook.outlook_errors import (
    OutlookCOMUnavailableError,
)

logger = logging.getLogger("zye.office.outlook.mailbox")


class OutlookMailboxInspector:
    """Inspects unread counts, recent message headers, and summaries."""

    def __init__(self, adapter: Optional[OutlookAdapter] = None) -> None:
        self.adapter = adapter or OutlookAdapter()
        self.worker = self.adapter.worker

    def get_unread_count(self) -> Dict[str, Any]:
        """Count unread emails in default Inbox."""
        def _sta_unread() -> Dict[str, Any]:
            inbox = self.adapter.get_default_folder_raw(OutlookConstants.olFolderInbox)
            if inbox is None:
                raise OutlookCOMUnavailableError("Cannot access Outlook Inbox.")

            return {
                "status": "SUCCESS",
                "unread_count": inbox.UnReadItemCount,
                "total_count": inbox.Items.Count,
            }

        return self.worker.run(_sta_unread)

    def get_recent_messages(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieve headers and bounded previews of recent Inbox messages."""
        def _sta_recent() -> List[Dict[str, Any]]:
            inbox = self.adapter.get_default_folder_raw(OutlookConstants.olFolderInbox)
            if inbox is None:
                return []

            items = inbox.Items
            items.Sort("[ReceivedTime]", True)  # Descending

            messages = []
            count = 0
            for item in items:
                if count >= limit:
                    break
                try:
                    # Check if standard MailItem (Class == 43)
                    if getattr(item, "Class", 0) == 43:
                        subj = getattr(item, "Subject", "(No Subject)")
                        sender = getattr(item, "SenderName", "Unknown")
                        time_str = str(getattr(item, "ReceivedTime", ""))
                        unread = bool(getattr(item, "UnRead", False))
                        body_preview = (getattr(item, "Body", "") or "").strip()[:200]

                        att_names = []
                        if getattr(item.Attachments, "Count", 0) > 0:
                            for a in item.Attachments:
                                att_names.append(a.FileName)

                        messages.append(OutlookMessageMetadata(
                            status="SUCCESS",
                            entry_id=getattr(item, "EntryID", None),
                            subject=subj,
                            sender_name=sender,
                            received_time=time_str,
                            is_unread=unread,
                            has_attachments=len(att_names) > 0,
                            attachment_names=att_names,
                            body_preview=body_preview,
                        ).model_dump())
                        count += 1
                except Exception:
                    pass

            return messages

        return self.worker.run(_sta_recent)
