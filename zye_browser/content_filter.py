"""
Content Filtering Engine — Day 24.
Filters extracted text by specific criteria: urgent only, action items, financial/invoices, or keywords.
"""

from __future__ import annotations

import re
from typing import List, Optional


class ContentFilter:
    """Filters extracted document text into focused segments."""

    URGENT_KEYWORDS = [
        "urgent", "asap", "deadline", "immediate", "action required", "priority",
        "emergency", "due today", "due tomorrow", "critical", "அவசரம்", "உடனடியாக"
    ]

    ACTION_KEYWORDS = [
        "please send", "action required", "please submit", "to do", "todo",
        "action item", "please review", "please approve", "kindly update",
        "steps to take", "task:", "follow up", "அனுப்பு", "சரிபார்"
    ]

    FINANCE_KEYWORDS = [
        "$", "₹", "rs.", "eur", "usd", "inr", "invoice", "receipt", "total amount",
        "due date", "billing", "subtotal", "payment", "balance due", "statement"
    ]

    @classmethod
    def filter_urgent(cls, text: str) -> str:
        """Filter text paragraphs containing urgency keywords."""
        paragraphs = text.split("\n\n")
        matched = []
        for p in paragraphs:
            p_lower = p.lower()
            if any(k in p_lower for k in cls.URGENT_KEYWORDS):
                matched.append(p.strip())
        return "\n\n".join(matched) if matched else "No urgent items detected in extracted content."

    @classmethod
    def filter_action_items(cls, text: str) -> str:
        """Filter text paragraphs containing action items or tasks."""
        paragraphs = text.split("\n\n")
        matched = []
        for p in paragraphs:
            p_lower = p.lower()
            if any(k in p_lower for k in cls.ACTION_KEYWORDS) or p.strip().startswith("- [ ]"):
                matched.append(p.strip())
        return "\n\n".join(matched) if matched else "No explicit action items detected in extracted content."

    @classmethod
    def filter_finance_and_invoices(cls, text: str) -> str:
        """Filter paragraphs containing financial or invoice details."""
        paragraphs = text.split("\n\n")
        matched = []
        for p in paragraphs:
            p_lower = p.lower()
            if any(k in p_lower for k in cls.FINANCE_KEYWORDS) or re.search(r"\b\d+[\.,]\d{2}\b", p):
                matched.append(p.strip())
        return "\n\n".join(matched) if matched else "No invoice or financial figures detected in extracted content."

    @classmethod
    def filter_by_keywords(cls, text: str, keywords: List[str]) -> str:
        """Filter paragraphs containing any of the specified keywords."""
        if not keywords:
            return text

        clean_keys = [k.strip().lower() for k in keywords if k.strip()]
        paragraphs = text.split("\n\n")
        matched = []
        for p in paragraphs:
            p_lower = p.lower()
            if any(k in p_lower for k in clean_keys):
                matched.append(p.strip())
        return "\n\n".join(matched) if matched else f"No paragraphs matched keywords: {', '.join(keywords)}"
