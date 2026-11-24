"""
Syndication & Duplicate Article Detection Engine (Day 38 / Phase 3).
Identifies wire-service attribution, identical headline fingerprints, syndicated republishing,
and pairwise source independence using deterministic text normalization.
"""

from __future__ import annotations

import hashlib
import re
from typing import List, Optional, Set, Tuple

from zye_realtime_tactical.news.news_models import (
    IndependenceClassification,
    NewsArticle,
    SourceIndependenceResult,
)
from zye_realtime_tactical.news.publisher_registry import PublisherRegistry


# Explicit wire-service attribution patterns in headline or snippet
WIRE_PATTERNS = [
    re.compile(r"(?:\(|\b)(reuters|ap|afp|pti|bloomberg|ani|upi)(?:\)|\b)", re.IGNORECASE),
    re.compile(r"\bvia\s+(reuters|associated press|ap|pti|afp|bloomberg)\b", re.IGNORECASE),
    re.compile(r"\b(pr\s*newswire|business\s*wire|globe\s*newswire)\b", re.IGNORECASE),
    re.compile(r"\bby\s+(reuters|associated press|pti|afp)\b", re.IGNORECASE),
    re.compile(r"\breported\s+by\s+(reuters|ap|afp|pti|bloomberg)\b", re.IGNORECASE),
    re.compile(r"\b(reuters|associated press|pti)\s+reports\b", re.IGNORECASE),
]

# Stop words for headline fingerprinting
STOP_WORDS: Set[str] = {
    "a", "an", "the", "in", "on", "at", "by", "for", "with", "about",
    "against", "between", "into", "through", "during", "before", "after",
    "above", "below", "to", "from", "up", "down", "is", "are", "was",
    "were", "be", "been", "being", "have", "has", "had", "do", "does",
    "did", "but", "if", "or", "because", "as", "until", "while", "of",
    "and", "it", "its", "that", "this", "these", "those",
}


