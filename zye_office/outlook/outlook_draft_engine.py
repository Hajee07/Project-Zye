"""
Email Draft Engine for Microsoft Outlook — Zye Day 23.
Creates and persists drafts in the Drafts folder (Draft-First principle).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from zye_office.outlook.outlook_adapter import OutlookAdapter
from zye_office.outlook.outlook_constants import OutlookConstants
from zye_office.outlook.outlook_errors import (
    OutlookCOMUnavailableError,
)
from zye_office.outlook.outlook_validator import OutlookValidator

logger = logging.getLogger("zye.office.outlook.drafts")


class OutlookDraftEngine:
    """Manages email composition and saving to Drafts folder."""

    def __init__(
        self,
        adapter: Optional[OutlookAdapter] = None,
        validator: Optional[OutlookValidator] = None,
    ) -> None:
        self.adapter = adapter or OutlookAdapter()
        self.worker = self.adapter.worker
        self.validator = validator or OutlookValidator()

    def create_draft(
        self,
        to_recipients: List[str],
        subject: str,
        body: str,
        cc_recipients: Optional[List[str]] = None,
        html_body: Optional[str] = None,
        attachment_paths: Optional[List[str]] = None,
        save: bool = True,
    ) -> Dict[str, Any]:
        """Create a new Outlook email draft."""
        def _sta_draft() -> Dict[str, Any]:
            app = self.adapter.get_raw_app()
            if app is None:
                raise OutlookCOMUnavailableError()

            # CreateItem(olMailItem = 0)
            mail = app.CreateItem(OutlookConstants.olMailItem)

            # Assign recipients
            if to_recipients:
                mail.To = "; ".join(to_recipients)
            if cc_recipients:
                mail.CC = "; ".join(cc_recipients)

            mail.Subject = subject

            if html_body:
                mail.HTMLBody = html_body
            else:
                mail.Body = body

            # Attachments
            attached_count = 0
            if attachment_paths:
                for path in attachment_paths:
                    norm_path = self.validator.validate_attachment(path)
                    mail.Attachments.Add(norm_path)
                    attached_count += 1

            if save:
                mail.Save()

            return {
                "status": "SUCCESS",
                "entry_id": getattr(mail, "EntryID", None),
                "to": to_recipients,
                "subject": subject,
                "attachments_count": attached_count,
                "is_draft_saved": save,
            }

        return self.worker.run(_sta_draft)
