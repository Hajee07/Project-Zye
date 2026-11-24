"""
Message Reader Engine for Microsoft Outlook — Zye Day 23.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from zye_office.models.day23_models import OutlookMessageMetadata
from zye_office.outlook.outlook_adapter import OutlookAdapter
from zye_office.outlook.outlook_errors import (
    OutlookMessageNotFoundError,
)

logger = logging.getLogger("zye.office.outlook.reader")


class OutlookMessageReader:
    """Reads specific message details safely by EntryID."""

    def __init__(self, adapter: Optional[OutlookAdapter] = None) -> None:
        self.adapter = adapter or OutlookAdapter()
        self.worker = self.adapter.worker

    def read_message(self, entry_id: str) -> Dict[str, Any]:
        """Retrieve full details and body of a specific email."""
        def _sta_read() -> Dict[str, Any]:
            ns = self.adapter.get_namespace_raw()
            if ns is None:
                raise OutlookMessageNotFoundError(entry_id)

            try:
                item = ns.GetItemFromID(entry_id)
            except Exception:
                raise OutlookMessageNotFoundError(entry_id)

            subj = getattr(item, "Subject", "")
            sender = getattr(item, "SenderName", "")
            body = getattr(item, "Body", "")
            time_str = str(getattr(item, "ReceivedTime", ""))

            att_names = []
            if getattr(item.Attachments, "Count", 0) > 0:
                for a in item.Attachments:
                    att_names.append(a.FileName)

            return {
                "status": "SUCCESS",
                "entry_id": entry_id,
                "subject": subj,
                "sender": sender,
                "received_time": time_str,
                "body": body,
                "attachments": att_names,
            }

        return self.worker.run(_sta_read)
