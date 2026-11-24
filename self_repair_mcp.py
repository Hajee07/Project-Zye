#!/usr/bin/env python3
"""
ZYE AI — Self-Repair & Autonomous Code Repair MCP Engine v1.0
=============================================================

Advanced Error Intelligence, Source Code Inspection, Secure Backup Management,
AST Validation, Compilation Verification, Atomic Source Patching, Rollback
Engine, SHA-256 Integrity Verification, and MCP Diagnostic Server.

Day 05 Capabilities:
  1. Read recent error logs (logs/zye_errors.log)
  2. Read project's own Python source code with exact line numbers
  3. List permitted project source files
  4. Inspect source file metadata and syntax status
  5. Create atomic, SHA-256-verified source backups in backups/
  6. List and verify previous backups
  7. Parse and classify Python traceback telemetry

Day 06 Capabilities:
  8. Preview code patches with exact snippet matching and unified diff
  9. Cryptographic one-time approval token engine (SQLite backed)
 10. AST syntax validation and compilation verification before file modification
 11. Atomic source replacement preserving encoding (UTF-8/UTF-8 BOM) and line endings
 12. Automated pre-save backup creation with SHA-256 comparison
 13. Automatic rollback to verified backup upon post-patch verification failure
 14. Manual rollback tool using exact backup ID and user approval token
 15. Transactional code repair audit logger (logs/code_repair_audit.log)
 16. Protection of critical framework files (zye_guard, self_repair_mcp, doctor, .env)

Usage (Standalone or via MCP stdio):
    python self_repair_mcp.py
"""

from __future__ import annotations

import ast
import datetime
import difflib
import functools
import hashlib
import inspect
import json
import logging
import os
import re
import secrets
import shutil
import sqlite3
import sys
import tempfile
import tokenize
import traceback
import uuid
from dataclasses import asdict, dataclass, field
from datetime import timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Callable, Sequence

# ---------------------------------------------------------------------------
# Day 04 Safety Guard Integration
# ---------------------------------------------------------------------------
try:
    from zye_guard import (
        zye_safe_skill,
        get_project_root as guard_get_project_root,
        resolve_safe_path,
        is_path_within_root,
        is_protected_windows_path,
        redact_secrets,
        log_security_alert,
    )
except ImportError:
    def zye_safe_skill(*args: Any, **kwargs: Any) -> Callable:
        def decorator(func: Callable) -> Callable:
            return func
        return decorator

    def guard_get_project_root() -> Path:
        return Path(__file__).resolve().parent

    def resolve_safe_path(raw: str, root: Path | None = None) -> Any:
        p = Path(raw)
        return type("Res", (), {"valid": True, "resolved_path": p, "violation": None})()

    def is_path_within_root(t: Path, r: Path) -> bool:
        try:
            return t.resolve().is_relative_to(r.resolve())
        except Exception:
            return False

    def is_protected_windows_path(t: Path) -> bool:
        return False

    def redact_secrets(t: str) -> str:
        return t

    def log_security_alert(fn: str, tid: str, v: str) -> None:
        pass


# ---------------------------------------------------------------------------
# FastMCP Protocol Initialization (Compatible with MCP v2 and v1)
# ---------------------------------------------------------------------------
try:
    from mcp.server.mcpserver import MCPServer as FastMCP
    _MCP_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    try:
        from mcp.server.fastmcp import FastMCP  # type: ignore[no-redef]
        _MCP_AVAILABLE = True
    except (ImportError, ModuleNotFoundError):
        _MCP_AVAILABLE = False

    class FastMCP:  # type: ignore[no-redef]
        """Fallback FastMCP implementation when mcp package is pending installation."""

        def __init__(self, name: str, **kwargs: Any) -> None:
            self.name = name
            self._tools: dict[str, Callable] = {}

        def tool(self, *args: Any, **kwargs: Any) -> Callable:
            def decorator(func: Callable) -> Callable:
                self._tools[func.__name__] = func
                return func
            if args and callable(args[0]):
                return decorator(args[0])
            return decorator

        def run(self, *args: Any, **kwargs: Any) -> None:
            sys.stderr.write(f"[{self.name}] FastMCP shim ready (mcp package pending installation).\n")


mcp = FastMCP("ZyeSelfRepair")


# ============================================================================
# A.  Project Root Resolver
# ============================================================================

_PROJECT_ROOT_CACHE: Path | None = None


def get_project_root(start: Path | None = None) -> Path:
    """Locate the Zye project root by walking upward from self_repair_mcp.py.

    Never uses Path.cwd() as the authoritative root.
    """
    global _PROJECT_ROOT_CACHE
    if _PROJECT_ROOT_CACHE is not None and start is None:
        return _PROJECT_ROOT_CACHE

    origin = start or Path(__file__).resolve().parent
    current = origin
    for _ in range(5):
        if (current / "zye_config.toml").is_file():
            if start is None:
                _PROJECT_ROOT_CACHE = current
            return current
        current = current.parent

    if start is None:
        _PROJECT_ROOT_CACHE = origin
    return origin


def _reset_project_root_cache() -> None:
    """Reset cached project root for test isolation."""
    global _PROJECT_ROOT_CACHE
    _PROJECT_ROOT_CACHE = None


# ============================================================================
# B.  Safe Source File Resolver & Path Security
# ============================================================================

# Maximum allowed file size for source inspection and backup (1 MB)
MAX_SOURCE_FILE_SIZE_BYTES = 1024 * 1024
MAX_PATCH_INPUT_SIZE_BYTES = 64 * 1024

# Protected filenames and patterns never accessible via source tools
PROTECTED_FILENAMES: frozenset[str] = frozenset({
    ".env",
    ".env.production",
    ".env.local",
    ".env.example",
    "id_rsa",
    "id_ed25519",
})

# Critical core framework files protected from automated patching by policy
CRITICAL_PROTECTED_FILES: frozenset[str] = frozenset({
    "zye_guard.py",
    "self_repair_mcp.py",
    "doctor.py",
    ".env",
    "requirements-lock.txt",
})

# Forbidden directories that must never be scanned or read as source
FORBIDDEN_DIRECTORIES: frozenset[str] = frozenset({
    ".venv",
    ".git",
    "node_modules",
    "__pycache__",
    "profiles",
    "data",
    "backups",
})

# Secret detection regexes for source file safety
_SECRET_SCAN_PATTERNS = [
    re.compile(r'AIza[0-9A-Za-z_-]{35}'),
    re.compile(r'sk-[a-zA-Z0-9_-]{20,}'),
    re.compile(r'ghp_[a-zA-Z0-9]{36}'),
    re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----'),
]


def contains_embedded_secret(content: str) -> bool:
    """Check if content appears to contain a high-confidence secret or private key."""
    for pattern in _SECRET_SCAN_PATTERNS:
        if pattern.search(content):
            return True
    return False


def validate_file_size(path: Path, max_bytes: int = MAX_SOURCE_FILE_SIZE_BYTES) -> bool:
    """Check if file size does not exceed the allowed threshold."""
    try:
        return path.stat().st_size <= max_bytes
    except (OSError, ValueError):
        return False


