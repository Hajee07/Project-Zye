"""
Entity Relationship Engine.
Extracts semantic connections between entities and documents:
- ENTITY_MENTIONED_IN_DOCUMENT
- SAME_ENTITY_CANDIDATE
- DOCUMENT_REFERENCES_PROJECT
- PERSON_ASSOCIATED_WITH_ORGANIZATION
- PROJECT_REFERENCES_TECHNOLOGY
Distinguishes between explicit relationships and co-occurrence in document context.
"""

from __future__ import annotations

import logging
import uuid
from typing import Dict, List

from zye_computer_intelligence.schemas.entity_schemas import (
    CanonicalEntity,
    EntityMention,
    EntityRelationship,
    EntityType,
    RelationshipType,
)

logger = logging.getLogger("zye.computer_intelligence.entity_linking.relationships")


class EntityRelationshipEngine:
    """Discovers relationships across entities and documents."""

    @classmethod
    def build_relationships(
        cls,
        entities: List[CanonicalEntity],
        mentions: List[EntityMention],
    ) -> List[EntityRelationship]:
        """Infers document mentions, organization associations, and tech references."""
        relationships: List[EntityRelationship] = []

        # Map canonical entities by ID and name
        entity_by_id: Dict[str, CanonicalEntity] = {e.entity_id: e for e in entities}
        name_to_entity: Dict[str, CanonicalEntity] = {e.canonical_name.lower(): e for e in entities}

        # 1. Document mentions relationship for all entities
        for ent in entities:
            docs_seen = set()
            for m in ent.sample_mentions:
                if m.document_id in docs_seen:
                    continue
                docs_seen.add(m.document_id)

                rel_type = RelationshipType.ENTITY_MENTIONED_IN_DOCUMENT
                if ent.entity_type == EntityType.PROJECT:
                    rel_type = RelationshipType.DOCUMENT_REFERENCES_PROJECT

                relationships.append(
                    EntityRelationship(
                        relationship_id=f"rel_{uuid.uuid4().hex[:10]}",
                        source_entity_id=m.document_id,
                        target_entity_id=ent.entity_id,
                        relationship_type=rel_type,
                        evidence=m.surrounding_text,
                        is_explicit=True,
                        source_document_id=m.document_id,
                        provenance={
                            "document_id": m.document_id,
                            "page_number": m.page_number,
                            "sheet_name": m.sheet_name,
                        },
                    )
                )

        # 2. Co-occurrence / Association relationships in same snippet/document
        # Find PERSON and ORGANIZATION in same document
        person_entities = [e for e in entities if e.entity_type == EntityType.PERSON]
        org_entities = [e for e in entities if e.entity_type == EntityType.ORGANIZATION]
        proj_entities = [e for e in entities if e.entity_type == EntityType.PROJECT]
        tech_entities = [e for e in entities if e.entity_type == EntityType.TECHNICAL_ENTITY]

        for p in person_entities:
            p_docs = {m.document_id for m in p.sample_mentions}
            for org in org_entities:
                shared_docs = p_docs.intersection({m.document_id for m in org.sample_mentions})
                for doc in shared_docs:
                    relationships.append(
                        EntityRelationship(
                            relationship_id=f"rel_{uuid.uuid4().hex[:10]}",
                            source_entity_id=p.entity_id,
                            target_entity_id=org.entity_id,
                            relationship_type=RelationshipType.PERSON_ASSOCIATED_WITH_ORGANIZATION,
                            evidence=f"Both '{p.canonical_name}' and '{org.canonical_name}' appear in document '{doc}'",
                            is_explicit=False,
                            source_document_id=doc,
                            provenance={"shared_document": doc},
                        )
                    )

        # 3. Project references technology in same document
        for proj in proj_entities:
            proj_docs = {m.document_id for m in proj.sample_mentions}
            for tech in tech_entities:
                shared_docs = proj_docs.intersection({m.document_id for m in tech.sample_mentions})
                for doc in shared_docs:
                    relationships.append(
                        EntityRelationship(
                            relationship_id=f"rel_{uuid.uuid4().hex[:10]}",
                            source_entity_id=proj.entity_id,
                            target_entity_id=tech.entity_id,
                            relationship_type=RelationshipType.PROJECT_REFERENCES_TECHNOLOGY,
                            evidence=f"Project '{proj.canonical_name}' and technology '{tech.canonical_name}' co-occur in '{doc}'",
                            is_explicit=False,
                            source_document_id=doc,
                            provenance={"shared_document": doc},
                        )
                    )

        return relationships
