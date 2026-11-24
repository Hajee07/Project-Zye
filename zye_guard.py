#!/usr/bin/env python3
"""
ZYE AI — Safety Guard Engine v1.0
==================================

Universal MCP tool protection framework providing the ``@zye_safe_skill``
decorator.  Automatically enforces:

  1. Function argument validation
  2. Required file existence checks
  3. Windows protected-path detection
  4. Project workspace path containment
  5. Path traversal protection
  6. Symlink escape detection
  7. Structured error responses (JSON)
  8. Synchronous function support
  9. Asynchronous function support
 10. Safe automatic retry (opt-in)
 11. Automatic traceback logging
 12. Secret redaction
 13. Retry attempt tracking
 14. Function signature preservation
 15. MCP FastMCP compatibility

Usage::

    from zye_guard import zye_safe_skill

    @zye_safe_skill(require_files=["input.txt"], allowed_roots=["data"])
    def read_data(path: str) -> dict:
        ...

Dependencies:
    Python 3.11+ standard library only.  No third-party packages required.
"""

from __future__ import annotations

import asyncio
import functools
import inspect
import json
import logging
import os
import re
import sys
import time
import traceback
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Callable, Sequence

# ============================================================================
# A.  Project Root Resolver
# ============================================================================

_PROJECT_ROOT_CACHE: Path | None = None


def get_project_root(start: Path | None = None) -> Path:
    """Locate the Zye project root by walking upward from *start*."""
    global _PROJECT_ROOT_CACHE
    if _PROJECT_ROOT_CACHE is not None:
        return _PROJECT_ROOT_CACHE
    origin = start or Path(__file__).resolve().parent
    current = origin
    for _ in range(5):
        if (current / "zye_config.toml").is_file():
            _PROJECT_ROOT_CACHE = current
            return current
        current = current.parent
    _PROJECT_ROOT_CACHE = origin
    return origin


def _reset_project_root_cache() -> None:
    """Reset the cached project root (used by tests)."""
    global _PROJECT_ROOT_CACHE
    _PROJECT_ROOT_CACHE = None


# ============================================================================
# B.  Protected Windows Path Engine
# ============================================================================

# Windows reserved device names (case-insensitive, with optional extension)
_WINDOWS_RESERVED_NAMES: frozenset[str] = frozenset({
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
})


def _get_protected_windows_dirs() -> list[Path]:
    """Return resolved paths of OS-protected directories from env vars."""
    env_keys = [
        "WINDIR", "SystemRoot",
        "ProgramFiles", "ProgramFiles(x86)",
        "ProgramData", "ProgramW6432",
    ]
    dirs: list[Path] = []
    for key in env_keys:
        val = os.environ.get(key)
        if val:
            try:
                dirs.append(Path(val).resolve())
            except (OSError, ValueError):
                pass
    # Always add common fallbacks
    for fallback in [r"C:\Windows", r"C:\Program Files", r"C:\Program Files (x86)"]:
        try:
            p = Path(fallback).resolve()
            if p not in dirs:
                dirs.append(p)
        except (OSError, ValueError):
            pass
    return dirs


def is_protected_windows_path(target: Path) -> bool:
    """Return True if *target* resides inside a protected OS directory.

    Uses component-aware comparison via ``Path.is_relative_to()`` — not
    string ``startswith()`` — so ``C:\\WindowsBackup`` does **not** match
    ``C:\\Windows``.
    """
    try:
        resolved = target.resolve()
    except (OSError, ValueError):
        return True  # Assume protected if we can't even resolve
    for protected in _get_protected_windows_dirs():
        try:
            if resolved.is_relative_to(protected):
                return True
        except (TypeError, ValueError):
            pass
    return False


# ============================================================================
# C.  Path Validation Engine
# ============================================================================

@dataclass(frozen=True)
class PathValidationResult:
    """Immutable result of a path validation check."""
    valid: bool
    resolved_path: Path | None = None
    violation: str | None = None


def _has_null_bytes(text: str) -> bool:
    return "\x00" in text


def _has_alternate_data_stream(name: str) -> bool:
    """Detect NTFS Alternate Data Streams (extra colons after drive letter)."""
    # Allow drive letter colon like C: but catch file.txt:hidden
    if len(name) >= 2 and name[1] == ":" and name[0].isalpha():
        rest = name[2:]
    else:
        rest = name
    return ":" in rest