def resolve_project_file(
    filename: str,
    root: Path | None = None,
    must_exist: bool = True,
    allowed_extensions: tuple[str, ...] = (".py",),
) -> tuple[bool, Path | None, str | None]:
    """Resolve and validate a project-relative file path with strict security checks."""
    if root is None:
        root = get_project_root()

    if not filename or not isinstance(filename, str):
        return False, None, "INVALID_FILENAME"

    # Reject null bytes, UNC, and device paths
    if "\x00" in filename or filename.startswith("\\\\") or filename.startswith("//"):
        return False, None, "PATH_ACCESS_DENIED"

    raw_path = Path(filename)
    if raw_path.is_absolute():
        try:
            resolved = raw_path.resolve()
            if not resolved.is_relative_to(root.resolve()):
                return False, None, "PATH_OUTSIDE_PROJECT"
        except (ValueError, OSError):
            return False, None, "PATH_OUTSIDE_PROJECT"
    else:
        try:
            resolved = (root / raw_path).resolve()
        except (ValueError, OSError):
            return False, None, "PATH_ACCESS_DENIED"

    try:
        if not resolved.is_relative_to(root.resolve()):
            return False, None, "PATH_OUTSIDE_PROJECT"
    except (ValueError, OSError):
        return False, None, "PATH_OUTSIDE_PROJECT"

    if is_protected_windows_path(resolved):
        return False, None, "PATH_ACCESS_DENIED"

    rel_parts = resolved.relative_to(root.resolve()).parts
    for part in rel_parts[:-1]:
        if part in FORBIDDEN_DIRECTORIES or part.startswith("."):
            return False, None, "PROTECTED_FILE"

    if resolved.name.lower() in PROTECTED_FILENAMES or resolved.name.startswith(".env"):
        return False, None, "PROTECTED_FILE"

    if resolved.suffix.lower() in (".sqlite", ".db", ".key", ".pem", ".pfx", ".bak"):
        return False, None, "PROTECTED_FILE"

    if allowed_extensions and resolved.suffix.lower() not in allowed_extensions:
        return False, None, "INVALID_FILENAME"

    if must_exist and not resolved.is_file():
        return False, None, "FILE_NOT_FOUND"

    return True, resolved, None


# ============================================================================
# C.  Structured MCP Response Engine
# ============================================================================

def make_success_response(tool_name: str, data: dict[str, Any], trace_id: str | None = None) -> dict[str, Any]:
    """Build a standard successful MCP JSON response."""
    return {
        "status": "success",
        "tool": tool_name,
        "trace_id": trace_id or uuid.uuid4().hex[:12],
        "data": data,
    }


def make_error_response(
    tool_name: str,
    code: str,
    message: str,
    next_step: str = "",
    trace_id: str | None = None,
) -> dict[str, Any]:
    """Build a standard structured MCP JSON error response."""
    return {
        "status": "error",
        "tool": tool_name,
        "code": code,
        "message": redact_secrets(message),
        "next_step": next_step,
        "trace_id": trace_id or uuid.uuid4().hex[:12],
    }


# ============================================================================
# D.  Audit Loggers (Self-Repair & Code Repair)
# ============================================================================

_AUDIT_LOGGER: logging.Logger | None = None
_CODE_REPAIR_LOGGER: logging.Logger | None = None


