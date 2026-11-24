"""
Email Reply & Forward Engine for Microsoft Outlook — Zye Day 23.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from zye_office.outlook.outlook_adapter import OutlookAdapter
from zye_office.outlook.outlook_errors import (
    OutlookMessageNotFoundError,
)

logger = logging.getLogger("zye.office.outlook.replies")


class OutlookReplyEngine:
    """Creates reply and forward drafts preserving conversation context."""

    def __init__(self, adapter: Optional[OutlookAdapter] = None) -> None:
        self.adapter = adapter or OutlookAdapter()
        self.worker = self.adapter.worker

    def reply_to_message(
        self,
        entry_id: str,
        reply_text: str,
        reply_all: bool = False,
        save_draft: bool = True,
    ) -> Dict[str, Any]:
        """Create a Reply or Reply-All draft."""
        def _sta_reply() -> Dict[str, Any]:
            ns = self.adapter.get_namespace_raw()
            if ns is None:
                raise OutlookMessageNotFoundError(entry_id)

            orig_mail = ns.GetItemFromID(entry_id)
            reply_mail = orig_mail.ReplyAll() if reply_all else orig_mail.Reply()

            reply_mail.Body = reply_text + "\n\n" + getattr(reply_mail, "Body", "")
            if save_draft:
                reply_mail.Save()

            return {
                "status": "SUCCESS",
                "entry_id": getattr(reply_mail, "EntryID", None),
                "reply_all": reply_all,
                "to": getattr(reply_mail, "To", ""),
                "subject": getattr(reply_mail, "Subject", ""),
                "is_draft_saved": save_draft,
            }

        return self.worker.run(_sta_reply)

    def forward_message(
        self,
        entry_id: str,
        to_recipients: List[str],
        forward_text: str = "",
        save_draft: bool = True,
    ) -> Dict[str, Any]:
        """Create a Forward draft."""
        def _sta_fwd() -> Dict[str, Any]:
            ns = self.adapter.get_namespace_raw()
            if ns is None:
                raise OutlookMessageNotFoundError(entry_id)

            orig_mail = ns.GetItemFromID(entry_id)
            fwd_mail = orig_mail.Forward()

            if to_recipients:
                fwd_mail.To = "; ".join(to_recipients)
            if forward_text:
                fwd_mail.Body = forward_text + "\n\n" + getattr(fwd_mail, "Body", "")

            if save_draft:
                fwd_mail.Save()

            return {
                "status": "SUCCESS",
                "entry_id": getattr(fwd_mail, "EntryID", None),
                "to": to_recipients,
                "subject": getattr(fwd_mail, "Subject", ""),
                "is_draft_saved": save_draft,
            }

        return self.worker.run(_sta_fwd)
