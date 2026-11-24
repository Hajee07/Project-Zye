"""
Cross-Document Entity Linking Schemas.
Pydantic data models for entity extraction, normalization, resolution,
source provenance, and relationship graphs.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class EntityType(str, Enum):
    PERSON = "PERSON"
    ORGANIZATION = "ORGANIZATION"
    PROJECT = "PROJECT"
    PRODUCT = "PRODUCT"
    LOCATION = "LOCATION"
    TECHNICAL_ENTITY = "TECHNICAL_ENTITY"
    IDENTIFIER = "IDENTIFIER"
    CONTACT_INFO = "CONTACT_INFO"
    TEMPORAL_ENTITY = "TEMPORAL_ENTITY"


class ResolutionStatus(str, Enum):
    RESOLVED = "RESOLVED"
    HIGH_CONFIDENCE_CANDIDATE = "HIGH_CONFIDENCE_CANDIDATE"
    AMBIGUOUS = "AMBIGUOUS"
    UNRESOLVED = "UNRESOLVED"
    REJECTED_MATCH = "REJECTED_MATCH"


class RelationshipType(str, Enum):
    ENTITY_MENTIONED_IN_DOCUMENT = "ENTITY_MENTIONED_IN_DOCUMENT"
    SAME_ENTITY_CANDIDATE = "SAME_ENTITY_CANDIDATE"
    ENTITY_ALIAS_OF = "ENTITY_ALIAS_OF"
    DOCUMENT_REFERENCES_PROJECT = "DOCUMENT_REFERENCES_PROJECT"
    PERSON_ASSOCIATED_WITH_ORGANIZATION = "PERSON_ASSOCIATED_WITH_ORGANIZATION"
    PRODUCT_BELONGS_TO_ORGANIZATION = "PRODUCT_BELONGS_TO_ORGANIZATION"
    PROJECT_REFERENCES_TECHNOLOGY = "PROJECT_REFERENCES_TECHNOLOGY"


class EntityMention(BaseModel):
    mention_id: str = Field(..., description="Unique mention identifier")
    document_id: str = Field(..., description="Document identifier or relative path")
    file_path: str = Field(..., description="Absolute path to source document")
    original_text: str = Field(..., description="Exact raw text snippet extracted from document")
    normalized_text: str = Field(..., description="Canonicalized or normalized candidate text")
    entity_type: EntityType = Field(..., description="Categorized entity taxonomy type")
    page_number: int | None = Field(default=None, description="PDF/document page number where found")
    sheet_name: str | None = Field(default=None, description="Spreadsheet sheet name where found")
    section_name: str | None = Field(default=None, description="Heading/section or definition name")
    line_number: int | None = Field(default=None, description="Source line number where found")
    char_start: int | None = Field(default=None, description="Character start offset in text")
    char_end: int | None = Field(default=None, description="Character end offset in text")
    surrounding_text: str = Field(default="", description="Surrounding contextual excerpt")
    extraction_method: str = Field(default="rule_pattern", description="Method: rule_pattern, regex, structural")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CanonicalEntity(BaseModel):
    entity_id: str = Field(..., description="Unique canonical entity ID")
    canonical_name: str = Field(..., description="Standardized canonical display name")
    entity_type: EntityType = Field(..., description="Taxonomy category")
    aliases: list[str] = Field(default_factory=list, description="Verified or candidate aliases")
    mention_count: int = Field(default=0, description="Total occurrences across documents")
    document_count: int = Field(default=0, description="Distinct source documents containing mentions")
    resolution_status: ResolutionStatus = Field(default=ResolutionStatus.UNRESOLVED)
    confidence_score: float = Field(default=0.0, description="Heuristic confidence / ranking score (0.0 to 1.0)")
    attributes: dict[str, Any] = Field(default_factory=dict, description="Metadata attributes (e.g. role, domain)")
    sample_mentions: list[EntityMention] = Field(default_factory=list, description="Sample source mentions")


class EntityMatchCandidate(BaseModel):
    candidate_id: str = Field(..., description="Candidate match identifier")
    entity_a_id: str = Field(..., description="Primary entity ID")
    entity_b_id: str = Field(..., description="Matched entity ID")
    score: float = Field(..., description="Match similarity score (0.0 to 1.0)")
    match_reasons: list[str] = Field(default_factory=list, description="Evidence reasons for candidate match")
    conflict_reasons: list[str] = Field(default_factory=list, description="Ambiguity or conflict warnings")
    status: str = Field(default="CANDIDATE", description="CANDIDATE, ACCEPTED, REJECTED, AMBIGUOUS")


class EntityRelationship(BaseModel):
    relationship_id: str = Field(..., description="Unique relationship ID")
    source_entity_id: str = Field(..., description="Source entity ID or document ID")
    target_entity_id: str = Field(..., description="Target entity ID")
    relationship_type: RelationshipType = Field(..., description="Semantic relationship category")
    evidence: str = Field(default="", description="Textual or structural evidence for relationship")
    is_explicit: bool = Field(default=False, description="True if explicitly stated; False if inferred co-occurrence")
    source_document_id: str = Field(..., description="Document in which relationship is witnessed")
    provenance: dict[str, Any] = Field(default_factory=dict, description="Detailed location provenance")


class CrossDocumentEntityResult(BaseModel):
    extraction_id: str = Field(..., description="Unique entity extraction run identifier")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: str = Field(default="COMPLETED")
    total_documents_processed: int = Field(default=0)
    total_mentions_found: int = Field(default=0)
    unique_entities_count: int = Field(default=0)
    resolved_entities_count: int = Field(default=0)
    ambiguous_candidates_count: int = Field(default=0)
    relationships_count: int = Field(default=0)
    duration_ms: float = Field(default=0.0)
    entities: list[CanonicalEntity] = Field(default_factory=list)
    relationships: list[EntityRelationship] = Field(default_factory=list)
    ambiguous_candidates: list[EntityMatchCandidate] = Field(default_factory=list)
