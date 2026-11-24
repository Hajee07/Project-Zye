"""
Attachment Manager for Microsoft Outlook — Zye Day 23.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from zye_office.outlook.outlook_adapter import OutlookAdapter
from zye_office.outlook.outlook_errors import (
    OutlookMessageNotFoundError,
)
from zye_office.outlook.outlook_validator import OutlookValidator

logger = logging.getLogger("zye.office.outlook.attachments")


class OutlookAttachmentManager:
    """Manages adding and removing attachments from drafts."""

    def __init__(
        self,
        adapter: Optional[OutlookAdapter] = None,
        validator: Optional[OutlookValidator] = None,
    ) -> None:
        self.adapter = adapter or OutlookAdapter()
        self.worker = self.adapter.worker
        self.validator = validator or OutlookValidator()

    def add_attachment(self, entry_id: str, file_path: str) -> Dict[str, Any]:
        """Attach a file to an existing draft message."""
        norm_path = self.validator.validate_attachment(file_path)

        def _sta_add_att() -> Dict[str, Any]:
            ns = self.adapter.get_namespace_raw()
            if ns is None:
                raise OutlookMessageNotFoundError(entry_id)

            mail = ns.GetItemFromID(entry_id)
            att = mail.Attachments.Add(norm_path)
            mail.Save()

            return {
                "status": "SUCCESS",
                "entry_id": entry_id,
                "attached_filename": att.FileName,
                "total_attachments": mail.Attachments.Count,
            }

        return self.worker.run(_sta_add_att)