def _is_reserved_device_name(name: str) -> bool:
    """Check if a filename matches a Windows reserved device name."""
    stem = Path(name).stem.upper()
    return stem in _WINDOWS_RESERVED_NAMES


def _is_unc_or_device_path(raw: str) -> bool:
    """Detect UNC ``\\\\server`` and device ``\\\\.\\`` or ``\\\\?\\`` paths."""
    return raw.startswith("\\\\") or raw.startswith("//")


def validate_path_components(raw: str) -> PathValidationResult:
    """Check a raw path string for dangerous components.

    Checks for:
      - Null bytes
      - UNC / device paths (``\\\\``, ``//``)
      - Alternate Data Streams (extra ``:`` beyond drive letter)
      - Reserved device names (CON, PRN, NUL, COM1–COM9, LPT1–LPT9)
    """
    if _has_null_bytes(raw):
        return PathValidationResult(False, violation="Path contains null byte")

    if _is_unc_or_device_path(raw):
        return PathValidationResult(False, violation=f"UNC or device path blocked: {raw[:30]}")

    # Check each component
    parts = Path(raw).parts
    for part in parts:
        if _has_alternate_data_stream(part):
            return PathValidationResult(False, violation=f"Alternate Data Stream detected in: {part}")
        if _is_reserved_device_name(part):
            return PathValidationResult(False, violation=f"Reserved device name blocked: {part}")

    return PathValidationResult(True, resolved_path=Path(raw))


def is_path_within_root(target: Path, root: Path) -> bool:
    """Return True if *target* resolves to a location inside *root*.

    Uses ``Path.is_relative_to()`` on resolved paths — component-aware.
    """
    try:
        return target.resolve().is_relative_to(root.resolve())
    except (OSError, ValueError):
        return False


def resolve_safe_path(raw: str, root: Path | None = None) -> PathValidationResult:
    """Full path resolution with all safety checks.

    1. Component validation (null, UNC, ADS, reserved names)
    2. Resolve the path
    3. Traversal protection (must stay within root)
    4. Symlink escape detection
    5. Protected Windows path check
    """
    if root is None:
        root = get_project_root()

    # Step 1: component validation
    comp_result = validate_path_components(raw)
    if not comp_result.valid:
        return comp_result

    # Step 2: resolve
    try:
        target = Path(raw)
        if not target.is_absolute():
            target = root / target
        resolved = target.resolve()
    except (OSError, ValueError) as exc:
        return PathValidationResult(False, violation=f"Path resolution failed: {exc}")

    # Step 3: traversal protection
    if not resolved.is_relative_to(root.resolve()):
        return PathValidationResult(
            False,
            resolved_path=resolved,
            violation=f"Path escapes project root: {resolved}",
        )

    # Step 4: symlink escape detection
    try:
        if target.exists() and target.is_symlink():
            link_target = target.resolve(strict=True)
            if not link_target.is_relative_to(root.resolve()):
                return PathValidationResult(
                    False,
                    resolved_path=resolved,
                    violation=f"Symlink escapes project root: {target} -> {link_target}",
                )
    except (OSError, ValueError):
        pass  # If we can't stat, skip symlink check

    # Step 5: protected path check
    if is_protected_windows_path(resolved):
        return PathValidationResult(
            False,
            resolved_path=resolved,
            violation=f"Target is inside a protected Windows directory: {resolved}",
        )

    return PathValidationResult(True, resolved_path=resolved)


def validate_safe_path(raw: str, root: Path | None = None) -> PathValidationResult:
    """Alias for ``resolve_safe_path`` — validates and resolves a raw path string."""
    return resolve_safe_path(raw, root)


def validate_required_path(raw: str, root: Path | None = None) -> PathValidationResult:
    """Like ``resolve_safe_path`` but also verifies the file exists."""
    result = resolve_safe_path(raw, root)
    if not result.valid:
        return result
    if result.resolved_path is None or not result.resolved_path.exists():
        return PathValidationResult(
            False,
            resolved_path=result.resolved_path,
            violation=f"Required file does not exist: {raw}",
        )
    return result


