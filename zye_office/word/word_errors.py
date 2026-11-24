"""
Structured Error Taxonomy for Microsoft Word Automation — Zye Day 21.
Inherits from ZyeOfficeError and provides domain-specific error codes and formatters.
"""

from __future__ import annotations

from typing import Any, Optional
from zye_office.errors import ZyeOfficeError


class WordAutomationError(ZyeOfficeError):
    """Base exception for all Microsoft Word automation failures."""

    def __init__(
        self,
        code: str = "WORD_AUTOMATION_ERROR",
        message: str = "",
        operation_id: Optional[str] = None,
        retryable: bool = False,
        remediation: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        error_code: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        effective_code = error_code or code
        super().__init__(
            code=effective_code,
            message=message,
            app_name="word",
            operation_id=operation_id,
            retryable=retryable,
            remediation=remediation,
            details=details,
        )


# Connection & Document State Errors
class WordConnectionError(WordAutomationError):
    def __init__(self, message: str = "Failed to connect to Microsoft Word COM instance.", **kwargs: Any) -> None:
        super().__init__("WORD_CONNECTION_FAILED", message, **kwargs)


class WordNotInstalledError(WordAutomationError):
    def __init__(self, message: str = "Microsoft Word is not installed on this system.", **kwargs: Any) -> None:
        super().__init__("WORD_NOT_INSTALLED", message, **kwargs)


class WordNoActiveDocumentError(WordAutomationError):
    def __init__(self, message: str = "Word has no active document open.", **kwargs: Any) -> None:
        super().__init__("WORD_NO_ACTIVE_DOCUMENT", message, **kwargs)


class WordDocumentNotFoundError(WordAutomationError):
    def __init__(self, message: str = "Specified Word document could not be found.", **kwargs: Any) -> None:
        super().__init__("WORD_DOCUMENT_NOT_FOUND", message, **kwargs)


class WordDocumentProtectedError(WordAutomationError):
    def __init__(self, message: str = "Document is protected against unauthorized editing.", **kwargs: Any) -> None:
        super().__init__("WORD_DOCUMENT_PROTECTED", message, **kwargs)


class WordDocumentReadOnlyError(WordAutomationError):
    def __init__(self, message: str = "Document is opened in read-only mode.", **kwargs: Any) -> None:
        super().__init__("WORD_DOCUMENT_READ_ONLY", message, **kwargs)


class WordDocumentIdentityMismatchError(WordAutomationError):
    def __init__(self, message: str = "Active document changed unexpectedly between inspection and execution.", **kwargs: Any) -> None:
        super().__init__("WORD_DOCUMENT_IDENTITY_MISMATCH", message, **kwargs)


# Content & Formatting Errors
class WordInvalidRangeError(WordAutomationError):
    def __init__(self, message: str = "Requested text range is invalid or out of bounds.", **kwargs: Any) -> None:
        super().__init__("WORD_INVALID_RANGE", message, **kwargs)


class WordTextNotFoundError(WordAutomationError):
    def __init__(self, message: str = "Target text was not found in document.", **kwargs: Any) -> None:
        super().__init__("WORD_TEXT_NOT_FOUND", message, **kwargs)


class WordFormattingError(WordAutomationError):
    def __init__(self, message: str = "Failed to apply requested text or paragraph formatting.", **kwargs: Any) -> None:
        super().__init__("WORD_FORMATTING_FAILED", message, **kwargs)


class WordStyleNotFoundError(WordAutomationError):
    def __init__(self, message: str = "Specified style is not available in document.", **kwargs: Any) -> None:
        super().__init__("WORD_STYLE_NOT_FOUND", message, **kwargs)


# Tables & Layout Errors
class WordInvalidTableError(WordAutomationError):
    def __init__(self, message: str = "Table index or table reference is invalid.", **kwargs: Any) -> None:
        super().__init__("WORD_INVALID_TABLE", message, **kwargs)


class WordTableSizeExceededError(WordAutomationError):
    def __init__(self, message: str = "Table dimensions exceed configured safety limits.", **kwargs: Any) -> None:
        super().__init__("WORD_TABLE_SIZE_EXCEEDED", message, **kwargs)


class WordLayoutOperationError(WordAutomationError):
    def __init__(self, message: str = "Page layout or section modification failed.", **kwargs: Any) -> None:
        super().__init__("WORD_LAYOUT_OPERATION_FAILED", message, **kwargs)


# Review & Mail Merge Errors
class WordRevisionNotFoundError(WordAutomationError):
    def __init__(self, message: str = "Revision index was not found.", **kwargs: Any) -> None:
        super().__init__("WORD_REVISION_NOT_FOUND", message, **kwargs)


class WordRevisionConfirmationRequiredError(WordAutomationError):
    def __init__(self, message: str = "Bulk revision acceptance/rejection requires explicit user confirmation.", **kwargs: Any) -> None:
        super().__init__("WORD_REVISION_CONFIRMATION_REQUIRED", message, **kwargs)


class WordMailMergeError(WordAutomationError):
    def __init__(self, code: str = "WORD_MERGE_EXECUTION_FAILED", message: str = "Mail merge operation failed.", **kwargs: Any) -> None:
        super().__init__(code, message, **kwargs)


# Security Errors
class WordSecurityError(WordAutomationError):
    def __init__(self, code: str = "WORD_UNAUTHORIZED_OPERATION", message: str = "Security policy violation.", **kwargs: Any) -> None:
        super().__init__(code, message, **kwargs)


class WordValidationError(WordAutomationError):
    def __init__(self, message: str = "Input validation failed for Word operation.", code: str = "WORD_VALIDATION_FAILED", **kwargs: Any) -> None:
        super().__init__(code, message, **kwargs)


def format_word_error(
    code_or_exc: Any,
    message: Optional[str] = None,
    operation_id: Optional[str] = None,
    document_name: Optional[str] = None,
    retryable: bool = False,
    remediation: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Helper to generate structured error dictionary directly without throwing unhandled exceptions."""
    if isinstance(code_or_exc, Exception):
        code = getattr(code_or_exc, "code", "WORD_AUTOMATION_ERROR")
        msg = str(code_or_exc) if not message else message
        op_id = getattr(code_or_exc, "operation_id", operation_id)
        ret = getattr(code_or_exc, "retryable", retryable)
        rem = getattr(code_or_exc, "remediation", remediation)
        det = getattr(code_or_exc, "details", details)
    else:
        code = str(code_or_exc)
        msg = message or ""
        op_id = operation_id
        ret = retryable
        rem = remediation
        det = details

    err = WordAutomationError(
        code=code,
        message=msg,
        operation_id=op_id,
        retryable=ret,
        remediation=rem,
        details=det,
    )
    d = err.to_dict()
    d["error_code"] = code
    if document_name:
        d["document_name"] = document_name
    return d
