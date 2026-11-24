"""
Local Search Index Manager.
Implements incremental metadata tracking and high-speed full-text indexing via SQLite FTS5.
"""

from __future__ import annotations

from contextlib import contextmanager
import hashlib
import logging
import re
import sqlite3
import time
from pathlib import Path
from typing import Any

from zye_computer_intelligence.security.local_search_policy import LocalSearchPolicy
from .local_document_extractor import LocalDocumentExtractor

logger = logging.getLogger("zye.computer_intelligence.index_manager")

DEFAULT_INDEX_DB_NAME = "local_search_fts.db"


class LocalIndexManager:
    """Manages SQLite FTS5 full-text indexing and incremental document synchronization."""

    def __init__(self, db_path: str | Path | None = None, policy: LocalSearchPolicy | None = None) -> None:
        if db_path:
            self.db_path = Path(db_path)
        else:
            self.db_path = Path("d:/Zye/data") / DEFAULT_INDEX_DB_NAME
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.policy = policy or LocalSearchPolicy()
        self._init_database()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(str(self.db_path))
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_database(self) -> None:
        """Initializes metadata table and FTS5 full-text virtual table."""
        with self._get_connection() as conn:
            # Metadata table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS document_metadata (
                    file_path TEXT PRIMARY KEY,
                    file_name TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    mtime REAL NOT NULL,
                    file_hash TEXT NOT NULL,
                    indexed_at REAL NOT NULL,
                    page_count INTEGER,
                    status TEXT NOT NULL
                );
            """)

            # FTS5 Virtual Table for full-text keyword indexing
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS local_docs_fts USING fts5(
                    file_path UNINDEXED,
                    file_name,
                    content,
                    tokenize='porter unicode61'
                );
            """)
            conn.commit()

    @staticmethod
    def _compute_quick_hash(file_path: Path) -> str:
        """Computes SHA-256 hash on first 64KB for quick change detection."""
        try:
            h = hashlib.sha256()
            with open(file_path, "rb") as f:
                chunk = f.read(65536)
                h.update(chunk)
            return h.hexdigest()
        except Exception:
            return ""

    def index_document(self, file_path: Path, force: bool = False) -> bool:
        """Indexes a single document if newly added or modified."""
        try:
            validated_path = self.policy.validate_file_access(file_path)
            stat = validated_path.stat()
            file_size = stat.st_size
            mtime = stat.st_mtime
            path_str = str(validated_path)

            # Check if index is already up to date
            if not force:
                with self._get_connection() as conn:
                    cur = conn.cursor()
                    cur.execute(
                        "SELECT mtime, file_size FROM document_metadata WHERE file_path = ?",
                        (path_str,)
                    )
                    row = cur.fetchone()
                    if row and abs(row[0] - mtime) < 1e-4 and row[1] == file_size:
                        return False  # Already indexed and unchanged

            # Extract document content
            extracted = LocalDocumentExtractor.extract_document(validated_path)
            content = extracted.get("content", "")
            page_count = extracted.get("page_count")

            file_hash = self._compute_quick_hash(validated_path)
            now = time.time()

            with self._get_connection() as conn:
                cur = conn.cursor()
                # Upsert metadata
                cur.execute("""
                    INSERT INTO document_metadata (
                        file_path, file_name, file_type, file_size, mtime, file_hash, indexed_at, page_count, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(file_path) DO UPDATE SET
                        file_size=excluded.file_size,
                        mtime=excluded.mtime,
                        file_hash=excluded.file_hash,
                        indexed_at=excluded.indexed_at,
                        page_count=excluded.page_count,
                        status=excluded.status;
                """, (
                    path_str,
                    validated_path.name,
                    validated_path.suffix.lower(),
                    file_size,
                    mtime,
                    file_hash,
                    now,
                    page_count,
                    extracted.get("status", "SUCCESS"),
                ))

                # Update FTS table
                cur.execute("DELETE FROM local_docs_fts WHERE file_path = ?", (path_str,))
                cur.execute(
                    "INSERT INTO local_docs_fts (file_path, file_name, content) VALUES (?, ?, ?)",
                    (path_str, validated_path.name, content),
                )
                conn.commit()

            return True
        except Exception as e:
            logger.debug("Failed to index '%s': %s", file_path.name, e)
            return False

    def rebuild_index(self, root_dir: Path | list[Path] | None = None, policy: LocalSearchPolicy | None = None) -> dict[str, Any]:
        """Walks authorized directory roots and indexes all valid documents."""
        pol = policy or self.policy
        if isinstance(root_dir, list):
            roots = [Path(r) for r in root_dir]
        elif root_dir:
            roots = [Path(root_dir)]
        else:
            roots = pol.allowed_roots
        indexed_count = 0
        scanned_count = 0
        start_time = time.time()
        import os
        from zye_computer_intelligence.security.local_search_policy import FORBIDDEN_DIRECTORY_NAMES

        for root in roots:
            p_root = Path(root).resolve()
            if not p_root.is_dir():
                continue

            for dirpath, dirnames, filenames in os.walk(p_root):
                dirnames[:] = [d for d in dirnames if d.lower() not in FORBIDDEN_DIRECTORY_NAMES and not d.startswith(".")]
                for fn in filenames:
                    file_path = Path(dirpath) / fn
                    scanned_count += 1
                    try:
                        if self.index_document(file_path):
                            indexed_count += 1
                    except Exception:
                        continue

        # Prune missing files
        self.prune_missing_entries()
        duration_ms = round((time.time() - start_time) * 1000, 2)

        return {
            "status": "SUCCESS",
            "scanned_files": scanned_count,
            "indexed_files": indexed_count,
            "indexed_count": indexed_count,
            "skipped_count": max(0, scanned_count - indexed_count),
            "duration_ms": duration_ms,
        }

    def prune_missing_entries(self) -> int:
        """Removes index entries for files that have been deleted from disk."""
        removed = 0
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT file_path FROM document_metadata")
            paths = cur.fetchall()

            for (p_str,) in paths:
                if not Path(p_str).exists():
                    cur.execute("DELETE FROM document_metadata WHERE file_path = ?", (p_str,))
                    cur.execute("DELETE FROM local_docs_fts WHERE file_path = ?", (p_str,))
                    removed += 1
            conn.commit()
        return removed

    def search_fts(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Executes full-text keyword search against SQLite FTS5 table."""
        # Sanitize query for FTS5 syntax
        clean_terms = [re.sub(r"[^a-zA-Z0-9_]", "", w) for w in query.split()]
        clean_terms = [w for w in clean_terms if w]
        if not clean_terms:
            return []

        fts_query = " OR ".join(clean_terms)
        results = []

        try:
            with self._get_connection() as conn:
                cur = conn.cursor()
                cur.execute("""
                    SELECT file_path, file_name, snippet(local_docs_fts, 2, '<b>', '</b>', '...', 32)
                    FROM local_docs_fts
                    WHERE local_docs_fts MATCH ?
                    ORDER BY rank
                    LIMIT ?;
                """, (fts_query, limit))

                for row in cur.fetchall():
                    results.append({
                        "file_path": row[0],
                        "file_name": row[1],
                        "snippet": row[2],
                    })
        except Exception as e:
            logger.warning("FTS search error for '%s': %s", query, e)

        return results

    def get_index_status(self) -> dict[str, Any]:
        """Returns statistics on the local document index."""
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*), SUM(file_size) FROM document_metadata")
            row = cur.fetchone()
            doc_count = row[0] or 0
            total_size_bytes = row[1] or 0

            cur.execute("SELECT file_type, COUNT(*) FROM document_metadata GROUP BY file_type")
            types = {r[0]: r[1] for r in cur.fetchall()}

        return {
            "status": "SUCCESS",
            "indexed_documents_count": doc_count,
            "indexed_files_count": doc_count,
            "total_size_bytes": total_size_bytes,
            "file_types_breakdown": types,
            "database_path": str(self.db_path),
        }

    def get_status(self) -> dict[str, Any]:
        """Alias for get_index_status."""
        return self.get_index_status()