def validate_allowed_root(raw: str, allowed_roots: Sequence[str], root: Path | None = None) -> PathValidationResult:
    """Validate the path is safe AND is inside one of the allowed sub-directories."""
    if root is None:
        root = get_project_root()
    result = resolve_safe_path(raw, root)
    if not result.valid:
        return result
    if not allowed_roots:
        return result  # No restriction
    resolved = result.resolved_path
    assert resolved is not None
    for allowed in allowed_roots:
        allowed_dir = (root / allowed).resolve()
        try:
            if resolved.is_relative_to(allowed_dir):
                return result
        except (TypeError, ValueError):
            pass
    allowed_str = ", ".join(allowed_roots)
    return PathValidationResult(
        False,
        resolved_path=resolved,
        violation=f"Path not in allowed roots ({allowed_str}): {resolved}",
    )


# ============================================================================
# D.  Input Validation Engine
# ============================================================================

def validate_function_arguments(func: Callable, args: tuple, kwargs: dict) -> str | None:
    """Validate that the provided arguments bind to *func*'s signature.

    Returns ``None`` on success or an error message string on failure.
    """
    try:
        sig = inspect.signature(func)
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()
        return None
    except TypeError as exc:
        return f"Argument validation failed: {exc}"


# ============================================================================
# E.  Structured Error Formatter
# ============================================================================

@dataclass
class GuardErrorResponse:
    """Structured JSON error response returned by ``@zye_safe_skill``."""
    status: str = "error"
    code: str = "GUARD_ERROR"
    reason: str = ""
    next_step: str = ""
    retryable: bool = False
    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    attempt: int = 0
    max_retries: int = 0
    tanglish_message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


def build_error_response(
    code: str,
    reason: str,
    *,
    next_step: str = "",
    retryable: bool = False,
    trace_id: str | None = None,
    attempt: int = 0,
    max_retries: int = 0,
    tanglish_message: str = "",
) -> dict[str, Any]:
    """Build a structured error dict ready for JSON serialization."""
    return GuardErrorResponse(
        code=code,
        reason=reason,
        next_step=next_step,
        retryable=retryable,
        trace_id=trace_id or uuid.uuid4().hex[:12],
        attempt=attempt,
        max_retries=max_retries,
        tanglish_message=tanglish_message,
    ).to_dict()


# ============================================================================
# F.  Secret Redaction Engine
# ============================================================================

_SECRET_PATTERNS: list[tuple[re.Pattern, str]] = [
    # Google AI Studio / Gemini API key
    (re.compile(r'AIza[0-9A-Za-z_-]{35}'), '[REDACTED_GEMINI_KEY]'),
    # OpenAI / Anthropic bearer tokens
    (re.compile(r'sk-[a-zA-Z0-9_-]{20,}'), '[REDACTED_API_KEY]'),
    # Key-value assignments
    (re.compile(
        r'(?i)(api[_-]?key|token|password|secret|auth|credential)\s*[:=]\s*["\']?[^\s"\']+["\']?'
    ), r'\1=[REDACTED]'),
]

# Collect env vars whose names look secret
_SECRET_ENV_VALUES: set[str] = set()


def _refresh_secret_env_values() -> None:
    """Scan environment for vars whose names suggest secrets."""
    global _SECRET_ENV_VALUES
    secret_names = {"GEMINI_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
                    "AUTH_TOKEN", "SECRET_KEY", "DATABASE_PASSWORD"}
    vals: set[str] = set()
    for name in secret_names:
        val = os.environ.get(name)
        if val and len(val) > 8 and val != f"your_{name.lower()}_here":
            vals.add(val)
    _SECRET_ENV_VALUES = vals


def redact_secrets(text: str) -> str:
    """Remove known API key patterns, passwords, and env-var secrets from *text*."""
    if not text:
        return ""
    for pattern, replacement in _SECRET_PATTERNS:
        text = pattern.sub(replacement, text)
    for secret_val in _SECRET_ENV_VALUES:
        if secret_val in text:
            text = text.replace(secret_val, "[REDACTED_ENV_SECRET]")
    return text


# ============================================================================
# G.  Traceback Logger
# ============================================================================

_GUARD_LOGGER: logging.Logger | None = None


