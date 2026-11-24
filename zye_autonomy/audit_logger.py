"""
Central Audit Logger for Zye Autonomy and Orchestrator (Day 15).
Persists structured security, safety gateway, and tool execution audit trails
to both SQLite (data/zye_audit.sqlite) and rotating JSONL logs (logs/security_audit.log).
"""

from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("zye.autonomy.audit_logger")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "zye_audit.sqlite"
DEFAULT_JSONL_PATH = PROJECT_ROOT / "logs" / "security_audit.log"

def redact_secrets(text: str) -> str:
    """Mask credentials, API keys, and sensitive tokens from log records."""
    if not text:
        return ""
    sanitized = text
    # Mask Gemini API keys
    sanitized = re.sub(r'AIza[0-9A-Za-z_-]{33,}', '[REDACTED_GEMINI_KEY]', sanitized)
    sanitized = re.sub(
        r'(?i)(api[_-]?key|token|password|secret|auth)\s*[:=]\s*["\']?[^\s"\']+["\']?',
        r'\1=[REDACTED]',
        sanitized
    )
    return sanitized


class AuditLogger:
    """
    Structured auditor supporting dual SQLite and JSONL audit sinks
    with secret scrubbing and query capabilities.
    """

    def __init__(
        self,
        db_path: str | Path | None = None,
        jsonl_path: str | Path | None = None,
    ) -> None:
        self._db_path = Path(db_path or DEFAULT_DB_PATH)
        self._jsonl_path = Path(jsonl_path or DEFAULT_JSONL_PATH)
        self._ensure_storage()

    def _ensure_storage(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._jsonl_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_sqlite()

    def _init_sqlite(self) -> None:
        conn = sqlite3.connect(str(self._db_path), timeout=5.0)
        try:
            with conn:
                conn.execute("PRAGMA journal_mode = WAL;")
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS audit_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        audit_id TEXT UNIQUE NOT NULL,
                        request_id TEXT NOT NULL,
                        user_task_id TEXT NOT NULL,
                        tool_name TEXT NOT NULL,
                        server_name TEXT NOT NULL,
                        mission_profile TEXT NOT NULL,
                        risk_level TEXT NOT NULL,
                        action_type TEXT NOT NULL,
                        target_resources TEXT NOT NULL,
                        premortem_risk TEXT NOT NULL,
                        authorized INTEGER NOT NULL,
                        result_status TEXT NOT NULL,
                        verification_result TEXT NOT NULL,
                        recovery_attempt INTEGER DEFAULT 0,
                        error_category TEXT NOT NULL,
                        details TEXT NOT NULL,
                        timestamp TEXT NOT NULL
                    );
                    """
                )
                conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_history(timestamp);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_tool ON audit_history(tool_name);")
        finally:
            conn.close()

    def log_event(
        self,
        tool_name: str,
        action_type: str = "TOOL_EXECUTE",
        risk_level: str = "LOW_RISK",
        server_name: str = "orchestrator",
        mission_profile: str = "NORMAL_ASSISTANT",
        target_resources: str = "",
        premortem_risk: str = "LOW",
        authorized: bool = True,
        result_status: str = "SUCCESS",
        verification_result: str = "VERIFIED",
        recovery_attempt: int = 0,
        error_category: str = "",
        details: str | dict[str, Any] = "",
        request_id: str = "",
        user_task_id: str = "",
        audit_id: str = "",
    ) -> str:
        """
        Record a comprehensive audit trail entry across SQLite and JSONL log file.
        Returns the unique audit_id.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        aid = audit_id or f"aud_{uuid.uuid4().hex[:12]}"
        req_id = request_id or f"req_{uuid.uuid4().hex[:8]}"
        task_id = user_task_id or f"task_{uuid.uuid4().hex[:8]}"

        raw_details = json.dumps(details) if isinstance(details, (dict, list)) else str(details)
        clean_details = redact_secrets(raw_details)
        clean_targets = redact_secrets(target_resources)

        # 1. Write to SQLite
        try:
            conn = sqlite3.connect(str(self._db_path), timeout=5.0)
            with conn:
                conn.execute(
                    """
                    INSERT INTO audit_history (
                        audit_id, request_id, user_task_id, tool_name, server_name,
                        mission_profile, risk_level, action_type, target_resources,
                        premortem_risk, authorized, result_status, verification_result,
                        recovery_attempt, error_category, details, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        aid,
                        req_id,
                        task_id,
                        tool_name,
                        server_name,
                        mission_profile,
                        risk_level,
                        action_type,
                        clean_targets,
                        premortem_risk,
                        1 if authorized else 0,
                        result_status,
                        verification_result,
                        recovery_attempt,
                        error_category,
                        clean_details,
                        now_iso,
                    ),
                )
            conn.close()
        except Exception as e:
            logger.error("Failed writing SQLite audit record: %s", e)

        # 2. Write to JSONL
        try:
            record = {
                "audit_id": aid,
                "request_id": req_id,
                "user_task_id": task_id,
                "timestamp": now_iso,
                "tool_name": tool_name,
                "server_name": server_name,
                "mission_profile": mission_profile,
                "risk_level": risk_level,
                "action_type": action_type,
                "target_resources": clean_targets,
                "premortem_risk": premortem_risk,
                "authorized": authorized,
                "result_status": result_status,
                "verification_result": verification_result,
                "recovery_attempt": recovery_attempt,
                "error_category": error_category,
                "details": clean_details,
            }
            with open(self._jsonl_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as e:
            logger.error("Failed writing JSONL audit record: %s", e)

        return aid

    def get_recent_audits(self, limit: int = 25) -> list[dict[str, Any]]:
        """Retrieve recent audit logs sorted by timestamp descending."""
        conn = sqlite3.connect(str(self._db_path), timeout=5.0)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.execute(
                """
                SELECT * FROM audit_history
                ORDER BY id DESC
                LIMIT ?;
                """,
                (limit,),
            )
            return [dict(r) for r in cursor.fetchall()]
        except Exception as e:
            logger.error("Failed reading audit history: %s", e)
            return []
        finally:
            conn.close()