class SyndicationDetector:
    """Detects wire attribution, republished syndicated copies, and evaluates publisher independence."""

    def __init__(self, registry: Optional[PublisherRegistry] = None) -> None:
        self.registry = registry or PublisherRegistry.get_instance()

    @classmethod
    def detect_wire_attribution(cls, text: str) -> Optional[str]:
        """Extracts explicit wire service credit from headlines or lead snippets."""
        if not text:
            return None
        for pattern in WIRE_PATTERNS:
            match = pattern.search(text)
            if match:
                raw_wire = match.group(1) if match.groups() else match.group(0)
                clean_wire = raw_wire.strip("() ").lower()
                return PublisherRegistry.get_wire_service_name(clean_wire) or clean_wire.upper()
        return None

    @classmethod
    def compute_text_fingerprint(cls, text: str) -> str:
        """
        Generates a deterministic SHA-256 fingerprint from normalized alphanumeric tokens.
        Strips punctuation, stop words, and whitespace variations.
        """
        if not text:
            return ""
        tokens = re.findall(r"\b[a-zA-Z0-9]+\b", text.lower())
        meaningful = [t for t in tokens if t not in STOP_WORDS and len(t) > 1]
        normalized_str = " ".join(sorted(meaningful))
        return hashlib.sha256(normalized_str.encode("utf-8")).hexdigest()[:16]

    @classmethod
    def compute_jaccard_similarity(cls, text_a: str, text_b: str, shingle_size: int = 3) -> float:
        """
        Calculates Jaccard overlap on token n-gram shingles.
        Values > 0.60 generally indicate syndicated rewrites or duplicate content.
        """
        tokens_a = re.findall(r"\b[a-zA-Z0-9]+\b", text_a.lower())
        tokens_b = re.findall(r"\b[a-zA-Z0-9]+\b", text_b.lower())

        if len(tokens_a) < shingle_size or len(tokens_b) < shingle_size:
            # Fall back to unigram token set overlap
            set_a = set(tokens_a)
            set_b = set(tokens_b)
            if not set_a or not set_b:
                return 0.0
            return len(set_a & set_b) / float(len(set_a | set_b))

        shingles_a = {" ".join(tokens_a[i : i + shingle_size]) for i in range(len(tokens_a) - shingle_size + 1)}
        shingles_b = {" ".join(tokens_b[i : i + shingle_size]) for i in range(len(tokens_b) - shingle_size + 1)}

        intersection = len(shingles_a & shingles_b)
        union = len(shingles_a | shingles_b)
        return (intersection / float(union)) if union > 0 else 0.0

    def classify_source_pair(self, article_a: NewsArticle, article_b: NewsArticle) -> IndependenceClassification:
        """
        Evaluates the relationship between two specific articles.
        Returns exact classification: INDEPENDENT, SAME_PUBLISHER, SAME_OWNERSHIP_GROUP, SYNDICATED, DUPLICATE.
        """
        # 1. Exact Canonical URL match -> DUPLICATE
        if article_a.canonical_url == article_b.canonical_url:
            return IndependenceClassification.DUPLICATE

        # 2. Same Canonical Domain -> SAME_PUBLISHER
        if article_a.canonical_domain == article_b.canonical_domain:
            return IndependenceClassification.SAME_PUBLISHER

        # 3. Same Corporate Ownership Group -> SAME_OWNERSHIP_GROUP
        if self.registry.are_publishers_affiliated(article_a.publisher_group, article_b.publisher_group):
            return IndependenceClassification.SAME_OWNERSHIP_GROUP

        # 4. Wire Attribution Shared -> SYNDICATED
        wire_a = article_a.wire_attribution or self.detect_wire_attribution(f"{article_a.title} {article_a.snippet}")
        wire_b = article_b.wire_attribution or self.detect_wire_attribution(f"{article_b.title} {article_b.snippet}")

        # If both articles cite the same wire agency (e.g. both cite Reuters or AP)
        if wire_a and wire_b and wire_a.lower() == wire_b.lower():
            return IndependenceClassification.SYNDICATED

        # If one outlet is the primary wire agency and the other cites it
        if (
            (article_a.publisher_group == f"WIRE_{wire_b}" if wire_b else False)
            or (article_b.publisher_group == f"WIRE_{wire_a}" if wire_a else False)
        ):
            return IndependenceClassification.SYNDICATED

        # 5. Text Fingerprint or Snippet Similarity Match -> SYNDICATED or DUPLICATE
        if article_a.fingerprint and article_b.fingerprint and article_a.fingerprint == article_b.fingerprint:
            return IndependenceClassification.SYNDICATED

        combined_a = f"{article_a.title} {article_a.snippet}"
        combined_b = f"{article_b.title} {article_b.snippet}"
        sim = self.compute_jaccard_similarity(combined_a, combined_b)
        if sim >= 0.65:
            return IndependenceClassification.SYNDICATED

        # 6. Distinct publishers with no shared provenance -> INDEPENDENT
        return IndependenceClassification.INDEPENDENT

    def analyze_source_set_independence(self, articles: List[NewsArticle]) -> SourceIndependenceResult:
        """
        Analyzes an entire set of retrieved articles, identifies duplicates, syndications,
        and determines the count of genuinely independent publishers.
        """
        total = len(articles)
        if total == 0:
            return SourceIndependenceResult(
                total_sources_evaluated=0,
                independent_publisher_count=0,
                explanation="No articles provided for evaluation.",
            )

        publishers_seen: Set[str] = set()
        independent_articles: List[NewsArticle] = []
        syndicated_records: List[dict] = []
        duplicate_records: List[dict] = []

        for i, art_curr in enumerate(articles):
            is_independent = True
            relation_reason = "Unique initial publisher"

            for art_prev in independent_articles:
                rel = self.classify_source_pair(art_prev, art_curr)
                if rel in (
                    IndependenceClassification.DUPLICATE,
                    IndependenceClassification.SAME_PUBLISHER,
                    IndependenceClassification.SAME_OWNERSHIP_GROUP,
                    IndependenceClassification.SYNDICATED,
                ):
                    is_independent = False
                    art_curr.independence = rel
                    relation_reason = f"Shares reporting origin with {art_prev.canonical_domain} ({rel.value})"

                    if rel == IndependenceClassification.DUPLICATE:
                        duplicate_records.append({
                            "original_url": art_prev.url,
                            "duplicate_url": art_curr.url,
                            "publisher": art_curr.canonical_domain,
                        })
                    else:
                        syndicated_records.append({
                            "primary_source": art_prev.canonical_domain,
                            "syndicated_source": art_curr.canonical_domain,
                            "classification": rel.value,
                            "title": art_curr.title,
                        })
                    break

            if is_independent:
                art_curr.independence = IndependenceClassification.INDEPENDENT
                independent_articles.append(art_curr)
                publishers_seen.add(art_curr.publisher_group)

        independent_count = len(independent_articles)
        explanation = (
            f"Evaluated {total} sources. Found {independent_count} genuinely independent publishers "
            f"({len(duplicate_records)} duplicate URLs, {len(syndicated_records)} syndicated/affiliated reports)."
        )

        return SourceIndependenceResult(
            total_sources_evaluated=total,
            independent_publisher_count=independent_count,
            publishers_identified=[
                {"domain": a.canonical_domain, "group": a.publisher_group, "url": a.url}
                for a in independent_articles
            ],
            syndication_detected=len(syndicated_records) > 0,
            syndication_details=syndicated_records,
            duplicates_detected=len(duplicate_records) > 0,
            duplicate_details=duplicate_records,
            independence_summary={
                a.url: a.independence.value for a in articles
            },
            explanation=explanation,
        )

    # Convenient alias
    analyze_sources = analyze_source_set_independence