def _get_guard_logger() -> logging.Logger:
    """Return a configured logger for guard tracebacks (singleton)."""
    global _GUARD_LOGGER
    if _GUARD_LOGGER is not None:
        return _GUARD_LOGGER

    logger = logging.getLogger("zye_guard")

    # Remove existing handlers to avoid duplicates
    for h in list(logger.handlers):
        try:
            h.close()
        except Exception:
            pass
        logger.removeHandler(h)

    root = get_project_root()
    logs_dir = root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    err_log = logs_dir / "zye_errors.log"

    try:
        handler = RotatingFileHandler(
            err_log, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8",
        )
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
            '"module": "%(name)s", "message": "%(message)s"}'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    except Exception:
        # Fall back to NullHandler if we can't write
        logger.addHandler(logging.NullHandler())

    logger.setLevel(logging.INFO)
    _GUARD_LOGGER = logger
    return logger


def _reset_guard_logger() -> None:
    """Close and reset the guard logger (used by tests)."""
    global _GUARD_LOGGER
    if _GUARD_LOGGER is not None:
        for h in list(_GUARD_LOGGER.handlers):
            try:
                h.close()
            except Exception:
                pass
            _GUARD_LOGGER.removeHandler(h)
    _GUARD_LOGGER = None


def log_bug_traceback(
    func_name: str,
    trace_id: str,
    exc: BaseException,
    *,
    attempt: int = 0,
    extra: dict[str, Any] | None = None,
) -> None:
    """Write a redacted traceback entry to ``logs/zye_errors.log``."""
    logger = _get_guard_logger()
    raw_tb = traceback.format_exception(type(exc), exc, exc.__traceback__)
    tb_text = "".join(raw_tb)
    sanitized = redact_secrets(tb_text)
    entry = {
        "event": "guard_traceback",
        "function": func_name,
        "trace_id": trace_id,
        "attempt": attempt,
        "exception_type": type(exc).__name__,
        "exception_message": redact_secrets(str(exc)),
        "traceback": sanitized,
    }
    if extra:
        entry["extra"] = {k: redact_secrets(str(v)) for k, v in extra.items()}
    logger.error(json.dumps(entry))


