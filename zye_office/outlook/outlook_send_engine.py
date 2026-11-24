"""
Send Authorization & Delivery Engine for Microsoft Outlook — Zye Day 23.
Enforces explicit user confirmation before executing mail.Send().
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from zye_office.outlook.outlook_adapter import OutlookAdapter
from zye_office.outlook.outlook_errors import (
    OutlookMessageNotFoundError,
)
from zye_office.outlook.outlook_permissions import OutlookPermissionEngine

logger = logging.getLogger("zye.office.outlook.send")


class OutlookSendEngine:
    """Manages pre-send inspection and authorized outbound transmission."""

    def __init__(self, adapter: Optional[OutlookAdapter] = None) -> None:
        self.adapter = adapter or OutlookAdapter()
        self.worker = self.adapter.worker

    def prepare_send_summary(self, entry_id: str) -> Dict[str, Any]:
        """Inspect all draft properties for user confirmation before transmission."""
        def _sta_prep() -> Dict[str, Any]:
            ns = self.adapter.get_namespace_raw()
            if ns is None:
                raise OutlookMessageNotFoundError(entry_id)

            mail = ns.GetItemFromID(entry_id)
            att_names = [a.FileName for a in mail.Attachments]

            return {
                "status": "READY_FOR_CONFIRMATION",
                "entry_id": entry_id,
                "to": getattr(mail, "To", ""),
                "cc": getattr(mail, "CC", ""),
                "subject": getattr(mail, "Subject", ""),
                "body_preview": (getattr(mail, "Body", "") or "")[:200],
                "attachment_count": len(att_names),
                "attachments": att_names,
                "confirmation_required": True,
            }

        return self.worker.run(_sta_prep)

    def send_authorized_email(self, entry_id: str, confirmed: bool = False) -> Dict[str, Any]:
        """Execute mail.Send() only when explicitly authorized with confirmed=True."""
        OutlookPermissionEngine.enforce_send_confirmation(confirmed)

        def _sta_send() -> Dict[str, Any]:
            ns = self.adapter.get_namespace_raw()
            if ns is None:
                raise OutlookMessageNotFoundError(entry_id)

            mail = ns.GetItemFromID(entry_id)
            subj = getattr(mail, "Subject", "")
            recipients = getattr(mail, "To", "")

            # Execute actual Outlook COM Send
            mail.Send()

            return {
                "status": "SUCCESS",
                "delivery_state": "SEND_ACCEPTED_BY_OUTLOOK",
                "to": recipients,
                "subject": subj,
                "message": "Email transmission submitted to Outlook Outbox.",
            }

        return self.worker.run(_sta_send)
