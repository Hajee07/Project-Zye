"""
Document Relationship Index (SQLite Graph Database).
Stores documents, canonical entities, source mentions with line/page provenance,
and semantic relationships in a persistent SQLite database (data/document_entity_graph.db).
"""

from __future__ import annotations

from contextlib import contextmanager
import json
import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from zye_computer_intelligence.schemas.entity_schemas import (
    CanonicalEntity,
    EntityMatchCandidate,
    EntityMention,
    EntityRelationship,
    EntityType,
    RelationshipType,
    ResolutionStatus,
)

logger = logging.getLogger("zye.computer_intelligence.entity_linking.index")

DEFAULT_DB_PATH = Path("data/document_entity_graph.db")


class DocumentRelationshipIndex:
    """Persistent SQLite database manager for entity graphs and document relationships."""

    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_tables()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_tables(self) -> None:
        """Initializes relational database schema with indices."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.executescript("""
            CREATE TABLE IF NOT EXISTS documents (
                document_id TEXT PRIMARY KEY,
                file_path TEXT NOT NULL,
                file_type TEXT,
                indexed_at TEXT NOT NULL,
                total_mentions INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS entities (
                entity_id TEXT PRIMARY KEY,
                canonical_name TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                resolution_status TEXT NOT NULL,
                confidence_score REAL DEFAULT 0.0,
                mention_count INTEGER DEFAULT 0,
                document_count INTEGER DEFAULT 0,
                attributes_json TEXT
            );

            CREATE TABLE IF NOT EXISTS entity_mentions (
                mention_id TEXT PRIMARY KEY,
                entity_id TEXT NOT NULL,
                document_id TEXT NOT NULL,
                original_text TEXT NOT NULL,
                normalized_text TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                page_number INTEGER,
                sheet_name TEXT,
                section_name TEXT,
                line_number INTEGER,
                char_start INTEGER,
                char_end INTEGER,
                surrounding_text TEXT,
                extraction_method TEXT,
                FOREIGN KEY (entity_id) REFERENCES entities(entity_id),
                FOREIGN KEY (document_id) REFERENCES documents(document_id)
            );

            CREATE TABLE IF NOT EXISTS entity_aliases (
                entity_id TEXT NOT NULL,
                alias_name TEXT NOT NULL,
                PRIMARY KEY (entity_id, alias_name),
                FOREIGN KEY (entity_id) REFERENCES entities(entity_id)
            );

            CREATE TABLE IF NOT EXISTS entity_relationships (
                relationship_id TEXT PRIMARY KEY,
                source_entity_id TEXT NOT NULL,
                target_entity_id TEXT NOT NULL,
                relationship_type TEXT NOT NULL,
                evidence TEXT,
                is_explicit INTEGER DEFAULT 0,
                source_document_id TEXT NOT NULL,
                provenance_json TEXT
            );

            CREATE TABLE IF NOT EXISTS entity_match_candidates (
                candidate_id TEXT PRIMARY KEY,
                entity_a_id TEXT NOT NULL,
                entity_b_id TEXT NOT NULL,
                score REAL NOT NULL,
                status TEXT NOT NULL,
                reasons_json TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(canonical_name);
            CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type);
            CREATE INDEX IF NOT EXISTS idx_mentions_doc ON entity_mentions(document_id);
            CREATE INDEX IF NOT EXISTS idx_mentions_entity ON entity_mentions(entity_id);
            CREATE INDEX IF NOT EXISTS idx_rel_source ON entity_relationships(source_entity_id);
            CREATE INDEX IF NOT EXISTS idx_rel_target ON entity_relationships(target_entity_id);
            """)
            conn.commit()

    def record_document(self, document_id: str, file_path: str, file_type: str, total_mentions: int) -> None:
        """Inserts or replaces indexed document entry."""
        from datetime import datetime, timezone
        now_str = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO documents (document_id, file_path, file_type, indexed_at, total_mentions)
                VALUES (?, ?, ?, ?, ?)
                """,
                (document_id, file_path, file_type, now_str, total_mentions),
            )
            conn.commit()

    def save_entities_and_mentions(
        self,
        entities: List[CanonicalEntity],
        mentions: List[EntityMention],
        relationships: List[EntityRelationship],
        candidates: List[EntityMatchCandidate],
    ) -> None:
        """Stores extracted and resolved graph components into SQLite."""
        with self._get_connection() as conn:
            cur = conn.cursor()

            # Insert/Update Entities
            for ent in entities:
                cur.execute(
                    """
                    INSERT OR REPLACE INTO entities 
                    (entity_id, canonical_name, entity_type, resolution_status, confidence_score, mention_count, document_count, attributes_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        ent.entity_id,
                        ent.canonical_name,
                        ent.entity_type.value,
                        ent.resolution_status.value,
                        ent.confidence_score,
                        ent.mention_count,
                        ent.document_count,
                        json.dumps(ent.attributes),
                    ),
                )
                # Aliases
                for alias in ent.aliases:
                    cur.execute(
                        "INSERT OR IGNORE INTO entity_aliases (entity_id, alias_name) VALUES (?, ?)",
                        (ent.entity_id, alias),
                    )

            # Insert Mentions
            # Build map of (type, normalized_text) -> entity_id
            key_to_eid = {(e.entity_type.value, e.canonical_name.lower()): e.entity_id for e in entities}
            for m in mentions:
                eid = key_to_eid.get((m.entity_type.value, m.normalized_text.lower()), "unknown")
                cur.execute(
                    """
                    INSERT OR REPLACE INTO entity_mentions
                    (mention_id, entity_id, document_id, original_text, normalized_text, entity_type,
                     page_number, sheet_name, section_name, line_number, char_start, char_end,
                     surrounding_text, extraction_method)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        m.mention_id,
                        eid,
                        m.document_id,
                        m.original_text,
                        m.normalized_text,
                        m.entity_type.value,
                        m.page_number,
                        m.sheet_name,
                        m.section_name,
                        m.line_number,
                        m.char_start,
                        m.char_end,
                        m.surrounding_text,
                        m.extraction_method,
                    ),
                )

            # Insert Relationships
            for rel in relationships:
                cur.execute(
                    """
                    INSERT OR REPLACE INTO entity_relationships
                    (relationship_id, source_entity_id, target_entity_id, relationship_type, evidence, is_explicit, source_document_id, provenance_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        rel.relationship_id,
                        rel.source_entity_id,
                        rel.target_entity_id,
                        rel.relationship_type.value,
                        rel.evidence,
                        1 if rel.is_explicit else 0,
                        rel.source_document_id,
                        json.dumps(rel.provenance),
                    ),
                )

            # Insert Match Candidates
            for cand in candidates:
                cur.execute(
                    """
                    INSERT OR REPLACE INTO entity_match_candidates
                    (candidate_id, entity_a_id, entity_b_id, score, status, reasons_json)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        cand.candidate_id,
                        cand.entity_a_id,
                        cand.entity_b_id,
                        cand.score,
                        cand.status,
                        json.dumps(cand.match_reasons),
                    ),
                )

            conn.commit()
