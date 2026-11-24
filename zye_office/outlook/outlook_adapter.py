"""
Universal Microsoft Outlook COM Adapter — Zye Day 23.
Dedicated STA thread-bound access to Outlook.Application COM interface.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from zye_office.com_runtime import OfficeCOMRuntime
from zye_office.com_worker import STACOMWorker
from zye_office.models import ConnectionPolicy
from zye_office.models.day23_models import OutlookMailboxSummary
from zye_office.outlook.outlook_constants import OutlookConstants
from zye_office.outlook.outlook_errors import (
    OutlookCOMUnavailableError,
    OutlookProfileUnavailableError,
)

logger = logging.getLogger("zye.office.outlook.adapter")


class OutlookAdapter:
    """Thread-safe COM Adapter for Microsoft Outlook executing on dedicated STA worker."""

    def __init__(
        self,
        com_runtime: Optional[OfficeCOMRuntime] = None,
        worker: Optional[STACOMWorker] = None,
    ) -> None:
        self.worker = worker or STACOMWorker.get_instance()
        self.com_runtime = com_runtime or OfficeCOMRuntime(worker=self.worker)

    def connect(
        self,
        policy: ConnectionPolicy = ConnectionPolicy.ATTACH_EXISTING,
    ) -> Dict[str, Any]:
        """Establish or attach to live Microsoft Outlook COM application."""
        return self.com_runtime.connect_office_application("outlook", policy=policy)

    def is_running(self) -> bool:
        """Check if Outlook COM application is reachable or running."""
        try:
            return self.get_raw_app() is not None
        except Exception:
            return False

    def get_raw_app(self) -> Any:
        """INTERNAL: Access raw Outlook.Application COM dispatch inside STA worker."""
        return self.com_runtime.get_raw_com_object("outlook")

    def get_namespace_raw(self) -> Any:
        """INTERNAL: Retrieve MAPI NameSpace inside STA worker."""
        app = self.get_raw_app()
        if app is None:
            conn = self.connect(policy=ConnectionPolicy.ATTACH_EXISTING)
            if conn.get("status") != "SUCCESS":
                return None
            app = self.get_raw_app()

        if app is None:
            return None

        try:
            return app.GetNamespace("MAPI")
        except Exception as exc:
            logger.warning("Error getting MAPI namespace from Outlook: %s", exc)
            return None

    def get_default_folder_raw(self, folder_type: int) -> Any:
        """INTERNAL: Retrieve a default Outlook folder inside STA worker."""
        ns = self.get_namespace_raw()
        if ns is None:
            return None
        try:
            return ns.GetDefaultFolder(folder_type)
        except Exception as exc:
            logger.warning("Error accessing default folder %s in Outlook: %s", folder_type, exc)
            return None

    def inspect_outlook_application(self) -> Dict[str, Any]:
        """Return structured summary of active Outlook profile and folder counts."""
        def _sta_inspect() -> Dict[str, Any]:
            app = self.get_raw_app()
            if app is None:
                conn = self.connect(policy=ConnectionPolicy.ATTACH_EXISTING)
                if conn.get("status") != "SUCCESS":
                    return conn
                app = self.get_raw_app()

            if app is None:
                raise OutlookCOMUnavailableError()

            ns = self.get_namespace_raw()
            if ns is None:
                raise OutlookProfileUnavailableError()

            prof_name = getattr(ns, "CurrentProfileName", "Default Profile")

            # Inbox counts
            inbox_unread = 0
            inbox_total = 0
            try:
                inbox = ns.GetDefaultFolder(OutlookConstants.olFolderInbox)
                inbox_unread = inbox.UnReadItemCount
                inbox_total = inbox.Items.Count
            except Exception:
                pass

            # Sent & Drafts counts
            sent_total = 0
            drafts_total = 0
            try:
                sent = ns.GetDefaultFolder(OutlookConstants.olFolderSentMail)
                sent_total = sent.Items.Count
            except Exception:
                pass
            try:
                drafts = ns.GetDefaultFolder(OutlookConstants.olFolderDrafts)
                drafts_total = drafts.Items.Count
            except Exception:
                pass

            return OutlookMailboxSummary(
                status="SUCCESS",
                profile_name=prof_name,
                inbox_unread_count=inbox_unread,
                inbox_total_count=inbox_total,
                sent_count=sent_total,
                drafts_count=drafts_total,
            ).model_dump()

        return self.worker.run(_sta_inspect)
