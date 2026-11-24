"""
Audit Logging System for Zye Personal Assistant (Day 14).
Records sensitive assistant operations, authorization states, and risk levels to SQLite.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zye_personal_assistant.database import get_db_connection, init_assistant_database

logger = logging.getLogger("zye.personal_assistant.audit")


class AuditLogger:
    def __init__(self, db_path: str | Path | None = None) -> None:
        self._db_path = db_path
        if db_path is not None:
            try:
                init_assistant_database(db_path)
            except Exception as e:
                logger.debug("AuditLogger db init notice: %s", e)

    def log_action(
        self,
        action_type: str,
        target_resources: str = "",
        premortem_risk: str = "LOW",
        authorized: bool = True,
        result_status: str = "SUCCESS",
        details: str = "",
    ) -> int:
        """Record an audit trail entry and return its database ID."""
        now = datetime.now(timezone.utc).isoformat()
        conn = get_db_connection(self._db_path)
        try:
            with conn:
                cursor = conn.execute(
                    """
                    INSERT INTO audit_history 
                    (action_type, target_resources, premortem_risk, authorized, result_status, details, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        action_type,
                        target_resources,
                        premortem_risk,
                        1 if authorized else 0,
                        result_status,
                        details,
                        now,
                    ),
                )
                return cursor.lastrowid or 0
        except Exception as e:
            logger.error("Failed to write audit history: %s", e)
            return 0
        finally:
            conn.close()

    def get_recent_audit_logs(self, limit: int = 20) -> list[dict[str, Any]]:
        """Retrieve recent audit logs in descending timestamp order."""
        conn = get_db_connection(self._db_path)
        try:
            rows = conn.execute(
                """
                SELECT id, action_type, target_resources, premortem_risk, authorized, result_status, details, timestamp
                FROM audit_history
                ORDER BY id DESC LIMIT ?;
                """,
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()
