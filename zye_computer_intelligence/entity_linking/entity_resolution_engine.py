"""
Entity Resolution Engine.
Clusters mentions into CanonicalEntity instances with resolution statuses:
- RESOLVED: High confidence with corroborating evidence
- HIGH_CONFIDENCE_CANDIDATE: Strong match
- AMBIGUOUS: Conflicting or isolated short name
- UNRESOLVED: Insufficient match confidence
Enforces strict disambiguation safeguards (e.g. never merging common first names alone).
"""

from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from typing import Dict, List, Tuple

from zye_computer_intelligence.entity_linking.entity_matcher import EntityMatcher
from zye_computer_intelligence.schemas.entity_schemas import (
    CanonicalEntity,
    EntityMatchCandidate,
    EntityMention,
    EntityType,
    ResolutionStatus,
)

logger = logging.getLogger("zye.computer_intelligence.entity_linking.resolution")


class EntityResolutionEngine:
    """Resolves and consolidates entity mentions into canonical entities."""

    @classmethod
    def resolve_mentions(
        cls, mentions: List[EntityMention]
    ) -> Tuple[List[CanonicalEntity], List[EntityMatchCandidate]]:
        """
        Groups mentions by normalized form, evaluates cross-mentions,
        and assigns resolution status.
        """
        # Bucket mentions by (entity_type, normalized_text.lower())
        mention_buckets: Dict[Tuple[EntityType, str], List[EntityMention]] = defaultdict(list)
        for m in mentions:
            mention_buckets[(m.entity_type, m.normalized_text.lower())].append(m)

        canonical_entities: List[CanonicalEntity] = []
        match_candidates: List[EntityMatchCandidate] = []

        for (ent_type, norm_key), group in mention_buckets.items():
            primary_mention = group[0]
            display_name = primary_mention.normalized_text
            distinct_docs = {m.document_id for m in group}

            # Check if this name is an ambiguous single word for a PERSON
            is_single_word = len(display_name.split()) == 1
            if ent_type == EntityType.PERSON and is_single_word:
                # Single word person names across different documents are AMBIGUOUS
                if len(distinct_docs) > 1:
                    status = ResolutionStatus.AMBIGUOUS
                    confidence = 0.50
                else:
                    status = ResolutionStatus.HIGH_CONFIDENCE_CANDIDATE
                    confidence = 0.70
            elif ent_type in (EntityType.IDENTIFIER, EntityType.CONTACT_INFO):
                status = ResolutionStatus.RESOLVED
                confidence = 1.0
            elif len(distinct_docs) > 1 or len(group) >= 2:
                status = ResolutionStatus.RESOLVED
                confidence = 0.90
            else:
                status = ResolutionStatus.HIGH_CONFIDENCE_CANDIDATE
                confidence = 0.80

            entity_id = f"ent_{uuid.uuid4().hex[:10]}"
            aliases = list({m.original_text for m in group if m.original_text.lower() != display_name.lower()})

            canonical_ent = CanonicalEntity(
                entity_id=entity_id,
                canonical_name=display_name,
                entity_type=ent_type,
                aliases=aliases,
                mention_count=len(group),
                document_count=len(distinct_docs),
                resolution_status=status,
                confidence_score=confidence,
                sample_mentions=group[:10],
            )
            canonical_entities.append(canonical_ent)

        # Cross-entity candidate matching (detect potential aliases / overlaps)
        for i in range(len(canonical_entities)):
            for j in range(i + 1, len(canonical_entities)):
                ent_a = canonical_entities[i]
                ent_b = canonical_entities[j]
                if ent_a.entity_type != ent_b.entity_type:
                    continue

                score, reasons, conflicts = EntityMatcher.calculate_match_score(
                    ent_a.canonical_name, ent_a.entity_type,
                    ent_b.canonical_name, ent_b.entity_type,
                )

                if score >= 0.70:
                    cand_status = "ACCEPTED" if score >= 0.85 else "CANDIDATE"
                    if conflicts:
                        cand_status = "AMBIGUOUS"

                    cand = EntityMatchCandidate(
                        candidate_id=f"cand_{uuid.uuid4().hex[:8]}",
                        entity_a_id=ent_a.entity_id,
                        entity_b_id=ent_b.entity_id,
                        score=score,
                        match_reasons=reasons,
                        conflict_reasons=conflicts,
                        status=cand_status,
                    )
                    match_candidates.append(cand)

        return canonical_entities, match_candidates
