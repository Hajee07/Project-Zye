"""
Zye AI — Python Syntax & Compilation Verification Engine (Day 17).
Performs AST parsing, static compilation checks, and syntax diagnostics
without executing arbitrary model-generated Python code.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, Optional, Tuple


def validate_python_ast(source_code: str, filename: str = "<source>") -> Tuple[bool, dict[str, Any]]:
    """Validate Python code via AST parsing without execution."""
    try:
        ast.parse(source_code, filename=filename, type_comments=True)
        return True, {"status": "PASS", "details": "AST parsed successfully"}
    except (SyntaxError, IndentationError) as err:
        return False, {
            "status": "FAIL",
            "error_type": type(err).__name__,
            "line_number": err.lineno,
            "column_offset": err.offset,
            "message": getattr(err, "msg", str(err)),
        }
    except Exception as exc:
        return False, {
            "status": "FAIL",
            "error_type": type(exc).__name__,
            "message": str(exc),
        }


def validate_python_compile(source_code: str, filename: str = "<source>") -> Tuple[bool, Optional[str]]:
    """Verify that source code compiles to bytecode."""
    try:
        compile(source_code, filename, "exec", dont_inherit=True)
        return True, None
    except Exception as exc:
        return False, str(exc)


def validate_file_syntax(file_path: Path) -> dict[str, Any]:
    """Inspect and validate the Python syntax of an on-disk file."""
    if not file_path.is_file():
        return {
            "status": "ERROR",
            "code": "FILE_NOT_FOUND",
            "message": f"File does not exist: {file_path}",
        }

    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
        ast_ok, ast_diag = validate_python_ast(content, filename=file_path.name)
        comp_ok, comp_err = validate_python_compile(content, filename=file_path.name)

        return {
            "status": "PASS" if (ast_ok and comp_ok) else "FAIL",
            "filename": file_path.name,
            "ast_valid": ast_ok,
            "compile_valid": comp_ok,
            "ast_diagnostics": ast_diag,
            "compile_error": comp_err,
        }
    except Exception as exc:
        return {
            "status": "ERROR",
            "code": "INSPECTION_FAILED",
            "message": str(exc),
        }


def full_validation(source_code: str, filename: str = "<source>") -> dict[str, Any]:
    """Execute complete validation suite across AST and bytecode compilation."""
    ast_ok, ast_diag = validate_python_ast(source_code, filename=filename)
    comp_ok, comp_err = validate_python_compile(source_code, filename=filename)

    passed = ast_ok and comp_ok
    return {
        "valid": passed,
        "ast_ok": ast_ok,
        "compile_ok": comp_ok,
        "ast_diagnostics": ast_diag,
        "compile_error": comp_err,
    }
