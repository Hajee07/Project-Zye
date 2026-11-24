"""
Intelligent Search Query Planner & Intent Classifier.
Determines search mode (LOCAL_ONLY, WEB_ONLY, HYBRID, AUTO), parses Tamil/Tanglish/English
queries, preserves technical identifiers, and generates query expansions.
"""

from __future__ import annotations

import enum
import logging
import re
from typing import Any

logger = logging.getLogger("zye.computer_intelligence.search_planner")


class SearchMode(str, enum.Enum):
    LOCAL_ONLY = "local_only"
    WEB_ONLY = "web_only"
    HYBRID = "hybrid"
    AUTO = "auto"


class SearchIntent:
    def __init__(
        self,
        raw_query: str,
        cleaned_query: str,
        mode: SearchMode,
        language: str,
        entities: list[str],
        domain_filters: list[str],
        file_type_filters: list[str],
        time_sensitivity: str = "NORMAL",
        is_comparison: bool = False,
    ) -> None:
        self.raw_query = raw_query
        self.cleaned_query = cleaned_query
        self.mode = mode
        self.language = language
        self.entities = entities
        self.domain_filters = domain_filters
        self.file_type_filters = file_type_filters
        self.time_sensitivity = time_sensitivity
        self.is_comparison = is_comparison

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw_query": self.raw_query,
            "cleaned_query": self.cleaned_query,
            "mode": self.mode.value,
            "language": self.language,
            "entities": self.entities,
            "domain_filters": self.domain_filters,
            "file_type_filters": self.file_type_filters,
            "time_sensitivity": self.time_sensitivity,
            "is_comparison": self.is_comparison,
        }


# Keywords indicative of search mode
LOCAL_TRIGGERS = [
    r"\blocal\b", r"\bmy computer\b", r"\blaptop\b", r"\bennoda\b", r"\benoda\b", r"\ben\b",
    r"\bproject documentation\b", r"\bmy files\b", r"\blocal files\b", r"\bfolder\b",
    r"\bin my code\b", r"\benga irukku\b", r"\bcomputer-la\b", r"\blaptop-la\b",
    r"\bproject-la\b", r"\bdocument-la\b", r"\bexisting\b", r"\bdisk\b",
    r"உள்ளூர்", r"கணினி", r"கோப்பு",
]

WEB_TRIGGERS = [
    r"\bweb\b", r"\binternet\b", r"\bonline\b", r"\bnet\b", r"\bofficial documentation\b",
    r"\blatest release\b", r"\blatest version\b", r"\bwebsite\b", r"\bnews\b",
    r"\bgoogle\b", r"\binternet-la\b", r"\bweb-la\b", r"\bonline-la\b", r"\bnet-la\b",
    r"\bpublic\b", r"\bofficial\b", r"\bdocs\b",
    r"இணையம்", r"இணையத்தில்", r"வலை",
]

COMPARISON_TRIGGERS = [
    r"\bcompare\b", r"\bdifference\b", r"\bversus\b", r"\bvs\b",
    r"\bcompare pannu\b", r"\bcontrast\b", r"\bnewer\b", r"\bolder\b",
    r"\bup to date\b", r"\bcompatibility\b",
]

FILE_EXTENSIONS_MAP = {
    "pdf": ".pdf",
    "word": ".docx",
    "docx": ".docx",
    "excel": ".xlsx",
    "xlsx": ".xlsx",
    "csv": ".csv",
    "python": ".py",
    "code": ".py",
    "text": ".txt",
    "markdown": ".md",
    "json": ".json",
}


