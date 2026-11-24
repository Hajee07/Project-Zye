"""
Entity Query Engine.
Executes semantic graph queries, cross-document connection discovery,
entity profiling, and evidence citation lookups against DocumentRelationshipIndex.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from zye_computer_intelligence.entity_linking.document_relationship_index import (
    DEFAULT_DB_PATH,
    DocumentRelationshipIndex,
)
from zye_computer_intelligence.schemas.entity_schemas import (
    CanonicalEntity,
    EntityMention,
    EntityType,
    ResolutionStatus,
)

logger = logging.getLogger("zye.computer_intelligence.entity_linking.query")


class EntityQueryEngine:
    """Executes high-level queries against the document relationship index."""

    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self.index = DocumentRelationshipIndex(db_path)

    def search_entities(
        self,
        query: str,
        entity_types: Optional[List[str]] = None,
        min_confidence: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """Searches for entities matching a substring or alias."""
        sql = """
        SELECT e.*, GROUP_CONCAT(a.alias_name, '; ') as aliases
        FROM entities e
        LEFT JOIN entity_aliases a ON e.entity_id = a.entity_id
        WHERE (e.canonical_name LIKE ? OR a.alias_name LIKE ?)
          AND e.confidence_score >= ?
        """
        params: List[Any] = [f"%{query}%", f"%{query}%", min_confidence]

        if entity_types:
            placeholders = ",".join("?" for _ in entity_types)
            sql += f" AND e.entity_type IN ({placeholders})"
            params.extend(entity_types)

        sql += " GROUP BY e.entity_id ORDER BY e.confidence_score DESC, e.mention_count DESC LIMIT 50"

        with self.index._get_connection() as conn:
            cursor = conn.cursor()
            rows = cursor.execute(sql, params).fetchall()

            results = []
            for r in rows:
                alias_list = r["aliases"].split("; ") if r["aliases"] else []
                results.append({
                    "entity_id": r["entity_id"],
                    "canonical_name": r["canonical_name"],
                    "entity_type": r["entity_type"],
                    "resolution_status": r["resolution_status"],
                    "confidence_score": r["confidence_score"],
                    "mention_count": r["mention_count"],
                    "document_count": r["document_count"],
                    "aliases": alias_list,
                })
            return results

    def get_entity_profile(self, entity_id_or_name: str) -> Optional[Dict[str, Any]]:
        """Retrieves comprehensive profile including mentions, citations, and connected entities."""
        with self.index._get_connection() as conn:
            cur = conn.cursor()

            # Find entity
            row = cur.execute(
                "SELECT * FROM entities WHERE entity_id = ? OR canonical_name LIKE ? LIMIT 1",
                (entity_id_or_name, entity_id_or_name),
            ).fetchone()

            if not row:
                return None

            eid = row["entity_id"]

            # Mentions
            mentions_rows = cur.execute(
                "SELECT * FROM entity_mentions WHERE entity_id = ? ORDER BY document_id",
                (eid,),
            ).fetchall()

            mentions = []
            docs_set = set()
            for mr in mentions_rows:
                docs_set.add(mr["document_id"])
                # Build citation string
                cits = [mr["document_id"]]
                if mr["page_number"]:
                    cits.append(f"Page {mr['page_number']}")
                if mr["sheet_name"]:
                    cits.append(f"Sheet '{mr['sheet_name']}'")
                if mr["section_name"]:
                    cits.append(f"Section '{mr['section_name']}'")
                if mr["line_number"]:
                    cits.append(f"Line {mr['line_number']}")

                mentions.append({
                    "mention_id": mr["mention_id"],
                    "document_id": mr["document_id"],
                    "original_text": mr["original_text"],
                    "citation": f"[{', '.join(cits)}]",
                    "surrounding_text": mr["surrounding_text"],
                })

            # Relationships
            rels = cur.execute(
                """
                SELECT r.*, e.canonical_name as target_name, e.entity_type as target_type
                FROM entity_relationships r
                LEFT JOIN entities e ON r.target_entity_id = e.entity_id
                WHERE r.source_entity_id = ? OR r.target_entity_id = ?
                """,
                (eid, eid),
            ).fetchall()

            connected = []
            for rel in rels:
                connected.append({
                    "relationship_id": rel["relationship_id"],
                    "relationship_type": rel["relationship_type"],
                    "source_id": rel["source_entity_id"],
                    "target_id": rel["target_entity_id"],
                    "target_name": rel["target_name"] or rel["target_entity_id"],
                    "evidence": rel["evidence"],
                    "source_document_id": rel["source_document_id"],
                })

            return {
                "entity_id": eid,
                "canonical_name": row["canonical_name"],
                "entity_type": row["entity_type"],
                "resolution_status": row["resolution_status"],
                "confidence_score": row["confidence_score"],
                "total_mentions": len(mentions),
                "distinct_documents": list(docs_set),
                "mentions": mentions,
                "connected_relationships": connected,
            }

    def find_cross_document_connections(self, doc_a: str, doc_b: str) -> List[Dict[str, Any]]:
        """Finds entities that appear in both document A and document B."""
        sql = """
        SELECT e.entity_id, e.canonical_name, e.entity_type, e.resolution_status,
               COUNT(m.mention_id) as total_shared_mentions
        FROM entities e
        JOIN entity_mentions m ON e.entity_id = m.entity_id
        WHERE m.document_id IN (?, ?)
        GROUP BY e.entity_id
        HAVING COUNT(DISTINCT m.document_id) >= 2
        ORDER BY total_shared_mentions DESC
        """
        with self.index._get_connection() as conn:
            cur = conn.cursor()
            rows = cur.execute(sql, (doc_a, doc_b)).fetchall()
            results = []
            for r in rows:
                results.append({
                    "entity_id": r["entity_id"],
                    "canonical_name": r["canonical_name"],
                    "entity_type": r["entity_type"],
                    "resolution_status": r["resolution_status"],
                    "shared_mentions_count": r["total_shared_mentions"],
                })
            return results

    def find_entities_in_document(self, document_id: str) -> List[Dict[str, Any]]:
        """Returns all distinct entities found inside a specific document."""
        sql = """
        SELECT e.entity_id, e.canonical_name, e.entity_type, e.resolution_status,
               COUNT(m.mention_id) as mention_count
        FROM entities e
        JOIN entity_mentions m ON e.entity_id = m.entity_id
        WHERE m.document_id = ?
        GROUP BY e.entity_id
        ORDER BY mention_count DESC
        """
        with self.index._get_connection() as conn:
            cur = conn.cursor()
            rows = cur.execute(sql, (document_id,)).fetchall()
            return [dict(r) for r in rows]

    def get_graph_statistics(self) -> Dict[str, Any]:
        """Returns overall statistical summary of the entity graph."""
        with self.index._get_connection() as conn:
            cur = conn.cursor()
            doc_cnt = cur.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
            ent_cnt = cur.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
            men_cnt = cur.execute("SELECT COUNT(*) FROM entity_mentions").fetchone()[0]
            rel_cnt = cur.execute("SELECT COUNT(*) FROM entity_relationships").fetchone()[0]
            cand_cnt = cur.execute("SELECT COUNT(*) FROM entity_match_candidates").fetchone()[0]

            type_counts = cur.execute(
                "SELECT entity_type, COUNT(*) FROM entities GROUP BY entity_type"
            ).fetchall()

            return {
                "total_documents": doc_cnt,
                "total_entities": ent_cnt,
                "total_mentions": men_cnt,
                "total_relationships": rel_cnt,
                "total_match_candidates": cand_cnt,
                "entities_by_type": {r[0]: r[1] for r in type_counts},
            }
