"""
Hyperlink Engine — Zye Day 21.
Validates URLs against dangerous schemes and manages document hyperlinks.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
import urllib.parse

from zye_office.word.word_adapter import WordAdapter
from zye_office.word.word_errors import WordNoActiveDocumentError, WordSecurityError
from zye_office.word.word_validator import WordValidator

logger = logging.getLogger("zye.office.word.hyperlinks")

SAFE_URL_SCHEMES = frozenset({"http", "https", "mailto"})


class WordHyperlinkEngine:
    """Safely validates and inserts hyperlinks into Microsoft Word documents."""

    def __init__(
        self,
        adapter: Optional[WordAdapter] = None,
        validator: Optional[WordValidator] = None,
    ) -> None:
        self.adapter = adapter or WordAdapter()
        self.validator = validator or WordValidator()

    def validate_url(self, url: str) -> str:
        """Verifies URL scheme is in allowlist and blocks dangerous protocols."""
        clean_url = (url or "").strip()
        parsed = urllib.parse.urlparse(clean_url)
        scheme = parsed.scheme.lower()
        if scheme not in SAFE_URL_SCHEMES:
            raise WordSecurityError(
                code="WORD_UNSAFE_HYPERLINK",
                message=f"URL scheme '{scheme}' is blocked. Allowed schemes: {sorted(list(SAFE_URL_SCHEMES))}",
            )
        return clean_url

    def insert_hyperlink(
        self,
        display_text: str = "",
        url: str = "",
        address: Optional[str] = None,
        text: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Inserts an allowlisted hyperlink with display text at current selection."""
        eff_url = address or url
        eff_display = text or display_text
        valid_url = self.validate_url(eff_url)
        clean_display = self.validator.validate_unicode_text(eff_display)

        def _sta_link() -> Dict[str, Any]:
            app = self.adapter.get_raw_app()
            doc = self.adapter.get_active_document_raw()
            if doc is None:
                raise WordNoActiveDocumentError()

            rng = app.Selection.Range
            doc.Hyperlinks.Add(
                Anchor=rng,
                Address=valid_url,
                TextToDisplay=clean_display,
            )

            return {
                "status": "SUCCESS",
                "display_text": clean_display,
                "url": valid_url,
                "address": valid_url,
                "message": f"Hyperlink '{clean_display}' inserted.",
            }

        return self.adapter.worker.run(_sta_link)

    def get_document_hyperlinks(self) -> Dict[str, Any]:
        """Returns all hyperlinks embedded in the active document."""
        def _sta_get_links() -> Dict[str, Any]:
            doc = self.adapter.get_active_document_raw()
            if doc is None:
                raise WordNoActiveDocumentError()

            links = []
            hl_coll = doc.Hyperlinks
            hl_count = getattr(hl_coll, "Count", len(hl_coll) if isinstance(hl_coll, (list, tuple)) else 0)
            for i in range(1, hl_count + 1):
                try:
                    h = hl_coll(i) if callable(hl_coll) else (hl_coll[i-1] if isinstance(hl_coll, (list, tuple)) else getattr(hl_coll, str(i), None))
                    links.append({
                        "index": i,
                        "text": getattr(h, "TextToDisplay", ""),
                        "address": getattr(h, "Address", ""),
                    })
                except Exception:
                    pass

            return {"status": "SUCCESS", "count": len(links), "hyperlinks": links}

        return self.adapter.worker.run(_sta_get_links)
