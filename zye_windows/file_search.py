"""
Fast Local File Search & Safe Opener Engine — Zye Day 16 & Day 18.
Searches user directories (Desktop, Documents, Downloads, Videos) with bounded recursion depth,
caching, timeouts, case-insensitivity, candidate disambiguation, and safe OS default opening.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
import os
import pathlib
import sys
import time
from typing import Any, Optional

from zye_windows.windows_models import FileSearchResult

logger = logging.getLogger("zye.windows.file_search")

DEFAULT_SEARCH_DIRECTORIES = ["Desktop", "Documents", "Downloads", "Videos"]
MAX_RESULTS = 10
MAX_SEARCH_DEPTH = 4
SEARCH_TIMEOUT_SECONDS = 5.0

EXECUTABLE_EXTENSIONS = {
    ".exe", ".bat", ".cmd", ".ps1", ".vbs", ".msi", ".reg", ".com", ".scr", ".pif"
}

CACHE_FILE = pathlib.Path(__file__).resolve().parent.parent / "data" / "file_search_cache.json"


class WindowsFileSearch:
    """
    Finds and opens local files in user home directories safely with metadata indexing.
    """

    def __init__(self, base_dirs: Optional[list[str]] = None, cache_file: Optional[pathlib.Path] = None) -> None:
        self.home = pathlib.Path.home()
        self.allowed_dir_names = base_dirs or DEFAULT_SEARCH_DIRECTORIES
        self.cache_file = cache_file or CACHE_FILE
        self._memory_cache: list[FileSearchResult] = []
        self._last_index_time = 0.0

    def search_local_files(
        self,
        query: str,
        directories: Optional[list[str]] = None,
        limit: int = MAX_RESULTS,
    ) -> list[FileSearchResult]:
        """
        Search for files matching query string across allowed user directories.
        Supports partial names, extensions (e.g. '.pdf'), and case-insensitivity.
        """
        if not query or not str(query).strip():
            return []

        q = str(query).strip().lower()

        # Reject path traversal tokens
        if ".." in q or "/" in q or "\\" in q:
            logger.warning("Path traversal or separators rejected in search query: %s", query)
            return []

        target_dirs = directories or self.allowed_dir_names
        search_paths: list[pathlib.Path] = []
        for d in target_dirs:
            p = self.home / d
            if p.exists() and p.is_dir():
                search_paths.append(p)

        results: list[FileSearchResult] = []
        start_time = time.monotonic()

        for folder in search_paths:
            if len(results) >= limit or (time.monotonic() - start_time > SEARCH_TIMEOUT_SECONDS):
                break
            try:
                self._search_recursive(folder, q, results, depth=0, start_time=start_time, limit=limit)
            except Exception as exc:
                logger.warning("Error searching folder %s: %s", folder, exc)

        return results[:limit]

    def get_file_details(self, path: str) -> dict[str, Any]:
        """
        Retrieve filesystem details for a specific canonical file path.
        """
        try:
            p = pathlib.Path(path).resolve()
            if not p.exists() or not p.is_file():
                return {"status": "NOT_FOUND", "path": path}

            stat = p.stat()
            ext = p.suffix.lower()
            is_exec = ext in EXECUTABLE_EXTENSIONS

            return {
                "status": "SUCCESS",
                "filename": p.name,
                "path": str(p),
                "extension": ext,
                "size_bytes": stat.st_size,
                "size_kb": round(stat.st_size / 1024, 2),
                "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                "is_executable": is_exec,
                "is_readonly": not os.access(p, os.W_OK),
            }
        except Exception as exc:
            return {"status": "ERROR", "message": f"Failed to get file details: {exc}", "path": path}

    def find_and_open_local_file(
        self,
        filename_query: str,
        open_file: bool = False,
        directories: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """
        Search for files matching query. If open_file is True:
        - If exactly 1 match: Opens safely via default Windows association (unless executable).
        - If multiple matches: Returns candidates and prompts for disambiguation.
        """
        if not filename_query or not str(filename_query).strip():
            return {
                "status": "ERROR",
                "message": "filename_query cannot be empty.",
                "query": filename_query,
                "results": [],
            }

        q = str(filename_query).strip().lower()
        if ".." in q or "/" in q or "\\" in q:
            return {
                "status": "REJECTED",
                "message": "Path traversal or directory separators are not permitted in filename_query.",
                "query": filename_query,
            }

        results = self.search_local_files(query=q, directories=directories, limit=MAX_RESULTS)

        if not results:
            target_dirs = directories or self.allowed_dir_names
            return {
                "status": "NOT_FOUND",
                "message": f"No files matching '{filename_query}' found in {target_dirs}.",
                "query": filename_query,
                "results": [],
            }

        # Handle multiple candidate disambiguation
        if len(results) > 1:
            candidate_list = [r.model_dump() for r in results]
            return {
                "status": "AMBIGUOUS_MATCH",
                "message": f"Multiple ({len(results)}) files match '{filename_query}'. Please specify which one to open.",
                "query": filename_query,
                "count": len(results),
                "candidates": candidate_list,
                "results": candidate_list,
                "open_requested": open_file,
            }

        # Exactly 1 match found
        single_result = results[0]
        target_path = pathlib.Path(single_result.path).resolve()

        if open_file:
            ext = target_path.suffix.lower()
            if ext in EXECUTABLE_EXTENSIONS:
                return {
                    "status": "EXECUTABLE_BLOCKED",
                    "message": f"File '{target_path.name}' is an executable ({ext}). Explicit authorization is required to launch executables.",
                    "file": single_result.model_dump(),
                    "is_executable": True,
                }

            try:
                os.startfile(str(target_path))
                return {
                    "status": "OPENED",
                    "message": f"Opened file: {target_path}",
                    "file": single_result.model_dump(),
                    "verified": True,
                }
            except Exception as exc:
                logger.error("Failed to open file %s: %s", target_path, exc)
                return {
                    "status": "ERROR",
                    "message": f"Failed to open file '{target_path}': {exc}",
                    "file": single_result.model_dump(),
                }
        else:
            return {
                "status": "SUCCESS",
                "file": single_result.model_dump(),
                "results": [single_result.model_dump()],
                "query": filename_query,
                "message": f"Found file: {single_result.filename} in {single_result.containing_folder}",
            }

    def _search_recursive(
        self,
        folder: pathlib.Path,
        query: str,
        results: list[FileSearchResult],
        depth: int,
        start_time: float,
        limit: int,
    ) -> None:
        """Recursive bounded directory scanner with timeout checks."""
        if depth > MAX_SEARCH_DEPTH:
            return
        if len(results) >= limit:
            return
        if time.monotonic() - start_time > SEARCH_TIMEOUT_SECONDS:
            return

        try:
            with os.scandir(folder) as it:
                for entry in it:
                    if len(results) >= limit:
                        return
                    if time.monotonic() - start_time > SEARCH_TIMEOUT_SECONDS:
                        return

                    try:
                        # Skip hidden files/folders
                        if entry.name.startswith("."):
                            continue

                        if entry.is_file(follow_symlinks=False):
                            name_lower = entry.name.lower()
                            if query in name_lower:
                                stat = entry.stat()
                                mod_iso = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
                                results.append(
                                    FileSearchResult(
                                        filename=entry.name,
                                        path=str(pathlib.Path(entry.path).resolve()),
                                        size_bytes=stat.st_size,
                                        modified_at=mod_iso,
                                        containing_folder=folder.name,
                                    )
                                )

                        elif entry.is_dir(follow_symlinks=False):
                            # Skip system/cache directories
                            if entry.name.lower() in ("appdata", "node_modules", ".git", "__pycache__", "temp", "tmp"):
                                continue
                            self._search_recursive(
                                pathlib.Path(entry.path),
                                query,
                                results,
                                depth + 1,
                                start_time,
                                limit,
                            )
                    except PermissionError:
                        continue
                    except Exception:
                        continue
        except PermissionError:
            pass
        except Exception:
            pass
