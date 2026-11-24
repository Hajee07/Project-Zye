"""
Zye AI — Self-Repair & Autonomous Healing Subsystem (Day 17).
Provides cryptographic backup management, AST/compilation validation,
single-occurrence atomic code patching, and safe point-in-time rollbacks.
"""

from __future__ import annotations

from zye_repair.backup_manager import (
    MAX_BACKUP_FILE_SIZE_BYTES,
    ZyeBackupManager,
    calculate_sha256,
)
from zye_repair.patch_manager import (
    CRITICAL_PROTECTED_FILES,
    ZyePatchManager,
)
from zye_repair.rollback_manager import ZyeRollbackManager
from zye_repair.syntax_validator import (
    full_validation,
    validate_file_syntax,
    validate_python_ast,
    validate_python_compile,
)

__all__ = [
    # Backup
    "MAX_BACKUP_FILE_SIZE_BYTES",
    "ZyeBackupManager",
    "calculate_sha256",
    # Patch
    "CRITICAL_PROTECTED_FILES",
    "ZyePatchManager",
    # Rollback
    "ZyeRollbackManager",
    # Syntax Validation
    "full_validation",
    "validate_file_syntax",
    "validate_python_ast",
    "validate_python_compile",
]