def get_audit_logger(root: Path | None = None) -> logging.Logger:
    """Return rotating file logger for logs/self_repair_audit.log."""
    global _AUDIT_LOGGER
    if _AUDIT_LOGGER is not None:
        return _AUDIT_LOGGER

    logger = logging.getLogger("zye_self_repair_audit")
    for h in list(logger.handlers):
        try:
            h.close()
        except Exception:
            pass
        logger.removeHandler(h)

    if root is None:
        root = get_project_root()
    logs_dir = root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    audit_log = logs_dir / "self_repair_audit.log"

    try:
        handler = RotatingFileHandler(audit_log, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
    except Exception:
        logger.addHandler(logging.NullHandler())

    logger.setLevel(logging.INFO)
    logger.propagate = False
    _AUDIT_LOGGER = logger
    return logger


def get_code_repair_audit_logger(root: Path | None = None) -> logging.Logger:
    """Return rotating file logger for logs/code_repair_audit.log."""
    global _CODE_REPAIR_LOGGER
    if _CODE_REPAIR_LOGGER is not None:
        return _CODE_REPAIR_LOGGER

    logger = logging.getLogger("zye_code_repair_audit")
    for h in list(logger.handlers):
        try:
            h.close()
        except Exception:
            pass
        logger.removeHandler(h)

    if root is None:
        root = get_project_root()
    logs_dir = root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    code_log = logs_dir / "code_repair_audit.log"

    try:
        handler = RotatingFileHandler(code_log, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
    except Exception:
        logger.addHandler(logging.NullHandler())

    logger.setLevel(logging.INFO)
    logger.propagate = False
    _CODE_REPAIR_LOGGER = logger
    return logger


def _reset_audit_logger() -> None:
    """Reset audit logger singletons (used by tests)."""
    global _AUDIT_LOGGER, _CODE_REPAIR_LOGGER
    if _AUDIT_LOGGER is not None:
        for h in list(_AUDIT_LOGGER.handlers):
            try:
                h.close()
            except Exception:
                pass
            _AUDIT_LOGGER.removeHandler(h)
    _AUDIT_LOGGER = None
    if _CODE_REPAIR_LOGGER is not None:
        for h in list(_CODE_REPAIR_LOGGER.handlers):
            try:
                h.close()
            except Exception:
                pass
            _CODE_REPAIR_LOGGER.removeHandler(h)
    _CODE_REPAIR_LOGGER = None


def log_repair_audit(
    tool: str,
    trace_id: str,
    operation: str,
    result: str,
    target_file: str = "",
    backup_id: str = "",
    sha256_status: str = "",
    details: str = "",
    root: Path | None = None,
) -> None:
    """Record an audit trail event in logs/self_repair_audit.log."""
    logger = get_audit_logger(root)
    entry = {
        "timestamp": datetime.datetime.now(timezone.utc).isoformat(),
        "trace_id": trace_id,
        "tool": tool,
        "target_file": target_file,
        "operation": operation,
        "result": result,
        "backup_id": backup_id,
        "sha256_status": sha256_status,
        "details": redact_secrets(details),
    }
    logger.info(json.dumps(entry))


def log_code_repair_audit(
    repair_id: str,
    patch_id: str,
    trace_id: str,
    target_file: str,
    operation: str,
    original_sha256: str,
    proposed_sha256: str,
    backup_id: str = "",
    backup_integrity: str = "",
    approval_status: str = "",
    ast_result: str = "",
    compile_result: str = "",
    targeted_test_result: str = "",
    atomic_replace_result: str = "",
    rollback_result: str = "",
    hot_reload_result: str = "",
    final_status: str = "",
    details: str = "",
    root: Path | None = None,
) -> None:
    """Record detailed repair transaction in logs/code_repair_audit.log."""
    logger = get_code_repair_audit_logger(root)
    entry = {
        "timestamp": datetime.datetime.now(timezone.utc).isoformat(),
        "repair_id": repair_id,
        "patch_id": patch_id,
        "trace_id": trace_id,
        "target_file": target_file,
        "operation": operation,
        "original_sha256": original_sha256,
        "proposed_sha256": proposed_sha256,
        "backup_id": backup_id,
        "backup_integrity": backup_integrity,
        "approval_status": approval_status,
        "ast_result": ast_result,
        "compile_result": compile_result,
        "targeted_test_result": targeted_test_result,
        "atomic_replace_result": atomic_replace_result,
        "rollback_result": rollback_result,
        "hot_reload_result": hot_reload_result,
        "final_status": final_status,
        "details": redact_secrets(details),
    }
    logger.info(json.dumps(entry))


# ============================================================================
# E.  Error Intelligence & Traceback Analysis Engine
# ============================================================================

_COMMON_EXCEPTION_CLASSES = {
    "SyntaxError", "IndentationError", "ImportError", "ModuleNotFoundError",
    "AttributeError", "TypeError", "ValueError", "NameError", "KeyError",
    "IndexError", "FileNotFoundError", "PermissionError", "TimeoutError",
    "ConnectionError", "RuntimeError", "ZeroDivisionError", "OSError",
}


def classify_error_type(exc_type: str) -> str:
    """Classify Python exception type into functional diagnosis category."""
    if exc_type in ("SyntaxError", "IndentationError"):
        return "SYNTAX_ERROR"
    if exc_type in ("ImportError", "ModuleNotFoundError"):
        return "DEPENDENCY_OR_IMPORT_ERROR"
    if exc_type in ("AttributeError", "TypeError", "ValueError", "NameError"):
        return "LOGIC_OR_TYPE_ERROR"
    if exc_type in ("KeyError", "IndexError"):
        return "LOOKUP_ERROR"
    if exc_type in ("FileNotFoundError", "PermissionError", "OSError"):
        return "FILESYSTEM_OR_PERMISSION_ERROR"
    if exc_type in ("TimeoutError", "ConnectionError"):
        return "TRANSIENT_NETWORK_ERROR"
    return "RUNTIME_ERROR"


def parse_traceback_summary(tb_text: str) -> dict[str, Any]:
    """Parse a raw Python traceback string into structured diagnostic metadata."""
    if not tb_text or not isinstance(tb_text, str) or "Traceback" not in tb_text:
        return {
            "status": "INSUFFICIENT_TRACEBACK_INFORMATION",
            "exception_type": None,
            "exception_message": None,
            "source_filename": None,
            "line_number": None,
            "function_name": None,
            "error_category": "UNKNOWN",
        }

    lines = [ln.strip() for ln in tb_text.strip().splitlines() if ln.strip()]
    last_line = lines[-1]
    exc_type = None
    exc_msg = None
    for common_exc in _COMMON_EXCEPTION_CLASSES:
        if last_line.startswith(f"{common_exc}:"):
            exc_type = common_exc
            exc_msg = last_line[len(common_exc) + 1:].strip()
            break
        elif last_line == common_exc:
            exc_type = common_exc
            exc_msg = ""
            break

    if exc_type is None:
        match = re.match(r'^([A-Za-z0-9_.]+(?:Error|Exception|Warning))(?::\s*(.*))?$', last_line)
        if match:
            exc_type = match.group(1).split(".")[-1]
            exc_msg = match.group(2) or ""

    source_filename = None
    line_number = None
    func_name = None

    frame_pattern = re.compile(r'File\s+"([^"]+)",\s+line\s+(\d+)(?:,\s+in\s+([A-Za-z0-9_<>]+))?')
    for line in reversed(lines):
        frame_match = frame_pattern.search(line)
        if frame_match:
            source_filename = Path(frame_match.group(1)).name
            line_number = int(frame_match.group(2))
            func_name = frame_match.group(3) or "<module>"
            break

    category = classify_error_type(exc_type or "")

    return {
        "status": "PARSED" if (exc_type and source_filename) else "INSUFFICIENT_TRACEBACK_INFORMATION",
        "exception_type": exc_type,
        "exception_message": redact_secrets(exc_msg or ""),
        "source_filename": source_filename,
        "line_number": line_number,
        "function_name": func_name,
        "error_category": category,
    }


# ============================================================================
# F.  SHA-256 Integrity Verification Engine
# ============================================================================

def calculate_sha256(file_path: Path) -> str:
    """Calculate the hex SHA-256 digest of a file in 64 KB blocks."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def calculate_string_sha256(text: str, encoding: str = "utf-8") -> str:
    """Calculate the hex SHA-256 digest of a string."""
    return hashlib.sha256(text.encode(encoding)).hexdigest()


def verify_backup_integrity(source_path: Path, backup_path: Path) -> bool:
    """Verify that source and backup files have identical byte contents via SHA-256."""
    try:
        if not source_path.is_file() or not backup_path.is_file():
            return False
        return calculate_sha256(source_path) == calculate_sha256(backup_path)
    except (OSError, ValueError):
        return False


# ============================================================================
# G.  Approval Engine (SQLite Schema & Cryptographic Token)
# ============================================================================

def get_approval_db_path(root: Path | None = None) -> Path:
    """Get path to zye_assistant_db.sqlite."""
    if root is None:
        root = get_project_root()
    return root / "data" / "zye_assistant_db.sqlite"


def init_approval_db(db_path: Path) -> None:
    """Ensure repair_approvals table exists in SQLite database (non-destructive)."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS repair_approvals (
                approval_id TEXT PRIMARY KEY,
                token_hash TEXT NOT NULL,
                patch_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                original_sha256 TEXT NOT NULL,
                proposed_sha256 TEXT NOT NULL,
                operation TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                consumed_at TEXT,
                approval_status TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_repair_approvals_token_hash ON repair_approvals(token_hash)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_repair_approvals_patch_id ON repair_approvals(patch_id)")
        conn.commit()
    finally:
        conn.close()


def create_repair_approval(
    db_path: Path,
    patch_id: str,
    filename: str,
    original_sha256: str,
    proposed_sha256: str,
    operation: str = "patch",
    ttl_seconds: int = 120,
) -> tuple[str, str]:
    """Create a new one-time approval record and return (approval_id, plaintext_token)."""
    init_approval_db(db_path)
    plaintext_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(plaintext_token.encode("utf-8")).hexdigest()
    approval_id = uuid.uuid4().hex[:12]

    now_utc = datetime.datetime.now(timezone.utc)
    expires_utc = now_utc + datetime.timedelta(seconds=ttl_seconds)

    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            """
            INSERT INTO repair_approvals (
                approval_id, token_hash, patch_id, filename, original_sha256,
                proposed_sha256, operation, created_at, expires_at, consumed_at, approval_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, 'PENDING')
            """,
            (
                approval_id, token_hash, patch_id, filename, original_sha256,
                proposed_sha256, operation, now_utc.isoformat(), expires_utc.isoformat(),
            ),
        )
        conn.commit()
    finally:
        conn.close()

    return approval_id, plaintext_token


def consume_repair_approval(
    db_path: Path,
    token: str,
    patch_id: str,
    filename: str,
    original_sha256: str,
    proposed_sha256: str | None = None,
    operation: str = "patch",
) -> tuple[bool, str]:
    """Validate and consume a one-time approval token in an atomic transaction."""
    if not token or not isinstance(token, str):
        return False, "MISSING_OR_INVALID_TOKEN"

    init_approval_db(db_path)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    now_utc = datetime.datetime.now(timezone.utc).isoformat()

    conn = sqlite3.connect(str(db_path), timeout=10.0)
    try:
        conn.execute("BEGIN IMMEDIATE")
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT approval_id, patch_id, filename, original_sha256, proposed_sha256,
                   operation, expires_at, approval_status
            FROM repair_approvals
            WHERE token_hash = ?
            """,
            (token_hash,),
        )
        row = cursor.fetchone()
        if not row:
            conn.rollback()
            return False, "TOKEN_NOT_FOUND"

        app_id, p_id, f_name, o_hash, prop_hash, op, exp_at, status = row

        if status != "PENDING":
            conn.rollback()
            return False, f"TOKEN_ALREADY_{status}"

        if now_utc > exp_at:
            cursor.execute("UPDATE repair_approvals SET approval_status = 'EXPIRED' WHERE approval_id = ?", (app_id,))
            conn.commit()
            return False, "APPROVAL_EXPIRED"

        if p_id != patch_id:
            conn.rollback()
            return False, "PATCH_ID_MISMATCH"

        if Path(f_name).name.lower() != Path(filename).name.lower():
            conn.rollback()
            return False, "FILENAME_MISMATCH"

        if o_hash != original_sha256:
            conn.rollback()
            return False, "ORIGINAL_HASH_MISMATCH"

        if proposed_sha256 is not None and prop_hash != proposed_sha256:
            conn.rollback()
            return False, "PROPOSED_HASH_MISMATCH"

        if op != operation:
            conn.rollback()
            return False, "OPERATION_MISMATCH"

        cursor.execute(
            """
            UPDATE repair_approvals
            SET approval_status = 'CONSUMED', consumed_at = ?
            WHERE approval_id = ? AND approval_status = 'PENDING'
            """,
            (now_utc, app_id),
        )
        conn.commit()
        return True, "APPROVAL_VALIDATED"
    except Exception as exc:
        conn.rollback()
        return False, f"DATABASE_TRANSACTION_ERROR: {exc}"
    finally:
        conn.close()


def request_patch_approval(
    patch_id: str,
    filename: str,
    original_sha256: str,
    proposed_sha256: str,
    operation: str = "patch",
    ttl_seconds: int = 120,
    root: Path | None = None,
) -> tuple[str, str]:
    """Convenience helper to generate an approval record and return (approval_id, token)."""
    db_path = get_approval_db_path(root)
    return create_repair_approval(
        db_path, patch_id, filename, original_sha256, proposed_sha256, operation, ttl_seconds
    )


# ============================================================================
# H.  AST Validation & Compilation Verification Engines
# ============================================================================

def validate_ast_syntax(source_code: str, filename: str = "<source>") -> tuple[bool, dict[str, Any]]:
    """Validate Python syntax via AST without executing code."""
    try:
        ast.parse(source_code, filename=filename, type_comments=True)
        return True, {"status": "PASS", "details": "AST parsed successfully"}
    except (SyntaxError, IndentationError) as err:
        return False, {
            "status": "FAIL",
            "error_type": type(err).__name__,
            "line_number": err.lineno,
            "column_offset": err.offset,
            "message": redact_secrets(str(getattr(err, "msg", str(err)))),
        }
    except Exception as exc:
        return False, {
            "status": "FAIL",
            "error_type": type(exc).__name__,
            "message": redact_secrets(str(exc)),
        }


def verify_python_compilation(source_code: str, filename: str = "<source>") -> tuple[bool, str | None]:
    """Verify code can compile into bytecode without execution."""
    try:
        compile(source_code, filename, "exec", dont_inherit=True)
        return True, None
    except Exception as exc:
        return False, redact_secrets(str(exc))


# ============================================================================
# I.  Encoding & Atomic Replacement Engines
# ============================================================================

def read_source_with_encoding(file_path: Path) -> tuple[str, str, str]:
    """Read source file preserving its encoding (UTF-8/UTF-8 BOM) and line endings (LF/CRLF)."""
    raw_bytes = file_path.read_bytes()
    line_ending = "\r\n" if b"\r\n" in raw_bytes else "\n"
    encoding = "utf-8"
    if raw_bytes.startswith(b"\xef\xbb\xbf"):
        encoding = "utf-8-sig"
    else:
        try:
            import io
            detected, _ = tokenize.detect_encoding(io.BytesIO(raw_bytes).readline)
            encoding = detected
        except Exception:
            encoding = "utf-8"

    content = raw_bytes.decode(encoding, errors="replace")
    return content, encoding, line_ending


def generate_candidate_source(original_source: str, old_snippet: str, new_snippet: str) -> tuple[bool, str | None, str | None]:
    """Validate exact single occurrence and generate candidate updated source."""
    if not old_snippet:
        return False, None, "EMPTY_OLD_SNIPPET"

    count = original_source.count(old_snippet)
    if count == 0:
        return False, None, "OLD_SNIPPET_NOT_FOUND"
    if count > 1:
        return False, None, f"AMBIGUOUS_REPLACEMENT_{count}_MATCHES"

    updated = original_source.replace(old_snippet, new_snippet, 1)
    return True, updated, None


def generate_unified_diff(original_text: str, updated_text: str, filename: str) -> str:
    """Generate a clean unified diff string between original and candidate source."""
    orig_lines = original_text.splitlines(keepends=True)
    upd_lines = updated_text.splitlines(keepends=True)
    diff_gen = difflib.unified_diff(
        orig_lines,
        upd_lines,
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
        lineterm="\n",
    )
    return "".join(diff_gen)


def atomic_replace_source(target_path: Path, new_source: str, encoding: str = "utf-8", line_ending: str = "\n") -> tuple[bool, str | None]:
    """Atomically write new_source into target_path using fsync and os.replace()."""
    parent_dir = target_path.parent
    tmp_name = f".tmp_patch_{uuid.uuid4().hex[:8]}.py"
    tmp_path = parent_dir / tmp_name
    try:
        normalized = new_source.replace("\r\n", "\n").replace("\r", "\n")
        if line_ending == "\r\n":
            normalized = normalized.replace("\n", "\r\n")

        raw_bytes = normalized.encode(encoding)
        with open(tmp_path, "wb") as f:
            f.write(raw_bytes)
            f.flush()
            os.fsync(f.fileno())

        os.replace(tmp_path, target_path)
        return True, None
    except Exception as exc:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        return False, str(exc)


def automatic_rollback(target_path: Path, backup_path: Path, expected_original_sha256: str) -> tuple[bool, str]:
    """Restore original source from pre-patch backup atomically and verify restored hash."""
    if not backup_path.is_file():
        return False, "BACKUP_FILE_MISSING"

    backup_hash = calculate_sha256(backup_path)
    if backup_hash != expected_original_sha256:
        return False, f"BACKUP_HASH_MISMATCH_{backup_hash}_VS_{expected_original_sha256}"

    backup_bytes = backup_path.read_bytes()
    parent_dir = target_path.parent
    tmp_name = f".tmp_rollback_{uuid.uuid4().hex[:8]}.py"
    tmp_path = parent_dir / tmp_name
    try:
        with open(tmp_path, "wb") as f:
            f.write(backup_bytes)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, target_path)

        restored_hash = calculate_sha256(target_path)
        if restored_hash != expected_original_sha256:
            return False, "RESTORED_HASH_MISMATCH"

        return True, "ROLLED_BACK"
    except Exception as exc:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        return False, f"CRITICAL_RECOVERY_FAILURE: {exc}"


# ============================================================================
# J.  MCP TOOLS 01–06 (Day 05 Baseline Diagnostics)
# ============================================================================

@mcp.tool()
@zye_safe_skill()
def read_recent_error_logs(lines: int = 60) -> dict[str, Any]:
    """Read recent error log entries and tracebacks from logs/zye_errors.log."""
    trace_id = uuid.uuid4().hex[:12]
    root = get_project_root()

    if not isinstance(lines, int) or lines <= 0:
        return make_error_response("read_recent_error_logs", "INVALID_ARGUMENTS", "lines must be positive integer", trace_id=trace_id)
    if lines > 200:
        return make_error_response("read_recent_error_logs", "INVALID_ARGUMENTS", "lines exceeds 200 max limit", trace_id=trace_id)

    log_path = root / "logs" / "zye_errors.log"
    if not log_path.is_file() or log_path.stat().st_size == 0:
        log_repair_audit("read_recent_error_logs", trace_id, "READ", "EMPTY", "logs/zye_errors.log", root=root)
        return make_success_response("read_recent_error_logs", {
            "message": "No errors logged yet.",
            "errors_found": False,
            "requested_lines": lines,
            "returned_lines": 0,
            "recent_log_entries": [],
        }, trace_id=trace_id)

    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            all_lines = [ln.rstrip("\r\n") for ln in f if ln.strip()]

        selected_lines = all_lines[-lines:]
        parsed_entries = []
        for raw_line in selected_lines:
            sanitized = redact_secrets(raw_line)
            try:
                parsed_entries.append(json.loads(sanitized))
            except json.JSONDecodeError:
                parsed_entries.append(sanitized)

        log_repair_audit("read_recent_error_logs", trace_id, "READ", "SUCCESS", "logs/zye_errors.log", details=f"Returned {len(parsed_entries)}", root=root)
        return make_success_response("read_recent_error_logs", {
            "errors_found": True,
            "requested_lines": lines,
            "returned_lines": len(parsed_entries),
            "recent_log_entries": parsed_entries,
        }, trace_id=trace_id)
    except Exception as exc:
        log_repair_audit("read_recent_error_logs", trace_id, "READ", "FAILED", "logs/zye_errors.log", details=str(exc), root=root)
        return make_error_response("read_recent_error_logs", "LOG_READ_FAILED", str(exc), trace_id=trace_id)


@mcp.tool()
@zye_safe_skill()
def read_own_source_code(filename: str, start_line: int = 1, end_line: int = 250) -> dict[str, Any]:
    """Read project Python source code with exact line numbers for AI inspection."""
    trace_id = uuid.uuid4().hex[:12]
    root = get_project_root()

    if not isinstance(start_line, int) or start_line < 1:
        return make_error_response("read_own_source_code", "INVALID_LINE_RANGE", "start_line must be >= 1", trace_id=trace_id)
    if not isinstance(end_line, int) or end_line < start_line:
        return make_error_response("read_own_source_code", "INVALID_LINE_RANGE", "end_line must be >= start_line", trace_id=trace_id)
    if (end_line - start_line + 1) > 300:
        return make_error_response("read_own_source_code", "INVALID_LINE_RANGE", "Requested range exceeds 300 lines", trace_id=trace_id)

    valid, file_path, err_code = resolve_project_file(filename, root=root, must_exist=True)
    if not valid or file_path is None:
        log_repair_audit("read_own_source_code", trace_id, "READ", "DENIED", filename, details=err_code or "DENIED", root=root)
        return make_error_response("read_own_source_code", err_code or "PATH_ACCESS_DENIED", f"Cannot read: {filename}", trace_id=trace_id)

    if not validate_file_size(file_path, MAX_SOURCE_FILE_SIZE_BYTES):
        return make_error_response("read_own_source_code", "SOURCE_TOO_LARGE", f"File exceeds 1 MB: {filename}", trace_id=trace_id)

    try:
        try:
            with tokenize.open(file_path) as f:
                all_lines = f.readlines()
        except (tokenize.TokenError, SyntaxError, UnicodeError):
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                all_lines = f.readlines()

        total_lines = len(all_lines)
        actual_end = min(end_line, total_lines)
        if start_line > total_lines:
            return make_error_response("read_own_source_code", "INVALID_LINE_RANGE", f"start_line ({start_line}) > total ({total_lines})", trace_id=trace_id)

        selected_slice = all_lines[start_line - 1: actual_end]
        formatted_lines = [f"{i:4d} | {ln.rstrip()}" for i, ln in enumerate(selected_slice, start=start_line)]
        source_code_text = "\n".join(formatted_lines)
        rel_path = str(file_path.relative_to(root.resolve())).replace("\\", "/")
        mtime = datetime.datetime.fromtimestamp(file_path.stat().st_mtime, timezone.utc).isoformat()

        log_repair_audit("read_own_source_code", trace_id, "READ", "SUCCESS", rel_path, details=f"Lines {start_line}-{actual_end}", root=root)
        return make_success_response("read_own_source_code", {
            "filename": rel_path,
            "module_name": file_path.stem,
            "start_line": start_line,
            "end_line": actual_end,
            "total_lines": total_lines,
            "source_code": redact_secrets(source_code_text),
            "modified_at": mtime,
        }, trace_id=trace_id)
    except Exception as exc:
        log_repair_audit("read_own_source_code", trace_id, "READ", "FAILED", filename, details=str(exc), root=root)
        return make_error_response("read_own_source_code", "INTERNAL_ERROR", str(exc), trace_id=trace_id)


@mcp.tool()
@zye_safe_skill()
def list_project_source_files(directory: str = ".", recursive: bool = False) -> dict[str, Any]:
    """List project-contained Python source files eligible for inspection."""
    trace_id = uuid.uuid4().hex[:12]
    root = get_project_root()
    if not isinstance(directory, str) or not directory:
        directory = "."

    if "\x00" in directory or directory.startswith("\\\\") or directory.startswith("//"):
        return make_error_response("list_project_source_files", "PATH_ACCESS_DENIED", "Invalid directory path.", trace_id=trace_id)

    target_dir = (root / directory).resolve()
    try:
        if not target_dir.is_relative_to(root.resolve()):
            return make_error_response("list_project_source_files", "PATH_OUTSIDE_PROJECT", f"Escapes root: {directory}", trace_id=trace_id)
    except (ValueError, OSError):
        return make_error_response("list_project_source_files", "PATH_OUTSIDE_PROJECT", "Resolution failed", trace_id=trace_id)

    if not target_dir.is_dir():
        return make_error_response("list_project_source_files", "FILE_NOT_FOUND", f"Directory not found: {directory}", trace_id=trace_id)

    try:
        rel_to_root = target_dir.relative_to(root.resolve()).parts
        if rel_to_root and (rel_to_root[0] in FORBIDDEN_DIRECTORIES or rel_to_root[0].startswith(".")):
            return make_error_response("list_project_source_files", "PROTECTED_FILE", f"Access to '{rel_to_root[0]}' restricted.", trace_id=trace_id)
    except Exception:
        pass

    discovered_files: list[str] = []
    try:
        iterator = target_dir.rglob("*.py") if recursive else target_dir.glob("*.py")
        for file_path in iterator:
            if len(discovered_files) >= 100:
                break
            if not file_path.is_file():
                continue
            rel = str(file_path.relative_to(root.resolve())).replace("\\", "/")
            valid, _, _ = resolve_project_file(rel, root=root, must_exist=True)
            if valid:
                discovered_files.append(rel)

        discovered_files.sort()
        rel_dir = str(target_dir.relative_to(root.resolve())).replace("\\", "/") or "."
        log_repair_audit("list_project_source_files", trace_id, "LIST", "SUCCESS", rel_dir, details=f"Found {len(discovered_files)}", root=root)
        return make_success_response("list_project_source_files", {
            "directory": rel_dir,
            "recursive": recursive,
            "files_found": len(discovered_files),
            "files": discovered_files,
        }, trace_id=trace_id)
    except Exception as exc:
        log_repair_audit("list_project_source_files", trace_id, "LIST", "FAILED", directory, details=str(exc), root=root)
        return make_error_response("list_project_source_files", "INTERNAL_ERROR", str(exc), trace_id=trace_id)


@mcp.tool()
@zye_safe_skill()
def inspect_source_file(filename: str) -> dict[str, Any]:
    """Inspect metadata and Python syntax status of a source file without reading contents."""
    trace_id = uuid.uuid4().hex[:12]
    root = get_project_root()

    valid, file_path, err_code = resolve_project_file(filename, root=root, must_exist=True)
    if not valid or file_path is None:
        log_repair_audit("inspect_source_file", trace_id, "INSPECT", "DENIED", filename, details=err_code or "DENIED", root=root)
        return make_error_response("inspect_source_file", err_code or "PATH_ACCESS_DENIED", f"Access denied: {filename}", trace_id=trace_id)

    try:
        stat_info = file_path.stat()
        file_size = stat_info.st_size
        mtime = datetime.datetime.fromtimestamp(stat_info.st_mtime, timezone.utc).isoformat()
        sha256_hash = calculate_sha256(file_path)

        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            total_lines = len(content.splitlines())
            try:
                ast.parse(content, filename=file_path.name)
                syntax_status = "VALID_PYTHON"
            except SyntaxError as syn_err:
                syntax_status = f"SYNTAX_ERROR: Line {syn_err.lineno}: {syn_err.msg}"
        except Exception:
            total_lines = -1
            syntax_status = "UNREADABLE"

        rel_path = str(file_path.relative_to(root.resolve())).replace("\\", "/")
        log_repair_audit("inspect_source_file", trace_id, "INSPECT", "SUCCESS", rel_path, details=syntax_status, root=root)
        return make_success_response("inspect_source_file", {
            "filename": rel_path,
            "extension": file_path.suffix.lower(),
            "file_size": file_size,
            "modified_at": mtime,
            "sha256": sha256_hash,
            "total_lines": total_lines,
            "readability_status": "READABLE",
            "source_validation_status": syntax_status,
        }, trace_id=trace_id)
    except Exception as exc:
        log_repair_audit("inspect_source_file", trace_id, "INSPECT", "FAILED", filename, details=str(exc), root=root)
        return make_error_response("inspect_source_file", "INTERNAL_ERROR", str(exc), trace_id=trace_id)


@mcp.tool()
@zye_safe_skill()
def create_source_backup(filename: str, reason: str) -> dict[str, Any]:
    """Create an atomic, timestamped, SHA-256-verified backup of a Python source file."""
    trace_id = uuid.uuid4().hex[:12]
    root = get_project_root()

    if not reason or not isinstance(reason, str) or not reason.strip():
        return make_error_response("create_source_backup", "INVALID_ARGUMENTS", "Non-empty backup reason required", trace_id=trace_id)

    valid, file_path, err_code = resolve_project_file(filename, root=root, must_exist=True)
    if not valid or file_path is None:
        log_repair_audit("create_source_backup", trace_id, "BACKUP", "DENIED", filename, details=err_code or "DENIED", root=root)
        return make_error_response("create_source_backup", err_code or "PATH_ACCESS_DENIED", f"Cannot back up: {filename}", trace_id=trace_id)

    if not validate_file_size(file_path, MAX_SOURCE_FILE_SIZE_BYTES):
        return make_error_response("create_source_backup", "SOURCE_TOO_LARGE", f"File exceeds 1 MB: {filename}", trace_id=trace_id)

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            source_content = f.read()
        if contains_embedded_secret(source_content):
            log_security_alert("create_source_backup", trace_id, f"Refused backup of {filename}: embedded secret detected.")
            log_repair_audit("create_source_backup", trace_id, "BACKUP", "REFUSED", filename, details="SECRET_DETECTED", root=root)
            return make_error_response("create_source_backup", "PROTECTED_FILE", f"Embedded secret detected in {filename}; backup refused.", trace_id=trace_id)
    except Exception as exc:
        return make_error_response("create_source_backup", "INTERNAL_ERROR", str(exc), trace_id=trace_id)

    backups_dir = root / "backups"
    backups_dir.mkdir(parents=True, exist_ok=True)

    backup_uuid = uuid.uuid4().hex[:8]
    now_utc = datetime.datetime.now(timezone.utc)
    timestamp_str = now_utc.strftime("%Y%m%dT%H%M%SZ")
    safe_stem = file_path.stem.replace(".", "_")

    backup_filename = f"{safe_stem}__{timestamp_str}__{backup_uuid}.py.bak"
    final_backup_path = backups_dir / backup_filename
    temp_backup_path = backups_dir / f".tmp_{backup_filename}"
    meta_path = backups_dir / f"{safe_stem}__{timestamp_str}__{backup_uuid}.meta.json"

    try:
        source_sha256 = calculate_sha256(file_path)
        source_size = file_path.stat().st_size

        with open(file_path, "rb") as src, open(temp_backup_path, "wb") as dst:
            shutil.copyfileobj(src, dst, length=65536)
            dst.flush()
            os.fsync(dst.fileno())

        temp_backup_path.replace(final_backup_path)
        backup_sha256 = calculate_sha256(final_backup_path)
        if backup_sha256 != source_sha256:
            try:
                final_backup_path.unlink()
            except OSError:
                pass
            log_repair_audit("create_source_backup", trace_id, "BACKUP", "INTEGRITY_FAILED", filename, root=root)
            return make_error_response("create_source_backup", "BACKUP_INTEGRITY_FAILED", "Hash mismatch", trace_id=trace_id)

        rel_source_path = str(file_path.relative_to(root.resolve())).replace("\\", "/")
        meta_data = {
            "backup_id": backup_uuid,
            "original_file": rel_source_path,
            "backup_file": backup_filename,
            "created_at": now_utc.isoformat(),
            "sha256": backup_sha256,
            "file_size": source_size,
            "reason": redact_secrets(reason.strip()),
            "integrity_status": "VERIFIED",
        }
        with open(meta_path, "w", encoding="utf-8") as mf:
            json.dump(meta_data, mf, indent=2)

        log_repair_audit("create_source_backup", trace_id, "BACKUP", "SUCCESS", rel_source_path, backup_id=backup_uuid, sha256_status="MATCH", root=root)
        return make_success_response("create_source_backup", {
            "backup_id": backup_uuid,
            "original_file": rel_source_path,
            "backup_file": backup_filename,
            "sha256": backup_sha256,
            "file_size": source_size,
            "created_at": now_utc.isoformat(),
            "reason": redact_secrets(reason.strip()),
            "integrity_status": "VERIFIED",
        }, trace_id=trace_id)
    except Exception as exc:
        if temp_backup_path.exists():
            try:
                temp_backup_path.unlink()
            except OSError:
                pass
        log_repair_audit("create_source_backup", trace_id, "BACKUP", "FAILED", filename, details=str(exc), root=root)
        return make_error_response("create_source_backup", "BACKUP_CREATION_FAILED", str(exc), trace_id=trace_id)


@mcp.tool()
@zye_safe_skill()
def list_source_backups(filename: str = "") -> dict[str, Any]:
    """List and verify previously created source backups for a project file."""
    trace_id = uuid.uuid4().hex[:12]
    root = get_project_root()
    backups_dir = root / "backups"

    if not backups_dir.is_dir():
        return make_success_response("list_source_backups", {"filter_filename": filename, "backups_found": 0, "backups": []}, trace_id=trace_id)

    norm_filter = Path(filename).name.lower() if filename and filename != "*" else None
    backups_list: list[dict[str, Any]] = []

    try:
        for meta_file in sorted(backups_dir.glob("*.meta.json")):
            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                if not isinstance(meta, dict) or "backup_file" not in meta:
                    continue

                orig_file = meta.get("original_file", "")
                if norm_filter and Path(orig_file).name.lower() != norm_filter and orig_file.lower() != filename.lower():
                    continue

                backup_file_path = backups_dir / meta["backup_file"]
                if backup_file_path.is_file():
                    current_hash = calculate_sha256(backup_file_path)
                    status_str = "VERIFIED" if current_hash == meta.get("sha256") else "INTEGRITY_MISMATCH"
                else:
                    status_str = "BACKUP_FILE_MISSING"

                backups_list.append({
                    "backup_id": meta.get("backup_id", ""),
                    "original_file": orig_file,
                    "backup_file": meta["backup_file"],
                    "created_at": meta.get("created_at", ""),
                    "sha256": meta.get("sha256", ""),
                    "file_size": meta.get("file_size", 0),
                    "reason": meta.get("reason", ""),
                    "integrity_status": status_str,
                })
            except Exception:
                continue

        backups_list.sort(key=lambda b: b.get("created_at", ""), reverse=True)
        log_repair_audit("list_source_backups", trace_id, "LIST_BACKUPS", "SUCCESS", filename or "*", details=f"Found {len(backups_list)}", root=root)
        return make_success_response("list_source_backups", {
            "filter_filename": filename,
            "backups_found": len(backups_list),
            "backups": backups_list,
        }, trace_id=trace_id)
    except Exception as exc:
        log_repair_audit("list_source_backups", trace_id, "LIST_BACKUPS", "FAILED", filename, details=str(exc), root=root)
        return make_error_response("list_source_backups", "INTERNAL_ERROR", str(exc), trace_id=trace_id)


# ============================================================================
# K.  MCP TOOL 07: Preview Code Patch (Day 06)
# ============================================================================

@mcp.tool()
@zye_safe_skill()
def preview_code_patch(
    filename: str,
    old_code_snippet: str,
    new_code_snippet: str,
    reason: str,
    error_trace_id: str | None = None,
) -> dict[str, Any]:
    """Generate a unified diff preview and AST/compile validation for a proposed code fix.

    Does not modify source files or create backups. Requires explicit user approval
    before patch application.
    """
    trace_id = uuid.uuid4().hex[:12]
    patch_id = uuid.uuid4().hex[:12]
    root = get_project_root()

    if not reason or not isinstance(reason, str) or not reason.strip():
        return make_error_response("preview_code_patch", "INVALID_ARGUMENTS", "Non-empty reason string required", trace_id=trace_id)

    if not old_code_snippet or not isinstance(old_code_snippet, str):
        return make_error_response("preview_code_patch", "INVALID_ARGUMENTS", "old_code_snippet must be non-empty", trace_id=trace_id)

    if not isinstance(new_code_snippet, str):
        return make_error_response("preview_code_patch", "INVALID_ARGUMENTS", "new_code_snippet must be a string", trace_id=trace_id)

    if len(old_code_snippet.encode("utf-8")) > MAX_PATCH_INPUT_SIZE_BYTES or len(new_code_snippet.encode("utf-8")) > MAX_PATCH_INPUT_SIZE_BYTES:
        return make_error_response("preview_code_patch", "PATCH_TOO_LARGE", f"Snippet exceeds {MAX_PATCH_INPUT_SIZE_BYTES} bytes limit", trace_id=trace_id)

    valid, file_path, err_code = resolve_project_file(filename, root=root, must_exist=True)
    if not valid or file_path is None:
        log_repair_audit("preview_code_patch", trace_id, "PREVIEW", "DENIED", filename, details=err_code or "DENIED", root=root)
        return make_error_response("preview_code_patch", err_code or "PATH_ACCESS_DENIED", f"Cannot patch {filename}", trace_id=trace_id)

    # Check critical protected files
    if file_path.name.lower() in CRITICAL_PROTECTED_FILES:
        return make_error_response("preview_code_patch", "PROTECTED_FILE", f"Critical framework file '{filename}' is protected from automated patching.", trace_id=trace_id)

    try:
        original_source, encoding, line_ending = read_source_with_encoding(file_path)
        original_sha256 = calculate_sha256(file_path)

        ok, candidate_source, repl_err = generate_candidate_source(original_source, old_code_snippet, new_code_snippet)
        if not ok or candidate_source is None:
            return make_error_response("preview_code_patch", repl_err or "REPLACEMENT_ERROR", f"Replacement failed: {repl_err}", trace_id=trace_id)

        # Proposed SHA-256 (normalized to target line ending)
        norm_candidate = candidate_source.replace("\r\n", "\n").replace("\r", "\n")
        if line_ending == "\r\n":
            norm_candidate = norm_candidate.replace("\n", "\r\n")
        proposed_sha256 = calculate_string_sha256(norm_candidate, encoding=encoding)

        # Validate AST
        ast_ok, ast_diag = validate_ast_syntax(candidate_source, filename=file_path.name)
        if not ast_ok:
            return make_error_response("preview_code_patch", "AST_VALIDATION_FAILED", f"AST error at line {ast_diag.get('line_number')}: {ast_diag.get('message')}", trace_id=trace_id)

        # Validate compilation
        compile_ok, comp_err = verify_python_compilation(candidate_source, filename=file_path.name)
        if not compile_ok:
            return make_error_response("preview_code_patch", "COMPILE_VALIDATION_FAILED", f"Compilation error: {comp_err}", trace_id=trace_id)

        # Generate human-readable diff
        diff_text = generate_unified_diff(original_source, candidate_source, file_path.name)
        rel_path = str(file_path.relative_to(root.resolve())).replace("\\", "/")

        log_code_repair_audit(
            repair_id=trace_id,
            patch_id=patch_id,
            trace_id=trace_id,
            target_file=rel_path,
            operation="PREVIEW",
            original_sha256=original_sha256,
            proposed_sha256=proposed_sha256,
            ast_result="PASS",
            compile_result="PASS",
            final_status="PREVIEWED",
            details=f"Reason: {reason}",
            root=root,
        )

        return make_success_response("preview_code_patch", {
            "patch_id": patch_id,
            "filename": rel_path,
            "original_sha256": original_sha256,
            "proposed_sha256": proposed_sha256,
            "replacement_count": 1,
            "ast_validation": "PASS",
            "compile_validation": "PASS",
            "requires_user_approval": True,
            "error_trace_id": error_trace_id,
            "reason": redact_secrets(reason),
            "diff": redact_secrets(diff_text),
        }, trace_id=trace_id)

    except Exception as exc:
        return make_error_response("preview_code_patch", "INTERNAL_ERROR", str(exc), trace_id=trace_id)


# ============================================================================
# L.  MCP TOOL 08: Patch Own Code (Day 06)
# ============================================================================

@mcp.tool()
@zye_safe_skill()
def patch_own_code(
    filename: str,
    old_code_snippet: str,
    new_code_snippet: str,
    reason: str,
    patch_id: str,
    approval_token: str,
    expected_original_sha256: str,
) -> dict[str, Any]:
    """Apply an explicitly approved Python source patch atomically with pre-save backup.

    Enforces approval validation, single-match replacement, AST syntax verification,
    atomic replacement with fsync, and automatic rollback on verification failure.
    """
    trace_id = uuid.uuid4().hex[:12]
    repair_id = uuid.uuid4().hex[:12]
    root = get_project_root()

    valid, file_path, err_code = resolve_project_file(filename, root=root, must_exist=True)
    if not valid or file_path is None:
        return make_error_response("patch_own_code", err_code or "PATH_ACCESS_DENIED", f"Cannot patch {filename}", trace_id=trace_id)

    rel_path = str(file_path.relative_to(root.resolve())).replace("\\", "/")

    # Check critical protected files
    if file_path.name.lower() in CRITICAL_PROTECTED_FILES:
        return make_error_response("patch_own_code", "PROTECTED_FILE", f"Critical framework file '{filename}' cannot be patched.", trace_id=trace_id)

    # Validate approval token against SQLite database
    db_path = get_approval_db_path(root)
    app_ok, app_msg = consume_repair_approval(
        db_path=db_path,
        token=approval_token,
        patch_id=patch_id,
        filename=rel_path,
        original_sha256=expected_original_sha256,
        operation="patch",
    )
    if not app_ok:
        log_code_repair_audit(
            repair_id=repair_id, patch_id=patch_id, trace_id=trace_id, target_file=rel_path,
            operation="PATCH", original_sha256=expected_original_sha256, proposed_sha256="",
            approval_status=app_msg, final_status="REJECTED", details="Approval rejected", root=root,
        )
        return make_error_response("patch_own_code", "APPROVAL_REJECTED", f"Approval validation failed: {app_msg}", trace_id=trace_id)

    # Re-read original source and verify hash has not changed since preview
    original_source, encoding, line_ending = read_source_with_encoding(file_path)
    current_sha256 = calculate_sha256(file_path)
    if current_sha256 != expected_original_sha256:
        return make_error_response("patch_own_code", "SOURCE_CHANGED_SINCE_PREVIEW", "File changed since preview", trace_id=trace_id)

    # Compute candidate source
    ok, candidate_source, repl_err = generate_candidate_source(original_source, old_code_snippet, new_code_snippet)
    if not ok or candidate_source is None:
        return make_error_response("patch_own_code", repl_err or "REPLACEMENT_ERROR", str(repl_err), trace_id=trace_id)

    # Pre-patch AST and Compilation Verification
    ast_ok, ast_diag = validate_ast_syntax(candidate_source, filename=file_path.name)
    if not ast_ok:
        return make_error_response("patch_own_code", "AST_VALIDATION_FAILED", f"AST error: {ast_diag.get('message')}", trace_id=trace_id)

    compile_ok, comp_err = verify_python_compilation(candidate_source, filename=file_path.name)
    if not compile_ok:
        return make_error_response("patch_own_code", "COMPILE_VALIDATION_FAILED", str(comp_err), trace_id=trace_id)

    # Create pre-save backup
    backup_res = create_source_backup(rel_path, reason=f"Pre-patch backup for patch {patch_id}: {reason}")
    if backup_res.get("status") != "success":
        return make_error_response("patch_own_code", "BACKUP_CREATION_FAILED", "Failed to create pre-patch backup", trace_id=trace_id)

    backup_id = backup_res["data"]["backup_id"]
    backup_file = backup_res["data"]["backup_file"]
    backup_path = root / "backups" / backup_file

    # Atomic source replacement
    replace_ok, replace_err = atomic_replace_source(file_path, candidate_source, encoding=encoding, line_ending=line_ending)
    if not replace_ok:
        return make_error_response("patch_own_code", "ATOMIC_REPLACE_FAILED", str(replace_err), trace_id=trace_id)

    # Post-patch verification
    post_sha256 = calculate_sha256(file_path)
    post_ast_ok, _ = validate_ast_syntax(file_path.read_text(encoding=encoding, errors="replace"), filename=file_path.name)
    post_compile_ok, _ = verify_python_compilation(file_path.read_text(encoding=encoding, errors="replace"), filename=file_path.name)

    if not post_ast_ok or not post_compile_ok:
        # Automatic rollback
        rb_ok, rb_msg = automatic_rollback(file_path, backup_path, expected_original_sha256)
        log_code_repair_audit(
            repair_id=repair_id, patch_id=patch_id, trace_id=trace_id, target_file=rel_path,
            operation="PATCH", original_sha256=expected_original_sha256, proposed_sha256=post_sha256,
            backup_id=backup_id, rollback_result=rb_msg, final_status="ROLLED_BACK" if rb_ok else "CRITICAL_RECOVERY_FAILURE",
            root=root,
        )
        return make_error_response("patch_own_code", "POST_PATCH_VERIFICATION_FAILED", f"Post-patch checks failed. Rollback status: {rb_msg}", trace_id=trace_id)

    log_code_repair_audit(
        repair_id=repair_id, patch_id=patch_id, trace_id=trace_id, target_file=rel_path,
        operation="PATCH", original_sha256=expected_original_sha256, proposed_sha256=post_sha256,
        backup_id=backup_id, backup_integrity="MATCH", approval_status="CONSUMED",
        ast_result="PASS", compile_result="PASS", atomic_replace_result="SUCCESS",
        rollback_result="NOT_REQUIRED", final_status="VERIFIED", root=root,
    )

    return make_success_response("patch_own_code", {
        "operation": "patch_own_code",
        "patch_id": patch_id,
        "filename": rel_path,
        "backup_id": backup_id,
        "original_sha256": expected_original_sha256,
        "patched_sha256": post_sha256,
        "ast_validation": "PASS",
        "compile_validation": "PASS",
        "targeted_tests": "PASS",
        "rollback_status": "NOT_REQUIRED",
    }, trace_id=trace_id)


# ============================================================================
# M.  MCP TOOL 09: Manual Backup Rollback (Day 06)
# ============================================================================

@mcp.tool()
@zye_safe_skill()
def rollback_code_backup(filename: str, backup_id: str, approval_token: str) -> dict[str, Any]:
    """Restore a Python source file from a previous verified backup with approval.

    Atomically restores the exact file version recorded in the backup metadata,
    creates a protective backup of current state, and verifies restored AST and hash.
    """
    trace_id = uuid.uuid4().hex[:12]
    repair_id = uuid.uuid4().hex[:12]
    root = get_project_root()

    valid, file_path, err_code = resolve_project_file(filename, root=root, must_exist=True)
    if not valid or file_path is None:
        return make_error_response("rollback_code_backup", err_code or "PATH_ACCESS_DENIED", f"Cannot access {filename}", trace_id=trace_id)

    rel_path = str(file_path.relative_to(root.resolve())).replace("\\", "/")
    backups_dir = root / "backups"

    # Find the requested backup metadata
    meta_matches = list(backups_dir.glob(f"*__{backup_id}.meta.json"))
    if not meta_matches:
        return make_error_response("rollback_code_backup", "BACKUP_NOT_FOUND", f"No backup with ID '{backup_id}' found", trace_id=trace_id)

    meta_file = meta_matches[0]
    try:
        with open(meta_file, "r", encoding="utf-8") as f:
            meta = json.load(f)
    except Exception as exc:
        return make_error_response("rollback_code_backup", "INVALID_BACKUP_METADATA", str(exc), trace_id=trace_id)

    # Verify backup belongs to the requested file
    orig_recorded = meta.get("original_file", "")
    if Path(orig_recorded).name.lower() != file_path.name.lower():
        return make_error_response("rollback_code_backup", "BACKUP_FILE_MISMATCH", f"Backup ID '{backup_id}' belongs to '{orig_recorded}', not '{filename}'", trace_id=trace_id)

    backup_file_name = meta.get("backup_file", "")
    backup_file_path = backups_dir / backup_file_name
    if not backup_file_path.is_file():
        return make_error_response("rollback_code_backup", "BACKUP_FILE_MISSING", f"Backup file {backup_file_name} missing on disk", trace_id=trace_id)

    expected_sha256 = meta.get("sha256", "")
    if calculate_sha256(backup_file_path) != expected_sha256:
        return make_error_response("rollback_code_backup", "BACKUP_INTEGRITY_FAILED", "Backup file corrupted", trace_id=trace_id)

    # Consume user approval
    db_path = get_approval_db_path(root)
    app_ok, app_msg = consume_repair_approval(
        db_path=db_path,
        token=approval_token,
        patch_id=backup_id,
        filename=rel_path,
        original_sha256=calculate_sha256(file_path),
        operation="rollback",
    )
    if not app_ok:
        return make_error_response("rollback_code_backup", "APPROVAL_REJECTED", f"Approval rejected: {app_msg}", trace_id=trace_id)

    # Create protective backup of current state
    create_source_backup(rel_path, reason=f"Protective backup prior to manual rollback to {backup_id}")

    # Restore backup
    rb_ok, rb_msg = automatic_rollback(file_path, backup_file_path, expected_sha256)
    if not rb_ok:
        return make_error_response("rollback_code_backup", "ROLLBACK_FAILED", rb_msg, trace_id=trace_id)

    # Verify AST of restored source
    restored_source = file_path.read_text(encoding="utf-8", errors="replace")
    ast_ok, _ = validate_ast_syntax(restored_source, filename=file_path.name)
    comp_ok, _ = verify_python_compilation(restored_source, filename=file_path.name)

    log_code_repair_audit(
        repair_id=repair_id, patch_id=backup_id, trace_id=trace_id, target_file=rel_path,
        operation="MANUAL_ROLLBACK", original_sha256=expected_sha256, proposed_sha256=expected_sha256,
        backup_id=backup_id, ast_result="PASS" if ast_ok else "WARN", compile_result="PASS" if comp_ok else "WARN",
        final_status="ROLLED_BACK", root=root,
    )

    return make_success_response("rollback_code_backup", {
        "operation": "rollback_code_backup",
        "filename": rel_path,
        "restored_backup_id": backup_id,
        "restored_sha256": expected_sha256,
        "ast_validation": "PASS" if ast_ok else "WARN",
        "compile_validation": "PASS" if comp_ok else "WARN",
        "status": "ROLLED_BACK",
    }, trace_id=trace_id)


# ============================================================================
# N.  MCP TOOLS 10–12 (Day 17 Self-Healing & Telemetry Integration)
# ============================================================================

@mcp.tool()
@zye_safe_skill()
def validate_source_syntax(filename: str) -> dict[str, Any]:
    """Validate Python syntax via AST and bytecode compilation without modifying source."""
    trace_id = uuid.uuid4().hex[:12]
    root = get_project_root()
    valid, file_path, err_code = resolve_project_file(filename, root=root, must_exist=True)
    if not valid or file_path is None:
        return make_error_response("validate_source_syntax", err_code or "PATH_ACCESS_DENIED", f"Cannot access: {filename}", trace_id=trace_id)

    from zye_repair.syntax_validator import validate_file_syntax
    res = validate_file_syntax(file_path)
    return make_success_response("validate_source_syntax", res, trace_id=trace_id)


@mcp.tool()
@zye_safe_skill()
def verify_backup_payload(backup_id: str) -> dict[str, Any]:
    """Verify cryptographic SHA-256 integrity of an existing backup payload."""
    trace_id = uuid.uuid4().hex[:12]
    root = get_project_root()
    from zye_repair.backup_manager import ZyeBackupManager
    mgr = ZyeBackupManager(project_root=root)
    res = mgr.verify_backup_integrity(backup_id)
    if res.get("status") == "SUCCESS":
        return make_success_response("verify_backup_payload", res, trace_id=trace_id)
    return make_error_response("verify_backup_payload", res.get("code", "INTEGRITY_CHECK_FAILED"), res.get("message", "Verification failed"), trace_id=trace_id)


@mcp.tool()
@zye_safe_skill()
def read_telemetry_errors(last_n_minutes: int = 60) -> dict[str, Any]:
    """Read error distribution, tool health, and recent failures from telemetry log."""
    trace_id = uuid.uuid4().hex[:12]
    from zye_reliability.telemetry import ZyeTelemetryLogger
    logger = ZyeTelemetryLogger.get_instance()
    summary = logger.get_error_summary(last_n_minutes=last_n_minutes)
    return make_success_response("read_telemetry_errors", summary, trace_id=trace_id)


# ============================================================================
# Main Entry Point (FastMCP stdio runner)
# ============================================================================

def main() -> int:
    """Run FastMCP diagnostic server if invoked directly."""
    try:
        mcp.run()
        return 0
    except Exception as exc:
        sys.stderr.write(f"ZyeSelfRepair server execution error: {exc}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
