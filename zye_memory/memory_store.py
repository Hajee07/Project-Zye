"""
ZYE AI — Persistent SQLite Fact Store
====================================

Implements durable, low-latency key facts storage for ZYE AI.
Uses thread-safe SQLite operations with WAL mode for fast concurrent reads and writes.
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("zye.memory.store")


@dataclass
class Fact:
    """A durable item of long-term memory."""

    id: str
    content: str
    source: str = "conversation"
    confidence: float = 1.0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    access_count: int = 0
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "source": self.source,
            "confidence": self.confidence,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "access_count": self.access_count,
            "tags": self.tags,
        }


class FactStore:
    """Thread-safe SQLite store for durable memory facts."""

    def __init__(self, db_path: str = "data/memory.db") -> None:
        self.db_path = db_path
        self._shared_conn: Optional[sqlite3.Connection] = None
        if self.db_path == ":memory:":
            # ZYE-BUG-015: Retain persistent connection for :memory: databases so schema survives
            self._shared_conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._shared_conn.row_factory = sqlite3.Row
        else:
            os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self._lock = threading.RLock()
        self._init_db()

    @contextlib.contextmanager
    def _connection(self):
        if self._shared_conn is not None:
            with self._lock:
                try:
                    yield self._shared_conn
                    self._shared_conn.commit()
                except Exception:
                    self._shared_conn.rollback()
                    raise
        else:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
                conn.commit()
            finally:
                conn.close()

    def close(self) -> None:
        """Close shared connection if open."""
        if self._shared_conn is not None:
            try:
                self._shared_conn.close()
            except Exception:
                pass
            self._shared_conn = None

    def _init_db(self) -> None:
        with self._lock, self._connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS facts (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    source TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    access_count INTEGER NOT NULL DEFAULT 0,
                    tags TEXT NOT NULL DEFAULT '[]'
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_facts_created ON facts(created_at);")

    def add_fact(
        self,
        content: str,
        source: str = "conversation",
        confidence: float = 1.0,
        tags: Optional[List[str]] = None,
    ) -> Fact:
        """Add or update a fact in the store."""
        fact_id = uuid.uuid4().hex[:12]
        now = time.time()
        tags_json = json.dumps(tags or [])

        fact = Fact(
            id=fact_id,
            content=content.strip(),
            source=source,
            confidence=confidence,
            created_at=now,
            updated_at=now,
            tags=tags or [],
        )

        with self._lock, self._connection() as conn:
            conn.execute(
                """
                INSERT INTO facts (id, content, source, confidence, created_at, updated_at, access_count, tags)
                VALUES (?, ?, ?, ?, ?, ?, 0, ?);
                """,
                (fact.id, fact.content, fact.source, fact.confidence, fact.created_at, fact.updated_at, tags_json),
            )
        return fact

    def get_fact(self, fact_id: str) -> Optional[Fact]:
        """Retrieve a specific fact by ID."""
        with self._lock, self._connection() as conn:
            row = conn.execute(
                """
                SELECT id, content, source, confidence, created_at, updated_at, access_count, tags
                FROM facts
                WHERE id = ?;
                """,
                (fact_id,),
            ).fetchone()
            if not row:
                return None
            try:
                tags = json.loads(row["tags"])
            except Exception:
                tags = []
            return Fact(
                id=row["id"],
                content=row["content"],
                source=row["source"],
                confidence=row["confidence"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                access_count=row["access_count"],
                tags=tags,
            )

    def search_facts(self, query: str, limit: int = 10) -> List[Fact]:
        """Simple substring search across facts."""
        q = f"%{query.strip().lower()}%"
        with self._lock, self._connection() as conn:
            cursor = conn.execute(
                """
                SELECT id, content, source, confidence, created_at, updated_at, access_count, tags
                FROM facts
                WHERE LOWER(content) LIKE ?
                ORDER BY updated_at DESC
                LIMIT ?;
                """,
                (q, limit),
            )
            rows = cursor.fetchall()

        results = []
        for r in rows:
            try:
                tags = json.loads(r["tags"])
            except Exception:
                tags = []
            results.append(
                Fact(
                    id=r["id"],
                    content=r["content"],
                    source=r["source"],
                    confidence=r["confidence"],
                    created_at=r["created_at"],
                    updated_at=r["updated_at"],
                    access_count=r["access_count"],
                    tags=tags,
                )
            )
        return results

    def list_facts(self, limit: int = 50) -> List[Fact]:
        """List recently updated facts."""
        with self._lock, self._connection() as conn:
            cursor = conn.execute(
                """
                SELECT id, content, source, confidence, created_at, updated_at, access_count, tags
                FROM facts
                ORDER BY updated_at DESC
                LIMIT ?;
                """,
                (limit,),
            )
            rows = cursor.fetchall()

        results = []
        for r in rows:
            try:
                tags = json.loads(r["tags"])
            except Exception:
                tags = []
            results.append(
                Fact(
                    id=r["id"],
                    content=r["content"],
                    source=r["source"],
                    confidence=r["confidence"],
                    created_at=r["created_at"],
                    updated_at=r["updated_at"],
                    access_count=r["access_count"],
                    tags=tags,
                )
            )
        return results

    def delete_fact(self, fact_id: str) -> bool:
        """Delete a fact by ID."""
        with self._lock, self._connection() as conn:
            cursor = conn.execute("DELETE FROM facts WHERE id = ?;", (fact_id,))
            return cursor.rowcount > 0

    def close(self) -> None:
        """No persistent handle to close since connections are per-operation."""
        pass



__all__ = ["Fact", "FactStore"]
