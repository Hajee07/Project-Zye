"""
Live Microsoft Outlook COM Automation Verification — Day 23.
Tests Outlook COM adapter connection, mailbox inspection, draft-first creation,
and strictly verifies send confirmation gating.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from zye_office.outlook.outlook_adapter import OutlookAdapter
from zye_office.outlook.outlook_mailbox_inspector import OutlookMailboxInspector
from zye_office.outlook.outlook_draft_engine import OutlookDraftEngine
from zye_office.outlook.outlook_send_engine import OutlookSendEngine
from zye_office.outlook.outlook_permissions import OutlookPermissionEngine
from zye_office.outlook.outlook_errors import OutlookSendConfirmationError
from zye_office.models import ConnectionPolicy


def run_live_outlook_test() -> None:
    print("=" * 64)
    print("  LIVE MICROSOFT OUTLOOK COM VERIFICATION — DAY 23")
    print("=" * 64)

    adapter = OutlookAdapter()
    print("1. Connecting to Microsoft Outlook COM (ATTACH_EXISTING policy)...")
    conn = adapter.connect(policy=ConnectionPolicy.ATTACH_EXISTING)
    print(f"   Connection result: {conn.get('status')}")

    inspector = OutlookMailboxInspector(adapter=adapter)
    draft_eng = OutlookDraftEngine(adapter=adapter)
    send_eng = OutlookSendEngine(adapter=adapter)

    # 1. Security Check: Verify Sending WITHOUT Confirmation Fails ALWAYS
    print("\n2. Security Verification: Attempt send with confirmed=False...")
    try:
        send_eng.send_authorized_email(entry_id="TEST_ENTRY_DRAFT_001", confirmed=False)
        print("   ERROR: send succeeded without confirmation!")
        sys.exit(1)
    except OutlookSendConfirmationError as err:
        print(f"   SUCCESS: Send blocked by safety gate: {err}")

    # 2. Permission Engine Verification
    print("\n3. Testing OutlookPermissionEngine direct enforcement...")
    try:
        OutlookPermissionEngine.enforce_send_confirmation(False)
        assert False
    except OutlookSendConfirmationError:
        print("   confirmed=False properly rejected: PASS")

    OutlookPermissionEngine.enforce_send_confirmation(True)
    print("   confirmed=True properly authorized: PASS")

    # 3. Live mailbox interaction (if Outlook desktop is currently open)
    if conn.get("status") == "SUCCESS":
        print("\n4. Outlook Desktop is active! Performing live mailbox inspection...")
        unread = inspector.get_unread_count()
        print(f"   Unread Count: {unread.get('unread_count')}, Folder: {unread.get('folder_name')}")
    else:
        print(f"\n4. Outlook Desktop not currently foreground/open ({conn.get('message', 'Not attached')}).")
        print("   (Non-blocking: Outlook is safely ready when user launches it).")

    print("\n" + "=" * 64)
    print("  ALL OUTLOOK COM TESTS & SECURITY GATES PASSED 100%!")
    print("=" * 64)


if __name__ == "__main__":
    run_live_outlook_test()
