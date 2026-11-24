"""
Document Metadata & Intelligence Engine — Zye Day 21.
Inspects and modifies built-in document properties (Title, Author, Subject, Keywords) and statistical metrics.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from zye_office.word.word_adapter import WordAdapter
from zye_office.word.word_errors import WordNoActiveDocumentError
from zye_office.word.word_validator import WordValidator

logger = logging.getLogger("zye.office.word.metadata")


class WordMetadataEngine:
    """Manages document properties and telemetry statistics."""

    def __init__(
        self,
        adapter: Optional[WordAdapter] = None,
        validator: Optional[WordValidator] = None,
    ) -> None:
        self.adapter = adapter or WordAdapter()
        self.validator = validator or WordValidator()

    def get_document_properties(self) -> Dict[str, Any]:
        """Reads standard BuiltInDocumentProperties."""
        def _sta_props() -> Dict[str, Any]:
            doc = self.adapter.get_active_document_raw()
            if doc is None:
                raise WordNoActiveDocumentError()

            props = {}
            for prop_name in ("Title", "Author", "Subject", "Keywords", "Comments", "Company", "Category"):
                try:
                    val = doc.BuiltInDocumentProperties(prop_name).Value
                    if val:
                        props[prop_name.lower()] = str(val)
                except Exception:
                    pass

            return {"status": "SUCCESS", "document_name": doc.Name, "properties": props}

        return self.adapter.worker.run(_sta_props)

    def set_document_properties(self, properties: Optional[Dict[str, str]] = None, **kwargs: Any) -> Dict[str, Any]:
        """Sets standard document metadata properties."""
        prop_input = dict(properties or {})
        prop_input.update(kwargs)

        def _sta_set_props() -> Dict[str, Any]:
            doc = self.adapter.get_active_document_raw()
            if doc is None:
                raise WordNoActiveDocumentError()

            updated = {}
            prop_map = {
                "title": "Title",
                "author": "Author",
                "subject": "Subject",
                "keywords": "Keywords",
                "comments": "Comments",
                "company": "Company",
                "category": "Category",
            }
            for k, v in prop_input.items():
                clean_k = k.lower().strip()
                if clean_k in prop_map:
                    try:
                        clean_v = self.validator.validate_unicode_text(str(v))
                        doc.BuiltInDocumentProperties(prop_map[clean_k]).Value = clean_v
                        updated[clean_k] = clean_v
                    except Exception as exc:
                        logger.warning("Could not set property %s: %s", clean_k, exc)

            return {
                "status": "SUCCESS",
                "updated": updated,
                "updated_properties": updated,
                "message": f"Updated {len(updated)} document metadata properties.",
            }

        return self.adapter.worker.run(_sta_set_props)

    def get_document_statistics(self) -> Dict[str, Any]:
        """Calculates exact statistical counts for words, pages, characters, paragraphs, and tables."""
        def _sta_stats() -> Dict[str, Any]:
            doc = self.adapter.get_active_document_raw()
            if doc is None:
                raise WordNoActiveDocumentError()

            wdWords = 0
            wdPages = 2
            wdChars = 3
            wdParas = 4

            words = int(doc.ComputeStatistics(wdWords)) if hasattr(doc, "ComputeStatistics") else 0
            pages = int(doc.ComputeStatistics(wdPages)) if hasattr(doc, "ComputeStatistics") else 1
            chars = int(doc.ComputeStatistics(wdChars)) if hasattr(doc, "ComputeStatistics") else 0
            paras = int(doc.ComputeStatistics(wdParas)) if hasattr(doc, "ComputeStatistics") else 0
            tables = doc.Tables.Count if hasattr(doc, "Tables") else 0
            sections = doc.Sections.Count if hasattr(doc, "Sections") else 1

            return {
                "status": "SUCCESS",
                "document_name": doc.Name,
                "words": words,
                "pages": pages,
                "characters": chars,
                "paragraphs": paras,
                "tables": tables,
                "sections": sections,
                "saved": getattr(doc, "Saved", True),
            }

        return self.adapter.worker.run(_sta_stats)
