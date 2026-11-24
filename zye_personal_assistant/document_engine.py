"""
Document Management Engine for Zye Personal Assistant (Day 14 & Day 29).
Provides multi-format indexing (PDF, DOCX, XLSX, CSV, TXT, MD, JSON, PY),
incremental indexing with SHA-256 fingerprints, ranked content search,
and safe category-based auto-organization with rollback support.
"""

from __future__ import annotations

import csv
import hashlib
import json
import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from zye_personal_assistant.database import get_db_connection, init_assistant_database
from zye_personal_assistant.safety_gateway import SafetyGateway

logger = logging.getLogger("zye.personal_assistant.documents")

CATEGORY_FOLDERS = {
    ".pdf": "PDF_Documents",
    ".docx": "Word_Docs",
    ".doc": "Word_Docs",
    ".xlsx": "Spreadsheets",
    ".xls": "Spreadsheets",
    ".csv": "Spreadsheets",
    ".txt": "Notes_and_Text",
    ".md": "Notes_and_Text",
    ".json": "Notes_and_Text",
    ".py": "Notes_and_Text",
}

SUPPORTED_EXTENSIONS = set(CATEGORY_FOLDERS.keys())
MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25MB safety limit
MAX_SNIPPET_CHARS = 500


class DocumentEngine:
    def __init__(
        self,
        db_path: str | Path | None = None,
        safety_gateway: Optional[SafetyGateway] = None,
    ) -> None:
        self._db_path = db_path
        self._safety = safety_gateway or SafetyGateway(db_path=db_path)
        self._last_move_manifest: list[dict[str, str]] = []
        init_assistant_database(self._db_path)

    def extract_text_snippet(self, file_path: Path, max_chars: int = MAX_SNIPPET_CHARS) -> str:
        """Extract a bounded plain text snippet from a supported document."""
        if not file_path.is_file():
            return ""

        ext = file_path.suffix.lower()
        try:
            if file_path.stat().st_size > MAX_FILE_SIZE_BYTES:
                return f"[File size exceeds {MAX_FILE_SIZE_BYTES // (1024*1024)}MB limit]"

            if ext == ".pdf":
                try:
                    import pypdf
                    reader = pypdf.PdfReader(str(file_path))
                    text = ""
                    for page in reader.pages[:3]:
                        t = page.extract_text() or ""
                        text += t + " "
                        if len(text) >= max_chars:
                            break
                    return text[:max_chars].strip()
                except Exception as e:
                    logger.debug("PDF extract error for %s: %s", file_path, e)
                    return ""

            elif ext in (".docx", ".doc"):
                try:
                    import docx
                    doc = docx.Document(str(file_path))
                    text = " ".join(p.text for p in doc.paragraphs if p.text)
                    return text[:max_chars].strip()
                except Exception as e:
                    logger.debug("DOCX extract error for %s: %s", file_path, e)
                    return ""

            elif ext == ".csv":
                try:
                    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                        lines = [f.readline() for _ in range(6)]
                        return " ".join(l.strip() for l in lines)[:max_chars].strip()
                except Exception as e:
                    logger.debug("CSV extract error for %s: %s", file_path, e)
                    return ""

            elif ext in (".xlsx", ".xls"):
                try:
                    import openpyxl
                    wb = openpyxl.load_workbook(str(file_path), read_only=True)
                    sheet = wb.active
                    text = ""
                    if sheet:
                        for row in sheet.iter_rows(max_row=8, values_only=True):
                            text += " ".join(str(c) for c in row if c is not None) + " "
                            if len(text) >= max_chars:
                                break
                    return text[:max_chars].strip()
                except Exception as e:
                    logger.debug("Excel extract error for %s: %s", file_path, e)
                    return ""

            elif ext in (".txt", ".md", ".json", ".py"):
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    return f.read(max_chars).strip()

            return ""
        except Exception as exc:
            logger.warning("Snippet extraction failed for %s: %s", file_path, exc)
            return ""

    def calculate_fingerprint(self, file_path: Path) -> str:
        """Compute SHA-256 hash of the initial file block for incremental change detection."""
        try:
            h = hashlib.sha256()
            with open(file_path, "rb") as f:
                block = f.read(65536)
                h.update(block)
            return h.hexdigest()[:24]
        except Exception:
            return ""

    def index_folder(self, directory_path: str) -> dict[str, Any]:
        """
        Scan and index all supported documents in the given directory.
        Implements incremental indexing: skips re-reading unchanged files.
        """
        folder = Path(directory_path).resolve()
        if not folder.is_dir():
            return {
                "status": "DOCUMENT_FOLDER_NOT_FOUND",
                "message": f"Directory does not exist or is not a folder: {directory_path}",
                "indexed_files": 0,
            }

        now_str = datetime.now(timezone.utc).isoformat()
        conn = get_db_connection(self._db_path)
        indexed_count = 0
        unchanged_count = 0
        skipped_count = 0

        try:
            with conn:
                for root, _, files in os.walk(folder):
                    for fname in files:
                        p = Path(root) / fname
                        ext = p.suffix.lower()
                        if ext not in SUPPORTED_EXTENSIONS:
                            skipped_count += 1
                            continue

                        category = CATEGORY_FOLDERS.get(ext, "Other")
                        try:
                            stat = p.stat()
                            fsize = stat.st_size
                            mtime = datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()

                            # Incremental check: check if already indexed with identical mtime and size
                            cached = conn.execute(
                                "SELECT modified_at, file_size FROM doc_index WHERE path = ?;",
                                (str(p),)
                            ).fetchone()
                            if cached and cached["modified_at"] == mtime and cached["file_size"] == fsize:
                                unchanged_count += 1
                                continue

                            snippet = self.extract_text_snippet(p)
                            chash = self.calculate_fingerprint(p)

                            conn.execute(
                                """
                                INSERT OR REPLACE INTO doc_index
                                (path, filename, category, modified_at, snippet, file_size, content_hash, indexed_at, processing_status)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'INDEXED');
                                """,
                                (str(p), fname, category, mtime, snippet, fsize, chash, now_str),
                            )
                            indexed_count += 1
                        except Exception as e:
                            logger.warning("Error indexing file %s: %s", p, e)
                            skipped_count += 1

            logger.info("Indexed %d new/updated, %d unchanged, %d skipped in %s", indexed_count, unchanged_count, skipped_count, folder)
            return {
                "status": "SUCCESS",
                "directory": str(folder),
                "indexed_files": indexed_count,
                "indexed_count": indexed_count,
                "unchanged_files": unchanged_count,
                "skipped_unchanged": unchanged_count,
                "skipped_files": skipped_count,
                "total_documents": indexed_count + unchanged_count,
            }
        finally:
            conn.close()

    def search_documents(self, query: str, limit: int = 15) -> list[dict[str, Any]]:
        """
        Search indexed documents by filename, snippet, or category.
        Ranks exact and starts-with filename matches higher than snippet matches.
        """
        clean_q = query.strip()
        if not clean_q:
            return []

        conn = get_db_connection(self._db_path)
        try:
            like_q = f"%{clean_q}%"
            rows = conn.execute(
                """
                SELECT path, filename, category, modified_at, snippet, file_size
                FROM doc_index
                WHERE filename LIKE ? OR snippet LIKE ? OR category LIKE ?
                ORDER BY 
                    CASE 
                        WHEN lower(filename) = lower(?) THEN 1
                        WHEN lower(filename) LIKE lower(?) || '%' THEN 2
                        WHEN lower(filename) LIKE '%' || lower(?) || '%' THEN 3
                        ELSE 4 
                    END,
                    modified_at DESC
                LIMIT ?;
                """,
                (like_q, like_q, like_q, clean_q, clean_q, clean_q, limit),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def auto_organize(
        self,
        directory_path: str,
        dry_run: bool = True,
        confirmed: bool = False,
    ) -> dict[str, Any]:
        """
        Organize documents into categorized subfolders with collision detection,
        Negative Brain audit, and rollback manifest.
        Requires dry_run=False and confirmed=True to execute moves.
        """
        folder = Path(directory_path).resolve()
        if not folder.is_dir():
            return {"status": "DOCUMENT_FOLDER_NOT_FOUND", "message": f"Target directory not found: {directory_path}"}

        planned_moves: list[dict[str, str]] = []
        collisions: list[str] = []

        for item in folder.iterdir():
            if item.is_file():
                ext = item.suffix.lower()
                if ext in CATEGORY_FOLDERS:
                    subfolder_name = CATEGORY_FOLDERS[ext]
                    dest_dir = folder / subfolder_name
                    dest_file = dest_dir / item.name

                    if dest_file.exists():
                        # Collision avoidance: propose non-colliding alternative name
                        stem = item.stem
                        counter = 1
                        alt_dest = dest_dir / f"{stem}_{counter}{ext}"
                        while alt_dest.exists():
                            counter += 1
                            alt_dest = dest_dir / f"{stem}_{counter}{ext}"
                        collisions.append(f"{item.name} exists in {subfolder_name} (will rename to {alt_dest.name})")
                        dest_file = alt_dest

                    planned_moves.append({
                        "src": str(item),
                        "dest": str(dest_file),
                        "category": subfolder_name,
                        "filename": item.name,
                    })

        # Negative Pre-Mortem Brain Audit
        audit = self._safety.authorize_personal_assistant_action_sync(
            action_type="DOC_ORGANIZE",
            task_description=f"Auto-organize {len(planned_moves)} documents in {folder}",
            proposed_steps=[
                f"Scan directory {folder}",
                f"Identify {len(planned_moves)} target file(s)",
                f"Verify {len(collisions)} collision(s)",
                f"Move files into subfolders ({', '.join(set(CATEGORY_FOLDERS.values()))})",
            ],
            target_resources=[str(folder)],
        )

        # Enforce two-stage approval: if dry_run or not confirmed, return preview
        if dry_run or not confirmed:
            return {
                "status": "DRY_RUN_COMPLETED",
                "dry_run": True,
                "planned_moves_count": len(planned_moves),
                "planned_moves": len(planned_moves),
                "planned_moves_list": planned_moves,
                "collisions_detected": collisions,
                "safety_audit": audit,
                "message": "Preview generated safely without moving files. Pass dry_run=False and confirmed=True to execute file organization.",
            }

        # Execute moves safely
        executed_moves: list[dict[str, str]] = []
        for move in planned_moves:
            src_path = Path(move["src"])
            dest_path = Path(move["dest"])
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.move(str(src_path), str(dest_path))
                executed_moves.append(move)
            except Exception as e:
                logger.error("Failed to move %s -> %s: %s", src_path, dest_path, e)

        self._last_move_manifest = executed_moves
        manifest_path = folder / ".zye_organize_manifest.json"
        try:
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump({"executed_moves": executed_moves}, f, indent=2)
        except Exception:
            pass

        return {
            "status": "ORGANIZATION_COMPLETED",
            "files_moved": len(executed_moves),
            "executed_moves_count": len(executed_moves),
            "executed_moves": executed_moves,
            "manifest_path": str(manifest_path),
            "collisions_avoided": len(collisions),
            "rollback_available": len(executed_moves) > 0,
            "safety_audit": audit,
            "message": f"Successfully organized {len(executed_moves)} documents into categorized subfolders.",
        }

    def rollback_organization(self, manifest_path: str = "") -> dict[str, Any]:
        """Roll back file organization moves using manifest file or in-memory history."""
        moves: list[dict[str, str]] = []
        if manifest_path and Path(manifest_path).is_file():
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    moves = data.get("executed_moves", [])
            except Exception as e:
                logger.error("Failed to read manifest %s: %s", manifest_path, e)
        if not moves:
            moves = self._last_move_manifest

        if not moves:
            return {"status": "NO_OP", "message": "No previous organization moves available to roll back."}

        rolled_back: list[dict[str, str]] = []
        for move in moves:
            dest_file = Path(move["dest"])
            original_src = Path(move["src"])
            if dest_file.exists():
                try:
                    original_src.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(dest_file), str(original_src))
                    rolled_back.append(move)
                except Exception as e:
                    logger.error("Rollback failed for %s: %s", dest_file, e)

        self._last_move_manifest = []
        return {
            "status": "ROLLBACK_COMPLETED",
            "files_restored": len(rolled_back),
            "rolled_back_count": len(rolled_back),
            "moves": rolled_back,
        }

    def rollback_last_organization(self) -> dict[str, Any]:
        """Roll back the last auto_organize move operations."""
        return self.rollback_organization()
