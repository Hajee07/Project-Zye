"""
Entity Normalizer.
Standardizes entity mention strings using Unicode NFC normalization,
whitespace collapse, casing rules, and suffix/title stripping
while preserving the exact raw text and multilingual Tamil/Tanglish integrity.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Tuple

from zye_computer_intelligence.entity_linking.entity_taxonomy import (
    ORG_SUFFIXES,
    PERSON_HONORIFICS,
)
from zye_computer_intelligence.schemas.entity_schemas import EntityType


def normalize_entity_text(raw_text: str, entity_type: EntityType) -> str:
    """
    Normalizes mention text into canonical matching form.
    - Applies Unicode NFC normalization
    - Strips leading/trailing punctuation and whitespace
    - Normalizes internal whitespace
    - Conditionally strips honorifics (for persons) or corporate suffixes (for orgs)
    """
    if not raw_text:
        return ""

    # Step 1: Unicode NFC Normalization
    text = unicodedata.normalize("NFC", raw_text.strip())

    # Step 2: Collapse repeated whitespace
    text = re.sub(r"\s+", " ", text)

    # Step 3: Strip surrounding quotes or parentheses
    text = text.strip("\"'()[]{}.,;: ")

    if not text:
        return ""

    # Step 4: Type-specific normalization
    if entity_type == EntityType.PERSON:
        tokens = text.split(" ")
        if len(tokens) > 1 and tokens[0].lower().rstrip(".") in PERSON_HONORIFICS:
            text = " ".join(tokens[1:])

    elif entity_type == EntityType.ORGANIZATION:
        tokens = text.split(" ")
        if len(tokens) > 1:
            last_token = tokens[-1].lower().rstrip(".")
            if last_token in ORG_SUFFIXES:
                text = " ".join(tokens[:-1])

    elif entity_type in (EntityType.CONTACT_INFO, EntityType.IDENTIFIER):
        # Email addresses and identifiers are strictly lowercased
        text = text.lower()

    elif entity_type == EntityType.TECHNICAL_ENTITY:
        text = text.lower()

    return text.strip()


def extract_name_tokens(text: str) -> set[str]:
    """Extracts alphanumeric lowercase word tokens from an entity name for Jaccard matching."""
    cleaned = re.sub(r"[^\w\s]", " ", text.lower())
    return {tok for tok in cleaned.split() if len(tok) > 1}
