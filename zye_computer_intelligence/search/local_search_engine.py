"""
Local Search Engine & File System Intelligence.
Performs exact phrase, keyword, code, document, and dataset searches
across authorized directories with context-aware snippet extraction.
"""

from __future__ import annotations

import logging
import os
import re
import time
from pathlib import Path
from typing import Any

from zye_computer_intelligence.security.local_search_policy import (
    LocalSearchPolicy,
    LocalSearchSecurityError,
)
from .local_index_manager import LocalIndexManager
from .local_document_extractor import LocalDocumentExtractor

logger = logging.getLogger("zye.computer_intelligence.local_search")


class LocalSearchEngine:
    """Core local search engine for documents, codebases, datasets, and file trees."""

    def __init__(
        self,
        policy: LocalSearchPolicy | None = None,
        index_manager: LocalIndexManager | None = None,
    ) -> None:
        self.policy = policy or LocalSearchPolicy()
        self.index_manager = index_manager or LocalIndexManager(policy=self.policy)

    def search_local_sources(
        self,
        query: str,
        root_path: str | Path | None = None,
        file_types: list[str] | None = None,
        max_results: int = 10,
        exact_phrase: bool = False,
    ) -> dict[str, Any]:
        """
        Executes unified local search across documents, code, and datasets.
        Combines SQLite FTS5 index results with active file tree scanning.
        """
        start_time = time.time()
        clean_query = query.strip()
        if not clean_query:
            return {
                "status": "ERROR",
                "error_code": "EMPTY_LOCAL_QUERY",
                "message": "Local search query cannot be empty.",
                "results": [],
            }

        search_roots = [Path(root_path).resolve()] if root_path else self.policy.allowed_roots
        for r in search_roots:
            if not self.policy.is_path_authorized(r):
                return {
                    "status": "ERROR",
                    "error_code": "LOCAL_SEARCH_PERMISSION_DENIED",
                    "message": f"Search path '{r}' is not authorized by LocalSearchPolicy.",
                    "results": [],
                }

        results: list[dict[str, Any]] = []
        seen_paths: set[str] = set()

        # 1. First query high-speed SQLite FTS5 index if available
        try:
            fts_hits = self.index_manager.search_fts(clean_query, limit=max_results * 2)
            for hit in fts_hits:
                p_str = hit["file_path"]
                p = Path(p_str)
                if not p.exists():
                    continue

                # Filter by file extension if requested
                if file_types and p.suffix.lower() not in file_types:
                    continue

                if p_str not in seen_paths:
                    seen_paths.add(p_str)
                    results.append({
                        "result_id": f"loc_{len(results)+1}",
                        "source_type": "local",
                        "title": hit["file_name"],
                        "file_path": p_str,
                        "file_name": hit["file_name"],
                        "file_type": p.suffix.lower().lstrip("."),
                        "file_size": p.stat().st_size if p.exists() else 0,
                        "content_snippet": hit.get("snippet", "")[:1000],
                        "match_type": "FTS_INDEX",
                        "citation_id": f"local_{len(results)+1}",
                    })
        except Exception as e:
            logger.debug("FTS search fallback to scanning: %s", e)

        # 2. File tree scan for filename and exact phrase matches with subtree pruning
        from zye_computer_intelligence.security.local_search_policy import FORBIDDEN_DIRECTORY_NAMES

        keywords = clean_query.lower().split()
        for root in search_roots:
            if len(results) >= max_results:
                break
            if not root.is_dir():
                continue

            for dirpath, dirnames, filenames in os.walk(root):
                if len(results) >= max_results:
                    break
                # Prune forbidden directory subtrees in-place
                dirnames[:] = [d for d in dirnames if d.lower() not in FORBIDDEN_DIRECTORY_NAMES and not d.startswith(".")]

                for fn in filenames:
                    if len(results) >= max_results:
                        break
                    file_path = Path(dirpath) / fn
                    p_str = str(file_path.resolve())
                    if p_str in seen_paths:
                        continue

                    # Extension filter
                    ext = file_path.suffix.lower()
                    if file_types and ext not in file_types:
                        continue

                    # Check security policy
                    try:
                        self.policy.validate_file_access(file_path)
                    except LocalSearchSecurityError:
                        continue

                    # Check filename match
                    fn_lower = file_path.name.lower()
                    name_match = (clean_query.lower() in fn_lower) if exact_phrase else any(k in fn_lower for k in keywords)

                    if name_match:
                        seen_paths.add(p_str)
                        extracted = LocalDocumentExtractor.extract_document(file_path)
                        results.append({
                            "result_id": f"loc_{len(results)+1}",
                            "source_type": "local",
                            "title": file_path.name,
                            "file_path": p_str,
                            "file_name": file_path.name,
                            "file_type": ext.lstrip("."),
                            "file_size": file_path.stat().st_size,
                            "content_snippet": extracted.get("snippet", "")[:1000],
                            "match_type": "FILENAME_MATCH",
                            "citation_id": f"local_{len(results)+1}",
                        })
                        continue

                    # Fast content check via direct slice read (< 512KB)
                    if ext in (".py", ".md", ".txt", ".json", ".yaml", ".yml", ".toml") and file_path.stat().st_size < 512 * 1024:
                        try:
                            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                                raw_text = f.read(65536)
                            content_lower = raw_text.lower()
                            content_match = (clean_query.lower() in content_lower) if exact_phrase else all(k in content_lower for k in keywords[:3])
                            if content_match:
                                seen_paths.add(p_str)
                                idx = content_lower.find(keywords[0]) if keywords else 0
                                start_idx = max(0, idx - 100)
                                end_idx = min(len(raw_text), idx + 400)
                                snippet = raw_text[start_idx:end_idx].strip()

                                results.append({
                                    "result_id": f"loc_{len(results)+1}",
                                    "source_type": "local",
                                    "title": file_path.name,
                                    "file_path": p_str,
                                    "file_name": file_path.name,
                                    "file_type": ext.lstrip("."),
                                    "file_size": file_path.stat().st_size,
                                    "content_snippet": f"...{snippet}...",
                                    "match_type": "CONTENT_SCAN",
                                    "citation_id": f"local_{len(results)+1}",
                                })
                        except Exception:
                            continue

        duration_ms = round((time.time() - start_time) * 1000, 2)
        return {
            "status": "SUCCESS",
            "query": clean_query,
            "results_count": len(results),
            "results": results[:max_results],
            "duration_ms": duration_ms,
        }

    def search_local_documents(
        self,
        query: str,
        root_path: str | Path | None = None,
        max_results: int = 10,
    ) -> dict[str, Any]:
        """Searches specifically across document formats (.pdf, .docx, .txt, .md)."""
        doc_types = [".pdf", ".docx", ".doc", ".txt", ".md"]
        return self.search_local_sources(
            query=query, root_path=root_path, file_types=doc_types, max_results=max_results
        )

    def search_local_code(
        self,
        query: str,
        root_path: str | Path | None = None,
        max_results: int = 10,
    ) -> dict[str, Any]:
        """Searches specifically across source code files (.py, .js, .ts, .html, .sql)."""
        code_types = [".py", ".js", ".ts", ".html", ".sql", ".json", ".toml", ".yaml"]
        return self.search_local_sources(
            query=query, root_path=root_path, file_types=code_types, max_results=max_results
        )

    def search_local_datasets(
        self,
        query: str,
        root_path: str | Path | None = None,
        max_results: int = 10,
    ) -> dict[str, Any]:
        """Searches specifically across tabular dataset files (.csv, .xlsx, .xls, .duckdb)."""
        dataset_types = [".csv", ".xlsx", ".xls", ".parquet", ".duckdb"]
        return self.search_local_sources(
            query=query, root_path=root_path, file_types=dataset_types, max_results=max_results
        )
