"""
Entity Linking Manager.
Orchestrates multi-document extraction, entity resolution, relationship inference,
and persistence to the SQLite entity graph database.
"""

from __future__ import annotations

import logging
import time
import uuid
from pathlib import Path
from typing import List, Optional

from zye_computer_intelligence.entity_linking.document_relationship_index import (
    DEFAULT_DB_PATH,
    DocumentRelationshipIndex,
)
from zye_computer_intelligence.entity_linking.entity_extraction_engine import EntityExtractionEngine
from zye_computer_intelligence.entity_linking.entity_relationship_engine import EntityRelationshipEngine
from zye_computer_intelligence.entity_linking.entity_resolution_engine import EntityResolutionEngine
from zye_computer_intelligence.schemas.entity_schemas import (
    CrossDocumentEntityResult,
    EntityMention,
    ResolutionStatus,
)
from zye_computer_intelligence.security.local_search_policy import LocalSearchPolicy
from zye_computer_intelligence.security.processing_resource_policy import ProcessingResourcePolicy

logger = logging.getLogger("zye.computer_intelligence.entity_linking.manager")


class EntityLinkingManager:
    """Coordinates batch document processing, entity extraction, and graph construction."""

    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self.db_path = db_path
        self.index = DocumentRelationshipIndex(db_path)

    def process_documents(self, file_paths: List[Path]) -> CrossDocumentEntityResult:
        """Processes a collection of files into the entity graph."""
        start_time = time.perf_counter()
        extraction_id = f"ext_{uuid.uuid4().hex[:12]}"

        all_mentions: List[EntityMention] = []
        valid_docs_count = 0

        # Cap files by resource policy
        bounded_files = file_paths[:ProcessingResourcePolicy.MAX_TOTAL_FILES_TO_SCAN]

        for p in bounded_files:
            try:
                resolved = p.resolve()
                if not resolved.exists() or not resolved.is_file():
                    continue

                # Path authorization check
                is_auth, _ = LocalSearchPolicy.validate_search_path(resolved)
                if not is_auth:
                    logger.warning("File '%s' not authorized by search policy", resolved)
                    continue

                doc_mentions = EntityExtractionEngine.extract_from_document(resolved)
                all_mentions.extend(doc_mentions)

                # Record document in database
                self.index.record_document(
                    document_id=resolved.name,
                    file_path=str(resolved),
                    file_type=resolved.suffix.lstrip(".").lower(),
                    total_mentions=len(doc_mentions),
                )
                valid_docs_count += 1

            except Exception as exc:
                logger.error("Error processing document '%s': %s", p, exc)

        # Step 2: Resolve mentions into canonical entities
        canonical_entities, candidates = EntityResolutionEngine.resolve_mentions(all_mentions)

        # Step 3: Infer relationships
        relationships = EntityRelationshipEngine.build_relationships(
            entities=canonical_entities,
            mentions=all_mentions,
        )

        # Step 4: Persist in SQLite
        self.index.save_entities_and_mentions(
            entities=canonical_entities,
            mentions=all_mentions,
            relationships=relationships,
            candidates=candidates,
        )

        resolved_count = sum(1 for e in canonical_entities if e.resolution_status == ResolutionStatus.RESOLVED)
        ambiguous_count = sum(1 for c in candidates if c.status == "AMBIGUOUS")
        duration_ms = (time.perf_counter() - start_time) * 1000.0

        return CrossDocumentEntityResult(
            extraction_id=extraction_id,
            status="COMPLETED",
            total_documents_processed=valid_docs_count,
            total_mentions_found=len(all_mentions),
            unique_entities_count=len(canonical_entities),
            resolved_entities_count=resolved_count,
            ambiguous_candidates_count=ambiguous_count,
            relationships_count=len(relationships),
            duration_ms=duration_ms,
            entities=canonical_entities,
            relationships=relationships,
            ambiguous_candidates=candidates,
        )
