"""
Cross-Document Entity Linker Facade.
High-level interface for document entity extraction, cross-document linking,
profile retrieval, and graph querying.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from zye_computer_intelligence.entity_linking.document_relationship_index import DEFAULT_DB_PATH
from zye_computer_intelligence.entity_linking.entity_linking_manager import EntityLinkingManager
from zye_computer_intelligence.entity_linking.entity_query_engine import EntityQueryEngine
from zye_computer_intelligence.schemas.entity_schemas import CrossDocumentEntityResult

logger = logging.getLogger("zye.computer_intelligence.entity_linking.facade")


class CrossDocumentEntityLinker:
    """Master facade for entity extraction, resolution, and graph intelligence."""

    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self.db_path = db_path
        self.manager = EntityLinkingManager(db_path)
        self.query_engine = EntityQueryEngine(db_path)

    def index_documents_sync(self, file_paths: List[str]) -> CrossDocumentEntityResult:
        """Processes and indexes documents synchronously."""
        paths = [Path(p) for p in file_paths]
        return self.manager.process_documents(paths)

    async def index_documents(self, file_paths: List[str]) -> CrossDocumentEntityResult:
        """Processes and indexes documents asynchronously."""
        return await asyncio.to_thread(self.index_documents_sync, file_paths)

    def index_directory_sync(self, dir_path: str, recursive: bool = True) -> CrossDocumentEntityResult:
        """Discovers supported documents in a directory and indexes them."""
        p = Path(dir_path)
        if not p.exists() or not p.is_dir():
            raise ValueError(f"Directory does not exist: {dir_path}")

        supported_exts = {".pdf", ".docx", ".xlsx", ".csv", ".json", ".txt", ".md", ".py"}
        file_paths: List[Path] = []

        if recursive:
            for item in p.rglob("*"):
                if item.is_file() and item.suffix.lower() in supported_exts:
                    file_paths.append(item)
        else:
            for item in p.glob("*"):
                if item.is_file() and item.suffix.lower() in supported_exts:
                    file_paths.append(item)

        return self.manager.process_documents(file_paths)

    async def index_directory(self, dir_path: str, recursive: bool = True) -> CrossDocumentEntityResult:
        """Discovers and indexes documents asynchronously."""
        return await asyncio.to_thread(self.index_directory_sync, dir_path, recursive)

    def search_entities(
        self,
        query: str,
        entity_types: Optional[List[str]] = None,
        min_confidence: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """Searches entities by name or alias."""
        return self.query_engine.search_entities(query, entity_types, min_confidence)

    def get_entity_profile(self, entity_id_or_name: str) -> Optional[Dict[str, Any]]:
        """Retrieves entity profile with mentions, citations, and relationships."""
        return self.query_engine.get_entity_profile(entity_id_or_name)

    def find_cross_document_connections(self, doc_a: str, doc_b: str) -> List[Dict[str, Any]]:
        """Finds entities connecting two documents."""
        return self.query_engine.find_cross_document_connections(doc_a, doc_b)

    def get_document_entities(self, doc_id: str) -> List[Dict[str, Any]]:
        """Returns all entities mentioned in a specific document."""
        return self.query_engine.find_entities_in_document(doc_id)

    def get_graph_statistics(self) -> Dict[str, Any]:
        """Returns graph statistics."""
        return self.query_engine.get_graph_statistics()
