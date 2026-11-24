"""
Browser Audit Logging Engine — Day 24.
Logs all browser actions, URLs, profiles, and operations to logs/zye_browser_audit.log for compliance and diagnostics.
"""

from __future__ import annotations

import datetime
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

AUDIT_LOG_FILE = Path("logs/zye_browser_audit.log")


class BrowserAuditLogger:
    """Logs browser navigation, clicks, and profile events to an append-only audit trail."""

    @classmethod
    def log_event(
        cls,
        action: str,
        profile_id: Optional[str] = None,
        url: Optional[str] = None,
        status: str = "SUCCESS",
        details: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> None:
        """Append an audit record in JSON format."""
        try:
            AUDIT_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            record = {
                "timestamp": datetime.datetime.now().isoformat(),
                "action": action,
                "profile_id": profile_id,
                "url": url,
                "status": status,
                "details": details or {},
                "error": error,
            }
            with open(AUDIT_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as exc:
            logging.getLogger("ZyeBrowserAudit").debug("Failed to write audit record: %s", exc)