def log_security_alert(
    func_name: str,
    trace_id: str,
    violation: str,
) -> None:
    """Write a security alert to ``logs/zye_security_alerts.log``."""
    root = get_project_root()
    alert_path = root / "logs" / "zye_security_alerts.log"
    alert_path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": "security_violation",
        "function": func_name,
        "trace_id": trace_id,
        "violation": redact_secrets(violation),
    }
    try:
        with open(alert_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


# ============================================================================
# H/I/J.  Sync & Async Wrapper + Retry Engine
# ============================================================================

# Default retry configuration
DEFAULT_RETRY_MAX = 3
DEFAULT_RETRY_BASE_DELAY = 0.8
DEFAULT_RETRY_MAX_DELAY = 30.0
DEFAULT_RETRYABLE_EXCEPTIONS: tuple[type[BaseException], ...] = (
    ConnectionError,
    TimeoutError,
    OSError,
)


def _should_retry(
    exc: BaseException,
    retry_safe: bool,
    retryable_exceptions: tuple[type[BaseException], ...],
    attempt: int,
    max_retries: int,
) -> bool:
    """Decide whether to retry after an exception."""
    if not retry_safe:
        return False
    if attempt >= max_retries:
        return False
    return isinstance(exc, retryable_exceptions)


def _compute_delay(attempt: int, base: float, max_delay: float) -> float:
    """Exponential backoff: ``base * 2^attempt`` capped at *max_delay*."""
    return min(base * (2 ** attempt), max_delay)


async def _async_sleep(delay: float) -> None:
    """Sleep asynchronously if an event loop is running, else fallback to time.sleep."""
    loop = None
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        pass
    if loop is not None and loop.is_running():
        await asyncio.sleep(delay)
    else:
        time.sleep(delay)


def _build_sync_wrapper(
    func: Callable,
    *,
    require_files: Sequence[str],
    allowed_roots: Sequence[str],
    retry_safe: bool,
    max_retries: int,
    retry_base_delay: float,
    retry_max_delay: float,
    retryable_exceptions: tuple[type[BaseException], ...],
    path_params: Sequence[str],
    timeout_seconds: float | None = None,
) -> Callable:
    """Create the synchronous execution wrapper."""

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        trace_id = uuid.uuid4().hex[:12]
        root = get_project_root()

        # --- Input validation ---
        err_msg = validate_function_arguments(func, args, kwargs)
        if err_msg:
            return build_error_response(
                "INVALID_ARGUMENTS", err_msg,
                trace_id=trace_id,
            )

        # --- Required file checks ---
        for req_file in require_files:
            result = validate_required_path(req_file, root)
            if not result.valid:
                return build_error_response(
                    "REQUIRED_FILE_MISSING",
                    result.violation or f"Required file not found: {req_file}",
                    trace_id=trace_id,
                )

        # --- Path parameter validation ---
        if path_params:
            sig = inspect.signature(func)
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            for pname in path_params:
                if pname in bound.arguments:
                    raw_path = str(bound.arguments[pname])
                    if allowed_roots:
                        result = validate_allowed_root(raw_path, allowed_roots, root)
                    else:
                        result = resolve_safe_path(raw_path, root)
                    if not result.valid:
                        violation = result.violation or "Path validation failed"
                        log_security_alert(func.__name__, trace_id, violation)
                        return build_error_response(
                            "PATH_SECURITY_VIOLATION",
                            violation,
                            trace_id=trace_id,
                        )

        # --- Execute with retry ---
        last_exc: BaseException | None = None
        effective_retries = max_retries if retry_safe else 0

        for attempt in range(effective_retries + 1):
            try:
                if timeout_seconds is not None:
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                        fut = ex.submit(func, *args, **kwargs)
                        return fut.result(timeout=timeout_seconds)
                else:
                    return func(*args, **kwargs)
            except Exception as exc:
                last_exc = exc
                log_bug_traceback(
                    func.__name__, trace_id, exc, attempt=attempt,
                )
                if _should_retry(exc, retry_safe, retryable_exceptions, attempt, effective_retries):
                    delay = _compute_delay(attempt, retry_base_delay, retry_max_delay)
                    time.sleep(delay)
                    continue
                break

        # All retries exhausted or non-retryable
        assert last_exc is not None
        code = "TIMEOUT" if isinstance(last_exc, (TimeoutError, asyncio.TimeoutError)) else "EXECUTION_ERROR"
        return build_error_response(
            code,
            redact_secrets(str(last_exc)),
            retryable=retry_safe and effective_retries > 0,
            trace_id=trace_id,
            attempt=effective_retries,
            max_retries=effective_retries,
            next_step="Check logs/zye_errors.log for full traceback",
        )

    return wrapper


def _build_async_wrapper(
    func: Callable,
    *,
    require_files: Sequence[str],
    allowed_roots: Sequence[str],
    retry_safe: bool,
    max_retries: int,
    retry_base_delay: float,
    retry_max_delay: float,
    retryable_exceptions: tuple[type[BaseException], ...],
    path_params: Sequence[str],
    timeout_seconds: float | None = None,
) -> Callable:
    """Create the asynchronous execution wrapper."""

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        trace_id = uuid.uuid4().hex[:12]
        root = get_project_root()

        # --- Input validation ---
        err_msg = validate_function_arguments(func, args, kwargs)
        if err_msg:
            return build_error_response(
                "INVALID_ARGUMENTS", err_msg,
                trace_id=trace_id,
            )

        # --- Required file checks ---
        for req_file in require_files:
            result = validate_required_path(req_file, root)
            if not result.valid:
                return build_error_response(
                    "REQUIRED_FILE_MISSING",
                    result.violation or f"Required file not found: {req_file}",
                    trace_id=trace_id,
                )

        # --- Path parameter validation ---
        if path_params:
            sig = inspect.signature(func)
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            for pname in path_params:
                if pname in bound.arguments:
                    raw_path = str(bound.arguments[pname])
                    if allowed_roots:
                        result = validate_allowed_root(raw_path, allowed_roots, root)
                    else:
                        result = resolve_safe_path(raw_path, root)
                    if not result.valid:
                        violation = result.violation or "Path validation failed"
                        log_security_alert(func.__name__, trace_id, violation)
                        return build_error_response(
                            "PATH_SECURITY_VIOLATION",
                            violation,
                            trace_id=trace_id,
                        )

        # --- Execute with retry ---
        last_exc: BaseException | None = None
        effective_retries = max_retries if retry_safe else 0

        for attempt in range(effective_retries + 1):
            try:
                if timeout_seconds is not None:
                    return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout_seconds)
                else:
                    return await func(*args, **kwargs)
            except asyncio.CancelledError:
                raise  # Never swallow cancellation
            except Exception as exc:
                last_exc = exc
                log_bug_traceback(
                    func.__name__, trace_id, exc, attempt=attempt,
                )
                if _should_retry(exc, retry_safe, retryable_exceptions, attempt, effective_retries):
                    delay = _compute_delay(attempt, retry_base_delay, retry_max_delay)
                    await _async_sleep(delay)
                    continue
                break

        assert last_exc is not None
        code = "TIMEOUT" if isinstance(last_exc, (TimeoutError, asyncio.TimeoutError)) else "EXECUTION_ERROR"
        return build_error_response(
            code,
            redact_secrets(str(last_exc)),
            retryable=retry_safe and effective_retries > 0,
            trace_id=trace_id,
            attempt=effective_retries,
            max_retries=effective_retries,
            next_step="Check logs/zye_errors.log for full traceback",
        )

    return wrapper


