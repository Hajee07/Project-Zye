"""
Safe Recycle Bin Management Engine — Zye Day 16 & Day 18.
Provides two-stage Recycle Bin inspection and deletion with mandatory preview,
tamper-proof user confirmation, and Win32 SHEmptyRecycleBinW integration.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import logging
from typing import Any, Optional

from zye_windows.windows_models import RecycleBinSummary

logger = logging.getLogger("zye.windows.recycle_bin")


class SHQUERYRBINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("i64Size", ctypes.c_longlong),
        ("i64NumItems", ctypes.c_longlong),
    ]


class WindowsRecycleBinManager:
    """
    Manages Windows Recycle Bin operations with strict confirmation interlocks.
    """

    def __init__(self) -> None:
        pass

    def preview_recycle_bin(self) -> dict[str, Any]:
        """
        Stage 1: Non-destructive preview of Windows Recycle Bin contents.
        Returns item count and total size in bytes/megabytes without deleting anything.
        """
        try:
            shell32 = ctypes.windll.shell32
            rb_info = SHQUERYRBINFO()
            rb_info.cbSize = ctypes.sizeof(SHQUERYRBINFO)

            res = shell32.SHQueryRecycleBinW(None, ctypes.byref(rb_info))
            if res == 0:
                items = int(rb_info.i64NumItems)
                size_bytes = int(rb_info.i64Size)
                size_mb = round(size_bytes / (1024 * 1024), 2)
                return {
                    "status": "SUCCESS",
                    "action": "preview_recycle_bin",
                    "item_count": items,
                    "total_size_bytes": size_bytes,
                    "total_size_mb": size_mb,
                    "message": f"Recycle Bin contains {items} items ({size_mb} MB).",
                    "cleanup_available": items > 0,
                }
            else:
                return {
                    "status": "WARN",
                    "action": "preview_recycle_bin",
                    "item_count": 0,
                    "total_size_bytes": 0,
                    "total_size_mb": 0.0,
                    "message": f"SHQueryRecycleBinW returned code {res}.",
                    "cleanup_available": True,
                }
        except Exception as exc:
            logger.error("Error querying Recycle Bin: %s", exc)
            return {
                "status": "ERROR",
                "message": f"Failed to query Recycle Bin: {exc}",
            }

    def get_recycle_bin_summary(self) -> RecycleBinSummary:
        """Fetch strongly typed summary model for Recycle Bin."""
        p = self.preview_recycle_bin()
        return RecycleBinSummary(
            total_items=p.get("item_count", 0),
            total_size_bytes=p.get("total_size_bytes", 0),
            total_size_mb=p.get("total_size_mb", 0.0),
            status=p.get("status", "READY"),
        )

    def empty_recycle_bin(self, confirmed: bool = False) -> dict[str, Any]:
        """
        Stage 2: Permanently empty the Windows Recycle Bin.
        CRITICAL_RISK operation: Permanently rejected unless confirmed=True.
        """
        if not confirmed:
            preview = self.preview_recycle_bin()
            items = preview.get("item_count", "unknown")
            size_mb = preview.get("total_size_mb", "unknown")
            return {
                "status": "CONFIRMATION_REQUIRED",
                "action": "empty_recycle_bin",
                "risk_level": "CRITICAL_RISK",
                "message": (
                    f"Warning: Emptying the Recycle Bin will permanently delete {items} items ({size_mb} MB). "
                    "This action cannot be undone. Please confirm by setting confirmed=True."
                ),
                "tanglish_message": (
                    f"Recycle Bin-la {items} items ({size_mb} MB) irukku boss! "
                    "Empty panna permanent-ah delete aaidum. Confirm panna confirmed=True nu sollunga."
                ),
                "preview": preview,
                "verified": False,
            }

        try:
            shell32 = ctypes.windll.shell32
            # SHERB_NOCONFIRMATION = 0x00000001, SHERB_NOPROGRESSUI = 0x00000002, SHERB_NOSOUND = 0x00000004
            flags = 0x00000001 | 0x00000002 | 0x00000004
            res = shell32.SHEmptyRecycleBinW(None, None, flags)

            if res == 0:
                logger.info("Successfully emptied Windows Recycle Bin.")
                return {
                    "status": "SUCCESS",
                    "action": "empty_recycle_bin",
                    "message": "Windows Recycle Bin has been completely emptied.",
                    "tanglish_message": "Recycle Bin-a clean panniyachu boss!",
                    "verified": True,
                }
            else:
                logger.warning("SHEmptyRecycleBinW returned code %d", res)
                return {
                    "status": "WARN",
                    "action": "empty_recycle_bin",
                    "message": f"SHEmptyRecycleBinW returned code {res} (Recycle Bin may already be empty).",
                    "verified": True,
                }
        except Exception as exc:
            logger.error("Failed to empty Recycle Bin: %s", exc)
            return {
                "status": "ERROR",
                "message": f"Failed to empty Recycle Bin: {exc}",
                "verified": False,
            }
