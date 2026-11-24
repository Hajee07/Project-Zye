"""
Entity Matcher and Similarity Scoring.
Computes typed match confidence scores between entity mentions
using exact match, Jaccard token overlap, identifier comparison, and acronym matching.
"""

from __future__ import annotations

import logging
from typing import List, Tuple

from zye_computer_intelligence.entity_linking.entity_normalizer import (
    extract_name_tokens,
    normalize_entity_text,
)
from zye_computer_intelligence.schemas.entity_schemas import (
    CanonicalEntity,
    EntityMatchCandidate,
    EntityMention,
    EntityType,
)

logger = logging.getLogger("zye.computer_intelligence.entity_linking.matcher")


class EntityMatcher:
    """Calculates similarity scores and generates candidate match records."""

    @classmethod
    def calculate_match_score(
        cls,
        text_a: str,
        type_a: EntityType,
        text_b: str,
        type_b: EntityType,
    ) -> Tuple[float, List[str], List[str]]:
        """
        Calculates similarity score (0.0 to 1.0), matching reasons, and conflicts.
        """
        reasons: List[str] = []
        conflicts: List[str] = []

        if type_a != type_b:
            conflicts.append(f"Entity types differ: {type_a.value} vs {type_b.value}")
            return 0.0, reasons, conflicts

        norm_a = normalize_entity_text(text_a, type_a)
        norm_b = normalize_entity_text(text_b, type_b)

        # 1. Exact identical string
        if text_a.strip().lower() == text_b.strip().lower():
            reasons.append("Exact string match")
            return 1.0, reasons, conflicts

        # 2. Normalized match
        if norm_a.lower() == norm_b.lower() and norm_a:
            reasons.append(f"Normalized string match ('{norm_a}')")
            return 0.95, reasons, conflicts

        # 3. For identifiers / contact info, exact match is required
        if type_a in (EntityType.IDENTIFIER, EntityType.CONTACT_INFO):
            conflicts.append("Unique identifier mismatch")
            return 0.0, reasons, conflicts

        # 4. Acronym match (e.g. "TCS" vs "Tata Consultancy Services")
        if cls.is_acronym_match(norm_a, norm_b):
            reasons.append(f"Acronym expansion match between '{norm_a}' and '{norm_b}'")
            return 0.85, reasons, conflicts

        # 5. Token Jaccard similarity for multi-word entities
        tokens_a = extract_name_tokens(norm_a)
        tokens_b = extract_name_tokens(norm_b)

        if tokens_a and tokens_b:
            intersection = tokens_a.intersection(tokens_b)
            union = tokens_a.union(tokens_b)
            jaccard = len(intersection) / len(union)

            if jaccard >= 0.75:
                reasons.append(f"High token overlap ({jaccard:.2f}): shared {list(intersection)}")
                return round(0.70 + (jaccard * 0.25), 2), reasons, conflicts

            if jaccard >= 0.50:
                reasons.append(f"Moderate token overlap ({jaccard:.2f}): shared {list(intersection)}")
                conflicts.append("Partial token match requires manual or contextual verification")
                return round(0.50 + (jaccard * 0.20), 2), reasons, conflicts

        conflicts.append("Insufficient lexical similarity")
        return 0.10, reasons, conflicts

    @classmethod
    def is_acronym_match(cls, text_a: str, text_b: str) -> bool:
        """Checks if one string is an acronym for the other (e.g. 'ZYE' -> 'Zye Youth Engine')."""
        words_a = text_a.split()
        words_b = text_b.split()

        if len(words_a) == 1 and len(words_b) > 1:
            acronym = "".join(w[0] for w in words_b if w).upper()
            return words_a[0].upper() == acronym

        if len(words_b) == 1 and len(words_a) > 1:
            acronym = "".join(w[0] for w in words_a if w).upper()
            return words_b[0].upper() == acronym

        return False
