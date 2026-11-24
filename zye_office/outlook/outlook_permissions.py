"""
Permission Engine for Microsoft Outlook — Zye Day 23.
Enforces draft-first policy and explicit confirmation for outbound emails.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from zye_office.outlook.outlook_errors import OutlookSendConfirmationError


class OutlookPermissionEngine:
    """Enforces send authorization and destructive mailbox safeguards."""

    @staticmethod
    def enforce_send_confirmation(confirmed: bool) -> None:
        """Mandatory policy: sending email strictly requires confirmed=True."""
        if not confirmed:
            raise OutlookSendConfirmationError(
                "Sending outbound email requires explicit user authorization (confirmed=True)."
            )

    @staticmethod
    def enforce_deletion_confirmation(operation: str, confirmed: bool) -> None:
        if not confirmed:
            raise ValueError(f"Destructive operation '{operation}' requires explicit confirmed=True.")
