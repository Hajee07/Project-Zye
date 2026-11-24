"""
Zye AI — Source Code Backup & Integrity Engine (Day 17).
Creates atomic, cryptographically verified pre-save source backups,
manages metadata catalogs, and validates backup integrity using SHA-256.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

MAX_BACKUP_FILE_SIZE_BYTES = 1024 * 1024  # 1 MB threshold


def calculate_sha256(file_path: Path) -> str:
    """Compute hex SHA-256 digest of a file in 64 KB chunks."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


class ZyeBackupManager:
    """Manages transactional file backups with SHA-256 integrity verification."""

    def __init__(self, project_root: Optional[Path] = None, backup_dir: str = "backups") -> None:
        if project_root is None:
            origin = Path(__file__).resolve().parent
            curr = origin
            root = origin
            for _ in range(5):
                if (curr / "zye_config.toml").is_file():
                    root = curr
                    break
                curr = curr.parent
            self.project_root = root
        else:
            self.project_root = project_root

        self.backup_dir = self.project_root / backup_dir
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_target(self, filename: str) -> Path:
        raw = Path(filename)
        if raw.is_absolute():
            return raw.resolve()
        return (self.project_root / raw).resolve()

    def create_backup(self, filename: str, reason: str = "") -> dict[str, Any]:
        """Create an atomic, timestamped backup verified via SHA-256."""
        target_path = self._resolve_target(filename)
        if not target_path.is_file():
            return {
                "status": "ERROR",
                "code": "FILE_NOT_FOUND",
                "message": f"Target file does not exist: {filename}",
            }

        try:
            target_path.relative_to(self.project_root.resolve())
        except ValueError:
            return {
                "status": "ERROR",
                "code": "PATH_OUTSIDE_PROJECT",
                "message": f"Path escapes project root: {filename}",
            }

        file_size = target_path.stat().st_size
        if file_size > MAX_BACKUP_FILE_SIZE_BYTES:
            return {
                "status": "ERROR",
                "code": "FILE_TOO_LARGE",
                "message": f"File size ({file_size} bytes) exceeds limit ({MAX_BACKUP_FILE_SIZE_BYTES} bytes).",
            }

        backup_id = uuid.uuid4().hex[:12]
        now_utc = datetime.now(timezone.utc)
        timestamp_str = now_utc.strftime("%Y%m%dT%H%M%SZ")
        safe_stem = target_path.stem.replace(".", "_")

        backup_filename = f"{safe_stem}__{timestamp_str}__{backup_id}.py.bak"
        final_backup_path = self.backup_dir / backup_filename
        tmp_backup_path = self.backup_dir / f".tmp_{backup_filename}"
        meta_path = self.backup_dir / f"{safe_stem}__{timestamp_str}__{backup_id}.meta.json"

        try:
            original_sha256 = calculate_sha256(target_path)

            # Atomic copy using temp file and fsync
            with open(target_path, "rb") as src, open(tmp_backup_path, "wb") as dst:
                shutil.copyfileobj(src, dst, length=65536)
                dst.flush()
                os.fsync(dst.fileno())

            os.replace(tmp_backup_path, final_backup_path)

            backup_sha256 = calculate_sha256(final_backup_path)
            if backup_sha256 != original_sha256:
                if final_backup_path.exists():
                    final_backup_path.unlink()
                return {
                    "status": "ERROR",
                    "code": "INTEGRITY_FAILED",
                    "message": "SHA-256 mismatch after copy.",
                }

            rel_original = str(target_path.relative_to(self.project_root.resolve())).replace("\\", "/")
            metadata = {
                "backup_id": backup_id,
                "original_file": rel_original,
                "backup_file": backup_filename,
                "created_at": now_utc.isoformat(),
                "sha256": backup_sha256,
                "file_size": file_size,
                "reason": reason.strip(),
                "integrity_status": "VERIFIED",
            }

            with open(meta_path, "w", encoding="utf-8") as mf:
                json.dump(metadata, mf, indent=2)

            return {
                "status": "SUCCESS",
                "backup_id": backup_id,
                "original_file": rel_original,
                "backup_file": backup_filename,
                "sha256": backup_sha256,
                "file_size": file_size,
                "created_at": now_utc.isoformat(),
                "reason": reason.strip(),
                "integrity_status": "VERIFIED",
            }

        except Exception as exc:
            if tmp_backup_path.exists():
                try:
                    tmp_backup_path.unlink()
                except OSError:
                    pass
            return {
                "status": "ERROR",
                "code": "BACKUP_EXCEPTION",
                "message": str(exc),
            }

    def list_backups(self, filename: str = "") -> list[dict[str, Any]]:
        """List and verify existing backups, optionally filtered by filename."""
        if not self.backup_dir.is_dir():
            return []

        norm_filter = Path(filename).name.lower() if filename and filename != "*" else None
        backups: list[dict[str, Any]] = []

        for meta_file in sorted(self.backup_dir.glob("*.meta.json")):
            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    meta = json.load(f)

                orig_file = meta.get("original_file", "")
                if norm_filter and Path(orig_file).name.lower() != norm_filter and orig_file.lower() != filename.lower():
                    continue

                b_file = meta.get("backup_file", "")
                b_path = self.backup_dir / b_file
                if b_path.is_file():
                    curr_hash = calculate_sha256(b_path)
                    meta["integrity_status"] = "VERIFIED" if curr_hash == meta.get("sha256") else "CORRUPTED"
                else:
                    meta["integrity_status"] = "FILE_MISSING"

                backups.append(meta)
            except Exception:
                continue

        backups.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return backups

    def verify_backup_integrity(self, backup_id: str) -> dict[str, Any]:
        """Verify the cryptographic integrity of a specific backup by ID."""
        matches = list(self.backup_dir.glob(f"*__{backup_id}.meta.json"))
        if not matches:
            return {"status": "ERROR", "code": "BACKUP_NOT_FOUND", "backup_id": backup_id}

        try:
            with open(matches[0], "r", encoding="utf-8") as f:
                meta = json.load(f)

            b_path = self.backup_dir / meta.get("backup_file", "")
            if not b_path.is_file():
                return {"status": "ERROR", "code": "BACKUP_FILE_MISSING", "backup_id": backup_id}

            curr_hash = calculate_sha256(b_path)
            expected_hash = meta.get("sha256", "")
            matches_expected = curr_hash == expected_hash

            return {
                "status": "SUCCESS" if matches_expected else "CORRUPTED",
                "backup_id": backup_id,
                "expected_sha256": expected_hash,
                "current_sha256": curr_hash,
                "verified": matches_expected,
            }
        except Exception as exc:
            return {"status": "ERROR", "code": "VERIFICATION_ERROR", "message": str(exc)}

    def get_latest_backup(self, filename: str) -> Optional[dict[str, Any]]:
        """Get the most recent verified backup for a specific file."""
        all_backups = self.list_backups(filename=filename)
        valid = [b for b in all_backups if b.get("integrity_status") == "VERIFIED"]
        return valid[0] if valid else None
