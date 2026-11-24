"""
Folder Management Engine for Microsoft Outlook — Zye Day 23.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from zye_office.outlook.outlook_adapter import OutlookAdapter
from zye_office.outlook.outlook_constants import OutlookConstants
from zye_office.outlook.outlook_errors import (
    OutlookCOMUnavailableError,
    OutlookMessageNotFoundError,
)

logger = logging.getLogger("zye.office.outlook.folders")


class OutlookFolderManager:
    """Manages mail folders and message moving."""

    def __init__(self, adapter: Optional[OutlookAdapter] = None) -> None:
        self.adapter = adapter or OutlookAdapter()
        self.worker = self.adapter.worker

    def get_folders(self) -> List[Dict[str, Any]]:
        """List top-level mail folders in default store."""
        def _sta_folders() -> List[Dict[str, Any]]:
            inbox = self.adapter.get_default_folder_raw(OutlookConstants.olFolderInbox)
            if inbox is None:
                return []

            parent = inbox.Parent
            folders_list = []
            for f in parent.Folders:
                folders_list.append({
                    "name": f.Name,
                    "item_count": f.Items.Count,
                    "unread_count": getattr(f, "UnReadItemCount", 0),
                })
            return folders_list

        return self.worker.run(_sta_folders)

    def create_folder(self, folder_name: str) -> Dict[str, Any]:
        """Create a new folder under Inbox."""
        def _sta_create_f() -> Dict[str, Any]:
            inbox = self.adapter.get_default_folder_raw(OutlookConstants.olFolderInbox)
            if inbox is None:
                raise OutlookCOMUnavailableError("Inbox not reachable.")

            new_f = inbox.Folders.Add(folder_name)
            return {
                "status": "SUCCESS",
                "folder_name": new_f.Name,
            }

        return self.worker.run(_sta_create_f)

    def move_message(self, entry_id: str, destination_folder_name: str) -> Dict[str, Any]:
        """Move a message to another folder."""
        def _sta_move() -> Dict[str, Any]:
            ns = self.adapter.get_namespace_raw()
            if ns is None:
                raise OutlookMessageNotFoundError(entry_id)

            mail = ns.GetItemFromID(entry_id)
            inbox = self.adapter.get_default_folder_raw(OutlookConstants.olFolderInbox)
            parent = inbox.Parent

            dest_folder = None
            for f in parent.Folders:
                if f.Name.lower() == destination_folder_name.lower():
                    dest_folder = f
                    break

            if dest_folder is None:
                raise FileNotFoundError(f"Folder '{destination_folder_name}' not found.")

            mail.Move(dest_folder)
            return {
                "status": "SUCCESS",
                "entry_id": entry_id,
                "destination_folder": destination_folder_name,
            }

        return self.worker.run(_sta_move)