# ============================================================================
# K.  @zye_safe_skill() Decorator
# ============================================================================

def zye_safe_skill(
    *,
    require_files: Sequence[str] = (),
    allowed_roots: Sequence[str] = (),
    path_params: Sequence[str] = (),
    retry_safe: bool = False,
    max_retries: int = DEFAULT_RETRY_MAX,
    retry_base_delay: float = DEFAULT_RETRY_BASE_DELAY,
    retry_max_delay: float = DEFAULT_RETRY_MAX_DELAY,
    retryable_exceptions: tuple[type[BaseException], ...] = DEFAULT_RETRYABLE_EXCEPTIONS,
    timeout_seconds: float | None = None,
) -> Callable:
    """Universal safety decorator for Zye MCP tools.

    Parameters
    ----------
    require_files : sequence of str
        Paths (relative to project root) that must exist before execution.
    allowed_roots : sequence of str
        Sub-directory names (relative to root) the function may access.
    path_params : sequence of str
        Parameter names whose values should be validated as safe paths.
    retry_safe : bool
        Enable automatic retry on transient exceptions (default False).
    max_retries : int
        Maximum retry attempts when ``retry_safe=True``.
    retry_base_delay : float
        Base delay in seconds for exponential backoff.
    retry_max_delay : float
        Maximum delay cap in seconds.
    retryable_exceptions : tuple of exception types
        Exception classes eligible for retry.
    """
    # Refresh environment-based secret detection
    _refresh_secret_env_values()

    def decorator(func: Callable) -> Callable:
        # Validate at decoration time
        if not callable(func):
            raise TypeError(f"zye_safe_skill: expected a callable, got {type(func).__name__}")

        if inspect.iscoroutinefunction(func):
            return _build_async_wrapper(
                func,
                require_files=require_files,
                allowed_roots=allowed_roots,
                retry_safe=retry_safe,
                max_retries=max_retries,
                retry_base_delay=retry_base_delay,
                retry_max_delay=retry_max_delay,
                retryable_exceptions=retryable_exceptions,
                path_params=path_params,
                timeout_seconds=timeout_seconds,
            )
        else:
            return _build_sync_wrapper(
                func,
                require_files=require_files,
                allowed_roots=allowed_roots,
                retry_safe=retry_safe,
                max_retries=max_retries,
                retry_base_delay=retry_base_delay,
                retry_max_delay=retry_max_delay,
                retryable_exceptions=retryable_exceptions,
                path_params=path_params,
                timeout_seconds=timeout_seconds,
            )

    return decorator


# ============================================================================
# Module-Level Exports
# ============================================================================

__all__ = [
    # Decorator
    "zye_safe_skill",
    # Path utilities
    "get_project_root",
    "resolve_safe_path",
    "validate_safe_path",
    "validate_required_path",
    "validate_allowed_root",
    "validate_path_components",
    "is_path_within_root",
    "is_protected_windows_path",
    # Input validation
    "validate_function_arguments",
    # Error formatting
    "build_error_response",
    "GuardErrorResponse",
    # Secret redaction
    "redact_secrets",
    # Logging
    "log_bug_traceback",
    "log_security_alert",
    # Data model
    "PathValidationResult",
    # Internal (for tests)
    "_reset_project_root_cache",
    "_reset_guard_logger",
]
