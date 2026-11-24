"""
Zye AI — Source Code Patching & Safety Engine (Day 17).
Provides safe code diff previews, single-occurrence replacement, AST/compile checks,
pre-patch backup creation, atomic fsync writes, and automatic rollback on verification failure.
"""

from __future__ import annotations

import difflib
import hashlib
import os
import uuid
from pathlib import Path
from typing import Any, Optional

from zye_repair.backup_manager import ZyeBackupManager, calculate_sha256
from zye_repair.syntax_validator import validate_python_ast, validate_python_compile

CRITICAL_PROTECTED_FILES: frozenset[str] = frozenset({
    "zye_guard.py",
    "self_repair_mcp.py",
    "doctor.py",
    ".env",
    ".env.production",
    ".env.local",
    "requirements-lock.txt",
})


class ZyePatchManager:
    """Manages transactional source code patching and safety gates."""

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

    def _resolve_file(self, filename: str) -> Path:
        raw = Path(filename)
        if raw.is_absolute():
            return raw.resolve()
        return (self.project_root / raw).resolve()

    def is_protected(self, file_path: Path) -> bool:
        """Check if file is protected from automated patching."""
        return file_path.name.lower() in CRITICAL_PROTECTED_FILES

    def preview_patch(
        self,
        filename: str,
        old_snippet: str,
        new_snippet: str,
        reason: str = "",
    ) -> dict[str, Any]:
        """Generate a unified diff and validate proposed patch without altering disk files."""
        if not old_snippet:
            return {"status": "ERROR", "code": "EMPTY_OLD_SNIPPET", "message": "old_code_snippet cannot be empty."}

        target_path = self._resolve_file(filename)
        if not target_path.is_file():
            return {"status": "ERROR", "code": "FILE_NOT_FOUND", "message": f"Target file not found: {filename}"}

        try:
            target_path.relative_to(self.project_root.resolve())
        except ValueError:
            return {"status": "ERROR", "code": "PATH_OUTSIDE_PROJECT", "message": "File is outside project root."}

        if self.is_protected(target_path):
            return {
                "status": "ERROR",
                "code": "PROTECTED_FILE",
                "message": f"File '{target_path.name}' is critical framework code and cannot be auto-patched.",
            }

        try:
            original_content = target_path.read_text(encoding="utf-8", errors="replace")
            count = original_content.count(old_snippet)
            if count == 0:
                return {"status": "ERROR", "code": "OLD_SNIPPET_NOT_FOUND", "message": "Target snippet not found in source."}
            if count > 1:
                return {
                    "status": "ERROR",
                    "code": "AMBIGUOUS_REPLACEMENT",
                    "message": f"Target snippet appears {count} times. Replacement must be unique.",
                }

            candidate_content = original_content.replace(old_snippet, new_snippet, 1)

            ast_ok, ast_diag = validate_python_ast(candidate_content, filename=target_path.name)
            if not ast_ok:
                return {
                    "status": "ERROR",
                    "code": "AST_VALIDATION_FAILED",
                    "message": f"AST syntax validation failed: {ast_diag.get('message')}",
                    "diagnostics": ast_diag,
                }

            comp_ok, comp_err = validate_python_compile(candidate_content, filename=target_path.name)
            if not comp_ok:
                return {
                    "status": "ERROR",
                    "code": "COMPILE_VALIDATION_FAILED",
                    "message": f"Bytecode compilation failed: {comp_err}",
                }

            orig_lines = original_content.splitlines(keepends=True)
            cand_lines = candidate_content.splitlines(keepends=True)
            diff = "".join(
                difflib.unified_diff(
                    orig_lines,
                    cand_lines,
                    fromfile=f"a/{target_path.name}",
                    tofile=f"b/{target_path.name}",
                    lineterm="\n",
                )
            )

            patch_id = uuid.uuid4().hex[:12]
            orig_hash = calculate_sha256(target_path)
            prop_hash = hashlib.sha256(candidate_content.encode("utf-8")).hexdigest()

            return {
                "status": "SUCCESS",
                "patch_id": patch_id,
                "filename": str(target_path.relative_to(self.project_root.resolve())).replace("\\", "/"),
                "original_sha256": orig_hash,
                "proposed_sha256": prop_hash,
                "diff": diff,
                "ast_validation": "PASS",
                "compile_validation": "PASS",
                "requires_approval": True,
                "reason": reason.strip(),
            }

        except Exception as exc:
            return {"status": "ERROR", "code": "PREVIEW_EXCEPTION", "message": str(exc)}

    def apply_patch(
        self,
        filename: str,
        old_snippet: str,
        new_snippet: str,
        patch_id: str,
        reason: str = "",
    ) -> dict[str, Any]:
        """Apply approved patch atomically with pre-save backup and auto-rollback."""
        target_path = self._resolve_file(filename)
        if not target_path.is_file():
            return {"status": "ERROR", "code": "FILE_NOT_FOUND", "message": f"Target file not found: {filename}"}

        if self.is_protected(target_path):
            return {"status": "ERROR", "code": "PROTECTED_FILE", "message": f"File '{target_path.name}' is protected."}

        try:
            original_content = target_path.read_text(encoding="utf-8", errors="replace")
            count = original_content.count(old_snippet)
            if count != 1:
                return {
                    "status": "ERROR",
                    "code": "MATCH_COUNT_ERROR",
                    "message": f"Expected 1 match for old snippet, found {count}.",
                }

            candidate_content = original_content.replace(old_snippet, new_snippet, 1)

            # Pre-validation
            ast_ok, ast_diag = validate_python_ast(candidate_content, filename=target_path.name)
            if not ast_ok:
                return {"status": "ERROR", "code": "AST_VALIDATION_FAILED", "message": str(ast_diag)}

            comp_ok, comp_err = validate_python_compile(candidate_content, filename=target_path.name)
            if not comp_ok:
                return {"status": "ERROR", "code": "COMPILE_VALIDATION_FAILED", "message": str(comp_err)}

            # Create pre-save backup
            backup_res = self.backup_mgr.create_backup(
                filename=str(target_path),
                reason=f"Pre-patch backup for patch {patch_id}: {reason}",
            )
            if backup_res.get("status") != "SUCCESS":
                return {
                    "status": "ERROR",
                    "code": "BACKUP_FAILED",
                    "message": "Pre-save backup creation failed; patch aborted.",
                    "details": backup_res,
                }

            backup_id = backup_res["backup_id"]
            backup_file = self.backup_mgr.backup_dir / backup_res["backup_file"]
            orig_hash = backup_res["sha256"]

            # Atomic file replacement
            tmp_patch = target_path.parent / f".tmp_patch_{uuid.uuid4().hex[:8]}.py"
            try:
                with open(tmp_patch, "wb") as f:
                    f.write(candidate_content.encode("utf-8"))
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp_patch, target_path)
            except Exception as write_err:
                if tmp_patch.exists():
                    tmp_patch.unlink()
                return {"status": "ERROR", "code": "ATOMIC_WRITE_FAILED", "message": str(write_err)}

            # Post-patch verification
            post_content = target_path.read_text(encoding="utf-8", errors="replace")
            post_ast_ok, _ = validate_python_ast(post_content, filename=target_path.name)
            post_comp_ok, _ = validate_python_compile(post_content, filename=target_path.name)

            if not post_ast_ok or not post_comp_ok:
                # Immediate rollback to backup
                try:
                    with open(backup_file, "rb") as bf, open(tmp_patch, "wb") as dst:
                        dst.write(bf.read())
                        dst.flush()
                        os.fsync(dst.fileno())
                    os.replace(tmp_patch, target_path)
                    rollback_msg = "ROLLED_BACK_TO_BACKUP"
                except Exception as rb_exc:
                    rollback_msg = f"CRITICAL_ROLLBACK_FAILURE: {rb_exc}"

                return {
                    "status": "ERROR",
                    "code": "POST_PATCH_VERIFICATION_FAILED",
                    "message": f"Verification failed after patch. Rollback status: {rollback_msg}",
                    "backup_id": backup_id,
                }

            patched_hash = calculate_sha256(target_path)
            return {
                "status": "SUCCESS",
                "patch_id": patch_id,
                "backup_id": backup_id,
                "filename": str(target_path.relative_to(self.project_root.resolve())).replace("\\", "/"),
                "original_sha256": orig_hash,
                "patched_sha256": patched_hash,
                "ast_validation": "PASS",
                "compile_validation": "PASS",
            }

        except Exception as exc:
            return {"status": "ERROR", "code": "APPLY_EXCEPTION", "message": str(exc)}

    def get_affected_functions(self, source_code: str, old_snippet: str) -> list[str]:
        """Identify which top-level or method functions contain the targeted code snippet."""
        import ast
        affected: list[str] = []
        try:
            tree = ast.parse(source_code)
            lines = source_code.splitlines()

            # Find line range of old_snippet
            start_line = -1
            end_line = -1
            snip_lines = old_snippet.strip().splitlines()
            if snip_lines:
                first = snip_lines[0].strip()
                for idx, ln in enumerate(lines, start=1):
                    if first in ln:
                        start_line = idx
                        end_line = idx + len(snip_lines) - 1
                        break

            if start_line != -1:
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        f_start = getattr(node, "lineno", 0)
                        f_end = getattr(node, "end_lineno", f_start)
                        if f_start <= start_line <= f_end or f_start <= end_line <= f_end:
                            affected.append(node.name)
        except Exception:
            pass

        return affected
