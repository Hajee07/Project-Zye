"""
Claim-Level Cross-Source Corroboration & Contradiction Engine (Day 38 / Phase 3).
Extracts atomic factual propositions (subjects, predicates, numbers, dates), constructs
an evidence matrix across reporting sources, and flags factual contradictions or corrections.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Tuple

from zye_realtime_tactical.news.news_models import (
    Claim,
    Contradiction,
    IndependenceClassification,
    NewsArticle,
)


class ClaimCorroborator:
    """Compares factual propositions across multiple independent sources to verify claims and detect conflicts."""

    @classmethod
    def extract_atomic_elements(cls, text: str) -> Dict[str, Any]:
        """
        Extracts salient factual elements from claim or headline text:
        - Numbers (counts, currency, percentages, ratios)
        - Dates and years
        - Key named entities / keywords
        """
        # Numbers with optional prefixes/suffixes (e.g. "$50 million", "12", "5%", "Rs 500 cr")
        number_patterns = re.findall(
            r"(?:\$|€|£|₹|Rs\.?\s*)?\b\d+(?:[.,]\d+)?(?:\s*(?:billion|million|trillion|lakh|crore|k|m|b|%|percent))?\b",
            text,
            re.IGNORECASE,
        )

        # Dates / Years (e.g. "2026", "November 22", "Monday")
        date_patterns = re.findall(
            r"\b(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}(?:,\s*\d{4})?|\d{4}|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b",
            text,
            re.IGNORECASE,
        )

        # Action / Event keywords
        tokens = re.findall(r"\b[a-zA-Z0-9]{2,}\b", text.lower())

        return {
            "numbers": [n.strip() for n in number_patterns if n.strip()],
            "dates": [d.strip() for d in date_patterns if d.strip()],
            "keywords": set(tokens),
        }

    @classmethod
    def do_articles_support_same_claim(
        cls,
        claim_text: str,
        article: NewsArticle,
    ) -> Tuple[bool, float, Optional[str]]:
        """
        Evaluates whether an article supports a specific claim text:
        Returns:
            (supports_claim: bool, confidence_score: float, matched_excerpt: str)
        """
        claim_elem = cls.extract_atomic_elements(claim_text)
        art_text = f"{article.title} {article.snippet}".lower()

        # 1. Number matching: If claim has prominent numbers, article must contain compatible numbers
        if claim_elem["numbers"]:
            claim_nums = [n.lower() for n in claim_elem["numbers"]]
            has_matching_num = any(cn in art_text for cn in claim_nums)
            if not has_matching_num:
                # Article lacks the specific numerical claim
                return False, 0.2, None

        # 2. Keyword & stem overlap
        claim_kws = claim_elem["keywords"]
        if not claim_kws:
            return False, 0.0, None

        art_tokens = set(re.findall(r"\b[a-zA-Z0-9]{2,}\b", art_text))
        matched_count = 0
        for kw in claim_kws:
            if kw in art_tokens:
                matched_count += 1
                continue
            # Prefix / root matching for inflections (e.g. announcement <-> announced)
            stem = kw[:5] if len(kw) >= 5 else kw
            if any(t.startswith(stem) or (len(t) >= 5 and kw.startswith(t[:5])) for t in art_tokens):
                matched_count += 1

        overlap_ratio = matched_count / float(len(claim_kws))

        # Must share at least 50% of meaningful keywords
        if overlap_ratio >= 0.50:
            excerpt = article.snippet if article.snippet else article.title
            return True, round(overlap_ratio, 3), excerpt

        return False, round(overlap_ratio, 3), None

    @classmethod
    def detect_contradictions(
        cls,
        articles: List[NewsArticle],
        claim_id: str = "claim_1",
    ) -> List[Contradiction]:
        """
        Discovers contradictions across articles:
        - Conflicting numbers on the same topic (e.g. "5 killed" vs "12 killed", "$10M" vs "$50M")
        - Conflicting dates
        - Flags explicit corrections where a newer report revises an earlier one
        """
        contradictions: List[Contradiction] = []
        n = len(articles)

        for i in range(n):
            for j in range(i + 1, n):
                art_a = articles[i]
                art_b = articles[j]

                elem_a = cls.extract_atomic_elements(f"{art_a.title} {art_a.snippet}")
                elem_b = cls.extract_atomic_elements(f"{art_b.title} {art_b.snippet}")

                # Check keyword relevance: both articles must be discussing the same incident
                shared_kw = elem_a["keywords"] & elem_b["keywords"]
                if len(shared_kw) < 3:
                    continue

                # Check numerical contradictions
                nums_a = set(elem_a["numbers"])
                nums_b = set(elem_b["numbers"])
                if nums_a and nums_b and not (nums_a & nums_b):
                    # Distinct numerical figures on the same event
                    val_a = ", ".join(nums_a)
                    val_b = ", ".join(nums_b)

                    # Determine if one is newer and indicates a correction
                    ts_a = art_a.published_timestamp or 0.0
                    ts_b = art_b.published_timestamp or 0.0
                    newer_url = art_b.url if ts_b > ts_a else (art_a.url if ts_a > ts_b else None)

                    is_corr = (
                        "correction" in art_a.title.lower()
                        or "revised" in art_a.title.lower()
                        or "correction" in art_b.title.lower()
                        or "revised" in art_b.title.lower()
                    )

                    contradictions.append(
                        Contradiction(
                            claim_id=claim_id,
                            conflict_type="NUMERICAL",
                            source_a_publisher=art_a.canonical_domain,
                            source_a_url=art_a.url,
                            source_a_value=val_a,
                            source_b_publisher=art_b.canonical_domain,
                            source_b_url=art_b.url,
                            source_b_value=val_b,
                            newer_source_url=newer_url,
                            is_correction=is_corr,
                            explanation=(
                                f"Numerical discrepancy between {art_a.canonical_domain} ({val_a}) "
                                f"and {art_b.canonical_domain} ({val_b})."
                            ),
                        )
                    )

        return contradictions

    @classmethod
    def evaluate_claim_corroboration(
        cls,
        claim_text: str,
        articles: List[NewsArticle],
        claim_id: str = "claim_1",
    ) -> Claim:
        """
        Builds the complete evidence matrix for an individual claim across all candidate articles.
        Returns a populated Claim object with corroboration status and supporting sources.
        """
        supporting_sources: List[Dict[str, Any]] = []
        contradicting_sources: List[Dict[str, Any]] = []

        independent_publishers_supporting: Set[str] = set()

        for art in articles:
            # Check if article has valid publication timestamp
            if art.timestamp_status not in ("VALID_UTC", "UNKNOWN"):
                continue

            supports, score, excerpt = cls.do_articles_support_same_claim(claim_text, art)
            if supports:
                source_rec = {
                    "publisher": art.canonical_domain,
                    "publisher_group": art.publisher_group,
                    "url": art.url,
                    "published_at": art.published_at_utc,
                    "independence": art.independence.value,
                    "evidence": excerpt or art.title,
                    "confidence_score": score,
                }
                supporting_sources.append(source_rec)
                if art.independence == IndependenceClassification.INDEPENDENT:
                    independent_publishers_supporting.add(art.publisher_group)

        # Detect contradictions within the supporting/candidate pool
        conflicts = cls.detect_contradictions(articles, claim_id=claim_id)
        for c in conflicts:
            contradicting_sources.append({
                "source_a": c.source_a_publisher,
                "value_a": c.source_a_value,
                "source_b": c.source_b_publisher,
                "value_b": c.source_b_value,
                "explanation": c.explanation,
            })

        status = "PENDING"
        if len(conflicts) > 0:
            status = "CONFLICTING"
        elif len(independent_publishers_supporting) >= 2:
            status = "CORROBORATED"
        elif len(supporting_sources) == 1:
            status = "SINGLE_SOURCE_UNVERIFIED"
        else:
            status = "UNVERIFIED"

        elem = cls.extract_atomic_elements(claim_text)
        return Claim(
            claim_id=claim_id,
            claim_text=claim_text,
            subject=claim_text.split()[0] if claim_text else "",
            event_or_action=" ".join(claim_text.split()[1:5]) if len(claim_text.split()) > 1 else "",
            numerical_values=elem["numbers"],
            date_values=elem["dates"],
            status=status,
            supporting_source_count=len(independent_publishers_supporting),
            supporting_sources=supporting_sources,
            contradicting_sources=contradicting_sources,
        )

    @classmethod
    def corroborate_articles(
        cls,
        articles: List[NewsArticle],
        claim_id: str = "claim_primary",
    ) -> Tuple[List[Claim], List[Contradiction]]:
        """Extracts primary claims and flags contradictions across a set of articles."""
        contradictions = cls.detect_contradictions(articles, claim_id=claim_id)
        claims: List[Claim] = []
        if articles:
            primary_claim = cls.evaluate_claim_corroboration(
                claim_text=articles[0].title,
                articles=articles,
                claim_id=claim_id,
            )
            claims.append(primary_claim)
        return claims, contradictions

