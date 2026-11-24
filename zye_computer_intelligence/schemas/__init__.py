"""
Schemas for Computer Intelligence Day 34 Deduplication and Entity Linking.
"""

from .duplicate_schemas import (
    DuplicateFileInfo,
    DuplicateGroup,
    DuplicateScanRequest,
    DuplicateScanResult,
    DuplicateType,
    VerificationStatus,
)
from .entity_schemas import (
    CanonicalEntity,
    CrossDocumentEntityResult,
    EntityMatchCandidate,
    EntityMention,
    EntityRelationship,
    EntityType,
    RelationshipType,
    ResolutionStatus,
)

__all__ = [
    "DuplicateFileInfo",
    "DuplicateGroup",
    "DuplicateScanRequest",
    "DuplicateScanResult",
    "DuplicateType",
    "VerificationStatus",
    "CanonicalEntity",
    "CrossDocumentEntityResult",
    "EntityMatchCandidate",
    "EntityMention",
    "EntityRelationship",
    "EntityType",
    "RelationshipType",
    "ResolutionStatus",
]
