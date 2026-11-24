"""
ZYE AI Cross-Document Entity Linking Package.
Extracts entities across 9 categories, canonicalizes with provenance,
infers structural and co-occurrence relationships, and maintains
a persistent SQLite entity knowledge graph.
"""

from zye_computer_intelligence.entity_linking.cross_document_entity_linker import CrossDocumentEntityLinker
from zye_computer_intelligence.entity_linking.document_relationship_index import (
    DEFAULT_DB_PATH,
    DocumentRelationshipIndex,
)
from zye_computer_intelligence.entity_linking.entity_extraction_engine import EntityExtractionEngine
from zye_computer_intelligence.entity_linking.entity_linking_manager import EntityLinkingManager
from zye_computer_intelligence.entity_linking.entity_matcher import EntityMatcher
from zye_computer_intelligence.entity_linking.entity_normalizer import (
    extract_name_tokens,
    normalize_entity_text,
)
from zye_computer_intelligence.entity_linking.entity_provenance import (
    build_provenance_dict,
    format_provenance_citation,
)
from zye_computer_intelligence.entity_linking.entity_query_engine import EntityQueryEngine
from zye_computer_intelligence.entity_linking.entity_relationship_engine import EntityRelationshipEngine
from zye_computer_intelligence.entity_linking.entity_resolution_engine import EntityResolutionEngine
from zye_computer_intelligence.entity_linking.entity_taxonomy import (
    KNOWN_TECH_ENTITIES,
    ORG_SUFFIXES,
    PERSON_HONORIFICS,
)

__all__ = [
    "CrossDocumentEntityLinker",
    "EntityLinkingManager",
    "EntityExtractionEngine",
    "EntityResolutionEngine",
    "EntityMatcher",
    "EntityRelationshipEngine",
    "EntityQueryEngine",
    "DocumentRelationshipIndex",
    "DEFAULT_DB_PATH",
    "normalize_entity_text",
    "extract_name_tokens",
    "format_provenance_citation",
    "build_provenance_dict",
]
