"""
Zye AI — Source Code Rollback & Restoration Engine (Day 17).
Provides point-in-time recovery to verified backups, post-restoration verification,
and persistent rollback audit event logging.
"""

from __future__ import annotations

import json
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from zye_repair.backup_manager import ZyeBackupManager, calculate_sha256
from zye_repair.syntax_validator import validate_python_ast


class ZyeRollbackManager:
    """Restores source files from verified backups with post-rollback integrity checks."""

    def __init__(
        self,
        project_root: Optional[Path] = None,
        backup_manager: Optional[ZyeBackupManager] = None,
    ) -> None:
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

        self.backup_mgr = backup_manager or ZyeBackupManager(project_root=self.project_root)
        self.history_log = self.project_root / "logs" / "rollback_history.log"
        self.history_log.parent.mkdir(parents=True, exist_ok=True)

    def _resolve_file(self, filename: str) -> Path:
        raw = Path(filename)
        if raw.is_absolute():
            return raw.resolve()
        return (self.project_root / raw).resolve()

    def _record_rollback_event(self, event: dict[str, Any]) -> None:
        event["timestamp"] = datetime.now(timezone.utc).isoformat()
        try:
            with open(self.history_log, "a", encoding="utf-8") as f:
                f.write(json.dumps(event) + "\n")
        except Exception:
            pass

    def rollback_to_backup(self, filename: str, backup_id: str) -> dict[str, Any]:
        """Restore target file from a specific backup ID."""
        target_path = self._resolve_file(filename)
        if not target_path.exists():
            return {"status": "ERROR", "code": "TARGET_NOT_FOUND", "message": f"Target file does not exist: {filename}"}

        # Find backup metadata
        matches = list(self.backup_mgr.backup_dir.glob(f"*__{backup_id}.meta.json"))
        if not matches:
            return {"status": "ERROR", "code": "BACKUP_NOT_FOUND", "message": f"No backup with ID '{backup_id}'."}

        try:
            with open(matches[0], "r", encoding="utf-8") as f:
                meta = json.load(f)

            b_file = self.backup_mgr.backup_dir / meta.get("backup_file", "")
            if not b_file.is_file():
                return {"status": "ERROR", "code": "BACKUP_FILE_MISSING", "message": "Backup payload missing from disk."}

            expected_sha256 = meta.get("sha256", "")
            if calculate_sha256(b_file) != expected_sha256:
                return {"status": "ERROR", "code": "BACKUP_CORRUPTED", "message": "Backup payload SHA-256 mismatch."}

            # Create safety backup of current state before reverting
            self.backup_mgr.create_backup(str(target_path), reason=f"Safety backup before rollback to {backup_id}")

            # Restore file atomically
            tmp_rollback = target_path.parent / f".tmp_rb_{uuid.uuid4().hex[:8]}.py"
            with open(b_file, "rb") as src, open(tmp_rollback, "wb") as dst:
                shutil.copyfileobj(src, dst)
                dst.flush()
                os.fsync(dst.fileno())

            os.replace(tmp_rollback, target_path)

            # Verify restored file
            restored_sha256 = calculate_sha256(target_path)
            content = target_path.read_text(encoding="utf-8", errors="replace")
            ast_ok, ast_diag = validate_python_ast(content, filename=target_path.name)

            rel_target = str(target_path.relative_to(self.project_root.resolve())).replace("\\", "/")
            res = {
                "status": "SUCCESS",
                "filename": rel_target,
                "restored_backup_id": backup_id,
                "restored_sha256": restored_sha256,
                "ast_validation": "PASS" if ast_ok else "FAIL",
                "diagnostics": ast_diag if not ast_ok else None,
            }

            self._record_rollback_event({
                "action": "rollback_to_backup",
                "filename": rel_target,
                "backup_id": backup_id,
                "sha256": restored_sha256,
                "status": "SUCCESS",
            })

            return res

        except Exception as exc:
            return {"status": "ERROR", "code": "ROLLBACK_EXCEPTION", "message": str(exc)}

    def rollback_to_latest(self, filename: str) -> dict[str, Any]:
        """Restore target file from its most recent verified backup."""
        latest = self.backup_mgr.get_latest_backup(filename)
        if not latest:
            return {
                "status": "ERROR",
                "code": "NO_VALID_BACKUPS",
                "message": f"No verified backups available for {filename}",
            }
        return self.rollback_to_backup(filename=filename, backup_id=latest["backup_id"])

    def verify_restored_file(self, filename: str, expected_sha256: str) -> bool:
        """Verify that restored file on disk exactly matches expected SHA-256."""
        target_path = self._resolve_file(filename)
        if not target_path.is_file():
            return False
        return calculate_sha256(target_path) == expected_sha256

    def get_rollback_history(self) -> list[dict[str, Any]]:
        """Retrieve audit log of past rollback events."""
        if not self.history_log.is_file():
            return []
        events: list[dict[str, Any]] = []
        try:
            with open(self.history_log, "r", encoding="utf-8") as f:
                for line in f:
                    s = line.strip()
                    if s:
                        events.append(json.loads(s))
        except Exception:
            pass
        return events