class SearchQueryPlanner:
    """Classifies user search intent, plans execution mode, and expands keywords."""

    @classmethod
    def plan_query(cls, query: str, explicit_mode: str | None = None) -> SearchIntent:
        """Plans query and extracts intent (alias for classify_search_intent)."""
        return cls.classify_search_intent(query, explicit_mode)

    @classmethod
    def classify_search_intent(cls, query: str, explicit_mode: str | None = None) -> SearchIntent:
        """Determines the optimal search strategy (LOCAL, WEB, HYBRID, AUTO) and filters."""
        raw = query.strip()
        lower = raw.lower()

        # Language detection heuristic
        is_tamil_tanglish = bool(
            re.search(r"[\u0B80-\u0BFF]", raw)
            or re.search(r"\b(ennoda|enoda|irukku|pannu|kandupidi|vendaam|inga|mattum)\b", lower)
        )
        language = "ta-IN" if is_tamil_tanglish else "en"

        # Explicit mode override
        if explicit_mode:
            em = str(explicit_mode).lower().strip()
            if em in ("local", "local_only"):
                forced_mode = SearchMode.LOCAL_ONLY
            elif em in ("web", "web_only", "online", "internet"):
                forced_mode = SearchMode.WEB_ONLY
            elif em in ("hybrid", "both", "compare"):
                forced_mode = SearchMode.HYBRID
            else:
                forced_mode = SearchMode.AUTO
        else:
            forced_mode = SearchMode.AUTO

        # Check comparison intent
        is_comparison = any(re.search(pat, lower) for pat in COMPARISON_TRIGGERS)

        # Detect local triggers
        has_local = any(re.search(pat, lower) for pat in LOCAL_TRIGGERS)
        # Detect web triggers
        has_web = any(re.search(pat, lower) for pat in WEB_TRIGGERS)

        # Mode determination
        if forced_mode != SearchMode.AUTO:
            mode = forced_mode
        elif is_comparison or (has_local and has_web):
            mode = SearchMode.HYBRID
        elif has_local and not has_web:
            mode = SearchMode.LOCAL_ONLY
        elif has_web and not has_local:
            mode = SearchMode.WEB_ONLY
        else:
            # Default auto evaluation
            if re.search(r"\b(what is|latest|current|news|who is|weather|price)\b", lower):
                mode = SearchMode.WEB_ONLY
            elif re.search(r"\b(file|document|script|config|todo|notes)\b", lower):
                mode = SearchMode.LOCAL_ONLY
            else:
                mode = SearchMode.AUTO

        # Extract file type filters
        file_types = []
        for word, ext in FILE_EXTENSIONS_MAP.items():
            if re.search(rf"\b{word}\b", lower):
                if ext not in file_types:
                    file_types.append(ext)

        # Extract domain filters (e.g. site:python.org or "official python documentation")
        domain_filters = []
        site_match = re.search(r"site:([a-zA-Z0-9.-]+)", raw)
        if site_match:
            domain_filters.append(site_match.group(1).lower())
        elif "official python" in lower:
            domain_filters.append("docs.python.org")
        elif "official scipy" in lower:
            domain_filters.append("scipy.org")
        elif "official sympy" in lower:
            domain_filters.append("sympy.org")

        # Extract technical identifiers (preserve exact casing e.g. SymPy, SciPy, computer_intelligence_mcp)
        entity_matches = re.findall(r"\b[A-Za-z0-9_]+(?:\.[a-zA-Z0-9_]+)+\b|\b[A-Z][a-zA-Z0-9_]+\b", raw)
        entities = list(dict.fromkeys(entity_matches))

        # Time sensitivity
        time_sensitivity = "NORMAL"
        if re.search(r"\b(latest|recent|today|current|now|2025|2026)\b", lower):
            time_sensitivity = "HIGH"

        return SearchIntent(
            raw_query=raw,
            cleaned_query=raw,
            mode=mode,
            language=language,
            entities=entities,
            domain_filters=domain_filters,
            file_type_filters=file_types,
            time_sensitivity=time_sensitivity,
            is_comparison=is_comparison,
        )

    @classmethod
    def expand_query(cls, intent: SearchIntent) -> list[str]:
        """Generates search query variants for technical completeness and recall."""
        queries = [intent.cleaned_query]

        # If domain filter is present, create clean site-directed query
        if intent.domain_filters:
            dom = intent.domain_filters[0]
            clean_term = re.sub(r"site:[^\s]+", "", intent.cleaned_query).strip()
            queries.append(f"{clean_term} site:{dom}")

        # English expansion if query contains Tanglish
        if intent.language == "ta-IN":
            # Extract technical entities
            if intent.entities:
                queries.append(" ".join(intent.entities))

        return list(dict.fromkeys(queries))
