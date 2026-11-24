"""
Advanced Document Management Engine — Zye Day 21.
Handles lifecycle, inspection, metadata aggregation, backup creation, and protection checks for Word documents.
"""

from __future__ import annotations

import logging
import os
import shutil
import time
from typing import Any, Dict, List, Optional

from zye_office.models.word_models import WordDocumentMetadata
from zye_office.word.word_adapter import WordAdapter
from zye_office.word.word_errors import (
    WordNoActiveDocumentError,
    WordDocumentReadOnlyError,
    WordDocumentProtectedError,
    WordDocumentNotFoundError,
    format_word_error,
)

logger = logging.getLogger("zye.office.word.doc_mgr")


class WordDocumentManager:
    """Manages document lifecycles, metadata inspection, duplicates, and backup copies."""

    def __init__(self, adapter: Optional[WordAdapter] = None) -> None:
        self.adapter = adapter or WordAdapter()

    def create_word_document(self) -> Dict[str, Any]:
        return self.adapter.create_document()

    def open_word_document(self, file_path: str, read_only: bool = False) -> Dict[str, Any]:
        return self.adapter.open_document(file_path, read_only=read_only)

    def save_word_document(self, path: Optional[str] = None) -> Dict[str, Any]:
        return self.adapter.save_document(path=path)

    def save_word_document_as(self, file_path: str) -> Dict[str, Any]:
        return self.adapter.save_document_as(file_path)

    def close_word_document(self, save_changes: bool = False) -> Dict[str, Any]:
        return self.adapter.close_document(save_changes=save_changes)

    create_document = create_word_document
    open_document = open_word_document
    save_document = save_word_document
    save_document_as = save_word_document_as
    close_document = close_word_document

    def get_open_word_documents(self) -> Dict[str, Any]:
        """List names and paths of all open Word documents in the instance."""
        def _sta_get_open() -> Dict[str, Any]:
            app = self.adapter.get_raw_app()
            if app is None or app.Documents.Count == 0:
                return {"status": "SUCCESS", "count": 0, "documents": []}

            docs = []
            for i in range(1, app.Documents.Count + 1):
                try:
                    d = app.Documents(i)
                    docs.append({
                        "index": i,
                        "name": d.Name,
                        "path": getattr(d, "FullName", ""),
                        "saved": getattr(d, "Saved", True),
                        "read_only": getattr(d, "ReadOnly", False),
                    })
                except Exception:
                    pass
            return {"status": "SUCCESS", "count": len(docs), "documents": docs}

        return self.adapter.worker.run(_sta_get_open)

    def get_document_metadata(self, max_preview_chars: int = 1500) -> Dict[str, Any]:
        """Inspect active document state and extract comprehensive metadata."""
        def _sta_metadata() -> Dict[str, Any]:
            doc = self.adapter.get_active_document_raw()
            if doc is None:
                return WordDocumentMetadata(
                    status="ERROR",
                    document_name="",
                    message="No active Word document open.",
                ).model_dump()

            name = getattr(doc, "Name", "")
            full_path = getattr(doc, "FullName", None)
            saved = getattr(doc, "Saved", True)
            read_only = getattr(doc, "ReadOnly", False)
            protection = getattr(doc, "ProtectionType", -1) != -1

            # Word statistics constants
            wdStatisticWords = 0
            wdStatisticLines = 1
            wdStatisticPages = 2
            wdStatisticCharacters = 3
            wdStatisticParagraphs = 4

            words = int(doc.ComputeStatistics(wdStatisticWords)) if hasattr(doc, "ComputeStatistics") else 0
            pages = int(doc.ComputeStatistics(wdStatisticPages)) if hasattr(doc, "ComputeStatistics") else 1
            chars = int(doc.ComputeStatistics(wdStatisticCharacters)) if hasattr(doc, "ComputeStatistics") else 0
            paras = int(doc.ComputeStatistics(wdStatisticParagraphs)) if hasattr(doc, "ComputeStatistics") else 0
            tables_count = doc.Tables.Count if hasattr(doc, "Tables") else 0
            sections_count = doc.Sections.Count if hasattr(doc, "Sections") else 1
            revisions_count = doc.Revisions.Count if hasattr(doc, "Revisions") else 0
            comments_count = doc.Comments.Count if hasattr(doc, "Comments") else 0
            track_changes = getattr(doc, "TrackRevisions", False)

            preview = ""
            try:
                raw_text = doc.Content.Text
                if raw_text:
                    preview = raw_text[:max_preview_chars].strip()
            except Exception:
                pass

            meta = WordDocumentMetadata(
                status="SUCCESS",
                document_name=name,
                path=full_path,
                is_saved=saved,
                is_read_only=read_only,
                is_protected=protection,
                word_count=words,
                page_count=pages,
                character_count=chars,
                paragraph_count=paras,
                table_count=tables_count,
                section_count=sections_count,
                revision_count=revisions_count,
                comment_count=comments_count,
                track_changes_active=track_changes,
                preview_text=preview,
            )
            return meta.model_dump()

        return self.adapter.worker.run(_sta_metadata)

    def create_document_backup(
        self,
        backup_dir: Optional[str] = None,
        source_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Creates an immediate snapshot backup file of the active document on disk."""
        if source_path:
            if not os.path.exists(source_path):
                raise WordDocumentNotFoundError(f"Source file does not exist on disk: {source_path}")
            orig_path = source_path
        else:
            meta = self.get_document_metadata()
            if meta.get("status") != "SUCCESS" or not meta.get("path"):
                return {
                    "status": "UNAVAILABLE",
                    "message": "Document must be saved to disk before a file backup can be generated.",
                }

            orig_path = meta["path"]
            if not os.path.exists(orig_path):
                return {"status": "ERROR", "message": f"Source file does not exist on disk: {orig_path}"}

        target_dir = backup_dir or os.path.join(os.getcwd(), "backups", "word")
        os.makedirs(target_dir, exist_ok=True)
        fname = os.path.basename(orig_path)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(target_dir, f"{timestamp}_{fname}")

        try:
            shutil.copy2(orig_path, backup_file)
            return {
                "status": "SUCCESS",
                "source_path": orig_path,
                "backup_path": backup_file,
                "file_size": os.path.getsize(backup_file),
                "timestamp": timestamp,
            }
        except Exception as exc:
            return {"status": "ERROR", "message": f"Backup copy failed: {exc}"}
