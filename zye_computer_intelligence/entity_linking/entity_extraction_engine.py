"""
Entity Extraction Engine.
Extracts entities across 9 categories from documents using LocalDocumentExtractor,
regex rules, lexical heuristics, and privacy redaction.
"""

from __future__ import annotations

import logging
import re
import uuid
from pathlib import Path
from typing import Any, List, Optional

from zye_computer_intelligence.entity_linking.entity_normalizer import normalize_entity_text
from zye_computer_intelligence.entity_linking.entity_taxonomy import (
    KNOWN_TECH_ENTITIES,
    ORG_SUFFIXES,
    PERSON_HONORIFICS,
    REGEX_DATE_READABLE,
    REGEX_EMAIL,
    REGEX_GIT_HASH,
    REGEX_ISO_DATE,
    REGEX_PHONE,
    REGEX_PROJECT_ID,
    REGEX_QUARTER,
    REGEX_URL,
    REGEX_UUID,
)
from zye_computer_intelligence.schemas.entity_schemas import EntityMention, EntityType
from zye_computer_intelligence.search.local_document_extractor import LocalDocumentExtractor
from zye_computer_intelligence.security.entity_privacy_policy import EntityPrivacyPolicy

logger = logging.getLogger("zye.computer_intelligence.entity_linking.extractor")


class EntityExtractionEngine:
    """Extracts typed entities with detailed source location provenance."""

    @classmethod
    def extract_from_document(cls, file_path: Path) -> List[EntityMention]:
        """Extracts all entities from a document file."""
        mentions: List[EntityMention] = []
        doc_data = LocalDocumentExtractor.extract_document(file_path)

        if doc_data.get("status") == "ERROR":
            logger.warning("Could not extract document '%s': %s", file_path.name, doc_data.get("error"))
            return mentions

        doc_id = file_path.name
        abs_path = str(file_path.resolve())

        # If sections are available (PDF pages, DOCX paragraphs, XLSX sheets, code lines), process each
        sections = doc_data.get("sections", [])
        if sections:
            for sec in sections:
                sec_type = sec.get("section_type", "")
                page_num = sec.get("page_number")
                sheet_name = sec.get("sheet_name")
                sec_name = sec.get("name") or (sec.get("content")[:40] if sec_type == "heading" else None)
                content = sec.get("content", "")

                sec_mentions = cls.extract_from_text(
                    text=content,
                    doc_id=doc_id,
                    file_path=abs_path,
                    page_number=page_num,
                    sheet_name=sheet_name,
                    section_name=sec_name,
                )
                mentions.extend(sec_mentions)
        else:
            # Fallback to full extracted content
            full_text = doc_data.get("content", "")
            mentions.extend(
                cls.extract_from_text(
                    text=full_text,
                    doc_id=doc_id,
                    file_path=abs_path,
                )
            )

        return mentions

    @classmethod
    def extract_from_text(
        cls,
        text: str,
        doc_id: str,
        file_path: str,
        page_number: Optional[int] = None,
        sheet_name: Optional[str] = None,
        section_name: Optional[str] = None,
        line_number: Optional[int] = None,
    ) -> List[EntityMention]:
        """Extracts entities from raw text, enforcing privacy redaction first."""
        if not text:
            return []

        # Enforce privacy redacting credentials before extracting
        safe_text = EntityPrivacyPolicy.redact_sensitive_content(text)
        mentions: List[EntityMention] = []

        def _add_mention(raw: str, ent_type: EntityType, start: int, end: int, method: str):
            clean = raw.strip()
            if not clean or len(clean) < 2:
                return
            norm = normalize_entity_text(clean, ent_type)
            if not norm:
                return

            # Snippet of surrounding context
            ctx_start = max(0, start - 40)
            ctx_end = min(len(safe_text), end + 40)
            snippet = safe_text[ctx_start:ctx_end].replace("\n", " ").strip()

            mentions.append(
                EntityMention(
                    mention_id=f"men_{uuid.uuid4().hex[:10]}",
                    document_id=doc_id,
                    file_path=file_path,
                    original_text=clean,
                    normalized_text=norm,
                    entity_type=ent_type,
                    page_number=page_number,
                    sheet_name=sheet_name,
                    section_name=section_name,
                    line_number=line_number,
                    char_start=start,
                    char_end=end,
                    surrounding_text=snippet,
                    extraction_method=method,
                )
            )

        # 1. Contact info: Emails
        for m in REGEX_EMAIL.finditer(safe_text):
            _add_mention(m.group(), EntityType.CONTACT_INFO, m.start(), m.end(), "regex_email")

        # 2. Contact info: Phones
        for m in REGEX_PHONE.finditer(safe_text):
            _add_mention(m.group(), EntityType.CONTACT_INFO, m.start(), m.end(), "regex_phone")

        # 3. Contact info: URLs
        for m in REGEX_URL.finditer(safe_text):
            _add_mention(m.group(), EntityType.CONTACT_INFO, m.start(), m.end(), "regex_url")

        # 4. Identifiers: UUIDs
        for m in REGEX_UUID.finditer(safe_text):
            _add_mention(m.group(), EntityType.IDENTIFIER, m.start(), m.end(), "regex_uuid")

        # 5. Identifiers: Project IDs
        for m in REGEX_PROJECT_ID.finditer(safe_text):
            _add_mention(m.group(), EntityType.IDENTIFIER, m.start(), m.end(), "regex_project_id")

        # 6. Temporal: ISO dates
        for m in REGEX_ISO_DATE.finditer(safe_text):
            _add_mention(m.group(), EntityType.TEMPORAL_ENTITY, m.start(), m.end(), "regex_iso_date")

        # 7. Temporal: Quarters
        for m in REGEX_QUARTER.finditer(safe_text):
            _add_mention(m.group(), EntityType.TEMPORAL_ENTITY, m.start(), m.end(), "regex_quarter")

        # 8. Technical Entities (known libraries & frameworks)
        words = re.findall(r"\b[A-Za-z0-9_+\.#-]+\b", safe_text)
        for w in words:
            wl = w.lower()
            if wl in KNOWN_TECH_ENTITIES:
                idx = safe_text.lower().find(wl)
                if idx != -1:
                    _add_mention(w, EntityType.TECHNICAL_ENTITY, idx, idx + len(w), "known_tech_dictionary")

        # 9. Capitalized multi-word phrases for Persons, Organizations, and Projects
        # Pattern: Title case sequences (e.g., "Dr. Ramesh Babu", "Google DeepMind", "Project Apollo")
        cap_pattern = re.compile(
            r"\b(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b"
        )
        for m in cap_pattern.finditer(safe_text):
            phrase = m.group().strip()
            phrase_lower = phrase.lower()
            tokens = phrase_lower.split()

            # Skip common header phrases or non-entities
            if phrase_lower in {"table of contents", "summary report", "page number"}:
                continue

            # Check if project
            if tokens[0] in {"project", "initiative"}:
                _add_mention(phrase, EntityType.PROJECT, m.start(), m.end(), "heuristic_project")
            # Check if organization
            elif any(tok.rstrip(".") in ORG_SUFFIXES for tok in tokens) or "corp" in phrase_lower:
                _add_mention(phrase, EntityType.ORGANIZATION, m.start(), m.end(), "heuristic_org")
            # Check if person (e.g. 2 words or honorific)
            elif tokens[0].rstrip(".") in PERSON_HONORIFICS or len(tokens) == 2:
                _add_mention(phrase, EntityType.PERSON, m.start(), m.end(), "heuristic_person")

        return mentions
