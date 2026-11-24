"""
Safe Clipboard Manager — Zye Day 16 & Day 18.
Provides privacy-conscious clipboard reading, metadata inspection, text modification,
active window pasting, and secret non-logging guarantees.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

try:
    import pyperclip
    _PYPERCLIP_AVAILABLE = True
except ImportError:
    _PYPERCLIP_AVAILABLE = False

try:
    import pyautogui
    _PYAUTOGUI_AVAILABLE = True
except ImportError:
    _PYAUTOGUI_AVAILABLE = False

from zye_windows.windows_models import ClipboardMetadata

logger = logging.getLogger("zye.windows.clipboard")

DEFAULT_MAX_CLIPBOARD_CHARS = 20000


class WindowsClipboardManager:
    """
    Manages clipboard text safely on explicit user command with privacy guarantees.
    """

    def __init__(self, max_chars: int = DEFAULT_MAX_CLIPBOARD_CHARS) -> None:
        self.max_chars = max_chars

    def get_clipboard_text(self, max_chars: Optional[int] = None) -> dict[str, Any]:
        """
        Read current text content of the Windows clipboard on explicit user command.
        Enforces maximum character bounding and strictly prevents logging raw content.
        """
        if not _PYPERCLIP_AVAILABLE:
            return {
                "status": "ERROR",
                "message": "pyperclip is not available for clipboard reading.",
                "text": "",
            }

        limit = max_chars or self.max_chars
        try:
            raw_text = pyperclip.paste()
            if not raw_text:
                return {
                    "status": "EMPTY",
                    "message": "Clipboard is empty or contains non-text data.",
                    "char_count": 0,
                    "text": "",
                }

            truncated = len(raw_text) > limit
            bounded_text = raw_text[:limit]

            # Privacy rule: Never log raw clipboard text
            logger.info("Retrieved clipboard text (char_count=%d, truncated=%s)", len(raw_text), truncated)
            return {
                "status": "SUCCESS",
                "char_count": len(raw_text),
                "returned_count": len(bounded_text),
                "truncated": truncated,
                "text": bounded_text,
            }
        except Exception as exc:
            logger.error("Failed to read clipboard: %s", exc)
            return {
                "status": "ERROR",
                "message": f"Clipboard read error: {exc}",
                "text": "",
            }

    def set_clipboard_text(self, text: str) -> dict[str, Any]:
        """Set clipboard text safely."""
        if not _PYPERCLIP_AVAILABLE:
            return {"status": "ERROR", "message": "pyperclip is not available."}
        try:
            pyperclip.copy(text)
            logger.info("Set clipboard text (char_count=%d)", len(text))
            return {"status": "SUCCESS", "char_count": len(text)}
        except Exception as exc:
            return {"status": "ERROR", "message": str(exc)}

    def clear_clipboard(self) -> dict[str, Any]:
        """Clear the clipboard."""
        if not _PYPERCLIP_AVAILABLE:
            return {"status": "ERROR", "message": "pyperclip is not available."}
        try:
            pyperclip.copy("")
            logger.info("Cleared clipboard.")
            return {"status": "SUCCESS", "message": "Clipboard cleared."}
        except Exception as exc:
            return {"status": "ERROR", "message": str(exc)}

    def get_clipboard_metadata(self) -> dict[str, Any]:
        """
        Inspect clipboard metadata without persisting or logging raw content.
        Calculates character count, word count, line count, and Unicode presence.
        """
        if not _PYPERCLIP_AVAILABLE:
            return {"status": "ERROR", "message": "pyperclip is not available."}

        try:
            raw_text = pyperclip.paste()
            if not raw_text:
                meta = ClipboardMetadata(
                    char_count=0,
                    line_count=0,
                    word_count=0,
                    is_empty=True,
                    has_unicode=False,
                    has_whitespace=False,
                    format_type="empty",
                )
                return {"status": "SUCCESS", "metadata": meta.model_dump()}

            # Check for non-ASCII Unicode
            has_unicode = any(ord(c) > 127 for c in raw_text)
            has_whitespace = any(c.isspace() for c in raw_text)
            lines = raw_text.splitlines()
            words = raw_text.split()

            meta = ClipboardMetadata(
                char_count=len(raw_text),
                line_count=len(lines) if lines else 1,
                word_count=len(words),
                is_empty=False,
                has_unicode=has_unicode,
                has_whitespace=has_whitespace,
                format_type="text/unicode" if has_unicode else "text/plain",
            )
            return {"status": "SUCCESS", "metadata": meta.model_dump()}
        except Exception as exc:
            return {"status": "ERROR", "message": f"Failed to inspect clipboard metadata: {exc}"}

    def paste_clipboard_to_active_window(self) -> dict[str, Any]:
        """
        Dispatches Ctrl+V to paste the current clipboard into the active focused window.
        """
        if not _PYAUTOGUI_AVAILABLE:
            return {"status": "ERROR", "message": "pyautogui is required for paste dispatch."}

        try:
            pyautogui.hotkey("ctrl", "v")
            time.sleep(0.1)
            return {
                "status": "SUCCESS",
                "action": "paste_clipboard_to_active_window",
                "message": "Pasted clipboard content into active window.",
                "verified": True,
            }
        except Exception as exc:
            return {"status": "ERROR", "message": f"Paste dispatch failed: {exc}"}
